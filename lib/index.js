/**
 * csl2-city-advisor · Host half（`package.json` 的 `main` / `exports["."]`）
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * 实际采用的「客户端 ↔ Host」承载方式（写在此处，便于后续审计）
 * ─────────────────────────────────────────────────────────────────────────────
 * **webServer 前缀路由 + 同源 fetch**，这是本机真实在跑的第三方插件的同构做法，不是权宜之计：
 *   - Host 侧范式：`C:\Users\Devcl\.dsh\profiles\desktop\node_modules\dsh-univer-office\lib\index.js:13171`
 *       `ctx.webServer.register({ kind: 'prefix', path: '/univer-api', handler: createUniverRouter(...) })`
 *       handler 是 node 风格 `(req, res)`，自己读 body、自己 writeHead/end。
 *   - Client 侧范式：同包 `lib/client.js:21949-21950`
 *       `request(path, init) { return fetch(`${window.location.origin}${path}`, init) }`
 *   - 路由 API 形态已核实：`@deepseek-ai/dsh-host-webserver/lib/index.js:177` `register(route)`，
 *     `kind` 只能取 `'exact'` / `'prefix'`（`:178` `route.kind === "exact" ? this.exact : this.prefixes`），
 *     前缀命中规则见 `:322-332`（`match()`，最长前缀优先）。
 *
 * 因此本插件注册：`{ kind: 'prefix', path: '/csl2-readings', handler }`，
 * 客户端调用：`fetch(window.location.origin + '/csl2-readings', { method:'POST', ... })`。
 *
 * `CONTRACT.md` §2 的四个语义动作（`readings.open` / `readings.submit` / `readings.skip` /
 * `readings.poll`）**完全不变**，只是承载为 POST body 的 `action` 字段（`'readings.open'` 与
 * `'open'` 两种写法都接受）。返回体同样保持契约里的四种形状。
 *
 * 未采用 `ctx.connection.fetch.register(...)`（Lead 先要求后撤销，理由：需要 `/api` 前缀，
 * 而真实插件用的是 webServer 自定义路由）。
 *
 * 安全边界（`dsh-host-webserver/README.md` 明说自定义路由没有服务器级鉴权）：
 * 本端点只吞吐「面板读数」这一种数据 —— 不回显文件系统内容、不返回 `savePath` 的真实解析结果、
 * 不做通用数据出口。`savePath`/`city`/`reason` 只是调用方自己传进来的展示字符串。
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * 已验证 / 未验证
 * ─────────────────────────────────────────────────────────────────────────────
 * [已验证-本机] `ctx.tools.register()` 需要**原始 JSON Schema**（不是 authoring DSL）：
 *   `@deepseek-ai/dsh-tools/lib/index.js:2878-2887` 只校验 `output.render` 与
 *   `output.schema`（`assertSupportedJsonSchema`，`:323`），`parameters` 在 `schemaOf()`
 *   (`:3039-3049`) 里被**原样**投影给模型 —— 没有 `parameterSchemaSpecToJsonSchema` 编译步骤。
 *   支持的 JSON Schema 关键字子集（`lib/types/json-schema.js:208`）：
 *   `type/oneOf/properties/required/additionalProperties/items/enum/const + 注解`；
 *   `required` 必须是**字符串数组**且只能出现在 `type:'object'` 上；不支持 `type` 数组、不支持 `nullable`。
 * [已验证-本机] skill provider 形态抄自 `dsh-univer-office\lib\index.js:11163-11251`。
 * [已验证-本机] `exec.callId` 存在：`@deepseek-ai/dsh-tools/lib/index.js:3310`
 *   `await tool.execute(exec.arguments, exec)`，`exec` 由 `createExecution()`(`:3131-3150`) 构造，
 *   带 `callId`/`rootCallId`/`signal`。客户端 `tool.call.toolview` 的 props 里也有同一个 `callId`
 *   （`_probe\DSH-CONTRACTS.md` Q7）—— 这就是 `readings.open` 可用的**无竞态关联键**。
 * [未验证-运行时] 路由在 GUI 里是否真的被浏览器请求到（需装进 profile 做端到端验证）。
 *   「路由没挂上」时的降级已实现：`carrier.mounted === false && carrier.pending === false`
 *   → `execute()` **立即**返回 `status:'unavailable'`，不挂起、不抛错。
 */

import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import {
  BANDS,
  BAND_LABELS,
  LEVELS,
  LEVEL_LABELS,
  STANDARD_SCHEMA,
  ZONE_LABELS,
  ZONES,
  clampBar,
  standardize
} from './rcio.js';

/** 模型可见的工具名（契约 §1，冻结）。 */
export const TOOL_NAME = 'csl2_city_readings';

/** 浏览器侧的端点路径（Host 注册前缀 / Client fetch 的字符串必须逐字一致）。 */
export const ROUTE_PATH = '/csl2-readings';

/** 契约 §2 的四个语义动作。 */
export const RPC_ACTIONS = Object.freeze(['readings.open', 'readings.submit', 'readings.skip', 'readings.poll']);

/** 等待上限（秒）：默认 900，最小 30（契约 §1）。 */
export const DEFAULT_TIMEOUT_SEC = 900;
export const MIN_TIMEOUT_SEC = 30;

/** 没有客户端来 `readings.open` 时的放弃窗口：60 s（task-1 第 3 点）。 */
const DEFAULT_NO_CLIENT_MS = 60_000;

/** 结算后保留面板的时长，供迟到的 `readings.poll` 仍能拿到 `{status:'settled'}`。 */
const SETTLED_TTL_MS = 300_000;

/** 请求体上限（面板读数不需要大 body）。 */
const MAX_BODY_BYTES = 64 * 1024;

const CONFIDENCE_VALUES = Object.freeze(['exact', 'approx', 'unknown']);

/** skill 名（= 插件内 `skills/` 目录名，未改动 frontmatter 的 `name`）。 */
const SKILL_NAME = 'cities-skylines-2-city-advisor';

/** provider 名（同时用于 `candidate.provider` 的自洽校验）。 */
const SKILL_PROVIDER_NAME = 'csl2-city-advisor';

/**
 * `BUNDLED_SKILL_RANK` 的值，抄自 `@deepseek-ai/dsh-skill/lib/index.js:23`。
 * 本插件**不声明依赖**（零依赖、无构建链），所以不能 `import` 该常量；`rank` 必须是有限数
 * （`lib/index.js:460` 的 `validateCandidate`），故此处硬编码并注明出处。
 */
const BUNDLED_SKILL_RANK = 600;

/** skill 的英文描述（取自 `SKILL.md` frontmatter 的 `description`，按 task-1 第 5 点略作裁剪）。 */
const SKILL_DESCRIPTION =
  'Advise on Cities: Skylines II (都市天际线2) city building, in a layered order — first keep the city '
  + 'growing, then secure four foundations (balanced population distribution, unemployment in the normal '
  + 'range, a public-transport network matching city scale, and an optimally tiered road network), and only '
  + 'then maximize tax revenue and happiness through land-use and transport efficiency. Covers land-use and '
  + 'density mix, job-housing balance, education-to-job matching, tax base vs land consumption, road '
  + 'hierarchy and congestion, public-transport network design (bus / tram / subway / train), station '
  + 'catchments, service coverage, budgets and expansion. Use when the user asks how to plan, fix, expand, or '
  + 'diagnose a CSL2 city, wants more income or higher happiness, shares save data or Carto exports. After '
  + 'the user shares a save, first collect the RCIO demand bars and the unemployment rate through the visual '
  + 'slider panel (skippable), then analyze.';

// ─────────────────────────────────────────────────────────────────────────────
// Cordis 插件外壳
// ─────────────────────────────────────────────────────────────────────────────
// (note: HMR reloads this plugin row when the file changes; client bundle rev follows the file mtime)

/** Cordis 插件名（= `package.json` 的 `name`，= `cordis.patch.yml` 的 insert name）。 */
export const name = 'csl2-city-advisor';

/**
 * 硬依赖：`tools`（注册 `csl2_city_readings`）与 `skills`（注册 skill provider）。
 * `webServer` **故意不放进 inject**：它通过下面的 `bindCarrier()` 惰性解析，
 * 这样「Web 宿主没挂 webServer」时插件仍能加载，工具退化为立刻 `unavailable` 而不是整个插件起不来。
 */
export const inject = ['tools', 'skills'];

/** 模块级面板表：`panelId` -> 面板记录。契约 §2 明文要求「Host 侧把每次调用存在内存 Map 里」。 */
const PANELS = new Map();
/** `callId` -> 面板记录：给 `readings.open` 一个无竞态的关联键（并发调用时不会串面板）。 */
const PANELS_BY_CALL = new Map();

/** 端点承载状态；`mounted`/`pending` 都为 false 时说明没有可用通道，工具立即降级。 */
const carrier = { mounted: false, pending: false };

let panelSequence = 0;

/**
 * 注册 Host half 的全部能力。所有注册都走 Cordis effect，卸载自动清理。
 * @param {any} ctx - Cordis Context
 */
export function apply(ctx) {
  registerTool(ctx);
  registerSkillProvider(ctx);
  bindCarrier(ctx);
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. 工具 csl2_city_readings
// ─────────────────────────────────────────────────────────────────────────────

/** 单条需求条的档位节点 schema（工厂：四处 sibling 复用同一个对象虽然合法，但独立实例更不容易踩到遍历器的坑）。 */
function zoneNodeSchema() {
  return {
    type: 'object',
    additionalProperties: false,
    properties: {
      bar: { type: 'integer', description: '面板读数（-100…100 的整数）。' },
      percent: { type: 'integer', description: '= bar（契约 §4 的唯一换算：percent = bar）。' },
      normalized: { type: 'number', description: '= bar / 100。' },
      level: { type: 'string', enum: LEVELS.slice(), description: '需求档位 id（契约 §4 六档）。' },
      levelLabel: {
        type: 'string',
        enum: LEVELS.map((level) => LEVEL_LABELS[level]),
        description: '需求档位中文。'
      }
    },
    required: ['bar', 'percent', 'normalized', 'level', 'levelLabel']
  };
}

/** 单条需求条的原始读数 schema（`raw.rcio.<zone>`）。 */
function rawZoneSchema() {
  return { type: 'integer', description: '玩家在游戏内看到的需求条位置，-100…100。' };
}

/** `{type:'null'} | T` 的联合（本运行时不支持 `nullable`，也不支持 `type` 数组）。 */
function nullable(schema) {
  return { oneOf: [{ type: 'null' }, schema] };
}

/** 契约 §1 的 `output.schema` 根（纯 JSON Schema，object 根，只用运行时允许的关键字子集）。 */
const OUTPUT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    status: {
      type: 'string',
      enum: ['provided', 'skipped', 'unavailable', 'timeout'],
      description: 'provided=玩家提交了读数；skipped=玩家跳过；unavailable=没有可用客户端；timeout=等待超时。'
    },
    source: {
      type: 'string',
      enum: ['slider-panel', 'agent-skip', 'no-client', 'timeout'],
      description: '读数来源。'
    },
    raw: {
      oneOf: [
        { type: 'null' },
        {
          type: 'object',
          additionalProperties: false,
          properties: {
            rcio: {
              type: 'object',
              additionalProperties: false,
              properties: {
                residential: rawZoneSchema(),
                commercial: rawZoneSchema(),
                industrial: rawZoneSchema(),
                office: rawZoneSchema()
              },
              required: ZONES.slice()
            },
            unemploymentRate: nullable({ type: 'number', description: '游戏内 Unemployment 读数（%）；null = 玩家未填。' }),
            confidence: {
              type: 'object',
              additionalProperties: false,
              properties: {
                residential: { type: 'string', enum: CONFIDENCE_VALUES.slice() },
                commercial: { type: 'string', enum: CONFIDENCE_VALUES.slice() },
                industrial: { type: 'string', enum: CONFIDENCE_VALUES.slice() },
                office: { type: 'string', enum: CONFIDENCE_VALUES.slice() },
                unemploymentRate: { type: 'string', enum: CONFIDENCE_VALUES.slice() }
              }
            },
            notes: { type: 'string', description: '玩家补充的自由文本。' }
          },
          required: ['rcio', 'unemploymentRate', 'confidence']
        }
      ]
    },
    standard: {
      oneOf: [
        { type: 'null' },
        {
          type: 'object',
          additionalProperties: false,
          properties: {
            schema: { type: 'string', const: STANDARD_SCHEMA },
            rcio: {
              type: 'object',
              additionalProperties: false,
              properties: {
                residential: zoneNodeSchema(),
                commercial: zoneNodeSchema(),
                industrial: zoneNodeSchema(),
                office: zoneNodeSchema()
              },
              required: ZONES.slice()
            },
            unemployment: {
              type: 'object',
              additionalProperties: false,
              properties: {
                percent: nullable({ type: 'number' }),
                fraction: nullable({ type: 'number' }),
                band: nullable({ type: 'string', enum: BANDS.slice() }),
                bandLabel: nullable({ type: 'string', enum: BANDS.map((band) => BAND_LABELS[band]) })
              },
              required: ['percent', 'fraction', 'band', 'bandLabel']
            },
            summary: { type: 'string', description: '单行中文摘要，例：住宅 −35｜商业 +12｜工业 0｜办公 +85｜失业率 6.5%。' },
            flags: {
              type: 'array',
              items: { type: 'string', enum: ['office_strong', 'residential_negative', 'unemployment_severe', 'all_neutral'] }
            }
          },
          required: ['schema', 'rcio', 'unemployment', 'summary', 'flags']
        }
      ]
    },
    message: { type: 'string', description: '给模型看的中文单行结论。' },
    panelId: { type: 'string', description: '本次调用的面板 id。' }
  },
  required: ['status', 'source', 'raw', 'standard', 'message', 'panelId']
};

/**
 * 模型可见的工具定义。
 * 用**原始 ToolDefinition**（不是 `defineTool`）：本插件零依赖，不能 `import @deepseek-ai/dsh-tools`，
 * 而 `ctx.tools.register()` 接受的正是原始形态（见文件头「已验证」）。
 */
const TOOL_DEFINITION = {
  name: TOOL_NAME,
  description:
    '在分析存档**之前**弹出可视化滑动面板，收集 RCIO 四条需求条（住宅/商业/工业/办公，−100…+100）'
    + '与失业率百分比 —— 这两项 Carto 导出里没有，只能问玩家。返回 csl2-rcio-standard/v1 标准数据。'
    + '玩家可以点「跳过，直接分析」，也可以在对话里直接说不用补：此时工具返回 skipped / timeout / unavailable，'
    + '**不构成阻塞**，必须照常继续分析，只是在报告第 0 栏列出缺项。'
    + '调用会阻塞等待玩家操作（默认上限 900 秒），同一份存档只调用一次。',
  parameters: {
    type: 'object',
    properties: {
      city: { type: 'string', description: '存档/城市名，用于面板标题。' },
      savePath: { type: 'string', description: '存档或 Carto 导出目录，仅用于面板展示。' },
      reason: { type: 'string', description: '为什么现在要读数（写进面板副标题）。' },
      timeoutSec: {
        type: 'number',
        description: `等待玩家提交的上限秒数；默认 ${DEFAULT_TIMEOUT_SEC}，最小 ${MIN_TIMEOUT_SEC}。`
      }
    }
  },
  output: {
    schema: OUTPUT_SCHEMA,
    /** 契约 §1：`output.render` 只产出简短中文。 */
    render(_args, value) {
      return [{ type: 'text', text: renderLine(value) }];
    },
    /** 契约 §1：`presentationMeta` 返回 `{ status, standard }` 供卡片回放（另附 `panelId` 以便重放时对上面板）。 */
    presentationMeta(_args, value) {
      const record = isRecord(value) ? value : {};
      return {
        status: typeof record.status === 'string' ? record.status : 'unavailable',
        standard: record.standard === undefined ? null : record.standard,
        panelId: typeof record.panelId === 'string' ? record.panelId : null
      };
    }
  },
  /**
   * 契约 §1 的规则：**永不抛错**给模型。取消（`exec.signal`）时清理 Map 并返回 unavailable。
   * @param {any} args
   * @param {any} exec
   */
  async execute(args, exec) {
    const safeArgs = isRecord(args) ? args : {};
    const timeoutSec = normalizeTimeoutSec(safeArgs.timeoutSec);
    const callId = exec !== null && typeof exec === 'object' && typeof exec.callId === 'string' ? exec.callId : null;

    const entry = {
      panelId: nextPanelId(),
      callId,
      city: text(safeArgs.city),
      savePath: text(safeArgs.savePath),
      reason: text(safeArgs.reason),
      timeoutSec,
      createdAt: Date.now(),
      settled: false,
      value: null,
      raw: null,
      finish: null
    };
    PANELS.set(entry.panelId, entry);
    if (callId !== null) PANELS_BY_CALL.set(callId, entry);

    try {
      // 路由没挂上（没有 webServer 也没有 connection）→ 立刻降级，不干等 60 s。
      if (carrier.mounted === false && carrier.pending === false) {
        return settle(entry, { kind: 'no-carrier' });
      }
      const signal = exec !== null && typeof exec === 'object' ? exec.signal : undefined;
      await waitForPanel(entry, {
        timeoutMs: timeoutSec * 1000,
        noClientMs: resolveNoClientMs(),
        signal
      });
      return entry.value;
    } catch (error) {
      logWarn(exec, `csl2_city_readings 内部错误，按 unavailable 继续：${messageOf(error)}`);
      return settle(entry, { kind: 'error' });
    }
  }
};

function registerTool(ctx) {
  const tools = serviceOf(ctx, 'tools');
  if (tools === undefined || typeof tools.register !== 'function') {
    logWarn(ctx, 'ctx.tools 不可用：csl2_city_readings 未注册');
    return;
  }
  // `register()` 自身返回 Cordis effect disposer（dsh-tools/lib/index.js:2886），无需再包 ctx.effect。
  tools.register(TOOL_DEFINITION);
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. skill provider
// ─────────────────────────────────────────────────────────────────────────────

const SKILL_LOCATOR = new URL(`../skills/${SKILL_NAME}/SKILL.md`, import.meta.url);

const SKILL_CANDIDATE = {
  name: SKILL_NAME,
  description: SKILL_DESCRIPTION,
  invocation: { modelInvocable: true, userInvocable: true },
  provider: SKILL_PROVIDER_NAME,
  source: 'bundled',
  resourceBase: {
    kind: 'directory',
    path: fileURLToPath(new URL(`../skills/${SKILL_NAME}/`, import.meta.url))
  },
  rank: BUNDLED_SKILL_RANK,
  locator: SKILL_LOCATOR
};

const SKILL_PROVIDER = {
  name: SKILL_PROVIDER_NAME,
  list: () => Promise.resolve([SKILL_CANDIDATE]),
  async get(candidate) {
    const locator = isRecord(candidate) && candidate.locator instanceof URL ? candidate.locator : SKILL_LOCATOR;
    const body = stripFrontmatter(await readFile(locator, 'utf8'));
    return {
      name: SKILL_NAME,
      description: SKILL_DESCRIPTION,
      invocation: SKILL_CANDIDATE.invocation,
      provider: SKILL_PROVIDER_NAME,
      source: SKILL_CANDIDATE.source,
      resourceBase: SKILL_CANDIDATE.resourceBase,
      content: body
    };
  }
};

function registerSkillProvider(ctx) {
  const skills = serviceOf(ctx, 'skills');
  if (skills === undefined || typeof skills.registerProvider !== 'function') {
    logWarn(ctx, 'ctx.skills 不可用：skill provider 未注册');
    return;
  }
  skills.registerProvider(() => SKILL_PROVIDER);
}

/**
 * 剥掉 YAML frontmatter —— skill 正文由注册表渲染进 `<skill_instructions>`，
 * 不能把 `---` 块再喂给模型。抄自 `dsh-univer-office/lib/index.js:11247-11251`，并兼容 CRLF 与 BOM。
 */
function stripFrontmatter(value) {
  const source = typeof value === 'string' ? value : '';
  const text = source.charCodeAt(0) === 0xfeff ? source.slice(1) : source;
  const match = /^---\r?\n[\s\S]*?\r?\n---[ \t]*\r?\n?/u.exec(text);
  return match === null ? text : text.slice(match[0].length);
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. Client ↔ Host 承载：webServer 前缀路由
// ─────────────────────────────────────────────────────────────────────────────

function bindCarrier(ctx) {
  if (mountRoute(ctx)) return;
  const injectFn = typeof ctx.inject === 'function' ? ctx.inject.bind(ctx) : null;
  if (injectFn === null) {
    logWarn(ctx, 'ctx.webServer 不可用且无法惰性等待：读数端点未挂载，工具将直接返回 unavailable');
    return;
  }
  carrier.pending = true;
  injectFn(['webServer'], (inner) => {
    if (mountRoute(inner)) return;
    carrier.pending = false;
    logWarn(inner, 'webServer 就绪但仍无法注册读数端点：工具将直接返回 unavailable');
  });
}

function mountRoute(ctx) {
  const webServer = serviceOf(ctx, 'webServer');
  if (webServer === undefined || typeof webServer.register !== 'function') return false;
  try {
    useDisposer(ctx, () => webServer.register({ kind: 'prefix', path: ROUTE_PATH, handler: readingsHandler }), 'csl2: readings http route');
    carrier.mounted = true;
    carrier.pending = false;
    return true;
  } catch (error) {
    logWarn(ctx, `注册读数端点失败：${messageOf(error)}`);
    return false;
  }
}

/** node 风格的请求处理器（`dsh-host-webserver` 的 handler 收 `(req, res)`）。 */
async function readingsHandler(request, response) {
  try {
    const url = new URL(typeof request.url === 'string' ? request.url : ROUTE_PATH, 'http://localhost');
    const method = (typeof request.method === 'string' ? request.method : 'GET').toUpperCase();

    let payload;
    let pathPanelId = null;
    if (url.pathname === ROUTE_PATH) {
      payload = {};
    } else if (url.pathname.startsWith(`${ROUTE_PATH}/`)) {
      // 兼容契约早期的兜底写法 `POST /csl2-readings/<panelId>`。
      const segment = decodeURIComponent(url.pathname.slice(ROUTE_PATH.length + 1));
      if (segment === '' || segment.includes('/')) {
        respondJson(response, 404, { ok: false, code: 'not-found', error: 'unknown readings endpoint' });
        return;
      }
      pathPanelId = segment === 'rpc' ? null : segment;
      payload = {};
    } else {
      respondJson(response, 404, { ok: false, code: 'not-found', error: 'unknown readings endpoint' });
      return;
    }

    if (method === 'GET') {
      payload = {
        action: url.searchParams.get('action') ?? 'poll',
        panelId: url.searchParams.get('panelId') ?? undefined,
        callId: url.searchParams.get('callId') ?? undefined
      };
    } else if (method === 'POST') {
      const body = await readBody(request);
      payload = body.trim() === '' ? {} : JSON.parse(body);
    } else {
      respondJson(response, 405, { ok: false, code: 'method-not-allowed', error: 'use POST (or GET for diagnostics)' });
      return;
    }

    if (pathPanelId !== null && isRecord(payload) && payload.panelId === undefined) payload.panelId = pathPanelId;
    respondJson(response, 200, dispatchRpc(payload));
  } catch (error) {
    respondJson(response, 400, { ok: false, code: 'bad-request', error: messageOf(error) });
  }
}

async function readBody(request) {
  const chunks = [];
  let bytes = 0;
  for await (const chunk of request) {
    const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    bytes += buffer.length;
    if (bytes > MAX_BODY_BYTES) throw new Error('request body is too large');
    chunks.push(buffer);
  }
  return Buffer.concat(chunks).toString('utf8');
}

function respondJson(response, status, value) {
  if (response.writableEnded === true || response.destroyed === true) return;
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'cache-control': 'no-store'
  });
  response.end(JSON.stringify(value));
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. RPC 语义（契约 §2 的四个动作；承载无关）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 客户端半在浏览器里跑，宿主看不到它的报错。这份计数是**宿主侧的"有没有人敲门"证据**：
 * 只要浏览器加载了客户端半并挂载了面板，就一定会打一次 `readings.open`。
 * `action:'diag'` 会把它原样返回，用于区分「bundle 没加载」与「加载了但没渲染」。
 */
const RPC_DIAG = {
  startedAt: Date.now(),
  total: 0,
  byAction: {},
  lastAction: null,
  lastAt: null,
  lastCode: null,
  pendingPanels: 0
};

/**
 * 派发一个契约 §2 的动作。**永不抛错**：未知动作返回 `{ok:false}` 而不是异常。
 * @param {unknown} payload - `{ action | method, panelId?, callId?, raw? }`
 */
export function dispatchRpc(payload) {
  const body = isRecord(payload) ? payload : {};
  const requested = typeof body.action === 'string' && body.action !== ''
    ? body.action
    : (typeof body.method === 'string' ? body.method : '');
  const action = requested.replace(/^readings\./u, '').trim();

  const bucket = action === '' ? '(empty)' : action;
  RPC_DIAG.total += 1;
  RPC_DIAG.byAction[bucket] = (RPC_DIAG.byAction[bucket] ?? 0) + 1;
  RPC_DIAG.lastAction = bucket;
  RPC_DIAG.lastAt = Date.now();
  RPC_DIAG.pendingPanels = PANELS.size;

  if (action === 'diag') {
    return { ok: true, diag: { ...RPC_DIAG, startedAtIso: new Date(RPC_DIAG.startedAt).toISOString() } };
  }

  const panelId = text(body.panelId);
  const callId = text(body.callId);
  const result = dispatchAction(action, requested, panelId, callId, body);
  RPC_DIAG.lastCode = isRecord(result) && typeof result.code === 'string' ? result.code : null;
  return result;
}

function dispatchAction(action, requested, panelId, callId, body) {
  switch (action) {
    case 'open':
      return opOpen(panelId, callId);
    case 'submit':
      return opSubmit(panelId, callId, body.raw);
    case 'skip':
      return opSkip(panelId, callId);
    case 'poll':
      return opPoll(panelId, callId);
    default:
      return {
        ok: false,
        code: 'unknown-action',
        error: `未知动作 ${JSON.stringify(requested)}；可用动作：${RPC_ACTIONS.join(' / ')}`
      };
  }
}

/**
 * `readings.open` -> `{ ok, panel }`。
 * 关联顺序：显式 `panelId` -> `callId`（无竞态）-> 唯一未结算面板 -> `ambiguous-panel` 错误。
 * 绝不猜测：同时存在多个未结算面板时返回错误而不是随便挑一个，避免并发调用把读数写错面板。
 */
function opOpen(panelId, callId) {
  if (panelId !== null) {
    const entry = PANELS.get(panelId);
    if (entry === undefined) return noPanel('panelId 未知或已过期');
    entry.seen = true;
    return { ok: true, panel: buildPanel(entry), settled: entry.settled === true };
  }
  if (callId !== null) {
    const entry = PANELS_BY_CALL.get(callId);
    if (entry === undefined) return noPanel('callId 对应的面板还没创建，请稍后重试');
    entry.seen = true;
    return { ok: true, panel: buildPanel(entry), settled: entry.settled === true };
  }
  const pending = [...PANELS.values()].filter((entry) => entry.settled === false);
  if (pending.length === 1) {
    const entry = pending[0];
    entry.seen = true;
    return { ok: true, panel: buildPanel(entry), settled: false };
  }
  if (pending.length === 0) return noPanel('当前没有未结算的读数面板');
  return {
    ok: false,
    code: 'ambiguous-panel',
    error: '同时存在多个未结算的读数面板，请带上 panelId（或 callId）再试',
    retry: true,
    panelIds: pending.map((entry) => entry.panelId),
    callIds: pending.map((entry) => entry.callId).filter((value) => value !== null)
  };
}

/** `readings.submit` -> `{ ok, status:'provided' }`。 */
function opSubmit(panelId, callId, raw) {
  const found = resolveEntry(panelId, callId);
  if (found.entry === undefined) return found.body;
  const entry = found.entry;
  entry.seen = true;
  if (entry.settled === true) return alreadySettled(entry);
  entry.raw = sanitizeRaw(raw);
  settle(entry, { kind: 'provided' });
  return { ok: true, status: 'provided', panelId: entry.panelId };
}

/** `readings.skip` -> `{ ok, status:'skipped' }`。 */
function opSkip(panelId, callId) {
  const found = resolveEntry(panelId, callId);
  if (found.entry === undefined) return found.body;
  const entry = found.entry;
  entry.seen = true;
  if (entry.settled === true) return alreadySettled(entry);
  settle(entry, { kind: 'skipped' });
  return { ok: true, status: 'skipped', panelId: entry.panelId };
}

/** `readings.poll` -> `{ status:'pending' }` | `{ status:'settled', result }`。 */
function opPoll(panelId, callId) {
  const found = resolveEntry(panelId, callId);
  if (found.entry === undefined) return found.body;
  const entry = found.entry;
  entry.seen = true;
  if (entry.settled === true) return { ok: true, status: 'settled', result: entry.value };
  return { ok: true, status: 'pending' };
}

function resolveEntry(panelId, callId) {
  if (panelId !== null) {
    const entry = PANELS.get(panelId);
    return entry === undefined ? { body: noPanel('panelId 未知或已过期') } : { entry };
  }
  if (callId !== null) {
    const entry = PANELS_BY_CALL.get(callId);
    return entry === undefined ? { body: noPanel('callId 对应的面板还没创建') } : { entry };
  }
  const pending = [...PANELS.values()].filter((entry) => entry.settled === false);
  if (pending.length === 1) return { entry: pending[0] };
  if (pending.length === 0) return { body: noPanel('当前没有未结算的读数面板') };
  return {
    body: {
      ok: false,
      code: 'ambiguous-panel',
      error: '同时存在多个未结算的读数面板，请带上 panelId（或 callId）再试',
      retry: true,
      panelIds: pending.map((entry) => entry.panelId)
    }
  };
}

function noPanel(reason) {
  return { ok: false, code: 'no-panel', error: reason, retry: true };
}

function alreadySettled(entry) {
  return {
    ok: false,
    code: 'already-settled',
    error: '该面板已经结算',
    status: entry.value === null || entry.value === undefined ? null : entry.value.status,
    retry: false
  };
}

/** 契约 §3 的面板载荷（Host 侧唯一的 UI 数据来源；客户端不读文件、不访问网络）。 */
function buildPanel(entry) {
  const city = entry.city === null ? '未命名城市' : entry.city;
  return {
    schema: 'csl2-panel/v1',
    panelId: entry.panelId,
    callId: entry.callId,
    city: entry.city,
    savePath: entry.savePath,
    reason: entry.reason,
    timeoutSec: entry.timeoutSec,
    title: `${city} · 请先补 RCIO 需求条与失业率`,
    subtitle: '这一步只影响建议精度，不影响是否分析。可直接点「跳过，直接分析」。',
    zones: ZONES.map((zone) => ({
      key: zone,
      label: ZONE_LABELS[zone],
      min: -100,
      max: 100,
      step: 1,
      ticks: [-100, -50, 0, 50, 100],
      defaultValue: 0
    })),
    unemployment: {
      key: 'unemploymentRate',
      label: '失业率',
      unit: '%',
      min: 0,
      max: 100,
      step: 0.1,
      optional: true,
      emptyMeansUnknown: true
    },
    buttons: { submit: '提交并分析', skip: '跳过，直接分析' },
    colors: { negative: '#C0392B', zero: '#8A93A0', positive: '#1B4B8C' },
    rpc: {
      transport: 'http',
      path: ROUTE_PATH,
      method: 'POST',
      actions: RPC_ACTIONS.slice(),
      bodyShape: { action: 'readings.open | readings.submit | readings.skip | readings.poll', panelId: 'string', callId: 'string?', raw: 'object?' }
    }
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. 输入净化 / canonical value
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 把客户端提交的 `raw` 净化成契约 §1 的形状。**永不抛错**。
 * - 四条需求条：夹取到 [-100, 100] 整数；不可数 -> 0，并把 `confidence` 标 `unknown`
 * - `unemploymentRate`：空 -> `null` 且 `confidence.unemploymentRate = 'unknown'`
 * - `confidence`：只接受 `exact|approx|unknown`；客户端没给就按「是否原样可用」推断
 */
export function sanitizeRaw(input) {
  const source = isRecord(input) ? input : {};
  const bars = isRecord(source.rcio) ? source.rcio : source;
  const submitted = isRecord(source.confidence) ? source.confidence : {};

  const rcio = {};
  const confidence = {};
  for (const zone of ZONES) {
    const value = bars[zone];
    rcio[zone] = clampBar(value);
    confidence[zone] = CONFIDENCE_VALUES.includes(submitted[zone])
      ? submitted[zone]
      : (isInRangeInteger(value) ? 'exact' : 'unknown');
  }

  const rawUnemployment = source.unemploymentRate;
  const unemploymentRate = isBlank(rawUnemployment) ? null : clampUnemployment(rawUnemployment);
  confidence.unemploymentRate = unemploymentRate === null
    ? 'unknown'
    : (CONFIDENCE_VALUES.includes(submitted.unemploymentRate)
      ? submitted.unemploymentRate
      : (isInRangePercent(rawUnemployment) ? 'exact' : 'unknown'));

  const result = { rcio, unemploymentRate, confidence };
  const notes = text(source.notes);
  if (notes !== null) result.notes = notes.slice(0, 500);
  return result;
}

function clampUnemployment(value) {
  const number = Number(value);
  if (Number.isFinite(number) === false) return null;
  return Math.round(Math.min(100, Math.max(0, number)) * 10) / 10;
}

function isBlank(value) {
  return value === null || value === undefined || (typeof value === 'string' && value.trim() === '');
}

function isInRangeInteger(value) {
  return typeof value === 'number' && Number.isInteger(value) && value >= -100 && value <= 100;
}

function isInRangePercent(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100;
}

/**
 * 面板结果 -> 契约 §1 的 canonical value。
 * @param {any} entry
 * @param {{kind:string}} outcome
 */
function toCanonical(entry, outcome) {
  const panelId = entry.panelId;
  switch (outcome.kind) {
    case 'provided': {
      const raw = entry.raw === null ? sanitizeRaw(null) : entry.raw;
      const standard = standardize(raw.rcio, raw.unemploymentRate);
      return {
        status: 'provided',
        source: 'slider-panel',
        raw,
        standard,
        message: providedMessage(standard),
        panelId
      };
    }
    case 'skipped':
      return {
        status: 'skipped',
        source: 'agent-skip',
        raw: null,
        standard: null,
        message: '用户选择不补数据，直接分析。请在报告第 0 栏声明：本次未提供 RCIO 需求条与失业率。',
        panelId
      };
    case 'timeout':
      return {
        status: 'timeout',
        source: 'timeout',
        raw: null,
        standard: null,
        message: `等待读数面板超时（${entry.timeoutSec} 秒），未取得 RCIO 需求条与失业率；`
          + '请照常继续分析，并在报告第 0 栏列出缺项。',
        panelId
      };
    case 'cancelled':
      return {
        status: 'unavailable',
        source: 'no-client',
        raw: null,
        standard: null,
        message: '读数面板调用在玩家提交前被取消，未取得 RCIO 需求条与失业率；'
          + '请照常继续分析，并在报告第 0 栏列出缺项。',
        panelId
      };
    default:
      return {
        status: 'unavailable',
        source: 'no-client',
        raw: null,
        standard: null,
        message: '当前没有可用的交互客户端（读数面板没有挂载），未取得 RCIO 需求条与失业率；'
          + '请照常继续分析，并在报告第 0 栏列出缺项。',
        panelId
      };
  }
}

function providedMessage(standard) {
  const levels = ZONES.map((zone) => `${ZONE_LABELS[zone]}${standard.rcio[zone].levelLabel}`).join('、');
  const flags = standard.flags.length === 0 ? '无结构性信号' : `信号 ${standard.flags.join('、')}`;
  return `已收到 RCIO 需求条与失业率：${standard.summary}。档位：${levels}；${flags}。可以照常开始分析。`;
}

/** `output.render` 的简短中文（契约 §1）。 */
function renderLine(value) {
  const record = isRecord(value) ? value : {};
  switch (record.status) {
    case 'provided':
      return `已收到 RCIO 读数：${isRecord(record.standard) && typeof record.standard.summary === 'string' ? record.standard.summary : '（摘要缺失）'}`;
    case 'skipped':
      return '用户选择跳过补数据，直接分析。';
    case 'timeout':
      return '等待读数面板超时；未取得 RCIO 需求条与失业率，照常继续分析并在第 0 栏声明。';
    default:
      return '没有可用的交互客户端；未取得 RCIO 需求条与失业率，照常继续分析并在第 0 栏声明。';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. 面板生命周期
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 等待结算。三个出口：客户端 submit/skip、`timeoutMs` 总超时、`noClientMs` 内无人 `open`、以及取消。
 * @param {any} entry
 * @param {{timeoutMs:number, noClientMs:number, signal:any}} options
 */
function waitForPanel(entry, options) {
  return new Promise((resolve) => {
    if (entry.settled === true) {
      resolve(entry.value);
      return;
    }
    const timers = [];
    const cleanup = () => {
      for (const timer of timers) clearTimeout(timer);
      if (options.signal !== undefined && options.signal !== null && typeof onAbort === 'function') {
        options.signal.removeEventListener('abort', onAbort);
      }
    };
    const onAbort = options.signal !== undefined && options.signal !== null && typeof options.signal.addEventListener === 'function'
      ? () => { cleanup(); resolve(settle(entry, { kind: 'cancelled' })); }
      : undefined;

    entry.finish = (value) => {
      cleanup();
      resolve(value);
    };

    // 总超时。
    timers.push(setTimeout(() => resolve(settle(entry, { kind: 'timeout' })), Math.max(1, options.timeoutMs)));
    // 无客户端窗口：只有「从来没有客户端碰过这个面板」时才放弃，所以按触发时刻重新判定。
    timers.push(setTimeout(() => {
      if (entry.seen === true || entry.settled === true) return;
      resolve(settle(entry, { kind: 'no-carrier' }));
    }, Math.max(1, options.noClientMs)));

    if (options.signal !== undefined && options.signal !== null) {
      if (options.signal.aborted === true) {
        cleanup();
        resolve(settle(entry, { kind: 'cancelled' }));
        return;
      }
      if (typeof options.signal.addEventListener === 'function') options.signal.addEventListener('abort', onAbort, { once: true });
    }
  });
}

/** 结算一次调用（幂等）：算出 canonical value、唤醒 `execute()`、安排回收。 */
function settle(entry, outcome) {
  if (entry.settled === true) return entry.value;
  entry.settled = true;
  entry.value = toCanonical(entry, outcome);
  if (outcome.kind !== 'provided') entry.raw = null;
  const notify = entry.finish;
  entry.finish = null;
  if (outcome.kind === 'cancelled') {
    // 取消 = 这次调用整个作废（卡片已经不在界面上了），立刻清理两张表，不留残余。
    forget(entry);
  } else {
    // 其余出口短暂保留，让迟到的 readings.poll 能拿到 {status:'settled'} 而停止轮询。
    const timer = setTimeout(() => forget(entry), SETTLED_TTL_MS);
    if (typeof timer.unref === 'function') timer.unref();
  }
  if (typeof notify === 'function') notify(entry.value);
  return entry.value;
}

function forget(entry) {
  PANELS.delete(entry.panelId);
  if (entry.callId !== null) PANELS_BY_CALL.delete(entry.callId);
}

function nextPanelId() {
  panelSequence += 1;
  return `r-${panelSequence.toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

function normalizeTimeoutSec(value) {
  if (value === null || value === undefined || value === '') return DEFAULT_TIMEOUT_SEC;
  const number = Number(value);
  if (Number.isFinite(number) === false) return DEFAULT_TIMEOUT_SEC;
  return Math.max(MIN_TIMEOUT_SEC, Math.round(number));
}

/**
 * 没有客户端时的放弃窗口。
 * 默认 60 s（task-1 第 3 点）；测试可用环境变量 `CSL2_NO_CLIENT_MS` 缩短，
 * 这样独立验证不必真的等 60 秒。正常运行路径不依赖该变量。
 */
function resolveNoClientMs() {
  const configured = typeof process !== 'undefined' && process.env !== undefined ? Number(process.env.CSL2_NO_CLIENT_MS) : Number.NaN;
  return Number.isFinite(configured) && configured > 0 ? configured : DEFAULT_NO_CLIENT_MS;
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. Cordis 小工具
// ─────────────────────────────────────────────────────────────────────────────

/** 惰性取服务：`inject` 之外的服务用这个查，缺失时返回 undefined 而不是抛错。 */
function serviceOf(ctx, key) {
  try {
    if (ctx !== null && ctx !== undefined && typeof ctx.get === 'function') {
      const viaGet = ctx.get(key);
      if (viaGet !== undefined && viaGet !== null) return viaGet;
    }
  } catch {
    // 服务未提供时 Cordis 可能抛错；按缺失处理。
  }
  try {
    const viaReflect = Reflect.get(ctx, key);
    if (viaReflect !== undefined && viaReflect !== null) return viaReflect;
  } catch {
    // 同上。
  }
  return undefined;
}

/** 注册一个「返回 disposer」的副作用；没有 `ctx.effect` 时退化为立即执行。 */
function useDisposer(ctx, register, label) {
  if (typeof ctx.effect === 'function') return ctx.effect(register, label);
  const disposer = register();
  return typeof disposer === 'function' ? disposer : () => {};
}

function logWarn(ctx, message) {
  let logged = false;
  try {
    if (ctx !== null && ctx !== undefined && ctx.logger !== undefined && typeof ctx.logger.warn === 'function') {
      ctx.logger.warn(message);
      logged = true;
    }
  } catch {
    // 日志永远不是关键路径。
  }
  if (logged) return;
  // 没有 ctx.logger 时才退化到控制台（避免同一条警告被记两遍）。
  try {
    if (typeof console !== 'undefined' && typeof console.warn === 'function') console.warn(`[csl2-city-advisor] ${message}`);
  } catch {
    // 同上。
  }
}

function isRecord(value) {
  return value !== null && typeof value === 'object' && Array.isArray(value) === false;
}

/** 非空字符串或 null（空串统一成 null，省得下游到处判空）。 */
function text(value) {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
}

function messageOf(error) {
  return error instanceof Error ? error.message : String(error);
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. 独立验证用的测试面（运行时不用；不改变任何契约语义）
// ─────────────────────────────────────────────────────────────────────────────

export const __test = {
  TOOL_DEFINITION,
  OUTPUT_SCHEMA,
  dispatchRpc,
  sanitizeRaw,
  buildPanel,
  pendingPanels: () => [...PANELS.values()],
  carrierState: () => ({ ...carrier }),
  isCarrierMounted: () => carrier.mounted
};
