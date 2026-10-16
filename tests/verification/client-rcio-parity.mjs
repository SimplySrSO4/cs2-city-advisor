/**
 * tests/verification/client-rcio-parity.mjs —— B6 / C-bundle 的独立验证
 *
 * 与作者自己的 `tests/client-rcio-parity.mjs` **无关**：这里从零另写一份比对逻辑，
 * 装载**真实的 lib/client.js bundle**（window.__ModuleLoader__.load 桩 + factory 的 require 桩），
 * 取出 `exports.__rcio` 钩子，与 `lib/rcio.js` 逐函数逐点比对；作者脚本的退出码另外单独跑一次并如实报告。
 *
 * 覆盖：
 *   B6.const.*      常量表（ZONE_KEYS/ZONE_LABELS/LEVELS/LEVEL_LABELS/BANDS/BAND_LABELS/SCHEMA）
 *   B6.random.*     500 组确定性随机输入 + -100…100 全整数网格 + 边界池，逐函数 + standardize 深度相等
 *   BUG1.static.*   静态：client.js 里不存在 classifyLevel(<...>/100) 的双重归一调用点
 *   BUG1.dynamic.*  动态：VerticalSlider 渲染出的档位文字与 lib/rcio.js 的 levelLabelOf(classifyLevel(bar)) 逐字一致
 *   BUG1.mutation   变异测试：把 bug 改回临时副本 -> 上面的动态断言必须失败（证明断言有牙）
 *   WIRE.open/poll  client 的 readings.open body 带 callId；四个动作名；poll 间隔 1500ms
 *   WIRE.business   业务失败 = HTTP 200 + body.ok:false（不是 4xx）；传输失败才退避重试
 *   AUTHOR.exitcode 作者脚本的退出码
 *
 * 运行：<node> tests/verification/client-rcio-parity.mjs [--json <path>]
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import * as HOST from '../../lib/rcio.js';
import { createReport, runCapture, LIB, PLUGIN, VERIFY_DIR, NODE, show, makeRandom } from './harness.mjs';

const r = createReport('client-rcio-parity');
const CLIENT_PATH = path.join(LIB, 'client.js');
const CLIENT_SOURCE = readFileSync(CLIENT_PATH, 'utf8');
const AUTHOR_TEST = path.join(PLUGIN, 'tests', 'client-rcio-parity.mjs');

/* ═════════════════════ 0) 装载器（bundle 是纯脚本，不是 ESM） ═════════════════════ */

const quietConsole = { warn() {}, error() {}, log() {}, info() {}, debug() {} };

/** 极简 React 桩：hook 状态按渲染序号持久化；effect 只记录不执行（避免真发 HTTP）。 */
function makeHookScope() {
  const hooks = [];
  let seq = 0;
  const effects = [];
  const react = {
    createElement: (type, props, ...children) => ({ type, props: props === undefined ? null : props, children }),
    useState(initial) {
      const index = seq++;
      if (!(index in hooks)) hooks[index] = { value: typeof initial === 'function' ? initial() : initial };
      const record = hooks[index];
      return [record.value, (next) => { record.value = typeof next === 'function' ? next(record.value) : next; }];
    },
    useRef(initial) {
      const index = seq++;
      if (!(index in hooks)) hooks[index] = { value: { current: initial } };
      return hooks[index].value;
    },
    useEffect(fn) { effects.push(fn); seq += 1; },
    useMemo(fn) { return fn(); },
    useCallback(fn) { return fn; },
    memo(component) { return component; },
    Fragment: Symbol.for('csl2.fragment')
  };
  return {
    react,
    effects,
    beginRender() { seq = 0; },
    runEffects() { const pending = effects.splice(0, effects.length); for (const fn of pending) fn(); return pending.length; }
  };
}

/**
 * 执行一段 bundle 源码，返回 { spec, mod }。
 * @param {string} source bundle 源码
 * @param {{fetchImpl?:Function, scope?:object}} options
 */
function loadBundle(source, options = {}) {
  const scope = options.scope ?? makeHookScope();
  let spec = null;
  const fakeWindow = {
    __ModuleLoader__: { load(value) { spec = value; } },
    location: { origin: 'http://127.0.0.1:19387' }
  };
  const run = new Function('window', 'document', 'fetch', 'console', source);
  run(fakeWindow, undefined, options.fetchImpl ?? (() => Promise.reject(new Error('no fetch stub'))), quietConsole);
  if (spec === null) throw new Error('bundle 没有调用 window.__ModuleLoader__.load({...})');
  const requireCalls = [];
  const mod = spec.factory((id) => {
    requireCalls.push(id);
    if (id === 'react') return scope.react;
    throw new Error(`测试桩不提供模块 ${id}`);
  });
  // apply()：设置内部 React 引用 + 注册槽位（不真渲染）
  const registered = [];
  mod.apply({
    slots: {
      inject(name, callback) { registered.push({ name, callback }); return () => {}; },
      register(options, component) { return { options, component }; }
    },
    effect(fn) { return typeof fn === 'function' ? fn() : undefined; },
    get() { return undefined; }
  });
  return { spec, mod, scope, requireCalls, registered };
}

/* ── 渲染小工具 ── */
function walk(node, visit) {
  if (node === null || node === undefined) return;
  if (Array.isArray(node)) { for (const child of node) walk(child, visit); return; }
  if (typeof node !== 'object') return;
  visit(node);
  walk(node.children, visit);
}
function collectByClass(tree, className) {
  const out = [];
  walk(tree, (node) => {
    const cn = node.props && node.props.className;
    if (typeof cn === 'string' && cn.split(/\s+/u).includes(className)) out.push(node);
  });
  return out;
}
function textOf(node) {
  if (node === null || node === undefined) return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(textOf).join('');
  return textOf(node.children);
}
function collectSliders(tree) {
  const out = [];
  walk(tree, (node) => {
    if (typeof node.type === 'function' && node.props && typeof node.props.aria === 'string'
      && typeof node.props.label === 'string' && 'value' in node.props) out.push(node);
  });
  return out;
}

/** 取面板卡片上状态行的文字：StatusLine 是函数组件元素（{text}），不展开也能读到它的 props.text。 */
function statusTextOf(tree) {
  let found = null;
  walk(tree, (node) => {
    if (found === null && typeof node.type === 'function' && node.props && typeof node.props.text === 'string') found = node.props.text;
  });
  return found === null ? '' : found;
}

const { mod: client, scope: labelScope } = loadBundle(CLIENT_SOURCE);
const CR = client.__rcio;
r.check('B6.hook.__rcio', CR !== null && typeof CR === 'object' && typeof CR.standardize === 'function',
  '客户端 bundle 暴露了 exports.__rcio 测试钩子（standardize 是函数）',
  `exports.__rcio 不可用：${show(CR)}`);

/* ═════════════════════ 1) 常量表 ═════════════════════ */

const constantPairs = [
  ['ZONE_KEYS', CR.ZONE_KEYS, HOST.ZONES],
  ['ZONE_LABELS', CR.ZONE_LABELS, HOST.ZONE_LABELS],
  ['LEVELS', CR.LEVELS, HOST.LEVELS],
  ['LEVEL_LABELS', CR.LEVEL_LABELS, HOST.LEVEL_LABELS],
  ['BANDS', CR.BANDS, HOST.BANDS],
  ['BAND_LABELS', CR.BAND_LABELS, HOST.BAND_LABELS],
  ['STANDARD_SCHEMA', CR.STANDARD_SCHEMA, HOST.STANDARD_SCHEMA]
];
const constBad = constantPairs.filter(([, a, b]) => !deepEqual(a, b)).map(([name, a, b]) => ({ name, client: a, host: b }));
r.check('B6.const.tables', constBad.length === 0,
  `7 张常量表逐项相等：${constantPairs.map(([name]) => name).join(' / ')}`,
  `常量表不一致：${show(constBad)}`);

/* ═════════════════════ 2) 逐函数 / standardize 比对 ═════════════════════ */

function deepEqual(a, b) {
  if (Object.is(a, b)) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null || typeof a !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  if (keysA.length !== keysB.length) return false;
  for (const key of keysA) {
    if (!Object.prototype.hasOwnProperty.call(b, key)) return false;
    if (!deepEqual(a[key], b[key])) return false;
  }
  return true;
}

const BAR_POOL = [-100, -61, -60, -59, -16, -15, -14, 0, 14, 15, 16, 49, 50, 51, 79, 80, 100, 101, -101,
  -0.5, 0.5, 2.5, -2.5, 99.6, -99.6, Number.NaN, null, undefined, 'abc', '', '12', '-35', {}, [], true];
const UO_POOL = [null, undefined, 0, 2.9, 3, 7.9, 8, 8.1, 11.9, 12, 12.1, 100, -1, 150, Number.NaN, 'abc', '', '6.5', 6.5, {}, []];

let comparisons = 0;
const mismatches = [];
function compare(label, hostValue, clientValue, sample) {
  comparisons += 1;
  if (!deepEqual(hostValue, clientValue)) {
    if (mismatches.length < 10) mismatches.push({ label, sample, host: hostValue, client: clientValue });
  }
}

const zoneFns = [
  ['clampBar', HOST.clampBar, CR.clampBar],
  ['normalizeBar', HOST.normalizeBar, CR.normalizeBar],
  ['classifyLevel', HOST.classifyLevel, CR.classifyLevel],
  ['levelLabelOf', HOST.levelLabelOf, CR.levelLabelOf],
  ['describeZone', HOST.describeZone, CR.describeZone],
  ['formatSignedBar', HOST.formatSignedBar, CR.formatSignedBar]
];
const fullBarGrid = [];
for (let bar = -100; bar <= 100; bar += 1) fullBarGrid.push(bar);
const barInputs = [...fullBarGrid, ...BAR_POOL];

for (const bar of barInputs) {
  for (const [name, hostFn, clientFn] of zoneFns) {
    let a; let b;
    try { a = hostFn(bar); } catch (error) { a = `THREW:${error.message}`; }
    try { b = clientFn(bar); } catch (error) { b = `THREW:${error.message}`; }
    compare(name, a, b, { bar });
  }
}

const bandFns = [
  ['classifyUnemployment', HOST.classifyUnemployment, CR.classifyUnemployment],
  ['bandLabelOf', HOST.bandLabelOf, CR.bandLabelOf],
  ['describeUnemployment', HOST.describeUnemployment, CR.describeUnemployment],
  ['formatPercent', HOST.formatPercent, CR.formatPercent]
];
const uoInputs = [...UO_POOL];
for (let step = 0; step <= 100; step += 1) uoInputs.push(step / 10);
for (const percent of uoInputs) {
  for (const [name, hostFn, clientFn] of bandFns) {
    let a; let b;
    try { a = hostFn(percent); } catch (error) { a = `THREW:${error.message}`; }
    try { b = clientFn(percent); } catch (error) { b = `THREW:${error.message}`; }
    compare(name, a, b, { percent });
  }
}

// 随机组合：rcio 四条 + 失业率（≥200 组，实际 500 组）
const random = makeRandom(0x5eed2026);
const RANDOM_CASES = 500;
for (let index = 0; index < RANDOM_CASES; index += 1) {
  const rcio = {};
  const zoneCount = 4 - Math.floor(random() * 1.5); // 有时故意缺字段
  for (let z = 0; z < zoneCount; z += 1) rcio[HOST.ZONES[z]] = BAR_POOL[Math.floor(random() * BAR_POOL.length)];
  if (random() < 0.12) { rcio[HOST.ZONES[Math.floor(random() * 4)]] = BAR_POOL[Math.floor(random() * BAR_POOL.length)]; }
  const unemployment = UO_POOL[Math.floor(random() * UO_POOL.length)];
  compare('standardize', HOST.standardize(rcio, unemployment), CR.standardize(rcio, unemployment), { rcio, unemployment });
  compare('flagsOf', HOST.flagsOf(rcio, unemployment), CR.flagsOf(rcio, unemployment), { rcio, unemployment });
  compare('summarize', HOST.summarize(rcio, unemployment), CR.summarize(rcio, unemployment), { rcio, unemployment });
}

// 契约 §1 那个示例也要逐项相同
compare('standardize.contractExample',
  HOST.standardize({ residential: -35, commercial: 12, industrial: 0, office: 85 }, 6.5),
  CR.standardize({ residential: -35, commercial: 12, industrial: 0, office: 85 }, 6.5),
  { example: true });

r.info(`B6 比对点总数 = ${comparisons}（含 -100…100 全整数网格 ${fullBarGrid.length} 点、随机组合 ${RANDOM_CASES} 组）`);
r.check('B6.random.parity', mismatches.length === 0,
  `lib/client.js 内联口径与 lib/rcio.js 在 ${comparisons} 个比对点上完全一致（0 个不一致）`,
  `发现 ${mismatches.length}+ 个不一致，前 10 个：${show(mismatches)}`);

/* ═════════════════════ 3) BUG1 静态断言：不得双重归一 ═════════════════════ */

const codeOnly = CLIENT_SOURCE
  .replace(/\/\*[\s\S]*?\*\//gu, ' ')
  .replace(/^\s*\/\/.*$/gmu, ' ')
  .replace(/(^|[^:])\/\/[^\n]*/gu, '$1 ');
const callSites = [];
const callRe = /classifyLevel\s*\(/gu;
let match;
while ((match = callRe.exec(codeOnly)) !== null) {
  const before = codeOnly.slice(Math.max(0, match.index - 30), match.index);
  if (/function\s+$/u.test(before)) continue; // 函数定义，不是调用点
  let depth = 0;
  let i = match.index + match[0].length - 1;
  let arg = '';
  for (; i < codeOnly.length; i += 1) {
    const ch = codeOnly[i];
    if (ch === '(') depth += 1;
    else if (ch === ')') { depth -= 1; if (depth === 0) break; }
    else if (depth >= 1) arg += ch;
  }
  callSites.push(arg.trim());
}
const doubleNormalized = callSites.filter((arg) => /\/\s*100\b/u.test(arg));
r.info(`classifyLevel 调用点（不含定义）：${show(callSites)}`);
r.check('BUG1.static.noDoubleNormalize', doubleNormalized.length === 0 && callSites.length >= 2,
  `${callSites.length} 个调用点的实参都不含 /100（不含双重归一）`,
  `发现疑似双重归一调用点：${show(doubleNormalized)}`);

/* ═════════════════════ 4) BUG1 动态断言：VerticalSlider 档位文字 ═════════════════════ */

const LABEL_BARS = [-100, -60, -35, 0, 12, 50, 80, 85, 100];
const EXPECTED_ZONE_LABELS = ['住宅', '商业', '工业', '办公'];

labelScope.beginRender();
const panelElement = client.__panel({
  phase: 'start',
  block: { phase: 'start', callId: 'call-A', name: 'csl2_city_readings', argsRaw: JSON.stringify({ city: '测试市', reason: '验证档位文字', savePath: 'C:/saves/测试市' }) },
  callId: 'call-A',
  toolName: 'csl2_city_readings'
});
const panelTree = typeof panelElement.type === 'function' ? panelElement.type(panelElement.props) : panelElement;
const sliders = collectSliders(panelTree);
r.check('BUG1.dynamic.sliderCount', sliders.length === 4 && sliders.map((node) => node.props.label).join(',') === EXPECTED_ZONE_LABELS.join(','),
  `InteractivePanel 渲染出 4 条竖向滑动条，顺序 ${show(sliders.map((node) => node.props.label))}`,
  `滑动条数量/顺序不符：${sliders.length} 条 ${show(sliders.map((node) => node.props.label))}`);

const labelBad = [];
const signedBad = [];
const ariaBad = [];
for (let zone = 0; zone < sliders.length; zone += 1) {
  for (const bar of LABEL_BARS) {
    const sliderTree = sliders[zone].type({ ...sliders[zone].props, value: bar });
    const levelNodes = collectByClass(sliderTree, 'csl2-zone-level');
    const valueNodes = collectByClass(sliderTree, 'csl2-zone-value');
    const levelText = levelNodes.length === 0 ? '(缺失)' : textOf(levelNodes[0]);
    const valueText = valueNodes.length === 0 ? '(缺失)' : textOf(valueNodes[0]);
    const expectedLevel = HOST.levelLabelOf(HOST.classifyLevel(bar));
    const expectedSigned = HOST.formatSignedBar(bar);
    if (levelText !== expectedLevel) labelBad.push({ zone: EXPECTED_ZONE_LABELS[zone], bar, expected: expectedLevel, actual: levelText });
    if (valueText !== expectedSigned) signedBad.push({ zone: EXPECTED_ZONE_LABELS[zone], bar, expected: expectedSigned, actual: valueText });
    // 无障碍：aria-valuetext = 带符号数值 + "，" + 档位文字
    const inputs = [];
    walk(sliderTree, (node) => { if (node.type === 'input' && node.props && node.props.type === 'range') inputs.push(node.props); });
    const expectedAria = `${expectedSigned}，${expectedLevel}`;
    if (inputs.length !== 1 || inputs[0]['aria-valuetext'] !== expectedAria) ariaBad.push({ zone: EXPECTED_ZONE_LABELS[zone], bar, expected: expectedAria, actual: inputs.map((p) => p['aria-valuetext']) });
  }
}
r.check('BUG1.dynamic.levelText', labelBad.length === 0,
  `VerticalSlider 在 bar = ${show(LABEL_BARS)} 上渲染出的档位文字与 lib/rcio.js 的 levelLabelOf(classifyLevel(bar)) 逐字一致（4 条 × ${LABEL_BARS.length} 个 bar = ${4 * LABEL_BARS.length} 个断言点）`,
  `档位文字不一致（${labelBad.length} 个）：${show(labelBad.slice(0, 8))}`);
r.check('BUG1.dynamic.signedText', signedBad.length === 0,
  `带符号数值文字与 formatSignedBar 一致（+48 / −35 / 0，U+2212）`,
  `带符号数值文字不一致：${show(signedBad.slice(0, 8))}`);
r.check('BUG1.dynamic.ariaValueText', ariaBad.length === 0,
  'input[type=range].aria-valuetext = "<带符号数值>，<档位文字>"',
  `aria-valuetext 不一致：${show(ariaBad.slice(0, 8))}`);

// 集成：从状态路径驱动（点滑动条 -> changeZone -> 重渲染 -> 档位文字变化）
labelScope.beginRender();
const panelTree2 = panelElement.type(panelElement.props);
const sliders2 = collectSliders(panelTree2);
const residentialSlider = sliders2[0];
residentialSlider.props.onChange(85);
labelScope.beginRender();
const panelTree3 = panelElement.type(panelElement.props);
const sliders3 = collectSliders(panelTree3);
const afterChange = collectByClass(sliders3[0].type({ ...sliders3[0].props, value: sliders3[0].props.value }), 'csl2-zone-level');
r.check('BUG1.dynamic.statePath',
  sliders3[0].props.value === 85 && afterChange.length === 1 && textOf(afterChange[0]) === '强需求',
  `onChange(85) -> InteractivePanel.bars.residential=85 -> 档位文字「强需求」`,
  `状态路径不符：value=${show(sliders3[0].props.value)} label=${show(afterChange.map(textOf))}`);

/* ═════════════════════ 5) 变异测试：把 bug 改回临时副本 ═════════════════════ */

const mutantsDir = path.join(VERIFY_DIR, 'mutants');
mkdirSync(mutantsDir, { recursive: true });
const MUTANT_PATH = path.join(mutantsDir, 'client-classifyLevel-double-normalize.js');
let mutantStatus = 'applied';
let mutantSource = CLIENT_SOURCE;
// 必须改在 VerticalSlider 的渲染路径上（第一处 classifyLevel(value) 在 describeZone 里，改了测不到卡片文字）。
const sliderStart = mutantSource.indexOf('function VerticalSlider(');
const valueCall = 'classifyLevel(value)';
const targetIndex = sliderStart >= 0 ? mutantSource.indexOf(valueCall, sliderStart) : -1;
if (targetIndex >= 0) {
  mutantSource = `${mutantSource.slice(0, targetIndex)}classifyLevel(value / 100)${mutantSource.slice(targetIndex + valueCall.length)}`;
} else {
  mutantStatus = 'pattern-not-found';
}
if (mutantStatus === 'applied') {
  writeFileSync(MUTANT_PATH, mutantSource, 'utf8');
  r.check('BUG1.mutation.applied', mutantSource !== CLIENT_SOURCE && mutantSource.includes('classifyLevel(value / 100)'),
    '变异副本已生成（VerticalSlider 内 classifyLevel(value) -> classifyLevel(value / 100)）',
    '变异副本没有真正改动源码');
  const { mod: mutant, scope: mutantScope } = loadBundle(mutantSource);
  mutantScope.beginRender();
  const mutantPanel = mutant.__panel({ phase: 'start', block: { argsRaw: JSON.stringify({ city: '测试市' }) }, callId: 'call-A' });
  const mutantTree = typeof mutantPanel.type === 'function' ? mutantPanel.type(mutantPanel.props) : mutantPanel;
  const mutantSliders = collectSliders(mutantTree);
  const mutantLabels = {};
  for (const bar of LABEL_BARS) {
    const tree = mutantSliders[0].type({ ...mutantSliders[0].props, value: bar });
    const nodes = collectByClass(tree, 'csl2-zone-level');
    mutantLabels[bar] = nodes.length === 0 ? '(缺失)' : textOf(nodes[0]);
  }
  const differ = LABEL_BARS.filter((bar) => mutantLabels[bar] !== HOST.levelLabelOf(HOST.classifyLevel(bar)));
  r.check('BUG1.mutation.detected', differ.length > 0,
    `变异副本（classifyLevel(value / 100)）在第 ${differ.length}/${LABEL_BARS.length} 个 bar 上与正确档位不符 -> 动态断言有牙；变异渲染值 ${show(mutantLabels)}`,
    `变异副本的档位文字与正确值完全相同 -> 动态断言无牙：${show(mutantLabels)}`);
  r.info(`变异副本路径：${MUTANT_PATH}（临时副本，未改动仓库文件）`);
} else {
  r.unverified('BUG1.mutation.detected', `没找到可替换的 classifyLevel(value) 调用点（${mutantStatus}）`);
}

/* ═════════════════════ 6) WIRE：open 带 callId / 动作名 / poll 间隔 / 业务失败语义 ═════════════════════ */

const realSetInterval = globalThis.setInterval;
const realClearInterval = globalThis.clearInterval;
const intervals = [];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function runWire(responses, { useFakeIntervals = true } = {}) {
  const calls = [];
  let index = 0;
  const fetchImpl = (url, init) => {
    let body = null;
    try { body = JSON.parse(init.body); } catch { body = null; }
    calls.push({ url, method: init.method, headers: init.headers, credentials: init.credentials, body });
    const next = responses[Math.min(index, responses.length - 1)];
    index += 1;
    if (next instanceof Error) return Promise.reject(next);
    return Promise.resolve({
      ok: next.ok,
      status: next.status,
      json: () => Promise.resolve(next.json)
    });
  };
  const scope = makeHookScope();
  const { mod } = loadBundle(CLIENT_SOURCE, { fetchImpl, scope });
  scope.beginRender();
  const element = mod.__panel({ phase: 'start', block: { argsRaw: JSON.stringify({ city: '测试市', reason: '验证 wire' }) }, callId: 'call-from-props' });
  const render = () => {
    scope.beginRender();
    return typeof element.type === 'function' ? element.type(element.props) : element;
  };
  let tree = render();
  if (useFakeIntervals) globalThis.setInterval = (callback, ms) => { const handle = { callback, ms, cleared: false }; intervals.push(handle); return handle; };
  scope.runEffects();
  await sleep(20);
  const cleanup = () => {
    for (const handle of intervals) { if (typeof handle === 'object' && typeof realClearInterval === 'function') realClearInterval.call(globalThis, handle); }
    globalThis.setInterval = realSetInterval;
  };
  return { calls, render, tree: () => tree, cleanup, scope };
}

// W1：open 成功 -> body 带 callId / action 全名 / panelId 未带；poll 间隔 1500ms
intervals.length = 0;
const wire1 = await runWire([
  { ok: true, status: 200, json: { ok: true, panel: { panelId: 'p-from-host' } } },
  { ok: true, status: 200, json: { ok: true, status: 'pending' } }
]);
const openCall = wire1.calls[0];
r.check('WIRE.open.body',
  openCall !== undefined && openCall.url === 'http://127.0.0.1:19387/csl2-readings' && openCall.method === 'POST'
  && openCall.headers && openCall.headers['content-type'] === 'application/json' && openCall.credentials === 'same-origin'
  && openCall.body && openCall.body.action === 'readings.open' && openCall.body.callId === 'call-from-props' && openCall.body.panelId === undefined,
  `open: POST /csl2-readings body=${show(openCall && openCall.body)}（带 callId，不带 panelId）`,
  `open body 不符：${show(openCall)}`);
r.check('WIRE.interval.cadence', intervals.length === 1 && intervals[0].ms === 1500,
  `拿到 panelId 后启动 1 个 setInterval，间隔 ${intervals.map((h) => h.ms).join(',')} ms`,
  `setInterval 形态不符：${show(intervals.map((h) => ({ ms: h.ms })))}`);
if (intervals.length >= 1) {
  intervals[0].callback();
  await sleep(20);
}
const pollCall = wire1.calls[1];
r.check('WIRE.poll.body',
  pollCall !== undefined && pollCall.body && pollCall.body.action === 'readings.poll' && pollCall.body.panelId === 'p-from-host',
  `poll: body=${show(pollCall && pollCall.body)}（用 Host 回填的 panelId）`,
  `poll body 不符：${show(pollCall)}`);
wire1.cleanup();

// W2：业务失败 = HTTP 200 + body.ok:false -> 不是「通道不可用」，按 no-panel 退避重试 1 次
intervals.length = 0;
const wire2 = await runWire([
  { ok: true, status: 200, json: { ok: false, code: 'no-panel', retry: true, error: '面板还没创建' } },
  { ok: true, status: 200, json: { ok: true, panel: { panelId: 'p2' } } }
]);
await sleep(60);
const statusAfterBusinessFail = statusTextOf(wire2.render());
const callsAfterBusinessFail = wire2.calls.length;
await sleep(750);
r.check('WIRE.businessFailureIsNotTransportFailure',
  statusAfterBusinessFail.includes('不可用') === false && statusAfterBusinessFail !== '' && callsAfterBusinessFail === 1 && wire2.calls.length === 2
  && wire2.calls[1].body.action === 'readings.open' && wire2.calls[1].body.callId === 'call-from-props',
  `HTTP 200 + ok:false(code:no-panel) 未按通道不可用处理（状态行="${statusAfterBusinessFail}"），只触发 1 次业务退避重试（共 ${wire2.calls.length} 次 fetch）`,
  `业务失败语义不符：calls=${wire2.calls.length} 状态行="${statusAfterBusinessFail}"`);
wire2.cleanup();

// W3：传输失败（HTTP 500）-> 退避重试 MAX_RETRIES=2 次（共 3 次 fetch）后显示通道不可用
intervals.length = 0;
const wire3 = await runWire([
  { ok: false, status: 500, json: {} },
  { ok: false, status: 500, json: {} },
  { ok: false, status: 500, json: {} }
]);
await sleep(1500);
r.check('WIRE.transportFailureRetries',
  wire3.calls.length === 3,
  `HTTP 500 -> 共 ${wire3.calls.length} 次 fetch（首试 + 2 次退避重试）`,
  `传输失败重试次数不符：${wire3.calls.length}`);
r.info(`HTTP 500 后的状态行="${statusTextOf(wire3.render())}"`);
wire3.cleanup();

// W4：四个动作名都是 readings.* 全名（源码级）
const actionLiterals = [...CLIENT_SOURCE.matchAll(/"(readings\.[a-z]+)"/gu)].map((m) => m[1]);
r.check('WIRE.actionNames',
  ['readings.open', 'readings.submit', 'readings.skip', 'readings.poll'].every((name) => actionLiterals.includes(name)),
  `客户端出现的动作名：${show([...new Set(actionLiterals)])}`,
  `四个动作名不全：${show([...new Set(actionLiterals)])}`);

/* ═════════════════════ 7) 作者脚本的退出码 ═════════════════════ */

const authorRun = runCapture(NODE, [AUTHOR_TEST], { timeout: 600000 });
const authorTail = authorRun.output.trim().split('\n').slice(-4).join(' | ');
r.check('AUTHOR.exitcode', authorRun.status === 0,
  `作者 tests/client-rcio-parity.mjs 退出码 0；末行：${authorTail}`,
  `作者 tests/client-rcio-parity.mjs 退出码 ${authorRun.status}（error=${show(authorRun.error)}）；末行：${authorTail}`);

r.finish();
