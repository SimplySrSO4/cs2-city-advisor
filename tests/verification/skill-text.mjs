/**
 * tests/verification/skill-text.mjs —— D. Skill 文本独立验证
 *
 * D11 SKILL.md：`### 第 0 步` 行号 < `### 第 1 步：问清问题与拿到数据` 行号；`铁律 14` 存在且 §0 的 1–14 连续；
 *     references/120-rcio-input-step.md 存在且 ≤120 行；`csl2_city_readings` 在 skill 内出现 ≥4 处
 * D12 frontmatter **宽松**断言（不做严格 YAML 解析）：`name:` 未变；`description` 行末尾含追加的英文那句
 * D13 references/120-rcio-input-step.md 的 JSON 示例与 CONTRACT.md §1 的 JSON 示例**空白归一后逐字相同**；
 *     6 档 + 4 档 = 10 行数据行两边同时命中
 *
 * 运行：<node> tests/verification/skill-text.mjs [--json <path>]
 */

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { createReport, SKILL_PLUGIN, SKILL_ORIGINAL, CONTRACT, PLUGIN, show } from './harness.mjs';

const r = createReport('skill-text');
const read = (file) => readFileSync(file, 'utf8');

const SKILL_MD = path.join(SKILL_PLUGIN, 'SKILL.md');
const REF_120 = path.join(SKILL_PLUGIN, 'references', '120-rcio-input-step.md');
const ORIG_SKILL_MD = path.join(SKILL_ORIGINAL, 'SKILL.md');

/** 物理行号（1-based）：按 \n 切分；文件末尾有换行时不额外算一行空行。 */
function physicalLines(text) {
  const normalized = text.replace(/\r\n/gu, '\n');
  const parts = normalized.split('\n');
  if (parts.length > 1 && parts[parts.length - 1] === '') parts.pop();
  return parts;
}
const lineOf = (lines, needle) => lines.findIndex((line) => line.includes(needle)) + 1;

/* ═════════════════════ D11 ═════════════════════ */

const skillText = read(SKILL_MD);
const skillLines = physicalLines(skillText);
const lineStep0 = lineOf(skillLines, '### 第 0 步');
const lineStep1 = lineOf(skillLines, '### 第 1 步：问清问题与拿到数据');
r.check('D11.stepOrder', lineStep0 > 0 && lineStep1 > 0 && lineStep0 < lineStep1,
  `### 第 0 步 = 第 ${lineStep0} 行 < ### 第 1 步：问清问题与拿到数据 = 第 ${lineStep1} 行`,
  `顺序不符：第 0 步 = 第 ${lineStep0} 行，第 1 步 = 第 ${lineStep1} 行`);
r.info(`SKILL.md 物理行数 = ${skillLines.length}；` + '### 第 0 步 命中行：' + JSON.stringify(skillLines[lineStep0 - 1]?.slice(0, 60)));

// 「正文纯净」：SKILL.md 正文**不得**再出现「铁律 N」这类自引用编号（条目改名成 【xx】）
const ruleSelfRef = [...skillText.matchAll(/铁律\s*\d/gu)].length;
// §0 的条目：从 `## 0.` 起，到下一个 `## ` 之前，取顶格（无缩进）的 `N. ` 条目
const section0Start = skillLines.findIndex((line) => /^##\s*0\./u.test(line));
let section0End = skillLines.length;
for (let i = section0Start + 1; i < skillLines.length; i += 1) {
  if (/^##\s/u.test(skillLines[i])) { section0End = i; break; }
}
const ruleNumbers = [];
if (section0Start >= 0) {
  for (let i = section0Start + 1; i < section0End; i += 1) {
    const match = /^(\d+)\.\s/u.exec(skillLines[i]);
    if (match !== null) ruleNumbers.push(Number(match[1]));
  }
}
const rulesContiguous = ruleNumbers.length >= 14 && ruleNumbers.every((value, index) => value === index + 1);
r.check('D11.rules', section0Start >= 0 && rulesContiguous && ruleSelfRef === 0,
  `§0（第 ${section0Start + 1} 行起）顶格条目 = [${ruleNumbers.join(',')}] 连续 1–${ruleNumbers.length}；`
  + `「铁律 N」自引用 = ${ruleSelfRef} 处（应为 0）`,
  `条目不符：§0 起点行 ${section0Start + 1}；条目 = [${ruleNumbers.join(',')}]；铁律自引用 = ${ruleSelfRef} 处`);

// 本轮新增的三条口径必须落在 §0 里（正文纯净 / 公共交通口径 / 商业亏损与潮汐）
const NEW_RULES = ['【正文纯净】', '【公共交通口径】', '【商业亏损与潮汐】'];
const missingNewRules = NEW_RULES.filter((name) => !skillText.includes(name));
r.check('D11.newRules', missingNewRules.length === 0,
  `§0 含三条新口径：${NEW_RULES.join(' / ')}`,
  `§0 缺新口径：${missingNewRules.join('、')}`);

// 容量归一与判亏口径的关键数值必须写在 SKILL.md 正文（不能只躺在 references 里）
const KEY_STRINGS = ['1080', '80 人/辆', '840', 'Profit ≤ 0', '停用线路', '逐线路长度相加'];
const missingKeyStrings = KEY_STRINGS.filter((s) => !skillText.includes(s));
r.check('D11.keyCalibers', missingKeyStrings.length === 0,
  `SKILL.md 含关键口径串：${KEY_STRINGS.join(' / ')}`,
  `SKILL.md 缺关键口径串：${missingKeyStrings.join('、')}`);

const ref120Exists = existsSync(REF_120);
const ref120Text = ref120Exists ? read(REF_120) : '';
const ref120Lines = physicalLines(ref120Text);
const ref120Newlines = (ref120Text.match(/\n/gu) ?? []).length;
r.check('D11.ref120.existsAndShort', ref120Exists && ref120Lines.length <= 120,
  `references/120-rcio-input-step.md 存在，物理行数 ${ref120Lines.length}（\\n 计数 ${ref120Newlines}）≤ 120`,
  `120 文件不存在或超长：exists=${ref120Exists} lines=${ref120Lines.length}`);

// `csl2_city_readings` 在 skill 内出现次数（SKILL.md + references/*.md）
const referenceDir = path.join(SKILL_PLUGIN, 'references');
const referenceFiles = readdirSync(referenceDir).filter((name) => name.endsWith('.md')).map((name) => path.join(referenceDir, name));
const toolNameHits = { 'SKILL.md': [...skillText.matchAll(/csl2_city_readings/gu)].length };
let toolNameTotal = toolNameHits['SKILL.md'];
for (const file of referenceFiles) {
  const count = [...read(file).matchAll(/csl2_city_readings/gu)].length;
  if (count > 0) toolNameHits[path.basename(file)] = count;
  toolNameTotal += count;
}
r.check('D11.toolNameMentions', toolNameTotal >= 4,
  `「csl2_city_readings」在 SKILL.md + references/*.md 内共出现 ${toolNameTotal} 处 ${show(toolNameHits)}（≥4）`,
  `出现次数不足：${toolNameTotal} 处 ${show(toolNameHits)}`);

/* ═════════════════════ D12 frontmatter（宽松） ═════════════════════ */

const APPENDED = 'After the user shares a save, first collect the RCIO demand bars and the unemployment rate through the visual slider panel (skippable), then analyze.';
const frontmatterLine = (text, key) => {
  const lines = physicalLines(text);
  if (lines[0]?.trim() !== '---') return null;
  for (let i = 1; i < lines.length; i += 1) {
    if (lines[i].trim() === '---') break;
    if (lines[i].startsWith(`${key}:`)) return lines[i].slice(key.length + 1).trim();
  }
  return null;
};
const pluginName = frontmatterLine(skillText, 'name');
const origName = frontmatterLine(read(ORIG_SKILL_MD), 'name');
r.check('D12.name', pluginName === origName && pluginName === 'cities-skylines-2-city-advisor',
  `frontmatter name = ${show(pluginName)}（与原目录 ${show(origName)} 相同）`,
  `name 不符：plugin=${show(pluginName)} original=${show(origName)}`);

// ⭐ 原目录已同步为插件内 skill 的镜像 → 两边 frontmatter 必须**完全相同**
//    （不再检查"插件比原目录多一句" —— 那是镜像之前的形态）
const pluginDesc = frontmatterLine(skillText, 'description');
const origDesc = frontmatterLine(read(ORIG_SKILL_MD), 'description');
const descIsSingleLine = physicalLines(skillText).slice(0, 6).filter((line) => line.startsWith('description:')).length === 1;
r.check('D12.description',
  typeof pluginDesc === 'string' && typeof origDesc === 'string' && pluginDesc === origDesc
  && pluginDesc.endsWith(APPENDED) && descIsSingleLine,
  `description 是单行、与原目录一致（${pluginDesc?.length} 字），末尾含「…(skippable), then analyze.」`,
  `description 不符：单行=${descIsSingleLine} 与原目录一致=${pluginDesc === origDesc}`
  + ` 末尾含追加句=${pluginDesc?.endsWith(APPENDED)}`);
r.info('D12 说明：按要求不做严格 YAML 解析（`Cities: Skylines II` 里的 ": " 是改动前就有的形态）。');

/* ═════════════════════ D13 两份 JSON 示例 / 两张档位表 ═════════════════════ */

const contractText = read(CONTRACT);
const normalize = (text) => text.replace(/\s+/gu, ' ').trim();

/** 取文件里第 index 个 ```json 围栏块的内容。 */
function jsonBlock(text, index) {
  const lines = text.split(/\r?\n/u);
  const blocks = [];
  let current = null;
  for (const line of lines) {
    if (current === null && /^```json\s*$/u.test(line.trim())) { current = []; continue; }
    if (current !== null && /^```\s*$/u.test(line.trim())) { blocks.push(current.join('\n')); current = null; continue; }
    if (current !== null) current.push(line);
  }
  return blocks[index] ?? null;
}
const contractJson = jsonBlock(contractText, 0);
const ref120Json = jsonBlock(ref120Text, 0);
r.check('D13.jsonExampleIdentical',
  contractJson !== null && ref120Json !== null && normalize(contractJson) === normalize(ref120Json),
  `CONTRACT.md §1 与 120-rcio-input-step.md §2 的 JSON 示例空白归一后逐字相同（各 ${contractJson?.split('\n').length} 行）`,
  `JSON 示例不同：contract=\n${normalize(contractJson ?? '')}\n\n120=\n${normalize(ref120Json ?? '')}`);
if (normalize(contractJson ?? '') !== normalize(ref120Json ?? '')) {
  const a = normalize(contractJson ?? '').split(' ');
  const b = normalize(ref120Json ?? '').split(' ');
  const firstDiff = a.findIndex((token, index) => token !== b[index]);
  r.info(`首个差异 token 下标 ${firstDiff}：contract=${show(a[firstDiff])} vs 120=${show(b[firstDiff])}`);
}

/** 抽某张表的数据行（跳过表头与分隔行）。 */
function tableRows(text, headerNeedles, limit) {
  const lines = text.split(/\r?\n/u);
  const start = lines.findIndex((line) => headerNeedles.every((needle) => line.includes(needle)));
  if (start < 0) return null;
  const rows = [];
  for (let i = start + 1; i < lines.length && rows.length < limit; i += 1) {
    const line = lines[i];
    if (!line.trimStart().startsWith('|')) break;
    const cells = line.trim().replace(/^\|/u, '').replace(/\|$/u, '').split('|').map((cell) => normalize(cell));
    if (cells.every((cell) => /^-+$/u.test(cell))) continue;
    rows.push(cells);
  }
  return rows;
}
const levelHeader = ['归一值', 'levelLabel'];
const bandHeader = ['`percent`', '`band`', 'bandLabel'];
const contractLevels = tableRows(contractText, levelHeader, 6);
const ref120Levels = tableRows(ref120Text, levelHeader, 6);
const contractBands = tableRows(contractText, bandHeader, 4);
const ref120Bands = tableRows(ref120Text, bandHeader, 4);
const rowsEqual = (a, b) => Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((row, index) => show(row) === show(b[index]));

r.check('D13.levelTableRows', rowsEqual(contractLevels, ref120Levels) && contractLevels?.length === 6,
  `6 行需求档位数据行两边逐格相同：${show(contractLevels)}`,
  `需求档位表不同：contract=${show(contractLevels)} 120=${show(ref120Levels)}`);
r.check('D13.bandTableRows', rowsEqual(contractBands, ref120Bands) && contractBands?.length === 4,
  `4 行失业率档位数据行两边逐格相同：${show(contractBands)}`,
  `失业率档位表不同：contract=${show(contractBands)} 120=${show(ref120Bands)}`);
r.check('D13.tenRowsBothSides',
  contractLevels?.length === 6 && ref120Levels?.length === 6 && contractBands?.length === 4 && ref120Bands?.length === 4,
  `6 档 + 4 档 = 10 行数据行两边同时命中（CONTRACT ${contractLevels?.length}+${contractBands?.length}，120 ${ref120Levels?.length}+${ref120Bands?.length}）`,
  `数据行数不符：contract=${contractLevels?.length}+${contractBands?.length} 120=${ref120Levels?.length}+${ref120Bands?.length}`);

r.info(`PLUGIN=${PLUGIN}`);
r.finish();
