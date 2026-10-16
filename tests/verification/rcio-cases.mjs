/**
 * tests/verification/rcio-cases.mjs —— B5. lib/rcio.js 口径（独立验证）
 *
 * 期望值来源：`CONTRACT.md` §4 的档位表 —— **在运行时从 CONTRACT.md 文本里抽出来**，
 * 不是抄作者代码里的常量。判定逻辑（expectedLevel/expectedBand/expectedFlags）
 * 是本脚本按 §4 表另写的一份独立实现。
 *
 * 覆盖：
 *   B5.bar.*       17 个 bar 边界值（-100/-61/-60/-59/-16/-15/-14/0/14/15/16/49/50/51/79/80/100）
 *   B5.band.*      失业率 0/2.9/3/7.9/8/8.1/11.9/12/12.1/100 + null
 *   B5.contract.*  §4 表逐字比对（boundary 文本、level/levelLabel、band/bandLabel）
 *   B5.example.*   §1 示例自洽（level/band/flags 有序/summary 逐字/与 CONTRACT.md 文本比对）
 *   B5.relation.*  normalized = bar/100、percent = bar、fraction = percent/100
 *   B5.flag.*      四条 flag 规则：各造「只触发该 flag」的输入 + 一个刚好不触发的边界输入
 *   B5.robust.*    反例：101/-101/NaN/缺字段/null/数组/字符串 —— 必须不抛错且可判定
 *   B5.signature.* classifyLevel(bar) / classifyUnemployment(percent) 的入参口径
 *
 * 运行：<node> tests/verification/rcio-cases.mjs [--json <path>]
 */

import { readFileSync } from 'node:fs';
import {
  LEVELS, LEVEL_LABELS, BANDS, BAND_LABELS, ZONES, ZONE_LABELS, STANDARD_SCHEMA,
  clampBar, normalizeBar, classifyLevel, levelLabelOf, classifyUnemployment, bandLabelOf,
  describeZone, describeUnemployment, flagsOf, summarize, standardize
} from '../../lib/rcio.js';
import { createReport, CONTRACT, show } from './harness.mjs';

const r = createReport('rcio-cases');
const contractText = readFileSync(CONTRACT, 'utf8');
const contractLines = contractText.split(/\r?\n/u);

/* ══════════ 1) 从 CONTRACT.md §4 抽出档位表（唯一期望值来源） ══════════ */

function tableAfter(headerIncludes, limit) {
  const start = contractLines.findIndex((line) => headerIncludes.every((needle) => line.includes(needle)));
  if (start < 0) return null;
  const rows = [];
  for (let i = start + 1; i < contractLines.length && rows.length < limit; i += 1) {
    const line = contractLines[i];
    if (!line.trimStart().startsWith('|')) break;
    const cells = line.trim().replace(/^\|/u, '').replace(/\|$/u, '').split('|').map((cell) => cell.trim());
    if (cells.every((cell) => /^-+$/u.test(cell))) continue; // 分隔行
    if (cells.some((cell) => cell.includes('level')) || cells.some((cell) => cell === 'band')) continue; // 表头
    rows.push(cells);
  }
  return rows;
}

const levelRows = tableAfter(['归一值', 'levelLabel'], 6);
const bandRows = tableAfter(['`percent`', '`band`', 'bandLabel'], 4);
r.check('B5.contract.tablesFound', levelRows?.length === 6 && bandRows?.length === 4,
  `CONTRACT.md §4 抽出 6 行需求档位 + 4 行失业率档位`,
  `CONTRACT.md §4 档位表抽取失败：levelRows=${show(levelRows)} bandRows=${show(bandRows)}`);

const stripBackticks = (text) => text.replace(/`/gu, '').trim();
const contractLevels = (levelRows ?? []).map((cells) => ({ boundary: stripBackticks(cells[0]), level: stripBackticks(cells[1]), label: stripBackticks(cells[2]) }));
const contractBands = (bandRows ?? []).map((cells) => ({ boundary: stripBackticks(cells[0]), band: stripBackticks(cells[1]), label: stripBackticks(cells[2]) }));

const EXPECTED_BOUNDARIES = ['≤ -0.6', '-0.6 < n < -0.15', '-0.15 ≤ n ≤ 0.15', '0.15 < n < 0.5', '0.5 ≤ n < 0.8', '≥ 0.8'];
const EXPECTED_BAND_BOUNDARIES = ['< 3', '3 – 8', '> 8 – 12', '> 12'];
r.check('B5.contract.levelBoundaries',
  show(contractLevels.map((row) => row.boundary)) === show(EXPECTED_BOUNDARIES),
  `§4 需求表边界逐字：${show(contractLevels.map((row) => row.boundary))}`,
  `§4 需求表边界与预期不符：${show(contractLevels.map((row) => row.boundary))}`);
r.check('B5.contract.bandBoundaries',
  show(contractBands.map((row) => row.boundary)) === show(EXPECTED_BAND_BOUNDARIES),
  `§4 失业率表边界逐字：${show(contractBands.map((row) => row.boundary))}`,
  `§4 失业率表边界与预期不符：${show(contractBands.map((row) => row.boundary))}`);
r.check('B5.contract.levelOrder',
  show(LEVELS) === show(contractLevels.map((row) => row.level)),
  `LEVELS = ${show(LEVELS)}（顺序与 §4 表一致）`,
  `LEVELS = ${show(LEVELS)} ≠ §4 表顺序 ${show(contractLevels.map((row) => row.level))}`);
r.check('B5.contract.levelLabels',
  show(contractLevels.map((row) => LEVEL_LABELS[row.level])) === show(contractLevels.map((row) => row.label)),
  `LEVEL_LABELS 与 §4 表逐字一致：${show(contractLevels.map((row) => row.label))}`,
  `LEVEL_LABELS 与 §4 表不一致：${show(contractLevels.map((row) => LEVEL_LABELS[row.level]))} vs ${show(contractLevels.map((row) => row.label))}`);
r.check('B5.contract.bandOrder',
  show(BANDS) === show(contractBands.map((row) => row.band)),
  `BANDS = ${show(BANDS)}（顺序与 §4 表一致）`,
  `BANDS = ${show(BANDS)} ≠ §4 表顺序 ${show(contractBands.map((row) => row.band))}`);
r.check('B5.contract.bandLabels',
  show(contractBands.map((row) => BAND_LABELS[row.band])) === show(contractBands.map((row) => row.label)),
  `BAND_LABELS 与 §4 表逐字一致：${show(contractBands.map((row) => row.label))}`,
  `BAND_LABELS 与 §4 表不一致：${show(contractBands.map((row) => BAND_LABELS[row.band]))} vs ${show(contractBands.map((row) => row.label))}`);
r.info(`ZONES = ${show(ZONES)}；ZONE_LABELS = ${show(ZONE_LABELS)}；STANDARD_SCHEMA = ${show(STANDARD_SCHEMA)}`);

/* ══════════ 2) 独立实现（按 §4 文本另写一份判定） ══════════ */

/** §4 需求档位：≤-0.6 collapse｜-0.6<n<-0.15 negative｜-0.15≤n≤0.15 neutral｜0.15<n<0.5 weak｜0.5≤n<0.8 demand｜≥0.8 strong */
function expectedLevel(bar) {
  const n = bar / 100;
  if (n <= -0.6) return 'collapse';
  if (n > -0.6 && n < -0.15) return 'negative';
  if (n >= -0.15 && n <= 0.15) return 'neutral';
  if (n > 0.15 && n < 0.5) return 'weak';
  if (n >= 0.5 && n < 0.8) return 'demand';
  if (n >= 0.8) return 'strong';
  return 'ERROR';
}
/** §4 失业率：<3 low｜3–8 normal｜>8–12 high｜>12 severe */
function expectedBand(percent) {
  if (percent === null) return null;
  if (percent < 3) return 'low';
  if (percent <= 8) return 'normal';
  if (percent <= 12) return 'high';
  return 'severe';
}
/** §4 flags 顺序：office_strong → residential_negative → unemployment_severe → all_neutral */
function expectedFlags(legalRcio, unemployment) {
  const bars = {};
  for (const zone of ZONES) bars[zone] = legalRcio[zone] === undefined ? 0 : legalRcio[zone];
  const flags = [];
  if (bars.office / 100 >= 0.8) flags.push('office_strong');
  if (bars.residential / 100 < -0.15) flags.push('residential_negative');
  if (expectedBand(unemployment === undefined ? null : unemployment) === 'severe') flags.push('unemployment_severe');
  if (ZONES.every((zone) => Math.abs(bars[zone] / 100) <= 0.15)) flags.push('all_neutral');
  return flags;
}

/* ══════════ 3) bar 边界用例 ══════════ */

const BAR_CASES = [-100, -61, -60, -59, -16, -15, -14, 0, 14, 15, 16, 49, 50, 51, 79, 80, 100];
let barBad = [];
for (const bar of BAR_CASES) {
  const expected = expectedLevel(bar);
  const actual = classifyLevel(bar);
  const node = describeZone(bar);
  const labelOk = node.levelLabel === LEVEL_LABELS[expected];
  if (actual !== expected || node.bar !== bar || node.percent !== bar || node.normalized !== bar / 100 || !labelOk) {
    barBad.push({ bar, expected, actual, node });
  }
}
r.check('B5.bar.boundaries', barBad.length === 0,
  `${BAR_CASES.length} 个 bar 边界值：level/bar/percent/normalized/levelLabel 全部与 §4 一致`,
  `以下 bar 用例不符：${show(barBad.slice(0, 6))}`);
r.info(`bar 边界映射：${BAR_CASES.map((bar) => `${bar}→${expectedLevel(bar)}`).join(' ')}`);

/* ══════════ 4) 失业率边界用例 ══════════ */

const BAND_CASES = [0, 2.9, 3, 7.9, 8, 8.1, 11.9, 12, 12.1, 100, null];
/** fraction = percent/100；rcio.js 会 round(x,6) 消浮点噪声，故按 1e-9 容差比较（2.9/100 的裸双精度值 = 0.028999999999999998）。 */
const sameNumber = (a, b) => typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) < 1e-9;
const bandBad = [];
for (const percent of BAND_CASES) {
  const expected = expectedBand(percent);
  const actual = classifyUnemployment(percent);
  const node = describeUnemployment(percent);
  const nodeOk = percent === null
    ? node.percent === null && node.fraction === null && node.band === null && node.bandLabel === null
    : node.percent === percent && sameNumber(node.fraction, percent / 100) && node.band === expected && node.bandLabel === BAND_LABELS[expected];
  if (actual !== expected || !nodeOk) bandBad.push({ percent, expected, actual, node });
}
r.check('B5.band.boundaries', bandBad.length === 0,
  `${BAND_CASES.length} 个失业率用例（含 null）全部与 §4 一致`,
  `以下失业率用例不符：${show(bandBad)}`);
r.info(`失业率映射：${BAND_CASES.map((p) => `${p}→${expectedBand(p)}`).join(' ')}`);

/* ══════════ 5) §1 示例自洽（并与 CONTRACT.md §1 文本比对） ══════════ */

const EXAMPLE_RCIO = { residential: -35, commercial: 12, industrial: 0, office: 85 };
const EXAMPLE_UNEMPLOYMENT = 6.5;
const example = standardize(EXAMPLE_RCIO, EXAMPLE_UNEMPLOYMENT);

const MINUS = '\u2212'; // U+2212 真减号
const VBAR = '\uFF5C';  // U+FF5C 全角竖线
const EXPECTED_SUMMARY = `住宅 ${MINUS}35${VBAR}商业 +12${VBAR}工业 0${VBAR}办公 +85${VBAR}失业率 6.5%`;

const expectedExample = {
  schema: 'csl2-rcio-standard/v1',
  rcio: {
    residential: { bar: -35, percent: -35, normalized: -0.35, level: 'negative', levelLabel: '负需求' },
    commercial: { bar: 12, percent: 12, normalized: 0.12, level: 'neutral', levelLabel: '无需求' },
    industrial: { bar: 0, percent: 0, normalized: 0, level: 'neutral', levelLabel: '无需求' },
    office: { bar: 85, percent: 85, normalized: 0.85, level: 'strong', levelLabel: '强需求' }
  },
  unemployment: { percent: 6.5, fraction: 0.065, band: 'normal', bandLabel: '正常范围' },
  summary: EXPECTED_SUMMARY,
  flags: ['office_strong', 'residential_negative']
};
r.check('B5.example.deepEqual', JSON.stringify(example) === JSON.stringify(expectedExample),
  `standardize(§1 示例) 与 §4 重算结果逐字段相等（flags 有序 = ${show(example.flags)}）`,
  `standardize(§1 示例) 不符：\n  实际 ${show(example)}\n  期望 ${show(expectedExample)}`);

// 与 CONTRACT.md §1 文本比对：summary / flags / unemployment / 四个 zone 节点
const contractSummary = (/^\s*"summary":\s*"(.+?)",\s*$/mu.exec(contractText) ?? [])[1] ?? null;
r.check('B5.example.contractSummary', contractSummary === example.summary,
  `CONTRACT.md §1 的 summary 与计算结果逐字相同：${show(contractSummary)}`,
  `CONTRACT.md §1 summary = ${show(contractSummary)} ≠ 计算值 ${show(example.summary)}`);
const contractFlags = (() => {
  const raw = (/^\s*"flags":\s*(\[[^\]]*\]),?\s*$/mu.exec(contractText) ?? [])[1];
  try { return JSON.parse(raw); } catch { return null; }
})();
r.check('B5.example.contractFlags', JSON.stringify(contractFlags) === JSON.stringify(example.flags),
  `CONTRACT.md §1 的 flags 与计算结果（含顺序）相同：${show(contractFlags)}`,
  `CONTRACT.md §1 flags = ${show(contractFlags)} ≠ 计算值 ${show(example.flags)}`);
const contractUnemployment = (() => {
  const raw = (/^\s*"unemployment":\s*(\{[^}]*\}),?\s*$/mu.exec(contractText) ?? [])[1];
  try { return JSON.parse(raw); } catch { return null; }
})();
r.check('B5.example.contractUnemployment', JSON.stringify(contractUnemployment) === JSON.stringify(example.unemployment),
  `CONTRACT.md §1 的 unemployment 节点与计算结果相同：${show(contractUnemployment)}`,
  `CONTRACT.md §1 unemployment = ${show(contractUnemployment)} ≠ 计算值 ${show(example.unemployment)}`);
const zoneLineRe = /^\s*"(residential|commercial|industrial|office)":\s*\{\s*"bar":\s*(-?\d+),\s*"percent":\s*(-?\d+),\s*"normalized":\s*(-?[\d.]+),\s*"level":\s*"(\w+)",\s*"levelLabel":\s*"([^"]+)"\s*\},?\s*$/gmu;
const contractZones = [...contractText.matchAll(zoneLineRe)].map((m) => ({ zone: m[1], bar: Number(m[2]), percent: Number(m[3]), normalized: Number(m[4]), level: m[5], levelLabel: m[6] }));
r.check('B5.example.contractZones',
  contractZones.length === 4 && contractZones.every((row) => JSON.stringify(example.rcio[row.zone]) === JSON.stringify({ bar: row.bar, percent: row.percent, normalized: row.normalized, level: row.level, levelLabel: row.levelLabel })),
  `CONTRACT.md §1 的 4 个 rcio 节点与计算结果逐字相同（${contractZones.length} 行命中）`,
  `CONTRACT.md §1 rcio 节点不符：${show(contractZones)} vs ${show(example.rcio)}`);

/* ══════════ 6) 换算关系 ══════════ */

const relBad = [];
for (const bar of [...BAR_CASES, -33, 7, 63, 99]) {
  const node = describeZone(bar);
  if (!sameNumber(node.normalized, bar / 100) || node.percent !== bar || node.bar !== bar) relBad.push({ bar, node });
}
const bandRelBad = [];
for (const percent of [0, 2.9, 6.5, 12, 12.1, 100]) {
  const node = describeUnemployment(percent);
  if (!sameNumber(node.fraction, percent / 100) || node.percent !== percent) bandRelBad.push({ percent, node });
}
r.check('B5.relation.normalizedPercentFraction', relBad.length === 0 && bandRelBad.length === 0,
  'normalized = bar/100、percent = bar、fraction = percent/100 全部成立（fraction 按 1e-9 容差，因 rcio.js 显式 round(x,6) 消噪）',
  `换算关系不符：rcio=${show(relBad)} unemployment=${show(bandRelBad)}`);

/* ══════════ 7) 四条 flag 规则（各一个只触发它的输入 + 一个刚好不触发的边界输入） ══════════ */

const zero = { residential: 0, commercial: 0, industrial: 0, office: 0 };
const FLAG_CASES = [
  { id: 'office_strong', trigger: { rcio: { ...zero, office: 80 }, u: 6 }, boundary: { rcio: { ...zero, office: 79 }, u: 6 } },
  { id: 'residential_negative', trigger: { rcio: { ...zero, residential: -16 }, u: 6 }, boundary: { rcio: { ...zero, residential: -15 }, u: 6 } },
  { id: 'unemployment_severe', trigger: { rcio: { ...zero, office: 20 }, u: 12.1 }, boundary: { rcio: { ...zero, office: 20 }, u: 12 } },
  { id: 'all_neutral', trigger: { rcio: { ...zero }, u: 6 }, boundary: { rcio: { ...zero, office: 16 }, u: 6 } }
];
const flagBad = [];
for (const item of FLAG_CASES) {
  const triggerFlags = flagsOf(item.trigger.rcio, item.trigger.u);
  const boundaryFlags = flagsOf(item.boundary.rcio, item.boundary.u);
  if (JSON.stringify(triggerFlags) !== JSON.stringify([item.id])) flagBad.push({ rule: item.id, kind: 'trigger', expected: [item.id], actual: triggerFlags });
  if (boundaryFlags.includes(item.id)) flagBad.push({ rule: item.id, kind: 'boundary-should-not-fire', actual: boundaryFlags });
  // 与独立实现比对
  if (JSON.stringify(triggerFlags) !== JSON.stringify(expectedFlags(item.trigger.rcio, item.trigger.u))) flagBad.push({ rule: item.id, kind: 'independent-trigger', actual: triggerFlags });
  if (JSON.stringify(boundaryFlags) !== JSON.stringify(expectedFlags(item.boundary.rcio, item.boundary.u))) flagBad.push({ rule: item.id, kind: 'independent-boundary', actual: boundaryFlags });
  r.info(`flag ${item.id}：触发输入 → ${show(triggerFlags)}；边界输入 → ${show(boundaryFlags)}`);
}
r.check('B5.flag.rules', flagBad.length === 0,
  '四条 flag 规则：只触发自身的输入 + 刚好不触发的边界输入全部符合 §4',
  `flag 规则不符：${show(flagBad)}`);

/* ══════════ 8) 反例：畸形输入必须不抛错且可判定 ══════════ */

const observations = [];
function attempt(id, fn, predicate) {
  let value;
  try {
    value = fn();
  } catch (error) {
    r.fail(`B5.robust.${id}`, `抛异常：${error instanceof Error ? error.message : String(error)}`);
    observations.push(`${id} -> THREW`);
    return;
  }
  let ok = false;
  try { ok = predicate(value) === true; } catch { ok = false; }
  const detail = `${id} -> ${show(value)}`;
  observations.push(detail);
  r.check(`B5.robust.${id}`, ok, `不抛错且可判定：${detail}`, `结果不可判定：${detail}`);
}
const isZoneNode = (node) => node && LEVELS.includes(node.level) && typeof node.bar === 'number' && node.bar >= -100 && node.bar <= 100;
const allZonesZeroNeutral = (standard) => ZONES.every((zone) => standard.rcio[zone].bar === 0 && standard.rcio[zone].level === 'neutral' && standard.rcio[zone].levelLabel === '无需求');

attempt('bar101', () => describeZone(101), (node) => isZoneNode(node) && node.bar === 100 && node.level === 'strong');
attempt('bar-101', () => describeZone(-101), (node) => isZoneNode(node) && node.bar === -100 && node.level === 'collapse');
attempt('barNaN', () => describeZone(Number.NaN), (node) => isZoneNode(node) && node.bar === 0 && node.level === 'neutral');
attempt('barMissingField', () => standardize({ residential: -35 }, 6.5), (standard) => standard.rcio.residential.bar === -35 && standard.rcio.residential.level === 'negative' && standard.rcio.commercial.bar === 0 && standard.rcio.commercial.level === 'neutral' && standard.rcio.office.bar === 0);
attempt('null', () => standardize(null, null), (standard) => allZonesZeroNeutral(standard) && standard.unemployment.percent === null && standard.unemployment.band === null && standard.flags.includes('all_neutral'));
attempt('array', () => standardize([1, 2, 3], 5), (standard) => allZonesZeroNeutral(standard) && standard.unemployment.band === 'normal' && standard.unemployment.percent === 5);
attempt('stringAbc', () => standardize('abc', 'abc'), (standard) => allZonesZeroNeutral(standard) && standard.unemployment.percent === null);
attempt('zoneNumberString', () => standardize({ residential: '12', commercial: 'abc', industrial: {}, office: [] }, ''), (standard) => standard.rcio.residential.bar === 12 && standard.rcio.commercial.bar === 0 && standard.rcio.industrial.bar === 0 && standard.rcio.office.bar === 0 && standard.unemployment.percent === null);
attempt('clampBarNaN', () => clampBar(Number.NaN), (value) => value === 0);
attempt('clampBarAbc', () => clampBar('abc'), (value) => value === 0);
attempt('clampBarInfinity', () => clampBar(Number.POSITIVE_INFINITY), (value) => value === 0);
attempt('clampBarNegativeInfinity', () => clampBar(Number.NEGATIVE_INFINITY), (value) => value === 0);
attempt('normalizeBarNull', () => normalizeBar(null), (value) => value === 0);
attempt('classifyLevelNull', () => classifyLevel(null), (value) => value === 'neutral');
attempt('classifyLevelAbc', () => classifyLevel('abc'), (value) => value === 'neutral');
attempt('classifyUnemploymentNaN', () => classifyUnemployment(Number.NaN), (value) => value === null);
attempt('classifyUnemploymentAbc', () => classifyUnemployment('abc'), (value) => value === null);
attempt('levelLabelOfUnknown', () => levelLabelOf('nope'), (value) => value === '');
attempt('bandLabelOfUnknown', () => bandLabelOf('nope'), (value) => value === '');
attempt('flagsOfNull', () => flagsOf(null, null), (value) => Array.isArray(value) && value.length === 1 && value[0] === 'all_neutral');
attempt('summarizeNull', () => summarize(null, null), (value) => value === `住宅 0${VBAR}商业 0${VBAR}工业 0${VBAR}办公 0${VBAR}失业率 未提供`);
attempt('unemploymentOverflow', () => describeUnemployment(150), (node) => node.percent === 100 && node.fraction === 1 && node.band === 'severe');
attempt('unemploymentUnderflow', () => describeUnemployment(-5), (node) => node.percent === 0 && node.band === 'low');
r.info('说明：±Infinity 走 toFiniteNumber 的 Number.isFinite 判定 -> 视为「不可数」-> 0（rcio.js JSDoc 明文「不可数 -> 0」）；JSON 线上也传不了 Infinity。有限越界值才夹取到 ±100。');
for (const line of observations) r.info(`反例实测：${line}`);

/* ══════════ 9) 函数签名契约（作者声明） ══════════ */

r.check('B5.signature.classifyLevelTakesBar',
  classifyLevel(-60) === 'collapse' && classifyLevel(-0.6) === 'neutral' && classifyLevel(80) === 'strong' && classifyLevel(0.8) === 'neutral' && classifyLevel(100) === 'strong',
  `classifyLevel 收 bar：(-60→${classifyLevel(-60)}, -0.6→${classifyLevel(-0.6)}, 80→${classifyLevel(80)}, 0.8→${classifyLevel(0.8)}）`,
  `classifyLevel 的入参不是 -100…100 的 bar：(-60→${classifyLevel(-60)}, -0.6→${classifyLevel(-0.6)}, 80→${classifyLevel(80)}, 0.8→${classifyLevel(0.8)}）`);
r.check('B5.signature.classifyUnemploymentTakesPercent',
  classifyUnemployment(0.5) === 'low' && classifyUnemployment(0.08) === 'low' && classifyUnemployment(3) === 'normal' && classifyUnemployment(13) === 'severe' && classifyUnemployment(null) === null && classifyUnemployment(undefined) === null && classifyUnemployment('') === null,
  `classifyUnemployment 收 percent 且 null 安全：(0.5→${classifyUnemployment(0.5)}, 3→${classifyUnemployment(3)}, 13→${classifyUnemployment(13)}, null→${show(classifyUnemployment(null))})`,
  `classifyUnemployment 口径不符：(0.5→${classifyUnemployment(0.5)}, 3→${classifyUnemployment(3)}, 13→${classifyUnemployment(13)}, null→${show(classifyUnemployment(null))})`);

/* ══════════ 10) 附加观察（非清单要求，如实记录） ══════════ */
const noUnemploymentSummary = summarize(EXAMPLE_RCIO, null);
r.check('B5.extra.summaryNoUnemployment', noUnemploymentSummary === `住宅 ${MINUS}35${VBAR}商业 +12${VBAR}工业 0${VBAR}办公 +85${VBAR}失业率 未提供`,
  `失业率未提供时 summary 写作「失业率 未提供」（与 rcio.js JSDoc 一致）：${show(noUnemploymentSummary)}`,
  `失业率未提供时 summary 与 JSDoc 不一致：${show(noUnemploymentSummary)}`);
r.check('B5.extra.flagsOrderIndependent', JSON.stringify(flagsOf({ residential: -35, commercial: 12, industrial: 0, office: 85 }, 6.5)) === JSON.stringify(expectedFlags({ residential: -35, commercial: 12, industrial: 0, office: 85 }, 6.5)),
  'flagsOf 与独立实现（§4 顺序）一致');

r.finish();
