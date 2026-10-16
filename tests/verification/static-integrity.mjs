/**
 * tests/verification/static-integrity.mjs —— A. 静态完整性（独立验证）
 *
 * A1 node --check：lib/index.js、lib/rcio.js、lib/client.js
 * A2 lib/client.js bundle 外壳：首行 window.__ModuleLoader__.load({、id === package.json name、
 *    无第三方裸包 import/require（只允许 require("react") / require("react-dom") 与 require("@deepseek-ai/…")）、无 ESM 语句
 *    —— `react-dom` 与 `react` 同属平台共享模块图的内置包（多个官方客户端包都直接 require("react-dom")）；
 *       2026-10-15 经 Lead 裁定加入允许清单，用途：把交互模态 Portal 到 document.body，
 *       从而不受工具卡片折叠/裁切影响（实测过"卡片未展开 → 模态不挂载"的故障）。
 * A3 package.json：dsh.bundle.patch / dsh.client.platform / dsh.client.inject / exports["./client"].default / main
 *
 * 运行：<node> tests/verification/static-integrity.mjs [--json <path>]
 * 说明：⚠️ 按 Lead 的更正，**不断言**客户端导出必须有 name（真实第三方客户端也没有）。
 */

import { readFileSync, existsSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { createReport, runCapture, LIB, PLUGIN, NODE, show } from './harness.mjs';

const r = createReport('static-integrity');
const readText = (file) => readFileSync(file, 'utf8');
const sha256 = (file) => createHash('sha256').update(readFileSync(file)).digest('hex').toUpperCase();

/** 把注释换成空格（保留字符串字面量内容），用于静态扫描。 */
function stripComments(source) {
  let out = '';
  let i = 0;
  let state = 'code';
  while (i < source.length) {
    const c = source[i];
    const n = source[i + 1];
    if (state === 'code') {
      if (c === '/' && n === '/') { state = 'line'; out += '  '; i += 2; continue; }
      if (c === '/' && n === '*') { state = 'block'; out += '  '; i += 2; continue; }
      if (c === '"') state = 'dq';
      else if (c === "'") state = 'sq';
      else if (c === '`') state = 'tpl';
      out += c; i += 1; continue;
    }
    if (state === 'line') {
      if (c === '\n') { state = 'code'; out += c; } else out += ' ';
      i += 1; continue;
    }
    if (state === 'block') {
      if (c === '*' && n === '/') { state = 'code'; out += '  '; i += 2; } else { out += c === '\n' ? '\n' : ' '; i += 1; }
      continue;
    }
    // 字符串 / 模板字面量：原样保留
    if (c === '\\') { out += c + (n ?? ''); i += 2; continue; }
    if ((state === 'dq' && c === '"') || (state === 'sq' && c === "'") || (state === 'tpl' && c === '`')) state = 'code';
    out += c; i += 1;
  }
  return out;
}

/* ───────────────────────── A1 node --check ───────────────────────── */
for (const name of ['index.js', 'rcio.js', 'client.js']) {
  const file = path.join(LIB, name);
  if (!existsSync(file)) { r.fail(`A1.node-check.${name}`, `${file} 不存在`); continue; }
  const res = runCapture(NODE, ['--check', file]);
  r.check(
    `A1.node-check.${name}`,
    res.status === 0,
    `node --check 退出码 0（${statSync(file).size} bytes）`,
    `node --check 退出码 ${res.status}${res.output ? `；输出：${res.output.trim().split('\n').slice(0, 3).join(' | ')}` : ''}`
  );
}

/* ───────────────────────── A2 client bundle 外壳 ───────────────────────── */
const pkgPath = path.join(PLUGIN, 'package.json');
const pkg = JSON.parse(readText(pkgPath));
const clientPath = path.join(LIB, 'client.js');
if (!existsSync(clientPath)) r.fatal('lib/client.js 不存在');

const clientSource = readText(clientPath).replace(/^\uFEFF/u, '');
const clientCode = stripComments(clientSource);
const firstLine = clientSource.split(/\r?\n/u)[0];

r.check(
  'A2.shell.firstLine',
  /^window\.__ModuleLoader__\.load\(\{/u.test(firstLine),
  `首行 = ${show(firstLine)}（sha256=${sha256(clientPath)}）`,
  `首行不匹配 window.__ModuleLoader__.load({：${show(firstLine)}`
);
r.info(`client.js 首行也可写成无 window. 前缀的 _ModuleLoader__.load({ —— 本文件用的是 window. 形式`);

const idMatch = /__ModuleLoader__[\s\S]{0,200}?\bid\s*:\s*["']([^"']+)["']/u.exec(clientCode);
const bundleId = idMatch === null ? null : idMatch[1];
r.check(
  'A2.shell.id',
  bundleId === pkg.name,
  `bundle id = ${show(bundleId)} === package.json name ${show(pkg.name)}`,
  `bundle id = ${show(bundleId)} ≠ package.json name ${show(pkg.name)}`
);

const requires = [...clientCode.matchAll(/\brequire\s*\(\s*["']([^"']+)["']\s*\)/gu)].map((m) => m[1]);
const allowRequire = (id) => id === 'react' || id === 'react-dom' || id === 'react/jsx-runtime' || id.startsWith('@deepseek-ai/') || id.startsWith('./') || id.startsWith('../');
const badRequires = [...new Set(requires)].filter((id) => !allowRequire(id));
r.info(`bundle 内的 require("…") 字面量：${requires.length === 0 ? '（无）' : show([...new Set(requires)])}`);
r.check(
  'A2.noThirdPartyRequire',
  badRequires.length === 0,
  `无第三方裸包 require（允许 react / react-dom / @deepseek-ai/*）；实际字面量 ${show([...new Set(requires)])}`,
  `发现不允许的 require 目标：${show(badRequires)}`
);

const nonLiteralRequires = [...clientCode.matchAll(/\brequire\s*\((?!\s*["'])/gu)].length;
r.check(
  'A2.requireLiteralOnly',
  nonLiteralRequires === 0,
  'require() 全部是字符串字面量',
  `有 ${nonLiteralRequires} 处 require() 不是字面量`
);

const dynamicImport = [...clientCode.matchAll(/\bimport\s*\(/gu)].length;
const staticImport = [...clientCode.matchAll(/(?:^|[;{}\n])\s*import\s+[\w$*{]/gu)].length;
const exportStmt = [...clientCode.matchAll(/(?:^|[;{}\n])\s*export\s+(?:default|const|let|var|function|class|\{)/gu)].length;
r.check(
  'A2.noEsmSyntax',
  dynamicImport === 0 && staticImport === 0 && exportStmt === 0,
  '无 import( / import x / export 语句（纯脚本 bundle）',
  `发现 ESM 语法：dynamicImport=${dynamicImport} staticImport=${staticImport} exportStmt=${exportStmt}`
);

// 客户端导出形态：真实第三方客户端只有 apply + inject（没有 name）——这里只记录，不当作 FAIL。
const exportsAssign = [...clientCode.matchAll(/exports\.([A-Za-z_$][\w$]*)\s*=/gu)].map((m) => m[1]);
r.info(`bundle 里 exports.* 赋值：${show([...new Set(exportsAssign)])}`);

/* ───────────────────────── A3 package.json ───────────────────────── */
const patchRel = pkg?.dsh?.bundle?.patch;
const patchOk = typeof patchRel === 'string' && existsSync(path.join(PLUGIN, patchRel));
r.check('A3.bundlePatch', patchOk, `dsh.bundle.patch = ${show(patchRel)} 指向的文件存在`, `dsh.bundle.patch = ${show(patchRel)} 指向的文件不存在`);

r.check(
  'A3.clientPlatform',
  pkg?.dsh?.client?.platform === 'web',
  `dsh.client.platform = ${show(pkg?.dsh?.client?.platform)}（必须是 "web"）`,
  `dsh.client.platform = ${show(pkg?.dsh?.client?.platform)} ≠ "web"`
);

const inject = pkg?.dsh?.client?.inject;
r.check(
  'A3.clientInject',
  Array.isArray(inject) && inject.includes('@deepseek-ai/dsh-client-ui-tool'),
  `dsh.client.inject = ${show(inject)} 含 "@deepseek-ai/dsh-client-ui-tool"`,
  `dsh.client.inject = ${show(inject)} 不含 "@deepseek-ai/dsh-client-ui-tool"`
);

const clientExport = pkg?.exports?.['./client'];
const clientRel = typeof clientExport === 'string' ? clientExport : clientExport?.default;
const clientExportOk = typeof clientRel === 'string' && existsSync(path.join(PLUGIN, clientRel));
r.check('A3.exportsClient', clientExportOk, `exports["./client"].default = ${show(clientRel)} 指向的文件存在`, `exports["./client"].default = ${show(clientRel)} 指向的文件不存在`);

const mainOk = typeof pkg.main === 'string' && existsSync(path.join(PLUGIN, pkg.main));
r.check('A3.main', mainOk, `main = ${show(pkg.main)} 指向的文件存在`, `main = ${show(pkg.main)} 指向的文件不存在`);

r.info(`冻结哈希：client.js=${sha256(clientPath)}；index.js=${sha256(path.join(LIB, 'index.js'))}；rcio.js=${sha256(path.join(LIB, 'rcio.js'))}`);
r.finish();
