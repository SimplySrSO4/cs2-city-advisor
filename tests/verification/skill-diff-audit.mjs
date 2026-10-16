/**
 * tests/verification/skill-diff-audit.mjs —— E. skill 镜像一致性 + 冻结指纹审计
 *
 * ⭐ 2026-10-15 起：工作区 `skill/cities-skylines-2-city-advisor` 已**同步为插件内 skill 的镜像**
 *    （用户明确要求），因此本文件从"差异审计"改为**一致性审计**：
 *
 * E14 把工作区原目录 `skill/cities-skylines-2-city-advisor` 全部文件的 mtime+sha256 记录到
 *     `_probe/verify/original-skill-hashes.json`；之后每次运行都与该基线比对，**任何差异都是 FAIL**
 *     （作用：闸住"镜像被误改"）
 * E15 逐文件比对原目录与 `plugins/csl2-city-advisor/skills/cities-skylines-2-city-advisor`：
 *     **两边必须完全一致**（无内容不同 / 无缺失 / 无多余）；`__pycache__` 与 `*.pyc` 不进快照
 * E16 冻结指纹核对（sha256 + bytes 为准；行数只作参考，不用于判 FAIL）
 *
 * 运行：<node> tests/verification/skill-diff-audit.mjs [--json <path>]
 */

import { readdirSync, readFileSync, writeFileSync, statSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { createReport, SKILL_PLUGIN, SKILL_ORIGINAL, VERIFY_DIR, show } from './harness.mjs';

const r = createReport('skill-diff-audit');
const BASELINE = path.join(VERIFY_DIR, 'original-skill-hashes.json');

/** 递归列出相对路径（用 '/' 分隔，跨平台一致）。 */
function walk(root) {
  const out = [];
  const stack = [''];
  while (stack.length > 0) {
    const rel = stack.pop();
    const abs = rel === '' ? root : path.join(root, rel);
    for (const entry of readdirSync(abs, { withFileTypes: true })) {
      const childRel = rel === '' ? entry.name : `${rel}/${entry.name}`;
      if (entry.isDirectory()) stack.push(childRel);
      else if (entry.isFile()) out.push(childRel);
    }
  }
  return out.sort();
}

function snapshot(root) {
  const files = {};
  let totalBytes = 0;
  let maxMtimeMs = 0;
  for (const rel of walk(root)) {
    // ⚠️ `__pycache__` / `*.pyc` 是跑脚本时生成的缓存，不是 skill 内容 —— 不进快照
    if (rel.includes('__pycache__') || rel.endsWith('.pyc')) continue;
    const abs = path.join(root, rel);
    const stat = statSync(abs);
    const hash = createHash('sha256').update(readFileSync(abs)).digest('hex').toUpperCase();
    files[rel] = { bytes: stat.size, sha256: hash, mtimeMs: Math.round(stat.mtimeMs) };
    totalBytes += stat.size;
    if (stat.mtimeMs > maxMtimeMs) maxMtimeMs = stat.mtimeMs;
  }
  return { files, count: Object.keys(files).length, totalBytes, maxMtimeMs };
}

const newlineCount = (abs) => (readFileSync(abs, 'utf8').match(/\n/gu) ?? []).length;

/* ═════════════════════ E14 原目录零改动 ═════════════════════ */

if (!existsSync(SKILL_ORIGINAL)) r.fatal(`原目录不存在：${SKILL_ORIGINAL}`);
const original = snapshot(SKILL_ORIGINAL);
r.info(`原目录：${SKILL_ORIGINAL}`);
r.info(`原目录快照：${original.count} 个文件，${original.totalBytes} bytes，最新 mtime = ${new Date(original.maxMtimeMs).toISOString()}`);

if (!existsSync(BASELINE)) {
  writeFileSync(BASELINE, JSON.stringify({
    root: SKILL_ORIGINAL,
    capturedAt: new Date().toISOString(),
    capturedBy: 'tests/verification/skill-diff-audit.mjs',
    note: '基线：之后每次运行都与本文件比对；任何 sha256/bytes/mtime 差异都判 FAIL。',
    count: original.count,
    totalBytes: original.totalBytes,
    maxMtimeMs: original.maxMtimeMs,
    files: original.files
  }, null, 2), 'utf8');
  r.check('E14.baselineCreated', true, `基线已写入 ${BASELINE}（${original.count} 个文件）；本次为首次快照，尚未有历史差异可比`);
} else {
  const baseline = JSON.parse(readFileSync(BASELINE, 'utf8'));
  const baseFiles = baseline.files ?? {};
  const missing = Object.keys(baseFiles).filter((rel) => !(rel in original.files));
  const added = Object.keys(original.files).filter((rel) => !(rel in baseFiles));
  const contentChanged = [];
  const mtimeOnly = [];
  for (const rel of Object.keys(baseFiles)) {
    if (!(rel in original.files)) continue;
    const before = baseFiles[rel];
    const after = original.files[rel];
    if (before.sha256 !== after.sha256 || before.bytes !== after.bytes) contentChanged.push({ rel, before: { bytes: before.bytes, sha256: before.sha256 }, after: { bytes: after.bytes, sha256: after.sha256 } });
    else if (before.mtimeMs !== after.mtimeMs) mtimeOnly.push({ rel, before: before.mtimeMs, after: after.mtimeMs });
  }
  r.info(`基线于 ${baseline.capturedAt} 记录（${baseline.count} 个文件）；本次快照 ${original.count} 个文件`);
  r.check('E14.originalUnchanged',
    missing.length === 0 && added.length === 0 && contentChanged.length === 0 && mtimeOnly.length === 0,
    `原目录与基线逐文件一致：${original.count} 个文件的 sha256/bytes/mtime 全部未变（无新增/删除/修改）`,
    `原目录发生变化：缺失 ${show(missing)}；新增 ${show(added)}；内容变化 ${show(contentChanged)}；仅 mtime 变化 ${show(mtimeOnly)}`);
}

/* ═════════════════════ E15 原目录 vs 插件内副本 ═════════════════════ */

const plugin = snapshot(SKILL_PLUGIN);
// ⭐ 镜像口径：原目录已同步为插件内 skill 的镜像 → **不允许任何差异**
const ALLOWED_DIFFERENT = new Set([]);
// 插件内**不应**有原目录没有的文件（两边文件集必须相同）
const ALLOWED_NEW = new Set([]);

const origRels = new Set(Object.keys(original.files));
const plugRels = new Set(Object.keys(plugin.files));
const missingInPlugin = [...origRels].filter((rel) => !plugRels.has(rel));
const extraInPlugin = [...plugRels].filter((rel) => !origRels.has(rel));

const byteIdentical = [];
const allowedDiffer = [];
const unexpectedDiffer = [];
for (const rel of [...origRels].filter((value) => plugRels.has(value))) {
  const same = original.files[rel].sha256 === plugin.files[rel].sha256 && original.files[rel].bytes === plugin.files[rel].bytes;
  if (same) byteIdentical.push(rel);
  else if (ALLOWED_DIFFERENT.has(rel)) allowedDiffer.push({ rel, orig: original.files[rel].bytes, plugin: plugin.files[rel].bytes });
  else unexpectedDiffer.push({ rel, orig: { bytes: original.files[rel].bytes, sha256: original.files[rel].sha256 }, plugin: { bytes: plugin.files[rel].bytes, sha256: plugin.files[rel].sha256 } });
}

r.info(`文件总数：原目录 ${original.count}，插件内 ${plugin.count}（差 ${plugin.count - original.count}）`);
r.check('E15.noUnexpectedDifference',
  unexpectedDiffer.length === 0 && missingInPlugin.length === 0,
  `镜像一致：${byteIdentical.length} 个文件 sha256 逐字节相同（无内容不同 / 无缺失）`,
  `镜像不一致：内容不同 ${show(unexpectedDiffer)}；插件内缺失 ${show(missingInPlugin)}`);
r.check('E15.noExtraInPlugin',
  extraInPlugin.length === 0,
  '插件内没有原目录之外的文件（两边文件集相同）',
  `插件内多出文件：${show(extraInPlugin)}`);
r.check('E15.allowedSet',
  allowedDiffer.length === 0,
  `无"允许差异"文件（镜像口径：允许集为空，实际差异 ${allowedDiffer.length} 个）`,
  `仍有内容不同的文件（镜像未同步）：${show(allowedDiffer.map((item) => `${item.rel} ${item.orig}->${item.plugin}B`))}`);

/* ═════════════════════ E16 冻结指纹（sha256 + bytes 为准） ═════════════════════ */

const FROZEN = [
  { rel: 'SKILL.md', expectSha: 'AD0A2F521523C56F78DD5413607D3906DB250861E74533C8ED485D218FE9EF8E', expectBytes: 162613 },
  { rel: 'references/46-algorithm-roadmap.md', expectSha: '67851DF38D4B5164D4976AD33158CF88E8388AEBE760002196235D04EEAC71FE', expectBytes: 38731 },
  { rel: 'references/100-worked-example.md', expectSha: '4A99DC6575CEC858972BF697AFECF1F630253EE79509BE205676D75AEAC80EE2', expectBytes: 7642 },
  { rel: 'references/70-carto-data-schema.md', expectSha: '1B432290EE0658B327BC60CE95EEA9BB2AC04517838E7FDCBF328E681C5D2A08', expectBytes: 52994 },
  { rel: 'references/120-rcio-input-step.md', expectSha: 'C73D52C5B33A920DF380B38AA30E2FE73945FA0706A8FA81EB5564602532F3C1', expectBytes: 7957 }
];
const frozenBad = [];
for (const item of FROZEN) {
  const actual = plugin.files[item.rel];
  if (actual === undefined) { frozenBad.push({ rel: item.rel, reason: '文件不存在' }); continue; }
  const shaOk = actual.sha256 === item.expectSha;
  const bytesOk = actual.bytes === item.expectBytes;
  const lines = newlineCount(path.join(SKILL_PLUGIN, item.rel));
  if (!shaOk || !bytesOk) frozenBad.push({ rel: item.rel, sha256: actual.sha256, bytes: actual.bytes, lines });
  else r.info(`${item.rel}: sha256 ✓ ${actual.sha256.slice(0, 16)}…，${actual.bytes} bytes，${lines} 个 \\n`);
}
r.check('E16.fingerprints', frozenBad.length === 0,
  `5 个冻结指纹（sha256 + bytes）全部吻合`,
  `指纹不符：${show(frozenBad)}`);

r.finish();
