/**
 * tests/verification/run-all.mjs —— 独立验证入口：一次跑完 A–E
 *
 * 依次运行（每个都是独立进程；子进程输出用文件描述符重定向捕获 —— 本机沙箱下
 * Node 的 child_process 默认 'pipe' 会 EPERM）：
 *   A  static-integrity.mjs（node --check / bundle 外壳 / package.json）
 *   A4 cordis-patch-assert.mjs（≤30 行、零依赖的 cordis.patch.yml 断言）
 *   B  rcio-cases.mjs（§4 口径、§1 示例、flag 规则、反例、函数签名）
 *   B6 client-rcio-parity.mjs（独立实现的 Host/Client 口径等价 + BUG1 回归 + client wire 形态 + 作者脚本退出码）
 *   C  host-http-roundtrip.mjs（真 HTTP 往返：open/poll/submit/skip/并发/405/404/400/超时/取消）
 *   D  skill-text.mjs（步骤顺序 / §0 条目连续且无「铁律 N」自引用 / 三条新口径 / 120 文件 / frontmatter / JSON 示例一致）
 *   E  skill-diff-audit.mjs（镜像一致性：原目录 vs 插件内 skill 逐字节相同 / 原目录基线未漂移 / 冻结指纹）
 *
 * 有 FAIL 则退出码非 0。汇总写到 `_probe/verify/run-all-summary.json`。
 *
 * 运行：<node> plugins/csl2-city-advisor/tests/verification/run-all.mjs
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { runCapture, HERE, LIB, PLUGIN, VERIFY_DIR, NODE } from './harness.mjs';

const SCRIPTS = [
  { id: 'A1-A3', file: 'static-integrity.mjs', note: '静态完整性（node --check / bundle 外壳 / package.json）' },
  { id: 'A4', file: 'cordis-patch-assert.mjs', note: 'cordis.patch.yml（≤30 行零依赖断言）' },
  { id: 'B5', file: 'rcio-cases.mjs', note: 'lib/rcio.js 口径（§4 表 / §1 示例 / flags / 反例）' },
  { id: 'B6', file: 'client-rcio-parity.mjs', note: 'Host/Client 口径等价 + BUG1 回归 + client wire + 作者脚本退出码' },
  { id: 'C', file: 'host-http-roundtrip.mjs', note: 'Host 工具可加载性（真 HTTP 往返 + 超时/取消）' },
  { id: 'D', file: 'skill-text.mjs', note: 'Skill 文本' },
  { id: 'E', file: 'skill-diff-audit.mjs', note: '与原 skill 目录差异审计 + 冻结指纹' }
];

const sha256Of = (file) => (existsSync(file) ? createHash('sha256').update(readFileSync(file)).digest('hex').toUpperCase() : '(缺失)');

mkdirSync(VERIFY_DIR, { recursive: true });
const jsonDir = path.join(VERIFY_DIR, 'run-all-json');
mkdirSync(jsonDir, { recursive: true });

console.log('='.repeat(100));
console.log('csl2-city-advisor 独立验证 run-all');
console.log(`node = ${NODE}（${process.version}）`);
console.log(`plugin = ${PLUGIN}`);
console.log('验证时的冻结哈希（本进程实测）：');
for (const rel of ['lib/client.js', 'lib/index.js', 'lib/rcio.js', 'package.json', 'cordis.patch.yml', 'CONTRACT.md']) {
  console.log(`  ${sha256Of(path.join(PLUGIN, rel))}  ${rel}`);
}
console.log('='.repeat(100));

const results = [];
let totalPass = 0;
let totalFail = 0;
let totalUnverified = 0;

for (const script of SCRIPTS) {
  const scriptPath = path.join(HERE, script.file);
  const jsonPath = path.join(jsonDir, `${script.id.replace(/[^\w.-]/gu, '_')}.json`);
  console.log('');
  console.log(`──────────────────────── ${script.id} · ${script.file} ────────────────────────`);
  console.log(`# ${script.note}`);
  const started = Date.now();
  const run = runCapture(NODE, [scriptPath, '--json', jsonPath], { timeout: 900000 });
  const elapsed = ((Date.now() - started) / 1000).toFixed(1);
  process.stdout.write(run.output);
  if (run.error) console.log(`子进程错误：${run.error}`);
  console.log(`[${script.id}] 退出码 ${run.status}（${elapsed}s）`);

  let summary = null;
  if (existsSync(jsonPath)) {
    try { summary = JSON.parse(readFileSync(jsonPath, 'utf8')); } catch { summary = null; }
  }
  if (summary === null) {
    // 没有 --json 输出的脚本（A4 的 ≤30 行断言脚本）按其退出码折算 1 个结论。
    summary = { pass: run.status === 0 ? 1 : 0, fail: run.status === 0 ? 0 : 1, unverified: 0, items: [{ id: `${script.id}.exitcode`, status: run.status === 0 ? 'PASS' : 'FAIL', detail: `退出码 ${run.status}（该脚本不产出 --json 汇总）` }] };
  }
  results.push({ ...script, exitCode: run.status, elapsedSec: Number(elapsed), pass: summary.pass ?? 0, fail: summary.fail ?? 0, unverified: summary.unverified ?? 0, items: summary.items ?? [] });
  totalPass += summary.pass ?? 0;
  totalFail += summary.fail ?? 0;
  totalUnverified += summary.unverified ?? 0;
}

console.log('');
console.log('='.repeat(100));
console.log('汇总');
console.log('='.repeat(100));
for (const item of results) {
  console.log(`${String(item.exitCode).padStart(3)} | PASS ${String(item.pass).padStart(3)} FAIL ${String(item.fail).padStart(2)} UNVERIFIED ${String(item.unverified).padStart(2)} | ${item.id.padEnd(6)} ${item.file}`);
}
const allFailures = results.flatMap((item) => item.items.filter((entry) => entry.status === 'FAIL').map((entry) => `${item.id} ${entry.id} :: ${entry.detail}`));
const allUnverified = results.flatMap((item) => item.items.filter((entry) => entry.status === 'UNVERIFIED').map((entry) => `${item.id} ${entry.id} :: ${entry.detail}`));
if (allFailures.length > 0) {
  console.log('');
  console.log(`FAIL 明细（${allFailures.length}）：`);
  for (const line of allFailures) console.log(`  - ${line}`);
}
if (allUnverified.length > 0) {
  console.log('');
  console.log(`UNVERIFIED 明细（${allUnverified.length}）：`);
  for (const line of allUnverified) console.log(`  - ${line}`);
}
console.log('');
console.log(`TOTAL: PASS=${totalPass} FAIL=${totalFail} UNVERIFIED=${totalUnverified}`);
console.log(`验证时 lib/client.js sha256 = ${sha256Of(path.join(LIB, 'client.js'))}`);
console.log(`验证时 lib/index.js  sha256 = ${sha256Of(path.join(LIB, 'index.js'))}`);

writeFileSync(path.join(VERIFY_DIR, 'run-all-summary.json'), JSON.stringify({
  ranAt: new Date().toISOString(),
  node: process.version,
  pluginRoot: PLUGIN,
  hashes: {
    'lib/client.js': sha256Of(path.join(LIB, 'client.js')),
    'lib/index.js': sha256Of(path.join(LIB, 'index.js')),
    'lib/rcio.js': sha256Of(path.join(LIB, 'rcio.js')),
    'package.json': sha256Of(path.join(PLUGIN, 'package.json')),
    'cordis.patch.yml': sha256Of(path.join(PLUGIN, 'cordis.patch.yml')),
    'CONTRACT.md': sha256Of(path.join(PLUGIN, 'CONTRACT.md'))
  },
  totalPass,
  totalFail,
  totalUnverified,
  results
}, null, 2), 'utf8');

process.exit(totalFail === 0 && results.every((item) => item.exitCode === 0) ? 0 : 1);
