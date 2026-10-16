/**
 * csl2-city-advisor · lib/rcio.js
 *
 * 纯函数口径层：RCIO 需求条原始读数 -> 标准数据 `csl2-rcio-standard/v1`。
 * 判据唯一来源 = `CONTRACT.md` §4 的档位表（§1 的示例 JSON 若与 §4 冲突，一律以 §4 为准）。
 *
 * 设计约束
 * - **零依赖、零 import、无副作用**：Host half（lib/index.js）与 Client half（lib/client.js 内联副本）
 *   必须给出逐项一致的结果。客户端 bundle 是独立打包产物，**不允许跨文件 import**，所以 client.js
 *   里内联同一份逻辑；本文件是「口径的规范来源」。
 * - **永不抛错**：任何畸形输入（null / 非对象 / NaN / 字符串 / 越界）都退化为可判定的降级结果
 *   （越界 -> 夹取到 ±100 并取整；不可数 -> 0），因为面板是回放安全的，不能让渲染路径炸掉。
 * - **只做线性归一与分档**，不引入游戏内不存在的机制（契约 §4 明文要求）。
 *
 * 公开 API（签名冻结，Host/Client 共用）
 *   ZONES, ZONE_LABELS                                    -> 四类用地顺序与中文名
 *   LEVELS, LEVEL_LABELS, classifyLevel(bar)              -> 6 档需求档位
 *   BANDS, BAND_LABELS, classifyUnemployment(percent)     -> 4 档失业率
 *   clampBar(value)                                       -> 夹取到 [-100,100] 的整数
 *   standardize(rcio, unemploymentRate)                   -> 契约 §1 的 `standard` 对象
 *   summarize(rcio, unemploymentRate)                     -> 契约 §1 的 `summary` 单行中文
 *   describeZone(bar) / describeUnemployment(percent)     -> 单节点（给 client 复用）
 *   flagsOf(rcio, unemploymentRate)                       -> 契约 §4 的四条信号
 */

/** 标准数据版本号（契约 §1 的 `standard.schema`）。 */
export const STANDARD_SCHEMA = 'csl2-rcio-standard/v1';

/** 四类用地的**固定顺序**（契约 §3：住宅 / 商业 / 工业 / 办公）。 */
export const ZONES = Object.freeze(['residential', 'commercial', 'industrial', 'office']);

/** 四类用地的中文名。 */
export const ZONE_LABELS = Object.freeze({
  residential: '住宅',
  commercial: '商业',
  industrial: '工业',
  office: '办公'
});

/** 需求档位 id，按契约 §4 表自上而下。 */
export const LEVELS = Object.freeze(['collapse', 'negative', 'neutral', 'weak', 'demand', 'strong']);

/** 需求档位中文（契约 §4 表逐字）。 */
export const LEVEL_LABELS = Object.freeze({
  collapse: '需求崩塌（负）',
  negative: '负需求',
  neutral: '无需求',
  weak: '弱正需求',
  demand: '需求',
  strong: '强需求'
});

/** 失业率档位 id，按契约 §4 表自上而下。 */
export const BANDS = Object.freeze(['low', 'normal', 'high', 'severe']);

/**
 * 失业率档位中文（契约 §4 表逐字）。
 * 注意：这是**诊断阈值**，不是游戏机制 —— 官方没有给过阈值，引用时必须标注为经验值。
 */
export const BAND_LABELS = Object.freeze({
  low: '偏低（劳动力紧张）',
  normal: '正常范围',
  high: '偏高',
  severe: '严重（税基会自己缩）'
});

/** 需求条取值区间（契约 §3：−100 … +100）。 */
export const BAR_MIN = -100;
export const BAR_MAX = 100;

/** 失业率取值区间（面板输入的百分比 0–100）。 */
export const UNEMPLOYMENT_MIN = 0;
export const UNEMPLOYMENT_MAX = 100;

/** 失业率低/正常分界与正常/偏高分界（契约 §4：<3 low，3–8 normal）。 */
export const UNEMPLOYMENT_LOW_MAX = 3;
export const UNEMPLOYMENT_NORMAL_MAX = 8;

/** 偏高/严重分界（契约 §4：>8–12 high，>12 severe）。 */
export const UNEMPLOYMENT_HIGH_MAX = 12;

/** 契约 §4 的 `all_neutral` 判据：四条归一值全在 ±0.15 内。 */
export const NEUTRAL_BAND = 0.15;

/** 契约 §4 的 `office_strong` 判据：办公归一值 ≥ 0.8。 */
export const OFFICE_STRONG_THRESHOLD = 0.8;

/** 是否为合法的需求档位 id。 */
export function isLevel(value) {
  return LEVELS.includes(value);
}

/** 是否为合法的失业率档位 id（`null` = 用户未填，走 `unknown` 而不是某个档）。 */
export function isBand(value) {
  return BANDS.includes(value);
}

/**
 * 把任意输入变成有限数；不可数返回 null。
 * 接受 number 与「看起来是数字」的字符串（面板输入框可能回传字符串）。
 * @param {unknown} value
 * @returns {number|null}
 */
function toFiniteNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed === '') return null;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

/** 保留 n 位小数，抹掉浮点噪声（0.12 不该变成 0.12000000000000001）。 */
function round(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

/**
 * 把任意输入夹取成合法需求条读数：整数、落在 [-100, 100]。
 * 不可数 -> 0；越界 -> 夹取；小数 -> 四舍五入；`-0` -> `0`。
 * @param {unknown} value
 * @returns {number} ∈ [-100, 100] 的整数
 */
export function clampBar(value) {
  const number = toFiniteNumber(value);
  if (number === null) return 0;
  const bounded = Math.min(BAR_MAX, Math.max(BAR_MIN, number));
  const rounded = Math.round(bounded);
  // `Math.round(-0.4)` 会得到 `-0`，它在 `JSON.stringify` 里会变成 `0` 但会让 `Object.is` 判断分裂。
  return rounded === 0 ? 0 : rounded;
}

/**
 * 需求条归一化：`normalized = bar / 100`（契约 §4 的唯一换算）。
 * @param {unknown} bar
 * @returns {number} ∈ [-1, 1]
 */
export function normalizeBar(bar) {
  const normalized = round(clampBar(bar) / 100, 4);
  return normalized === 0 ? 0 : normalized;
}

/**
 * 需求档位判定（契约 §4 的六个区间，边界归属逐字实现）：
 * `≤ -0.6 collapse`｜`-0.6 < n < -0.15 negative`｜`-0.15 ≤ n ≤ 0.15 neutral`
 * ｜`0.15 < n < 0.5 weak`｜`0.5 ≤ n < 0.8 demand`｜`≥ 0.8 strong`
 * @param {unknown} bar - 面板读数（-100…100），**不是**归一值
 * @returns {'collapse'|'negative'|'neutral'|'weak'|'demand'|'strong'}
 */
export function classifyLevel(bar) {
  const normalized = normalizeBar(bar);
  if (normalized <= -0.6) return 'collapse';
  if (normalized < -0.15) return 'negative';
  if (normalized <= 0.15) return 'neutral';
  if (normalized < 0.5) return 'weak';
  if (normalized < 0.8) return 'demand';
  return 'strong';
}

/** 需求档位中文；未知档位返回空串（不抛错）。 */
export function levelLabelOf(level) {
  return Object.prototype.hasOwnProperty.call(LEVEL_LABELS, level) ? LEVEL_LABELS[level] : '';
}

/**
 * 失业率分档（契约 §4：`< 3 low`｜`3 – 8 normal`｜`> 8 – 12 high`｜`> 12 severe`）。
 * 这是**诊断阈值**（社区/项目经验），不是游戏机制。
 * @param {unknown} percent - 面板输入的百分比；null/空/不可数 -> null
 * @returns {'low'|'normal'|'high'|'severe'|null}
 */
export function classifyUnemployment(percent) {
  const number = toFiniteNumber(percent);
  if (number === null) return null;
  const bounded = Math.min(UNEMPLOYMENT_MAX, Math.max(UNEMPLOYMENT_MIN, number));
  if (bounded < UNEMPLOYMENT_LOW_MAX) return 'low';
  if (bounded <= UNEMPLOYMENT_NORMAL_MAX) return 'normal';
  if (bounded <= UNEMPLOYMENT_HIGH_MAX) return 'high';
  return 'severe';
}

/** 失业率档位中文；null/未知返回空串（不抛错）。 */
export function bandLabelOf(band) {
  return Object.prototype.hasOwnProperty.call(BAND_LABELS, band) ? BAND_LABELS[band] : '';
}

/**
 * 单条需求条 -> 契约 §1 的 `standard.rcio.<zone>` 节点。
 * @param {unknown} bar
 * @returns {{bar:number, percent:number, normalized:number, level:string, levelLabel:string}}
 */
export function describeZone(bar) {
  const value = clampBar(bar);
  const level = classifyLevel(value);
  return {
    bar: value,
    percent: value,
    normalized: normalizeBar(value),
    level,
    levelLabel: levelLabelOf(level)
  };
}

/**
 * 失业率 -> 契约 §1 的 `standard.unemployment` 节点。
 * 用户留空时 `percent`/`fraction`/`band`/`bandLabel` 全为 `null`（该节点仍然存在，
 * 因为「没填」本身是要写进报告第 0 栏的信息）。
 * @param {unknown} percent
 */
export function describeUnemployment(percent) {
  const number = toFiniteNumber(percent);
  if (number === null) {
    return { percent: null, fraction: null, band: null, bandLabel: null };
  }
  const bounded = round(Math.min(UNEMPLOYMENT_MAX, Math.max(UNEMPLOYMENT_MIN, number)), 4);
  const band = classifyUnemployment(bounded);
  return {
    percent: bounded,
    fraction: round(bounded / 100, 6),
    band,
    bandLabel: bandLabelOf(band)
  };
}

/**
 * 契约 §4 的四条结构性信号，输出顺序与 §4 的枚举顺序一致。
 * - `office_strong`：办公归一值 ≥ 0.8（1.5.7f1 起办公需求受学历结构影响，属结构性信号）
 * - `residential_negative`：住宅归一值 < -0.15
 * - `unemployment_severe`：失业率 > 12
 * - `all_neutral`：四条归一值全在 ±0.15 内（结构僵化提示）
 * @param {unknown} rcio - `{residential, commercial, industrial, office}` 原始需求条
 * @param {unknown} unemploymentRate
 * @returns {string[]}
 */
export function flagsOf(rcio, unemploymentRate) {
  const source = isRecord(rcio) ? rcio : {};
  const flags = [];
  if (describeZone(source.office).normalized >= OFFICE_STRONG_THRESHOLD) flags.push('office_strong');
  if (describeZone(source.residential).normalized < -NEUTRAL_BAND) flags.push('residential_negative');
  if (classifyUnemployment(unemploymentRate) === 'severe') flags.push('unemployment_severe');
  const allNeutral = ZONES.every((zone) => Math.abs(describeZone(source[zone]).normalized) <= NEUTRAL_BAND);
  if (allNeutral) flags.push('all_neutral');
  return flags;
}

/** 是否为普通对象（数组/null 不算）。 */
function isRecord(value) {
  return value !== null && typeof value === 'object' && Array.isArray(value) === false;
}

/**
 * 带符号显示需求条：正数 `+48`、负数 `−35`（U+2212 真减号，与契约 §1 的 `summary` 逐字一致）、零 `0`。
 * @param {unknown} bar
 */
export function formatSignedBar(bar) {
  const value = clampBar(bar);
  if (value > 0) return `+${value}`;
  if (value < 0) return `\u2212${Math.abs(value)}`; // −
  return '0';
}

/** 百分比显示：去掉多余的尾随零（6.5 -> `6.5`，7 -> `7`）。 */
export function formatPercent(percent) {
  const number = toFiniteNumber(percent);
  if (number === null) return '';
  const bounded = round(number, 4);
  return `${String(bounded)}%`;
}

/**
 * 契约 §1 的 `standard.summary` 单行中文：
 * `住宅 −35｜商业 +12｜工业 0｜办公 +85｜失业率 6.5%`
 * 失业率未提供时该段写作 `失业率 未提供`。
 * @param {unknown} rcio
 * @param {unknown} unemploymentRate
 * @returns {string}
 */
export function summarize(rcio, unemploymentRate) {
  const source = isRecord(rcio) ? rcio : {};
  const bars = ZONES.map((zone) => `${ZONE_LABELS[zone]} ${formatSignedBar(source[zone])}`);
  const percent = formatPercent(unemploymentRate);
  return `${bars.join('\uFF5C')}\uFF5C失业率 ${percent === '' ? '未提供' : percent}`;
}

/**
 * RCIO 原始读数 -> 契约 §1 的 `standard` 对象（canonical，Host/Client 共用）。
 * 任何输入都不会抛错：非对象按全 0 处理，缺失字段按 0（= neutral/无需求）处理。
 * @param {unknown} rcio - `{residential, commercial, industrial, office}`，取值 -100…100
 * @param {unknown} unemploymentRate - 百分比；null/空 = 用户未填
 */
export function standardize(rcio, unemploymentRate) {
  const source = isRecord(rcio) ? rcio : {};
  const nodes = {};
  for (const zone of ZONES) nodes[zone] = describeZone(source[zone]);
  return {
    schema: STANDARD_SCHEMA,
    rcio: nodes,
    unemployment: describeUnemployment(unemploymentRate),
    summary: summarize(source, unemploymentRate),
    flags: flagsOf(source, unemploymentRate)
  };
}

export default {
  STANDARD_SCHEMA,
  ZONES,
  ZONE_LABELS,
  LEVELS,
  LEVEL_LABELS,
  BANDS,
  BAND_LABELS,
  BAR_MIN,
  BAR_MAX,
  UNEMPLOYMENT_MIN,
  UNEMPLOYMENT_MAX,
  NEUTRAL_BAND,
  OFFICE_STRONG_THRESHOLD,
  clampBar,
  normalizeBar,
  classifyLevel,
  levelLabelOf,
  classifyUnemployment,
  bandLabelOf,
  describeZone,
  describeUnemployment,
  flagsOf,
  formatSignedBar,
  formatPercent,
  summarize,
  standardize
};
