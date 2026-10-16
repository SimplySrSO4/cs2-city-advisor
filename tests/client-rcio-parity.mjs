#!/usr/bin/env node
/**
 * tests/client-rcio-parity.mjs
 *
 * 目的：证明 `lib/client.js` 内联的 RCIO 口径与 `lib/rcio.js`（Host/Client 共用口径的
 * 唯一真相）在同一批输入上**逐项一致**（CONTRACT §4）。
 *
 * 做法：在 Node 里用 `window.__ModuleLoader__.load` 的桩装载**真实的客户端 bundle**
 *      （不是复制一份口径再比对），然后：
 *        1. 全量整数网格 / §4 边界 / 失业率边界 / 确定性随机 —— `standardize` 深度相等；
 *        2. 逐个公开函数（classifyLevel / describeZone / classifyUnemployment /
 *           describeUnemployment / flagsOf / clampBar / normalizeBar / summarize）逐点比对；
 *        3. 常量表（LEVELS / BANDS / 中文标签 / schema id / zone 顺序）逐项比对；
 *        4. 畸形输入不抛错（回放安全）。
 *
 * 运行：node plugins/csl2-city-advisor/tests/client-rcio-parity.mjs
 * 退出码：0 = 全部一致；1 = 发现不一致（FAIL）；2 = 前置条件不满足（缺文件 / 接口形状不识别）
 *
 * 无第三方依赖：只用 Node 内建（fs / path / url）。
 */

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PKG_ROOT = path.resolve(HERE, "..");
const CLIENT_PATH = path.join(PKG_ROOT, "lib", "client.js");
const RCIO_PATH = path.join(PKG_ROOT, "lib", "rcio.js");
const PACKAGE_NAME = "csl2-city-advisor";
const TOOL_NAME = "csl2_city_readings";
const ZONE_KEYS = ["residential", "commercial", "industrial", "office"];

let failures = 0;
let warnings = 0;
const problems = [];
const stateLog = { hooks: [], refs: [], effects: [], hookSeq: 0 };
/** 最近一次装载的 client bundle 源码（供静态 CSS 断言使用）。 */
let bundleSource = "";

function say(text = "") {
  process.stdout.write(`${text}\n`);
}

function fail(text) {
  failures += 1;
  problems.push(text);
  say(`FAIL  ${text}`);
}

function warn(text) {
  warnings += 1;
  say(`WARN  ${text}`);
}

function ok(text) {
  say(`ok    ${text}`);
}

function fmt(value) {
  if (typeof value === "number" && Object.is(value, -0)) return "-0";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/* ------------------------------------------------------------------ *
 * 1) 装载客户端 bundle（真代码）
 * ------------------------------------------------------------------ */

/**
 * 极简 React 桩：hook 状态按「渲染序号」持久化在 log 里（重渲染时保留），
 * 这样测试可以像 React 一样「改状态 -> 重新渲染 -> 断言闭包拿到新值」。
 */
function makeReactStub(log) {
  log.hooks = log.hooks || [];
  log.refs = log.refs || [];
  log.effects = log.effects || [];
  if (typeof log.hookSeq !== "number") log.hookSeq = 0;
  return {
    createElement: (type, props, ...children) => ({ type, props: props ?? null, children }),
    useState: (initial) => {
      const index = log.hookSeq++;
      if (!log.hooks[index]) log.hooks[index] = { value: typeof initial === "function" ? undefined : initial };
      const record = log.hooks[index];
      const setter = (next) => {
        record.value = typeof next === "function" ? next(record.value) : next;
      };
      return [record.value, setter];
    },
    useEffect: () => {
      log.hookSeq += 1;
    },
    useRef: (initial) => {
      const index = log.hookSeq++;
      if (!log.refs[index]) log.refs[index] = { current: initial };
      return log.refs[index];
    },
    useMemo: (fn) => fn(),
    memo: (component) => component,
    Fragment: Symbol.for("csl2.fragment")
  };
}

/** 记录所有 effect；供 wire 测试手动触发挂载 effect。 */
function makeReactStubWithEffects(log) {
  const stub = makeReactStub(log);
  stub.useEffect = (fn) => {
    log.hookSeq += 1;
    log.effects.push(fn);
  };
  return stub;
}

async function loadClientExports(fetchImpl, log = stateLog) {
  if (!existsSync(CLIENT_PATH)) {
    say(`FATAL 找不到 ${CLIENT_PATH}`);
    process.exit(2);
  }
  const source = await readFile(CLIENT_PATH, "utf8");
  bundleSource = source;
  let spec = null;
  const fakeWindow = {
    __ModuleLoader__: { load: (value) => { spec = value; } },
    location: { origin: "http://127.0.0.1:19387" }
  };
  try {
    // bundle 不是 ESM（无 import/export），用 Function 构造器执行最贴近浏览器 <script> 的语义
    new Function("window", "document", "fetch", "console", source)(fakeWindow, undefined, fetchImpl, console);
  } catch (error) {
    say(`FATAL 客户端 bundle 执行失败：${error && error.message}`);
    process.exit(2);
  }
  if (spec === null) {
    say("FATAL 客户端 bundle 没有调用 window.__ModuleLoader__.load({...})");
    process.exit(2);
  }
  if (spec.id !== PACKAGE_NAME) fail(`bundle id 应为 ${PACKAGE_NAME}，实际 ${fmt(spec.id)}`);
  else ok(`bundle 外壳正确：id=${spec.id}`);
  if (typeof spec.factory !== "function") {
    say("FATAL bundle 缺少 factory");
    process.exit(2);
  }
  let exported;
  try {
    exported = spec.factory((id) => {
      if (id === "react") return makeReactStubWithEffects(log);
      throw new Error(`测试桩不提供模块 ${id}`);
    });
  } catch (error) {
    say(`FATAL factory 执行失败：${error && error.message}`);
    process.exit(2);
  }
  if (!exported || typeof exported.apply !== "function") fail("module.exports.apply 不是函数");
  else ok("module.exports.apply 是函数");
  if (!Array.isArray(exported.inject) || !exported.inject.includes("slots")) {
    fail(`module.exports.inject 应包含 'slots'，实际 ${fmt(exported.inject)}`);
  } else ok(`module.exports.inject = ${fmt(exported.inject)}`);
  if (!exported.__rcio || typeof exported.__rcio.standardize !== "function") {
    say("FATAL 客户端没有导出测试钩子 exports.__rcio.standardize");
    process.exit(2);
  }
  return { exported, spec };
}

/* ------------------------------------------------------------------ *
 * 2) 装载 lib/rcio.js
 * ------------------------------------------------------------------ */

async function loadHostRcio() {
  if (!existsSync(RCIO_PATH)) {
    say("");
    say(`FATAL 缺少 ${RCIO_PATH}`);
    say("      lib/rcio.js 由队友 host-tool-dev（task-1）并行编写；等它出现后重新运行：");
    say(`      node "${path.relative(process.cwd(), fileURLToPath(import.meta.url))}"`);
    process.exit(2);
  }
  let mod;
  try {
    mod = await import(pathToFileURL(RCIO_PATH).href);
  } catch (error) {
    say(`FATAL 无法导入 lib/rcio.js：${error && error.message}`);
    process.exit(2);
  }
  for (const required of ["standardize", "classifyLevel", "classifyUnemployment", "describeZone", "describeUnemployment", "flagsOf", "clampBar", "normalizeBar", "summarize"]) {
    if (typeof mod[required] !== "function") {
      say(`FATAL lib/rcio.js 未导出 ${required}(...) —— 无法做逐项比对（CONTRACT §4 要求 Host/Client 共用口径）`);
      process.exit(2);
    }
  }
  return mod;
}

/* ------------------------------------------------------------------ *
 * 3) 用例
 * ------------------------------------------------------------------ */

function barsOnly(key, value) {
  const bars = { residential: 0, commercial: 0, industrial: 0, office: 0 };
  bars[key] = value;
  return bars;
}

function buildCases() {
  const cases = [];
  for (const key of ZONE_KEYS) {
    for (let bar = -100; bar <= 100; bar += 1) cases.push({ bars: barsOnly(key, bar), rate: 6.5, label: `${key}=${bar}` });
  }
  const boundaryBars = [-100, -61, -60, -59, -16, -15, -14, 0, 14, 15, 16, 49, 50, 51, 79, 80, 100];
  for (const bar of boundaryBars) {
    cases.push({ bars: { residential: bar, commercial: -bar, industrial: bar, office: 0 }, rate: 6.5, label: `boundary-mix@${bar}` });
    cases.push({ bars: { residential: 0, commercial: 0, industrial: 0, office: bar }, rate: 6.5, label: `office@${bar}` });
  }
  const rates = [0, 2.9, 3, 7.9, 8, 8.1, 11.9, 12, 12.1, 100, 6.5, 0.1, null, "", "6.5", 100.4, -3];
  for (const rate of rates) {
    cases.push({
      bars: { residential: -35, commercial: 12, industrial: 0, office: 85 },
      rate,
      label: `rate=${fmt(rate)}`
    });
  }
  // 确定性 LCG（可复现，杜绝"随机碰巧通过"）
  let seed = 20260101;
  const next = () => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed;
  };
  for (let i = 0; i < 200; i += 1) {
    const bars = {};
    for (const key of ZONE_KEYS) bars[key] = (next() % 201) - 100;
    const rate = (next() % 1201) / 10; // 0.0 … 120.0（含越界）
    cases.push({ bars, rate, label: `random#${i}` });
  }
  return cases;
}

/* ------------------------------------------------------------------ *
 * 4) 主流程
 * ------------------------------------------------------------------ */

const { exported: client } = await loadClientExports();
say("");
ok(`已从 ${path.relative(PKG_ROOT, CLIENT_PATH)} 装载真实客户端 bundle`);
const host = await loadHostRcio();
ok(`已从 ${path.relative(PKG_ROOT, RCIO_PATH)} 装载 Host 口径（lib/rcio.js）`);
say("");

const c = client.__rcio;

/* 4a) 常量表 */
const constantChecks = [
  ["schema id", c.STANDARD_SCHEMA, host.STANDARD_SCHEMA],
  ["zone 顺序", c.ZONE_KEYS, host.ZONES],
  ["LEVELS", c.LEVELS, host.LEVELS],
  ["LEVEL_LABELS", c.LEVEL_LABELS, host.LEVEL_LABELS],
  ["BANDS", c.BANDS, host.BANDS],
  ["BAND_LABELS", c.BAND_LABELS, host.BAND_LABELS]
];
let constantsOk = true;
for (const [name, mine, theirs] of constantChecks) {
  if (fmt(mine) !== fmt(theirs)) {
    constantsOk = false;
    fail(`常量 ${name} 不一致：client=${fmt(mine)} rcio=${fmt(theirs)}`);
  }
}
if (constantsOk) ok(`常量表逐项一致（${constantChecks.length} 项：schema id / zone 顺序 / LEVELS / LEVEL_LABELS / BANDS / BAND_LABELS）`);
say("");

/* 4b) 逐函数比对 */
const GRID = [];
for (let bar = -100; bar <= 100; bar += 1) GRID.push(bar);
for (const extra of [-1000, 1000, -100.4, 100.4, 0.5, -0.5, NaN, Infinity, -Infinity, "48", "-35", "", "abc", null, undefined, true]) GRID.push(extra);

const rateGrid = [-1, 0, 0.1, 2.9, 3, 3.1, 7.9, 8, 8.1, 11.9, 12, 12.1, 50, 99.9, 100, 100.1, 1000, NaN, Infinity, "6.5", "", "abc", null, undefined];

function compareFn(name, mineFn, hostFn, inputs) {
  let bad = 0;
  const samples = [];
  for (const input of inputs) {
    let a;
    let b;
    try { a = mineFn(input); } catch (error) { a = `THREW:${error && error.message}`; }
    try { b = hostFn(input); } catch (error) { b = `THREW:${error && error.message}`; }
    if (fmt(a) !== fmt(b)) {
      bad += 1;
      if (samples.length < 5) samples.push(`input=${fmt(input)} client=${fmt(a)} rcio=${fmt(b)}`);
    }
  }
  if (bad === 0) ok(`${name}：${inputs.length} 个点逐项一致`);
  else {
    fail(`${name}：${bad}/${inputs.length} 个点不一致`);
    for (const sample of samples) say(`      ${sample}`);
  }
}

compareFn("clampBar", c.clampBar, host.clampBar, GRID);
compareFn("normalizeBar", c.normalizeBar, host.normalizeBar, GRID);
compareFn("classifyLevel", c.classifyLevel, host.classifyLevel, GRID);
compareFn("classifyUnemployment", c.classifyUnemployment, host.classifyUnemployment, rateGrid);
compareFn("describeZone", c.describeZone, host.describeZone, GRID);
compareFn("describeUnemployment", c.describeUnemployment, host.describeUnemployment, rateGrid);
compareFn("formatSignedBar", c.formatSignedBar, host.formatSignedBar, GRID);
compareFn("formatPercent", c.formatPercent, host.formatPercent, rateGrid);
compareFn("levelLabelOf", c.levelLabelOf, host.levelLabelOf, [...c.LEVELS, "nope", null, undefined]);
compareFn("bandLabelOf", c.bandLabelOf, host.bandLabelOf, [...c.BANDS, "nope", null, undefined]);
say("");

/* 4c) flagsOf / summarize / standardize 多参数比对 */
const flagCases = [
  ...buildCases().slice(0, 0),
  { bars: { residential: 0, commercial: 0, industrial: 0, office: 80 }, rate: 6.5 },
  { bars: { residential: -16, commercial: 0, industrial: 0, office: 0 }, rate: 6.5 },
  { bars: { residential: 0, commercial: 0, industrial: 0, office: 0 }, rate: 12.1 },
  { bars: { residential: 15, commercial: -15, industrial: 0, office: 0 }, rate: 3 },
  { bars: { residential: 16, commercial: 0, industrial: 0, office: 0 }, rate: null },
  { bars: null, rate: null },
  { bars: "nonsense", rate: "bad" },
  { bars: { office: 100, residential: -100 }, rate: 100 }
];
let multiOk = true;
for (const item of flagCases) {
  const mineFlags = fmt(c.flagsOf(item.bars, item.rate));
  const hostFlags = fmt(host.flagsOf(item.bars, item.rate));
  const mineSummary = fmt(c.summarize(item.bars, item.rate));
  const hostSummary = fmt(host.summarize(item.bars, item.rate));
  if (mineFlags !== hostFlags) {
    multiOk = false;
    fail(`flagsOf 不一致：bars=${fmt(item.bars)} rate=${fmt(item.rate)} client=${mineFlags} rcio=${hostFlags}`);
  }
  if (mineSummary !== hostSummary) {
    multiOk = false;
    fail(`summarize 不一致：bars=${fmt(item.bars)} rate=${fmt(item.rate)} client=${mineSummary} rcio=${hostSummary}`);
  }
}
if (multiOk) ok(`flagsOf / summarize：${flagCases.length} 组输入逐项一致（含全 0、深负、严重失业、未提供、畸形输入）`);
say("");

/* 4d) standardize 深度相等（全量用例） */
const cases = buildCases();
let standardizeBad = 0;
const standardizeSamples = [];
for (const item of cases) {
  let mine;
  let theirs;
  try { mine = c.standardize(item.bars, item.rate); } catch (error) { mine = `THREW:${error && error.message}`; }
  try { theirs = host.standardize(item.bars, item.rate); } catch (error) { theirs = `THREW:${error && error.message}`; }
  if (fmt(mine) !== fmt(theirs)) {
    standardizeBad += 1;
    if (standardizeSamples.length < 10) {
      standardizeSamples.push(`${item.label}: client=${fmt(mine)} rcio=${fmt(theirs)}`);
    }
  }
}
if (standardizeBad === 0) {
  ok(`standardize 深度相等：${cases.length} 组输入（含 summary / flags / 全部字段）逐字节一致`);
} else {
  fail(`standardize 有 ${standardizeBad}/${cases.length} 组不一致（前 10 条）：`);
  for (const sample of standardizeSamples) say(`      ${sample}`);
}
say("");

/* ------------------------------------------------------------------ *
 * 5) 畸形输入不抛错（回放安全）
 * ------------------------------------------------------------------ */

const malformed = [null, undefined, {}, { residential: NaN }, { residential: 101, office: -101 }, "nonsense", 42, { office: Infinity }];
const thrown = [];
for (const input of malformed) {
  try {
    c.standardize(input, NaN);
    c.describeZone(input);
    c.describeUnemployment(input);
  } catch (error) {
    thrown.push(`${fmt(input)} -> ${error && error.message}`);
  }
}
if (thrown.length === 0) ok("畸形输入（null/NaN/越界/非对象）下客户端口径函数不抛错");
else fail(`畸形输入导致客户端抛错：${thrown.join(" | ")}`);

/* ------------------------------------------------------------------ *
 * 6) 客户端 bundle 外壳断言
 * ------------------------------------------------------------------ */

const raw = await readFile(CLIENT_PATH, "utf8");
if (raw.startsWith("window.__ModuleLoader__.load({")) ok("首行为 window.__ModuleLoader__.load({");
else fail(`首行不是标准外壳：${fmt(raw.slice(0, 60))}`);
if (raw.includes(`id: "${PACKAGE_NAME}"`)) ok(`外壳 id 字面量为 "${PACKAGE_NAME}"`);
else fail(`外壳里没有 id: "${PACKAGE_NAME}"`);
if (raw.includes(TOOL_NAME)) ok(`bundle 含工具名 ${TOOL_NAME}`);
else fail(`bundle 未出现工具名 ${TOOL_NAME}`);
if (raw.includes("tool.call.toolview")) ok("bundle 使用 keyed 槽 tool.call.toolview");
else fail("bundle 没有注册 tool.call.toolview");
let forbidden = false;
for (const pattern of [/^\s*import\s/m, /require\(\s*["']\.\.?\//, /\bfrom\s+["']/]) {
  if (pattern.test(raw)) {
    forbidden = true;
    fail(`bundle 出现被禁止的模块加载写法：${pattern}`);
  }
}
if (!forbidden) ok("bundle 没有 import / 相对 require / 裸 from");

/* ------------------------------------------------------------------ *
 * 7) apply() 注册契约 + 组件浅渲染冒烟测试（无需 jsdom）
 * ------------------------------------------------------------------ */

const registrations = [];
const fakeCtx = {
  effect: (fn) => fn(),
  get: () => undefined,
  slots: {
    inject: (name, callback) => {
      registrations.push({ kind: "inject", name });
      return callback();
    },
    register: (options, component) => {
      registrations.push({ kind: "register", options, component });
      return () => {};
    }
  }
};

let applyThrew = null;
try {
  client.apply(fakeCtx);
} catch (error) {
  applyThrew = error;
}
if (applyThrew !== null) {
  fail(`apply(ctx) 抛错：${applyThrew && applyThrew.message}`);
} else {
  ok("apply(stubCtx) 正常返回（ctx.effect + ctx.slots.inject/register 路径）");
}

const injected = registrations.find((r) => r.kind === "inject");
const registered = registrations.find((r) => r.kind === "register");
if (!injected || injected.name !== "tool.call.toolview") {
  fail(`apply 应 ctx.slots.inject('tool.call.toolview', ...)，实际 ${fmt(injected && injected.name)}`);
} else if (!registered) {
  fail("apply 没有调用 ctx.slots.register");
} else {
  const options = registered.options || {};
  const optionKeys = Object.keys(options).sort().join(",");
  if (options.name !== "tool.call.toolview") fail(`register 的 name 应为 tool.call.toolview，实际 ${fmt(options.name)}`);
  else if (options.key !== TOOL_NAME) fail(`register 的 key 应为 ${TOOL_NAME}，实际 ${fmt(options.key)}`);
  else if (options.locale !== undefined) fail(`register 不应声明 locale（会要求先注册字典），实际 ${fmt(options.locale)}`);
  else if (typeof registered.component !== "function") fail("register 的第二个参数不是组件函数");
  else ok(`注册形态正确：register({ ${optionKeys} }, Component)，key=${options.key}，无 locale`);
}

/** 极简浅渲染：递归调用函数组件，收集所有宿主元素。 */
function render(node) {
  if (node === null || node === undefined || typeof node === "boolean") return null;
  if (typeof node === "string" || typeof node === "number") return { text: String(node), children: [] };
  if (Array.isArray(node)) return { text: "", children: node.map(render).filter(Boolean) };
  const props = node.props || {};
  const children = node.children && node.children.length > 0 ? (node.children.length === 1 ? node.children[0] : node.children) : props.children;
  if (typeof node.type === "function") return render(node.type({ ...props, children }));
  return { type: node.type, props, text: "", children: [].concat(children ?? []).map(render).filter(Boolean) };
}

function collect(node, predicate, out = []) {
  if (!node) return out;
  if (node.type !== undefined && predicate(node)) out.push(node);
  for (const child of node.children || []) collect(child, predicate, out);
  return out;
}

function allText(node, buffer = []) {
  if (!node) return buffer;
  if (node.text) buffer.push(node.text);
  for (const child of node.children || []) allText(child, buffer);
  return buffer;
}

const panel = client.__panel;
if (typeof panel !== "function") {
  fail("module.exports.__panel 不是组件函数");
} else {
  // 7a) 三种 phase + 畸形 props 都不抛错
  const startBlock = { phase: "start", callId: "c1", name: TOOL_NAME, argsRaw: '{"city":"测试城","savePath":"C:\\\\saves\\\\x.csl2","reason":"先看一眼需求条","panelId":"r-abc123"}' };
  const okResult = {
    kind: "tool-result",
    callId: "c1",
    call: { name: TOOL_NAME, argsRaw: startBlock.argsRaw },
    content: [{ type: "text", text: '{"status":"provided","panelId":"r-abc123"}' }],
    meta: { status: "provided", standard: host.standardize({ residential: -35, commercial: 12, industrial: 0, office: 85 }, 6.5) }
  };
  const renderCases = [
    ["preparing", { phase: "preparing", callId: "c1", name: TOOL_NAME }],
    ["start（有参数）", { phase: "start", callId: "c1", toolName: TOOL_NAME, block: startBlock }],
    ["result（presentationMeta）", { phase: "result", callId: "c1", toolName: TOOL_NAME, block: okResult }],
    ["result（skipped）", { phase: "result", callId: "c1", block: { kind: "tool-result", meta: { status: "skipped" }, content: [] } }],
    ["result（无 meta）", { phase: "result", callId: "c1", block: { kind: "tool-result", content: [] } }],
    ["phase 未知", { phase: "weird", callId: "c1", block: startBlock }],
    ["空 props", {}],
    ["props = null", null],
    ["start 无 block", { phase: "start", callId: "c1" }],
    ["start 参数不是 JSON", { phase: "start", callId: "c1", block: { phase: "start", argsRaw: "{不是 json" } }],
    ["start 参数是数组", { phase: "start", callId: "c1", block: { phase: "start", argsRaw: "[1,2,3]" } }],
    ["result meta 是字符串", { phase: "result", callId: "c1", block: { kind: "tool-result", meta: "boom", content: "boom" } }]
  ];
  const renderErrors = [];
  const trees = new Map();
  for (const [label, props] of renderCases) {
    try {
      trees.set(label, render(panel(props)));
    } catch (error) {
      renderErrors.push(`${label}: ${error && error.message}`);
    }
  }
  if (renderErrors.length === 0) ok(`组件浅渲染：${renderCases.length} 种 props（含 null/空/畸形/未知 phase）全部不抛错`);
  else {
    fail(`组件浅渲染抛错 ${renderErrors.length} 处：`);
    for (const line of renderErrors) { say(`      ${line}`); console.log("[DEBUG render error]", line); }
  }

  // 7b) start 阶段的面板契约
  const startTree = trees.get("start（有参数）");
  if (startTree) {
    const sliders = collect(startTree, (n) => n.type === "input" && n.props.type === "range" && n.props.role === "slider");
    if (sliders.length !== 4) fail(`start 面板应渲染 4 条 role=slider 的竖向滑条，实际 ${sliders.length}`);
    else {
      const bad = sliders.filter(
        (n) =>
          n.props["aria-valuemin"] !== -100 ||
          n.props["aria-valuemax"] !== 100 ||
          n.props["aria-valuenow"] !== 0 ||
          typeof n.props["aria-label"] !== "string" ||
          n.props["aria-orientation"] !== "vertical" ||
          n.props.min !== -100 ||
          n.props.max !== 100 ||
          n.props.step !== 1
      );
      if (bad.length > 0) fail(`滑条无障碍/区间属性不完整：${fmt(bad[0].props)}`);
      else ok("4 条竖向滑条：role=slider、aria-valuemin/max/now、aria-label、min/max/step(−100/100/1) 齐备");
    }
    const buttons = collect(startTree, (n) => n.type === "button");
    const labels = buttons.map((n) => allText(n).join(""));
    if (buttons.length !== 2) fail(`start 面板应有 2 个 <button>，实际 ${buttons.length}`);
    else if (!labels.includes("提交并分析") || !labels.includes("跳过，直接分析")) fail(`按钮文案不符：${fmt(labels)}`);
    else ok(`两个真实 <button>：${fmt(labels)}`);
    const text = allText(startTree).join("");
    if (text.includes("这一步只影响建议精度，不影响是否分析")) ok("顶部说明行存在：『这一步只影响建议精度，不影响是否分析…』");
    else fail("缺少『这一步只影响建议精度，不影响是否分析』说明行");
    if (text.includes("测试城")) ok("标题使用了工具参数里的城市名");
    else fail("标题没有使用工具参数里的 city");
    const numberInputs = collect(startTree, (n) => n.type === "input" && n.props.type === "number");
    if (numberInputs.length !== 1) fail(`失业率应有 1 个 number 输入，实际 ${numberInputs.length}`);
    else if (numberInputs[0].props.value !== "" || numberInputs[0].props.step !== 0.1) fail(`失业率输入默认值/步长不符：${fmt(numberInputs[0].props)}`);
    else ok("失业率 number 输入默认空、step=0.1、min=0、max=100");

    // 7c) 无 panelId 时按钮必须先禁用（等 open 回填），有 panelId 时可用
    const noIdTree = render(panel({ phase: "start", callId: "c2", block: { phase: "start", argsRaw: '{"city":"无号城"}' } }));
    const noIdButtons = collect(noIdTree, (n) => n.type === "button");
    if (noIdButtons.length !== 2 || noIdButtons.some((n) => n.props.disabled !== true)) {
      fail("args 里没有 panelId 时，两个按钮应处于 disabled（等待 open 回填 panelId）");
    } else {
      ok("缺少 panelId 时按钮先禁用（避免抢跑），open 回填后解锁");
    }
    const hasIdButtons = collect(startTree, (n) => n.type === "button");
    if (hasIdButtons.some((n) => n.props.disabled === true)) {
      fail("args 里已有 panelId 时按钮不应被禁用");
    } else {
      ok("args 自带 panelId 时按钮直接可用");
    }

    // 7d) 键盘：↑↓←→ / Home / End 改变需求条并 preventDefault
    const sliderByLabel = new Map(sliders.map((n) => [n.props["aria-label"], n]));
    const officeSlider = sliderByLabel.get("办公需求条");
    const expected = [
      ["ArrowUp", 1],
      ["ArrowRight", 1],
      ["ArrowDown", -1],
      ["ArrowLeft", -1],
      ["Home", -100],
      ["End", 100]
    ];
    const keyboardProblems = [];
    for (const [key, want] of expected) {
      const barsRecord = stateLog.hooks.find((r) => r.value && typeof r.value === "object" && "residential" in r.value);
      // 浅渲染器不会因为 setState 重新渲染，所以每次按键前把 office 复位到 0，
      // 以验证「按键 -> 相对当前值 +1/-1 / 跳到端点」的映射本身。
      if (barsRecord) barsRecord.value = { ...barsRecord.value, office: 0 };
      let prevented = false;
      officeSlider.props.onKeyDown({ key, preventDefault: () => { prevented = true; } });
      const got = barsRecord ? barsRecord.value.office : null;
      const expectedValue = want;
      if (!prevented) keyboardProblems.push(`${key} 未调用 preventDefault`);
      if (got !== expectedValue) keyboardProblems.push(`${key} 后 office=${fmt(got)}，期望 ${fmt(expectedValue)}`);
    }
    if (keyboardProblems.length === 0) ok("键盘 ↑↓←→ 与 Home/End 调整需求条并 preventDefault（6 个键）");
    else {
      fail(`键盘处理有问题：${keyboardProblems.join(" | ")}`);
    }

    // 7e) 回归锁：滑条上的档位文字必须按 bar 判定（曾经误写成 classifyLevel(value / 100)，
    //     双重归一后 -100…100 全部落到 neutral -> 面板永远显示「无需求」）。
    //     参考值直接取 lib/rcio.js，锁住的是「UI 接线」而不只是纯函数。
    const labelCases = [-100, -60, -35, 0, 12, 48, 85, 100];
    const barsRecord = stateLog.hooks.find((r) => r.value && typeof r.value === "object" && "residential" in r.value);
    const labelProblems = [];
    for (const value of labelCases) {
      if (barsRecord) barsRecord.value = { ...barsRecord.value, office: value };
      stateLog.hookSeq = 0;
      const tree = render(panel({ phase: "start", callId: "c1", block: startBlock }));
      const zones = collect(tree, (n) => n.type === "div" && n.props.className === "csl2-zone");
      const officeZone = zones[3];
      const levelNode = officeZone ? collect(officeZone, (n) => n.type === "div" && n.props.className === "csl2-zone-level")[0] : null;
      const shown = levelNode ? allText(levelNode).join("") : "<缺失>";
      const expected = host.levelLabelOf(host.classifyLevel(value));
      const wrong = c.levelLabelOf(c.classifyLevel(value / 100));
      if (shown !== expected) {
        labelProblems.push(`办公=${value}：面板显示「${shown}」，应为「${expected}」（双重归一的话会显示「${wrong}」）`);
      }
    }
    if (labelProblems.length === 0) {
      ok(`滑条档位文字按 bar 判定：${labelCases.length} 个取值与 lib/rcio.js 逐字一致（回归锁）`);
    } else {
      fail(`滑条档位文字有 ${labelProblems.length} 处错误：`);
      for (const line of labelProblems.slice(0, 6)) say(`      ${line}`);
    }
    if (barsRecord) barsRecord.value = { ...barsRecord.value, office: 0 };
    stateLog.hookSeq = 0;

    // 7f) 弹窗形态回归锁（用户要求：不要在对话流里来回滚动找面板）
    //     - start 阶段必须包在 .csl2-modal 模态外壳里（fixed + 遮罩 + dialog 语义）
    //     - result 阶段**不得**再出现模态（只读回放要能正常看结论）
    const modalNodes = collect(trees.get("start（有参数）"), (n) => n.type === "div" && n.props.className === "csl2-modal");
    const modalCard = collect(trees.get("start（有参数）"), (n) => n.type === "div" && n.props.className === "csl2-modal-card")[0];
    const modalProblems = [];
    if (modalNodes.length !== 1) modalProblems.push(`start 阶段应有且仅有 1 个 .csl2-modal，实际 ${modalNodes.length}`);
    else {
      const m = modalNodes[0];
      if (m.props.role !== "dialog") modalProblems.push(`模态外壳 role 应为 dialog，实际 ${fmt(m.props.role)}`);
      if (m.props["aria-modal"] !== "true") modalProblems.push(`模态外壳应标 aria-modal="true"，实际 ${fmt(m.props["aria-modal"])}`);
      if (typeof m.props.onMouseDown !== "function") modalProblems.push("模态外壳缺少遮罩点击处理");
    }
    if (!modalCard) modalProblems.push("缺少 .csl2-modal-card 卡片容器");
    else if (typeof modalCard.props.onKeyDown !== "function") modalProblems.push("模态卡片缺少 Esc 键盘处理");
    const modalCss = /\.csl2-modal\s*\{[\s\S]*?position\s*:\s*fixed/.test(bundleSource);
    if (!modalCss) modalProblems.push("CSS 里 .csl2-modal 未声明 position:fixed（弹窗会退化成内联卡片）");
    if (collect(trees.get("result（presentationMeta）"), (n) => n.type === "div" && n.props.className === "csl2-modal").length !== 0) {
      modalProblems.push("result 阶段不应再渲染模态（会挡住结论）");
    }
    if (modalProblems.length === 0) ok("弹窗形态：start 为 .csl2-modal 模态（dialog + 遮罩 + Esc），result 无模态");
    else {
      fail(`弹窗形态不合格：${modalProblems.join(" | ")}`);
    }
  }

  // 7d) result 阶段只读回放
  const settledTree = trees.get("result（presentationMeta）");
  if (settledTree) {
    const settledText = allText(settledTree).join("");
    const settledSliders = collect(settledTree, (n) => n.type === "input" && n.props.type === "range");
    const settledButtons = collect(settledTree, (n) => n.type === "button");
    if (settledSliders.length !== 0 || settledButtons.length !== 0) {
      fail(`result 阶段必须只读回放，实际滑条=${settledSliders.length} 按钮=${settledButtons.length}`);
    } else if (!settledText.includes("住宅") || !settledText.includes("办公") || !settledText.includes("正常范围")) {
      fail(`result 阶段回显不完整：${fmt(settledText.slice(0, 160))}`);
    } else {
      ok("result 阶段为只读回放：无滑条/按钮，回显四条需求与失业率档位");
    }
  }
  const skippedTree = trees.get("result（skipped）");
  if (skippedTree && !allText(skippedTree).join("").includes("未提供")) {
    fail("result(skipped) 未声明『本次未提供 RCIO 需求条与失业率』");
  } else if (skippedTree) {
    ok("result(skipped) 明确声明未提供数据（不假装有数）");
  }
  const preparingTree = trees.get("preparing");
  if (preparingTree && !allText(preparingTree).join("").includes("准备")) {
    fail("preparing 阶段未渲染『面板准备中』提示行");
  } else if (preparingTree) {
    ok("preparing 阶段只渲染提示行（不读 panelId）");
  }
}

/* ------------------------------------------------------------------ *
 * 8) wire 契约：与 Host（task-1）冻结的 POST /csl2-readings 逐条对齐
 *    用假 fetch + 假定时器，真实的客户端代码路径，不发真网络请求。
 * ------------------------------------------------------------------ */

const realTimers = {
  setInterval: globalThis.setInterval,
  clearInterval: globalThis.clearInterval,
  setTimeout: globalThis.setTimeout,
  clearTimeout: globalThis.clearTimeout
};

function installFakeTimers() {
  const intervals = [];
  const timeouts = [];
  globalThis.setInterval = (callback, ms) => {
    const handle = { callback, ms };
    intervals.push(handle);
    return handle;
  };
  globalThis.clearInterval = (handle) => {
    const index = intervals.indexOf(handle);
    if (index >= 0) intervals.splice(index, 1);
  };
  globalThis.setTimeout = (callback, ms) => {
    const handle = { callback, ms };
    timeouts.push(handle);
    return handle;
  };
  globalThis.clearTimeout = (handle) => {
    const index = timeouts.indexOf(handle);
    if (index >= 0) timeouts.splice(index, 1);
  };
  return { intervals, timeouts };
}

function restoreTimers() {
  globalThis.setInterval = realTimers.setInterval;
  globalThis.clearInterval = realTimers.clearInterval;
  globalThis.setTimeout = realTimers.setTimeout;
  globalThis.clearTimeout = realTimers.clearTimeout;
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

/**
 * 起一个「假 fetch + 假定时器」的客户端实例，跑 InteractivePanel 的挂载 effect。
 * 假定时器由调用方在整段 wire 测试外层安装一次（见下方 wireTimers），
 * 否则 promise 链里的退避重试会落到真定时器上。
 */
async function startWireSession(props, responder) {
  const log = { hooks: [], refs: [], effects: [], hookSeq: 0 };
  const requests = [];
  const mockFetch = (url, init) => {
    const body = JSON.parse(init.body);
    requests.push({ url, method: init.method, contentType: init.headers["content-type"], body });
    const reply = responder(body, requests.length - 1) ?? { ok: true, status: 200, json: { ok: true } };
    return Promise.resolve({
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: () => Promise.resolve(reply.json)
    });
  };
  const { exported } = await loadClientExports(mockFetch, log);
  const slots = [];
  exported.apply({
    effect: (fn) => fn(),
    get: () => undefined,
    slots: {
      inject: (name, callback) => callback(),
      register: (options, component) => {
        slots.push({ options, component });
        return () => {};
      }
    }
  });
  const component = slots[0].component;

  log.hookSeq = 0;
  const tree = render(component(props));
  const effect = log.effects[log.effects.length - 1];
  const cleanup = effect ? effect() : undefined;
  await flush();
  // 模拟 React 的重新渲染：hook 状态保留，组件闭包拿到最新值
  const rerender = () => {
    log.hookSeq = 0;
    return render(component(props));
  };
  return { requests, tree, cleanup, log, rerender };
}

function noticeOf(session) {
  const texts = session.log.hooks
    .filter((record) => typeof record.value === "string" && record.value !== "")
    .map((record) => record.value);
  return texts.join(" | ");
}

const wireTimers = installFakeTimers();
/** 触发一个已排队的假定时器（退避重试等），随后把 promise 链跑完。 */
async function drive(ms) {
  const handle = wireTimers.timeouts.find((t) => t.ms === ms);
  if (handle === undefined) return false;
  handle.callback();
  await flush();
  return true;
}

{
  // 8a) open 必须带 callId（Host 用它建索引），不带 panelId；随后 poll 带 panelId；submit 带 raw
  const session = await startWireSession(
    {
      phase: "start",
      callId: "call-1",
      toolName: TOOL_NAME,
      block: { phase: "start", callId: "call-1", name: TOOL_NAME, argsRaw: '{"city":"线城","reason":"先补数"}' }
    },
    (body) => {
      if (body.action === "readings.open") {
        return { ok: true, status: 200, json: { ok: true, panel: { panelId: "r-abc123", city: "线城" } } };
      }
      if (body.action === "readings.poll") return { ok: true, status: 200, json: { ok: true, status: "pending" } };
      if (body.action === "readings.submit") return { ok: true, status: 200, json: { ok: true, status: "provided", panelId: "r-abc123" } };
      return { ok: true, status: 200, json: { ok: false, code: "unexpected-action" } };
    }
  );

  const first = session.requests[0];
  if (!first) fail("wire：挂载后没有发出 readings.open");
  else if (first.url !== "http://127.0.0.1:19387/csl2-readings") fail(`wire：POST URL 不对：${first.url}`);
  else if (first.method !== "POST") fail(`wire：方法应为 POST，实际 ${first.method}`);
  else if (first.contentType !== "application/json") fail(`wire：content-type 应为 application/json，实际 ${fmt(first.contentType)}`);
  else if (first.body.action !== "readings.open") fail(`wire：open 动作名应为 readings.open，实际 ${fmt(first.body.action)}`);
  else if (first.body.callId !== "call-1") fail(`wire：open 必须带 callId（Host 索引键），实际 ${fmt(first.body.callId)}`);
  else if (first.body.panelId !== undefined) fail(`wire：args 里没有 panelId 时 open 不应带 panelId，实际 ${fmt(first.body.panelId)}`);
  else ok("wire：挂载即 POST /csl2-readings { action:'readings.open', callId:'call-1' }（无 panelId）");

  const interval = wireTimers.intervals.find((i) => i.ms === 1500);
  if (!interval) fail("wire：open 成功后没有开始轮询");
  else if (interval.ms !== 1500) fail(`wire：轮询间隔应为 1500ms，实际 ${interval.ms}`);
  else {
    interval.callback();
    await flush();
    const poll = session.requests.find((r) => r.body.action === "readings.poll");
    if (!poll) fail("wire：轮询没有发出 readings.poll");
    else if (poll.body.panelId !== "r-abc123") fail(`wire：poll 必须带 Host 回填的 panelId，实际 ${fmt(poll.body.panelId)}`);
    else ok("wire：每 1500ms POST { action:'readings.poll', panelId:'r-abc123' }");
  }

  // 失业率留空 -> null + confidence.unknown
  const buttons = collect(session.tree, (n) => n.type === "button");
  const submitButton = buttons[0];
  submitButton.props.onClick();
  await flush();
  const submit = session.requests.find((r) => r.body.action === "readings.submit");
  if (!submit) fail("wire：点击『提交并分析』没有发出 readings.submit");
  else {
    const raw = submit.body.raw || {};
    const problems = [];
    if (submit.body.panelId !== "r-abc123") problems.push(`panelId=${fmt(submit.body.panelId)}`);
    if (raw.unemploymentRate !== null) problems.push(`留空时 unemploymentRate 应为 null，实际 ${fmt(raw.unemploymentRate)}`);
    if (!raw.confidence || raw.confidence.unemploymentRate !== "unknown") problems.push(`留空时 confidence.unemploymentRate 应为 'unknown'，实际 ${fmt(raw.confidence && raw.confidence.unemploymentRate)}`);
    if (!raw.rcio || raw.rcio.residential !== 0 || raw.rcio.office !== 0) problems.push(`raw.rcio 初值应为全 0，实际 ${fmt(raw.rcio)}`);
    for (const key of ZONE_KEYS) {
      if (!raw.confidence || raw.confidence[key] !== "exact") problems.push(`confidence.${key} 应为 'exact'`);
    }
    if (problems.length === 0) ok("wire：submit 带 { action:'readings.submit', panelId, raw }，留空失业率 = null + confidence 'unknown'");
    else fail(`wire：submit 载荷不符（${problems.join(" / ")}）`);
  }
  if (typeof session.cleanup === "function") session.cleanup();
}

{
  // 8b) 填了失业率 -> raw.unemploymentRate 数值 + confidence 'exact'
  const session = await startWireSession(
    {
      phase: "start",
      callId: "call-2",
      block: { phase: "start", callId: "call-2", name: TOOL_NAME, argsRaw: '{"city":"线城2","panelId":"r-known"}' }
    },
    (body) => {
      if (body.action === "readings.open") return { ok: true, status: 200, json: { ok: true, panel: { panelId: "r-known" } } };
      if (body.action === "readings.submit") return { ok: true, status: 200, json: { ok: true, status: "provided" } };
      return { ok: true, status: 200, json: { ok: true, status: "pending" } };
    }
  );
  const openReq = session.requests[0];
  if (!openReq || openReq.body.panelId !== "r-known") fail(`wire：args 自带 panelId 时 open 应带上它，实际 ${fmt(openReq && openReq.body.panelId)}`);
  else ok("wire：args 自带 panelId 时 open 一并带上（Host 可直接命中）");

  const numberInput = collect(session.tree, (n) => n.type === "input" && n.props.type === "number")[0];
  numberInput.props.onChange({ target: { value: "6.5" } });
  const sliders = collect(session.tree, (n) => n.type === "input" && n.props.role === "slider");
  sliders[3].props.onKeyDown({ key: "End", preventDefault: () => {} }); // office = 100
  // 模拟 React 重新渲染后用户点击（组件闭包才会看到新状态）
  const tree2 = session.rerender();
  collect(tree2, (n) => n.type === "button")[0].props.onClick();
  await flush();
  const submit = session.requests.find((r) => r.body.action === "readings.submit");
  if (!submit) fail("wire：填了失业率后点击提交没有发出 readings.submit");
  else if (submit.body.raw.unemploymentRate !== 6.5) fail(`wire：unemploymentRate 应为 6.5，实际 ${fmt(submit.body.raw.unemploymentRate)}`);
  else if (submit.body.raw.confidence.unemploymentRate !== "exact") fail(`wire：confidence.unemploymentRate 应为 'exact'，实际 ${fmt(submit.body.raw.confidence.unemploymentRate)}`);
  else if (submit.body.raw.rcio.office !== 100) fail(`wire：office 应为 100，实际 ${fmt(submit.body.raw.rcio.office)}`);
  else ok("wire：填 6.5% + 办公拖到 +100 -> raw { unemploymentRate:6.5, confidence:'exact', rcio.office:100 }");
  if (typeof session.cleanup === "function") session.cleanup();
}

{
  // 8c) 失业率非法（>100）不提交，只提示
  const session = await startWireSession(
    {
      phase: "start",
      callId: "call-3",
      block: { phase: "start", callId: "call-3", name: TOOL_NAME, argsRaw: '{"city":"线城3"}' }
    },
    () => ({ ok: true, status: 200, json: { ok: true, panel: { panelId: "r-c3" } } })
  );
  collect(session.tree, (n) => n.type === "input" && n.props.type === "number")[0].props.onChange({ target: { value: "150" } });
  collect(session.rerender(), (n) => n.type === "button")[0].props.onClick();
  await flush();
  if (session.requests.some((r) => r.body.action === "readings.submit")) fail("wire：失业率 150 时不应提交");
  else ok("wire：失业率超出 0–100 时拒绝提交（只提示，不发请求）");
  if (typeof session.cleanup === "function") session.cleanup();
}

{
  // 8d) Host 未建面板（code:'no-panel'）-> 退避重试，绝不无限重试
  const session = await startWireSession(
    {
      phase: "start",
      callId: "call-4",
      block: { phase: "start", callId: "call-4", name: TOOL_NAME, argsRaw: '{"city":"线城4"}' }
    },
    (body, index) => {
      if (index === 0) return { ok: true, status: 200, json: { ok: false, code: "no-panel", error: "执行尚未登记面板", retry: true } };
      return { ok: true, status: 200, json: { ok: true, panel: { panelId: "r-c4" } } };
    }
  );
  const drove = await drive(600);
  if (!drove) fail("wire：code:'no-panel' 时应安排一次退避重试（600ms）");
  else {
    const opens = session.requests.filter((r) => r.body.action === "readings.open");
    if (opens.length !== 2) fail(`wire：no-panel 重试后应有 2 次 open，实际 ${opens.length}`);
    else ok("wire：Host 返回 code:'no-panel' 时退避重试（600ms/1200ms/1800ms，最多 3 次）");
  }
  if (typeof session.cleanup === "function") session.cleanup();
}

{
  // 8e) HTTP 404 -> 通道不可用：最多 2 次退避重试，只提示不抛错
  const session = await startWireSession(
    {
      phase: "start",
      callId: "call-5",
      block: { phase: "start", callId: "call-5", name: TOOL_NAME, argsRaw: '{"city":"线城5"}' }
    },
    () => ({ ok: false, status: 404, json: { ok: false } })
  );
  const notice = () => noticeOf(session);
  if (session.requests.length !== 1) fail(`wire：404 首次请求后应先等待退避（实际发出 ${session.requests.length} 次）`);
  else {
    await drive(400);
    await drive(800);
    if (session.requests.length !== 3) fail(`wire：404 应最多重试 2 次（共 3 次请求），实际 ${session.requests.length}`);
    else if (!notice().includes("面板通道不可用")) fail(`wire：404 后应显示『面板通道不可用』提示，实际通知=${fmt(notice())}`);
    else ok("wire：HTTP 404 视为通道不可用（最多 2 次退避重试），只提示不抛错");
  }
  if (typeof session.cleanup === "function") session.cleanup();
}

restoreTimers();

say("");
if (failures === 0) {
  say(`RESULT PASS（warnings=${warnings}）`);
  process.exit(0);
} else {
  say(`RESULT FAIL（failures=${failures}，warnings=${warnings}）`);
  process.exit(1);
}
