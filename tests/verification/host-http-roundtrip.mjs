/**
 * tests/verification/host-http-roundtrip.mjs —— C. Host 工具可加载性（**真 HTTP 往返**）
 *
 * C7  import() lib/index.js 的导出形状
 * C8  stub ctx 跑 apply()：工具定义 / 一条 prefix 路由 / skill provider（用 Proxy 记录「未实现却被访问」的成员）
 * C9  把捕获到的 handler 接到真的 node:http server 上：open / poll / submit / skip / 重复 submit /
 *     405 / 404 / 400 / 并发两个面板（各带自己的 callId）不串数据
 * C10 超时与取消：CSL2_NO_CLIENT_MS=120 -> ~120ms 返回 unavailable；exec.signal 取消 -> 降级 + 清理 Map；
 *     timeoutSec 夹取；总超时分支（timeoutSec:30，实测约 30 s）
 *
 * 运行：<node> tests/verification/host-http-roundtrip.mjs [--json <path>]
 */

import http from 'node:http';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { deepStrictEqual } from 'node:assert/strict';
import { createReport, LIB, PLUGIN, show } from './harness.mjs';
import * as HOST from '../../lib/rcio.js';

const r = createReport('host-http-roundtrip');
const MODULE_PATH = fileURLToPath(new URL('../../lib/index.js', import.meta.url));
let mod;
try {
  mod = await import(pathToFileURL(MODULE_PATH).href);
} catch (error) {
  r.fatal(`import(${MODULE_PATH}) 失败：${error instanceof Error ? error.stack : String(error)}`);
}

/* ═════════════════════ C7 导出形状 ═════════════════════ */

r.check('C7.exports', mod.name === 'csl2-city-advisor' && Array.isArray(mod.inject) && mod.inject.includes('tools') && mod.inject.includes('skills') && typeof mod.apply === 'function',
  `name=${show(mod.name)}；inject=${show(mod.inject)}（含 tools + skills）；apply 是 ${typeof mod.apply}`,
  `导出形状不符：name=${show(mod.name)} inject=${show(mod.inject)} apply=${typeof mod.apply}`);
r.info(`lib/index.js 导出：${show(Object.keys(mod))}`);

/* ═════════════════════ C8 stub ctx + apply() ═════════════════════ */

const registeredTools = [];
const routes = [];
const providerFactories = [];
const effectLabels = [];
const warnings = [];
const injectCalls = [];
const unimplemented = [];

const target = {
  tools: { register(definition) { registeredTools.push(definition); return () => {}; } },
  skills: { registerProvider(factory) { providerFactories.push(factory); return () => {}; } },
  webServer: { register(route) { routes.push(route); return () => {}; } },
  logger: { warn(message) { warnings.push(String(message)); }, info() {}, error() {}, debug() {} },
  get(key) { return target[key]; },
  effect(fn, label) { effectLabels.push(label); return typeof fn === 'function' ? fn() : undefined; },
  inject(deps, callback) { injectCalls.push(deps); return () => {}; }
};
const ctx = new Proxy(target, {
  get(t, prop, receiver) {
    if (typeof prop === 'symbol') return Reflect.get(t, prop, receiver);
    if (Object.prototype.hasOwnProperty.call(t, prop)) return Reflect.get(t, prop, receiver);
    unimplemented.push(String(prop));
    return undefined;
  }
});

let applyThrew = null;
try { mod.apply(ctx); } catch (error) { applyThrew = error; }
r.check('C8.apply.noThrow', applyThrew === null,
  `apply(stub) 未抛错；注册了 ${registeredTools.length} 个工具、${routes.length} 条路由、${providerFactories.length} 个 provider；effect 标签 ${show(effectLabels)}`,
  `apply(stub) 抛错：${applyThrew instanceof Error ? applyThrew.message : String(applyThrew)}`);
r.info(`未实现却被访问的 stub 成员：${unimplemented.length === 0 ? '（无）' : show(unimplemented)}`);
r.info(`ctx.logger.warn 记录：${warnings.length === 0 ? '（无）' : show(warnings)}；ctx.inject 调用：${show(injectCalls)}`);

// 工具定义
const tool = registeredTools[0];
r.check('C8.tool.registered', registeredTools.length === 1 && tool !== undefined && tool.name === 'csl2_city_readings',
  `注册了 1 个工具，name=${show(tool && tool.name)}`,
  `工具注册数/名称不符：count=${registeredTools.length} name=${show(tool && tool.name)}`);

const params = tool?.parameters;
const requiredOk = params?.required === undefined || (Array.isArray(params.required) && params.required.every((item) => typeof item === 'string'));
r.check('C8.tool.parametersRawJsonSchema',
  params !== undefined && params.type === 'object' && params.properties !== undefined
  && ['city', 'savePath', 'reason', 'timeoutSec'].every((key) => Object.prototype.hasOwnProperty.call(params.properties, key))
  && requiredOk && params.required === undefined,
  `parameters 是原始 JSON Schema：type=${show(params?.type)}，properties 含 city/savePath/reason/timeoutSec；required ${params?.required === undefined ? '不存在' : show(params.required)}`,
  `parameters 形态不符：${show(params)}`);
r.info(`timeoutSec schema = ${show(params?.properties?.timeoutSec)}`);

r.check('C8.tool.output',
  tool?.output !== undefined && tool.output.schema !== undefined && typeof tool.output.render === 'function' && typeof tool.output.presentationMeta === 'function',
  `output.schema 存在（根 type=${show(tool?.output?.schema?.type)}），output.render 是函数，output.presentationMeta 是函数`,
  `output 形态不符：schema=${show(tool?.output?.schema)} render=${typeof tool?.output?.render}`);
r.check('C8.tool.execute', typeof tool?.execute === 'function', 'tool.execute 是函数', `tool.execute 不是函数：${typeof tool?.execute}`);

// 路由
const route = routes[0];
r.check('C8.route',
  routes.length === 1 && route !== undefined && route.path === '/csl2-readings' && route.kind === 'prefix' && typeof route.handler === 'function',
  `注册了 1 条 HTTP 路由：${show({ kind: route?.kind, path: route?.path, handler: typeof route?.handler })}`,
  `路由形态不符：count=${routes.length} route=${show(route && { kind: route.kind, path: route.path, handler: typeof route.handler })}`);

// skill provider
const provider = providerFactories.length === 1 ? providerFactories[0]() : null;
const candidates = provider !== null && typeof provider.list === 'function' ? await provider.list() : null;
const candidate = Array.isArray(candidates) ? candidates[0] : null;
r.check('C8.skill.registerProvider', providerFactories.length === 1 && provider !== null,
  `skills.registerProvider 调用一次；provider.name=${show(provider?.name)}`,
  `registerProvider 调用次数=${providerFactories.length}`);
r.check('C8.skill.candidate',
  Array.isArray(candidates) && candidates.length >= 1 && candidate?.name === 'cities-skylines-2-city-advisor',
  `list() 返回 ${candidates?.length} 个候选，name=${show(candidate?.name)}`,
  `候选不符：${show(candidates)}`);
const resourceBasePath = candidate?.resourceBase?.path ?? null;
r.check('C8.skill.resourceBase',
  candidate?.resourceBase?.kind === 'directory' && typeof resourceBasePath === 'string'
  && resourceBasePath.includes('skills') && resourceBasePath.includes('cities-skylines-2-city-advisor') && existsSync(resourceBasePath),
  `resourceBase = ${show(candidate?.resourceBase)}（目录存在）`,
  `resourceBase 不符或目录不存在：${show(candidate?.resourceBase)}`);
let skillContent = null;
let skillError = null;
try {
  const record = await provider.get(candidate);
  skillContent = typeof record?.content === 'string' ? record.content : null;
} catch (error) { skillError = error; }
r.check('C8.skill.content',
  skillError === null && typeof skillContent === 'string' && skillContent.length > 0 && !skillContent.startsWith('---')
  && (skillContent.includes('城市规划顾问') || skillContent.includes('RCIO')),
  `provider.get(candidate).content 非空、不以 --- 开头（前 ${JSON.stringify(skillContent?.slice(0, 40))}…），含「城市规划顾问」或「RCIO」`,
  `content 不符：error=${show(skillError && skillError.message)} 前 60 字=${show(skillContent?.slice(0, 60))}`);

/* ═════════════════════ C9 真 HTTP 往返 ═════════════════════ */

const server = http.createServer((req, res) => {
  Promise.resolve(route.handler(req, res)).catch((error) => {
    try { res.writeHead(500, { 'content-type': 'text/plain' }); res.end(String(error)); } catch { /* 已结束 */ }
  });
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
r.info(`真 node:http server 已启动：http://127.0.0.1:${port}/csl2-readings（handler 直接取自 stub 捕获的路由）`);

function request(method, pathname, body) {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null : (typeof body === 'string' ? body : JSON.stringify(body));
    const headers = payload === null ? {} : { 'content-type': 'application/json', 'content-length': Buffer.byteLength(payload) };
    const req = http.request({ host: '127.0.0.1', port, method, path: pathname, headers, agent: false }, (res) => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { text += chunk; });
      res.on('end', () => {
        let json = null;
        try { json = JSON.parse(text); } catch { json = null; }
        resolve({ status: res.statusCode, text, json });
      });
    });
    req.on('error', reject);
    if (payload !== null) req.write(payload);
    req.end();
  });
}
const post = (body, pathname = '/csl2-readings') => request('POST', pathname, body);

const TOOL = mod.__test.TOOL_DEFINITION;
const LEGAL_RAW = {
  rcio: { residential: -35, commercial: 12, industrial: 0, office: 85 },
  unemploymentRate: 6.5,
  confidence: { residential: 'exact', commercial: 'exact', industrial: 'exact', office: 'exact', unemploymentRate: 'approx' },
  notes: '独立验证用'
};

/* ── C9.1 open（裸、不带 panelId）→ poll → submit → execute 的 standard 与 rcio.js 深度相等 ── */
const exec1 = TOOL.execute({ city: '测试市', savePath: 'C:/saves/测试市', reason: '独立验证', timeoutSec: 30 }, { callId: 'call-open', signal: undefined });
const open1 = await post({ action: 'readings.open' });
r.check('C9.open.bare',
  open1.status === 200 && open1.json?.ok === true && typeof open1.json?.panel?.panelId === 'string' && open1.json.panel.zones?.length === 4,
  `HTTP ${open1.status} {ok:${show(open1.json?.ok)}, panelId:${show(open1.json?.panel?.panelId)}, zones:${open1.json?.panel?.zones?.length}}（唯一未结算面板 -> 裸 open 可关联）`,
  `裸 open 不符：HTTP ${open1.status} body=${show(open1.json)}`);
const panelId1 = open1.json?.panel?.panelId ?? null;
r.check('C9.open.panelShape',
  open1.json?.panel?.title?.includes('测试市') === true && open1.json.panel.rpc?.path === '/csl2-readings' && open1.json.panel.rpc?.method === 'POST'
  && open1.json.panel.colors?.negative === '#C0392B' && open1.json.panel.colors?.positive === '#1B4B8C',
  `panel 标题=${show(open1.json?.panel?.title)}；rpc=${show(open1.json?.panel?.rpc && { path: open1.json.panel.rpc.path, method: open1.json.panel.rpc.method, actions: open1.json.panel.rpc.actions })}`,
  `panel 形状不符：${show(open1.json?.panel)}`);

const poll1 = await post({ action: 'readings.poll', panelId: panelId1 });
r.check('C9.poll.pending', poll1.status === 200 && poll1.json?.status === 'pending',
  `poll -> HTTP ${poll1.status} ${show(poll1.json)}`,
  `poll 应为 pending：HTTP ${poll1.status} ${show(poll1.json)}`);

const submit1 = await post({ action: 'readings.submit', panelId: panelId1, raw: LEGAL_RAW });
r.check('C9.submit.provided', submit1.status === 200 && submit1.json?.ok === true && submit1.json?.status === 'provided',
  `submit -> HTTP ${submit1.status} ${show(submit1.json)}`,
  `submit 不符：HTTP ${submit1.status} ${show(submit1.json)}`);

const value1 = await exec1;
let standardEqual = false;
let standardDiff = null;
try {
  deepStrictEqual(value1?.standard, HOST.standardize(LEGAL_RAW.rcio, LEGAL_RAW.unemploymentRate));
  standardEqual = true;
} catch (error) { standardDiff = error.message; }
r.check('C9.execute.provided',
  value1?.status === 'provided' && value1?.source === 'slider-panel' && value1?.panelId === panelId1 && value1?.raw?.unemploymentRate === 6.5
  && JSON.stringify(value1?.raw?.rcio) === JSON.stringify(LEGAL_RAW.rcio) && standardEqual,
  `execute() -> status=${show(value1?.status)} source=${show(value1?.source)}；standard 与 lib/rcio.js 对同一 raw 的结果深度相等；summary=${show(value1?.standard?.summary)}`,
  `execute() 不符：status=${show(value1?.status)} raw=${show(value1?.raw)} standardDiff=${show(standardDiff)}`);

const submitAgain = await post({ action: 'readings.submit', panelId: panelId1, raw: LEGAL_RAW });
r.check('C9.submit.duplicateRejected',
  submitAgain.json?.ok === false && submitAgain.json?.code === 'already-settled',
  `重复 submit 被拒：HTTP ${submitAgain.status} ${show(submitAgain.json)}（业务失败 = HTTP 200 + body.ok:false）`,
  `重复 submit 未被拒：HTTP ${submitAgain.status} ${show(submitAgain.json)}`);

const pollSettled = await post({ action: 'readings.poll', panelId: panelId1 });
r.check('C9.poll.settled', pollSettled.json?.status === 'settled' && pollSettled.json?.result?.status === 'provided',
  `结算后 poll -> ${show(pollSettled.json && { status: pollSettled.json.status, result: pollSettled.json.result && pollSettled.json.result.status })}`,
  `settled poll 不符：${show(pollSettled.json)}`);

/* ── C9.2 skip：execute 返回 skipped/raw null/standard null ── */
const exec2 = TOOL.execute({ city: '跳过城', timeoutSec: 30 }, { callId: 'call-skip', signal: undefined });
const open2 = await post({ action: 'readings.open', callId: 'call-skip' });
const panelId2 = open2.json?.panel?.panelId ?? null;
r.check('C9.open.callId', open2.json?.ok === true && typeof panelId2 === 'string',
  `open 带 callId -> HTTP ${open2.status} panelId=${show(panelId2)}（无竞态关联键）`,
  `open 带 callId 失败：${show(open2.json)}`);
const skip = await post({ action: 'readings.skip', panelId: panelId2 });
r.check('C9.skip.action', skip.status === 200 && skip.json?.ok === true && skip.json?.status === 'skipped',
  `skip -> HTTP ${skip.status} ${show(skip.json)}`,
  `skip 不符：HTTP ${skip.status} ${show(skip.json)}`);
const value2 = await exec2;
r.check('C9.execute.skipped',
  value2?.status === 'skipped' && value2?.source === 'agent-skip' && value2?.raw === null && value2?.standard === null && typeof value2?.message === 'string' && value2.message.includes('用户选择不补数据'),
  `execute() -> status=${show(value2?.status)} raw=${show(value2?.raw)} standard=${show(value2?.standard)} message=${show(value2?.message)}`,
  `skipped 结果不符：${show(value2)}`);

/* ── C9.3 并发两个面板（各带自己的 callId）不串数据 ── */
const RAW_A = { rcio: { residential: -60, commercial: 0, industrial: 0, office: 0 }, unemploymentRate: 3 };
const RAW_B = { rcio: { residential: 0, commercial: 0, industrial: 0, office: 90 }, unemploymentRate: 12.5 };
const execA = TOOL.execute({ city: '甲城', timeoutSec: 30 }, { callId: 'call-conc-A', signal: undefined });
const execB = TOOL.execute({ city: '乙城', timeoutSec: 30 }, { callId: 'call-conc-B', signal: undefined });
const openA = await post({ action: 'readings.open', callId: 'call-conc-A' });
const openB = await post({ action: 'readings.open', callId: 'call-conc-B' });
const panelA = openA.json?.panel ?? null;
const panelB = openB.json?.panel ?? null;
r.check('C9.concurrent.distinctPanels',
  panelA?.panelId !== undefined && panelB?.panelId !== undefined && panelA.panelId !== panelB.panelId
  && panelA.title?.includes('甲城') === true && panelB.title?.includes('乙城') === true && panelA.callId === 'call-conc-A' && panelB.callId === 'call-conc-B',
  `两个并发面板：A=${show({ id: panelA?.panelId, title: panelA?.title, callId: panelA?.callId })}；B=${show({ id: panelB?.panelId, title: panelB?.title, callId: panelB?.callId })}`,
  `并发面板串了：A=${show(panelA)} B=${show(panelB)}`);

const bareWhileTwo = await post({ action: 'readings.open' });
r.check('C9.concurrent.bareOpenAmbiguous',
  bareWhileTwo.json?.ok === false && bareWhileTwo.json?.code === 'ambiguous-panel',
  `有 2 个未结算面板时裸 open 被拒（不猜）：${show(bareWhileTwo.json && { ok: bareWhileTwo.json.ok, code: bareWhileTwo.json.code, panelIds: bareWhileTwo.json.panelIds })}`,
  `裸 open 在有多个面板时未被拒：${show(bareWhileTwo.json)}`);

const submitA = await post({ action: 'readings.submit', panelId: panelA.panelId, raw: RAW_A });
const valueA = await execA;
const submitB = await post({ action: 'readings.submit', panelId: panelB.panelId, raw: RAW_B });
const valueB = await execB;
const expectA = HOST.standardize(RAW_A.rcio, RAW_A.unemploymentRate);
const expectB = HOST.standardize(RAW_B.rcio, RAW_B.unemploymentRate);
let concEqualA = false;
let concEqualB = false;
try { deepStrictEqual(valueA?.standard, expectA); concEqualA = true; } catch { concEqualA = false; }
try { deepStrictEqual(valueB?.standard, expectB); concEqualB = true; } catch { concEqualB = false; }
r.check('C9.concurrent.noCrossTalk',
  submitA.json?.status === 'provided' && submitB.json?.status === 'provided'
  && valueA?.panelId === panelA.panelId && valueB?.panelId === panelB.panelId && concEqualA && concEqualB
  && valueA?.standard?.summary !== valueB?.standard?.summary && JSON.stringify(valueA?.raw?.rcio) === JSON.stringify(RAW_A.rcio) && JSON.stringify(valueB?.raw?.rcio) === JSON.stringify(RAW_B.rcio),
  `A 的 standard 只含 RAW_A（${show(valueA?.standard?.summary)}）；B 的只含 RAW_B（${show(valueB?.standard?.summary)}）；两个面板 id 各自对应`,
  `并发串数据：A.raw=${show(valueA?.raw)} B.raw=${show(valueB?.raw)} A.panelId=${show(valueA?.panelId)} B.panelId=${show(valueB?.panelId)} concEqualA=${concEqualA} concEqualB=${concEqualB}`);

/* ── C9.4 方法 / 路径 / body 错误码 ── */
const put = await request('PUT', '/csl2-readings', {});
const del = await request('DELETE', '/csl2-readings', {});
const patch = await request('PATCH', '/csl2-readings', {});
r.check('C9.method.notAllowed',
  put.status === 405 && del.status === 405 && patch.status === 405 && put.json?.code === 'method-not-allowed',
  `PUT/DELETE/PATCH -> HTTP ${put.status}/${del.status}/${patch.status} ${show(put.json)}`,
  `非 POST 方法状态码不符：PUT=${put.status} DELETE=${del.status} PATCH=${patch.status} body=${show(put.json)}`);
const getDiag = await request('GET', '/csl2-readings?action=readings.poll&panelId=nonexistent');
r.info(`GET /csl2-readings?... -> HTTP ${getDiag.status} ${show(getDiag.json)}（index.js 明文支持 GET 做诊断，故「非 POST 一律 405」只对 GET/POST 之外的动词成立；GET 不是 405 属实现者声明的行为）`);
const unknownPath = await post({}, '/nope');
const deepPath = await post({}, '/csl2-readings/a/b');
r.check('C9.path.notFound',
  unknownPath.status === 404 && unknownPath.json?.code === 'not-found' && deepPath.status === 404,
  `/nope -> HTTP ${unknownPath.status} ${show(unknownPath.json)}；/csl2-readings/a/b -> HTTP ${deepPath.status}`,
  `未知路径状态码不符：/nope=${unknownPath.status} /csl2-readings/a/b=${deepPath.status}`);
const malformed = await post('{bad json');
r.check('C9.body.malformedJson', malformed.status === 400 && malformed.json?.code === 'bad-request',
  `畸形 JSON body -> HTTP ${malformed.status} ${show(malformed.json && { code: malformed.json.code, error: malformed.json.error })}`,
  `畸形 JSON 状态码不符：HTTP ${malformed.status} ${show(malformed.json)}`);
const unknownAction = await post({ action: 'nope' });
r.check('C9.action.unknown', unknownAction.status === 200 && unknownAction.json?.ok === false && unknownAction.json?.code === 'unknown-action',
  `未知动作 -> HTTP ${unknownAction.status} ${show(unknownAction.json && { ok: unknownAction.json.ok, code: unknownAction.json.code })}`,
  `未知动作不符：HTTP ${unknownAction.status} ${show(unknownAction.json)}`);
const shortName = await post({ action: 'poll', panelId: panelId1 });
r.check('C9.action.shortNameAccepted', shortName.json?.status === 'settled',
  `短名 action:'poll' 被接受（等价 readings.poll）：${show(shortName.json && { status: shortName.json.status })}`,
  `短名动作不被接受：${show(shortName.json)}`);

/* ── C9.5 空 body / 无 action ── */
const emptyPost = await post('');
r.info(`空 body POST -> HTTP ${emptyPost.status} ${show(emptyPost.json)}`);

/* ── C10.1 无客户端：CSL2_NO_CLIENT_MS=120 -> ~120ms 返回 unavailable，不抛错 ── */
process.env.CSL2_NO_CLIENT_MS = '120';
const t0 = Date.now();
let value3 = null;
let threw3 = null;
try {
  value3 = await TOOL.execute({ city: '无客户端', timeoutSec: 30 }, { callId: 'call-nc', signal: undefined });
} catch (error) { threw3 = error; }
const elapsed3 = Date.now() - t0;
r.check('C10.noClient.fastUnavailable',
  threw3 === null && value3?.status === 'unavailable' && value3?.source === 'no-client' && value3?.raw === null && value3?.standard === null
  && elapsed3 >= 100 && elapsed3 <= 800,
  `CSL2_NO_CLIENT_MS=120 -> ${elapsed3} ms 返回 status=${show(value3?.status)} source=${show(value3?.source)}（不抛错，raw/standard 为 null）`,
  `无客户端分支不符：elapsed=${elapsed3}ms threw=${show(threw3 && threw3.message)} value=${show(value3)}`);

/* ── C10.2 取消：exec.signal -> 可判定降级 + 清理两张 Map ── */
delete process.env.CSL2_NO_CLIENT_MS;
const controller = new AbortController();
const execCancel = TOOL.execute({ city: '取消城', timeoutSec: 30 }, { callId: 'call-cancel', signal: controller.signal });
const openCancel = await post({ action: 'readings.open', callId: 'call-cancel' });
const panelIdCancel = openCancel.json?.panel?.panelId ?? null;
await new Promise((resolve) => setTimeout(resolve, 30));
controller.abort();
const valueCancel = await execCancel;
const pollByPanel = await post({ action: 'readings.poll', panelId: panelIdCancel });
const pollByCall = await post({ action: 'readings.poll', callId: 'call-cancel' });
r.check('C10.cancel.degradedAndCleaned',
  valueCancel?.status === 'unavailable' && valueCancel?.raw === null && valueCancel?.standard === null && typeof valueCancel?.message === 'string' && valueCancel.message.includes('取消')
  && pollByPanel.json?.ok === false && pollByPanel.json?.code === 'no-panel' && pollByCall.json?.ok === false && pollByCall.json?.code === 'no-panel',
  `signal 取消 -> status=${show(valueCancel?.status)}（message 含「取消」）；取消后 poll(panelId)=${show(pollByPanel.json?.code)} poll(callId)=${show(pollByCall.json?.code)}（两张 Map 都已清理）`,
  `取消分支不符：value=${show(valueCancel)} pollByPanel=${show(pollByPanel.json)} pollByCall=${show(pollByCall.json)}`);

/* ── C10.3 timeoutSec 夹取（min 30 / 非数字回落 900） ── */
const cancelA = new AbortController();
const clampLow = TOOL.execute({ timeoutSec: 5 }, { callId: 'call-clamp-low', signal: cancelA.signal });
const cancelB = new AbortController();
const clampBad = TOOL.execute({ timeoutSec: 'abc' }, { callId: 'call-clamp-bad', signal: cancelB.signal });
await new Promise((resolve) => setTimeout(resolve, 20));
const panels = mod.__test.pendingPanels();
const entryLow = panels.find((entry) => entry.callId === 'call-clamp-low');
const entryBad = panels.find((entry) => entry.callId === 'call-clamp-bad');
r.check('C10.timeoutClamp', entryLow?.timeoutSec === 30 && entryBad?.timeoutSec === 900,
  `timeoutSec=5 -> ${show(entryLow?.timeoutSec)}（夹到最小 30）；timeoutSec='abc' -> ${show(entryBad?.timeoutSec)}（回落默认 900）`,
  `timeoutSec 夹取不符：5->${show(entryLow?.timeoutSec)} 'abc'->${show(entryBad?.timeoutSec)}`);
cancelA.abort();
cancelB.abort();
await Promise.all([clampLow, clampBad]);

/* ── C10.4 总超时分支：timeoutSec=30（如实测约 30 s） ── */
const t4 = Date.now();
const value4 = await TOOL.execute({ city: '超时城', timeoutSec: 30 }, { callId: 'call-timeout', signal: undefined });
const elapsed4 = Date.now() - t4;
r.check('C10.totalTimeout',
  value4?.status === 'timeout' && value4?.source === 'timeout' && value4?.raw === null && value4?.standard === null
  && typeof value4?.message === 'string' && value4.message.includes('30') && elapsed4 >= 29000 && elapsed4 <= 45000,
  `timeoutSec=30 -> 实测 ${elapsed4} ms 后 status=${show(value4?.status)}（message=${show(value4?.message?.slice(0, 60))}…）`,
  `总超时分支不符：elapsed=${elapsed4}ms value=${show(value4)}`);
r.unverified('C10.default900sNotMeasured', 'CSL2 默认 timeoutSec=900 与实测的 30 s 走同一条 setTimeout 分支（index.js waitForPanel），按 900 s 实等不可接受，故未实测');

/* ── C10.5 execute 永不抛错（畸形参数） ── */
process.env.CSL2_NO_CLIENT_MS = '120';
const t5 = Date.now();
let threwBadArgs = null;
let valueBadArgs = null;
try { valueBadArgs = await TOOL.execute(null, null); } catch (error) { threwBadArgs = error; }
delete process.env.CSL2_NO_CLIENT_MS;
r.check('C10.execute.malformedArgsNoThrow',
  threwBadArgs === null && valueBadArgs?.status === 'unavailable' && valueBadArgs?.raw === null && valueBadArgs?.standard === null,
  `execute(null, null) 未抛错，${Date.now() - t5} ms 返回 status=${show(valueBadArgs?.status)}（契约 §1：工具永不抛错给模型）`,
  `execute(null, null) 行为不符：threw=${show(threwBadArgs && threwBadArgs.message)} value=${show(valueBadArgs)}`);

await new Promise((resolve) => { server.close(resolve); if (typeof server.closeAllConnections === 'function') server.closeAllConnections(); });
r.info(`客户端 bundle 提到了 ${readFileSync(new URL('../../lib/client.js', import.meta.url), 'utf8').includes('/csl2-readings') ? '同一条 /csl2-readings 路径' : '（未找到 /csl2-readings）'}；路由常量 ROUTE_PATH=${show(mod.ROUTE_PATH)}`);

r.finish();
