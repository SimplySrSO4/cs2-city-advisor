window.__ModuleLoader__.load({
  id: "csl2-city-advisor",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    "use strict";

    /* =====================================================================
     * csl2-city-advisor · Client half（纯 JS，无构建，无第三方 import）
     *
     * 职责：把工具 csl2_city_readings 的卡片渲染成可视化 RCIO 滑动输入面板。
     *   - 四条竖向需求条（住宅/商业/工业/办公，-100…+100，步长 1）
     *   - 失业率百分比输入（空 = 未提供 -> raw.unemploymentRate = null）
     *   - 「提交并分析」/「跳过，直接分析」
     *   - 挂载后 readings.open，随后每 1.5s readings.poll，settled 即停
     *
     * 注册方式（已在 _probe\DSH-CONTRACTS.md Q6 核实）：
     *   ctx.slots.inject('tool.call.toolview', () => ctx.slots.register({
     *     name: 'tool.call.toolview', key: 'csl2_city_readings'
     *   }, CityReadingsPanel))
     *   —— keyed 槽按 wire tool name 派发；未命中就退回通用卡片，不会崩。
     *   —— 不声明 locale（免去字典注册），文案全部由 React.createElement 自绘。
     * ===================================================================== */

    var TOOL_NAME = "csl2_city_readings";
    var ROUTE = "/csl2-readings"; // 同源 POST；Host 用 ctx.webServer.register({ kind:'prefix', path:'/csl2-readings' })
    // Host（task-1）冻结的四个动作名（短名 'open'/'submit'/'skip'/'poll' 也接受）
    var ACTION_OPEN = "readings.open";
    var ACTION_SUBMIT = "readings.submit";
    var ACTION_SKIP = "readings.skip";
    var ACTION_POLL = "readings.poll";
    var POLL_MS = 1500;
    var MAX_POLLS = 1200; // 30 分钟上限，避免任何形式的无限轮询
    var MAX_RETRIES = 2; // 传输层退避重试上限（业务错误不重试）
    var OPEN_NOT_READY_RETRIES = 3; // code:'no-panel'（execute 还没建面板）时的重试次数

    var COLOR_NEG = "#C0392B";
    var COLOR_ZERO = "#8A93A0";
    var COLOR_POS = "#1B4B8C";

    /* =====================================================================
     * 1) §4 数据转换口径（内联副本；Host 的 lib/rcio.js 是同一份口径，
     *    由 tests/client-rcio-parity.mjs 做逐项等价性比对）
     * ===================================================================== */

    var STANDARD_SCHEMA = "csl2-rcio-standard/v1";

    var ZONE_KEYS = ["residential", "commercial", "industrial", "office"];
    var ZONE_LABELS = { residential: "住宅", commercial: "商业", industrial: "工业", office: "办公" };
    var ZONE_ARIA = { residential: "住宅需求条", commercial: "商业需求条", industrial: "工业需求条", office: "办公需求条" };

    // 需求档位 id，按契约 §4 表自上而下
    var LEVELS = ["collapse", "negative", "neutral", "weak", "demand", "strong"];
    var LEVEL_LABELS = {
      collapse: "需求崩塌（负）",
      negative: "负需求",
      neutral: "无需求",
      weak: "弱正需求",
      demand: "需求",
      strong: "强需求"
    };

    // 失业率档位 id（诊断阈值，不是游戏机制）
    var BANDS = ["low", "normal", "high", "severe"];
    var BAND_LABELS = {
      low: "偏低（劳动力紧张）",
      normal: "正常范围",
      high: "偏高",
      severe: "严重（税基会自己缩）"
    };

    var BAR_MIN = -100;
    var BAR_MAX = 100;
    var UNEMPLOYMENT_MIN = 0;
    var UNEMPLOYMENT_MAX = 100;
    var UNEMPLOYMENT_LOW_MAX = 3;
    var UNEMPLOYMENT_NORMAL_MAX = 8;
    var UNEMPLOYMENT_HIGH_MAX = 12;
    var NEUTRAL_BAND = 0.15;
    var OFFICE_STRONG_THRESHOLD = 0.8;

    function isRecord(value) {
      return value !== null && typeof value === "object" && Array.isArray(value) === false;
    }

    /** 任意输入 -> 有限数；不可数返回 null（接受 "6.5" 这类数字字符串）。 */
    function toFiniteNumber(value) {
      if (typeof value === "number") return isFinite(value) ? value : null;
      if (typeof value === "string") {
        var trimmed = value.trim();
        if (trimmed === "") return null;
        var parsed = Number(trimmed);
        return isFinite(parsed) ? parsed : null;
      }
      return null;
    }

    /** 保留 n 位小数，抹掉浮点噪声。 */
    function round(value, digits) {
      var factor = Math.pow(10, digits);
      return Math.round(value * factor) / factor;
    }

    /** 任意输入 -> [-100, 100] 的整数；不可数 -> 0；越界夹取；-0 -> 0。 */
    function clampBar(value) {
      var number = toFiniteNumber(value);
      if (number === null) return 0;
      var bounded = Math.min(BAR_MAX, Math.max(BAR_MIN, number));
      var rounded = Math.round(bounded);
      return rounded === 0 ? 0 : rounded;
    }

    /** normalized = bar / 100（契约 §4 的唯一换算），保留 4 位小数消噪。 */
    function normalizeBar(bar) {
      var normalized = round(clampBar(bar) / 100, 4);
      return normalized === 0 ? 0 : normalized;
    }

    /** 需求档位判定；入参与 lib/rcio.js 一致，是 bar（-100…100）而不是归一值。 */
    function classifyLevel(bar) {
      var normalized = normalizeBar(bar);
      if (normalized <= -0.6) return "collapse";
      if (normalized < -0.15) return "negative";
      if (normalized <= 0.15) return "neutral";
      if (normalized < 0.5) return "weak";
      if (normalized < 0.8) return "demand";
      return "strong";
    }

    /** 档位中文；未知档位返回空串（不抛错）。 */
    function levelLabelOf(level) {
      return Object.prototype.hasOwnProperty.call(LEVEL_LABELS, level) ? LEVEL_LABELS[level] : "";
    }

    /** 失业率分档；null/不可数 -> null（「未填」走 unknown 而不是某个档）。 */
    function classifyUnemployment(percent) {
      var number = toFiniteNumber(percent);
      if (number === null) return null;
      var bounded = Math.min(UNEMPLOYMENT_MAX, Math.max(UNEMPLOYMENT_MIN, number));
      if (bounded < UNEMPLOYMENT_LOW_MAX) return "low";
      if (bounded <= UNEMPLOYMENT_NORMAL_MAX) return "normal";
      if (bounded <= UNEMPLOYMENT_HIGH_MAX) return "high";
      return "severe";
    }

    /** 档位中文；null/未知返回空串（不抛错）。 */
    function bandLabelOf(band) {
      return Object.prototype.hasOwnProperty.call(BAND_LABELS, band) ? BAND_LABELS[band] : "";
    }

    /** 单条需求条 -> 契约 §1 的 standard.rcio.<zone> 节点。 */
    function describeZone(bar) {
      var value = clampBar(bar);
      var level = classifyLevel(value);
      return {
        bar: value,
        percent: value,
        normalized: normalizeBar(value),
        level: level,
        levelLabel: levelLabelOf(level)
      };
    }

    /** 失业率 -> 契约 §1 的 standard.unemployment 节点；未填时四个字段全 null。 */
    function describeUnemployment(percent) {
      var number = toFiniteNumber(percent);
      if (number === null) return { percent: null, fraction: null, band: null, bandLabel: null };
      var bounded = round(Math.min(UNEMPLOYMENT_MAX, Math.max(UNEMPLOYMENT_MIN, number)), 4);
      var band = classifyUnemployment(bounded);
      return {
        percent: bounded,
        fraction: round(bounded / 100, 6),
        band: band,
        bandLabel: bandLabelOf(band)
      };
    }

    /** 契约 §4 的四条结构性信号，顺序与 §4 枚举一致。 */
    function flagsOf(rcio, unemploymentRate) {
      var source = isRecord(rcio) ? rcio : {};
      var flags = [];
      if (describeZone(source.office).normalized >= OFFICE_STRONG_THRESHOLD) flags.push("office_strong");
      if (describeZone(source.residential).normalized < -NEUTRAL_BAND) flags.push("residential_negative");
      if (classifyUnemployment(unemploymentRate) === "severe") flags.push("unemployment_severe");
      var allNeutral = true;
      for (var i = 0; i < ZONE_KEYS.length; i += 1) {
        if (Math.abs(describeZone(source[ZONE_KEYS[i]]).normalized) > NEUTRAL_BAND) allNeutral = false;
      }
      if (allNeutral) flags.push("all_neutral");
      return flags;
    }

    /** 带符号显示：+48 / −35（U+2212）/ 0。 */
    function formatSignedBar(bar) {
      var value = clampBar(bar);
      if (value > 0) return "+" + value;
      if (value < 0) return "\u2212" + Math.abs(value);
      return "0";
    }

    /** 百分比显示：6.5 -> "6.5%"；未提供 -> ""。 */
    function formatPercent(percent) {
      var number = toFiniteNumber(percent);
      if (number === null) return "";
      return String(round(number, 4)) + "%";
    }

    /** 契约 §1 的 standard.summary 单行中文。 */
    function summarize(rcio, unemploymentRate) {
      var source = isRecord(rcio) ? rcio : {};
      var parts = [];
      for (var i = 0; i < ZONE_KEYS.length; i += 1) {
        parts.push(ZONE_LABELS[ZONE_KEYS[i]] + " " + formatSignedBar(source[ZONE_KEYS[i]]));
      }
      var percent = formatPercent(unemploymentRate);
      parts.push("失业率 " + (percent === "" ? "未提供" : percent));
      return parts.join("\uFF5C");
    }

    /** RCIO 原始读数 -> 契约 §1 的 standard 对象（canonical，Host/Client 共用口径）。 */
    function standardize(rcio, unemploymentRate) {
      var source = isRecord(rcio) ? rcio : {};
      var nodes = {};
      for (var i = 0; i < ZONE_KEYS.length; i += 1) {
        nodes[ZONE_KEYS[i]] = describeZone(source[ZONE_KEYS[i]]);
      }
      return {
        schema: STANDARD_SCHEMA,
        rcio: nodes,
        unemployment: describeUnemployment(unemploymentRate),
        summary: summarize(source, unemploymentRate),
        flags: flagsOf(source, unemploymentRate)
      };
    }

    // 仅测试用（tests/client-rcio-parity.mjs 读它做逐项等价性比对）；运行时忽略。
    exports.__rcio = {
      STANDARD_SCHEMA: STANDARD_SCHEMA,
      ZONE_KEYS: ZONE_KEYS,
      ZONE_LABELS: ZONE_LABELS,
      LEVELS: LEVELS,
      LEVEL_LABELS: LEVEL_LABELS,
      BANDS: BANDS,
      BAND_LABELS: BAND_LABELS,
      clampBar: clampBar,
      normalizeBar: normalizeBar,
      classifyLevel: classifyLevel,
      levelLabelOf: levelLabelOf,
      classifyUnemployment: classifyUnemployment,
      bandLabelOf: bandLabelOf,
      describeZone: describeZone,
      describeUnemployment: describeUnemployment,
      flagsOf: flagsOf,
      formatSignedBar: formatSignedBar,
      formatPercent: formatPercent,
      summarize: summarize,
      standardize: standardize
    };

    /* =====================================================================
     * 2) 样式：优先运行时 styles.insert(css)，否则回退 document.head
     *    （dsh-univer-office 用的同一种已核实可用的注入方式）
     * ===================================================================== */

    var CSS = `
.csl2-panel{box-sizing:border-box;width:100%;max-width:760px;margin:10px 0 10px 4px;padding:14px 16px 12px;border:1px solid #DCE1E8;border-radius:14px;background:#FFFFFF;color:#1F2733;font-size:12.5px;line-height:1.5}
.csl2-title{margin:0 0 4px;font-size:13.5px;font-weight:700;color:#172033}
.csl2-sub{margin:0;color:#566174;font-size:11.5px}
.csl2-meta{margin:6px 0 0;color:#7D8798;font-size:11px;word-break:break-all}
.csl2-hint{margin:8px 0 0;padding:8px 10px;border-radius:9px;background:#F4F6F9;color:#566174;font-size:11.5px}
.csl2-hint-warn{background:#FBF3E6;color:#8A5A12}
.csl2-hint-error{background:#FBEDEB;color:#8E2F22}
.csl2-grid{display:flex;gap:14px;align-items:flex-start;margin:12px 0 6px}
.csl2-zone{display:flex;flex-direction:column;align-items:center;gap:6px;flex:1 1 0;min-width:0}
.csl2-zone-name{font-size:12px;font-weight:650;color:#1F2733}
.csl2-zone-value{font-variant-numeric:tabular-nums;font-size:14px;font-weight:700;line-height:1}
.csl2-zone-level{font-size:11px;line-height:1.3;text-align:center;min-height:15px}
.csl2-slider-row{position:relative;display:flex;gap:6px;align-items:stretch;height:172px}
.csl2-ticks{display:flex;flex-direction:column;justify-content:space-between;font-size:9.5px;color:#98A1AE;font-variant-numeric:tabular-nums;padding:1px 0}
.csl2-track{position:relative;width:30px;flex:none}
.csl2-track-zero{position:absolute;left:0;right:0;top:50%;height:1px;background:#D7DBE2}
.csl2-slider{position:absolute;inset:0;width:30px;height:100%;margin:0;padding:0;background:transparent;writing-mode:vertical-lr;direction:rtl;-webkit-appearance:slider-vertical;appearance:slider-vertical;cursor:pointer}
.csl2-slider:focus-visible{outline:2px solid #1B4B8C;outline-offset:2px;border-radius:6px}
.csl2-uo{margin-top:10px;display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.csl2-uo-label{font-size:12px;font-weight:650;color:#1F2733}
.csl2-uo-input{box-sizing:border-box;width:104px;padding:5px 8px;border:1px solid #D7DBE2;border-radius:8px;font:inherit;font-variant-numeric:tabular-nums;color:#1F2733;background:#FFFFFF}
.csl2-uo-input:focus-visible{outline:2px solid #1B4B8C;outline-offset:1px}
.csl2-uo-hint{font-size:11px;color:#7D8798}
.csl2-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.csl2-btn{box-sizing:border-box;padding:7px 15px;border-radius:9px;border:1px solid transparent;font:inherit;font-weight:650;cursor:pointer}
.csl2-btn-primary{background:${COLOR_POS};color:#FFFFFF;border-color:${COLOR_POS}}
.csl2-btn-secondary{background:#FFFFFF;color:#3C4657;border-color:#CBD2DC}
.csl2-btn:disabled{cursor:not-allowed;opacity:.55}
.csl2-btn:focus-visible{outline:2px solid #1B4B8C;outline-offset:2px}
.csl2-status{margin-top:10px;font-size:11.5px;color:#566174}
.csl2-kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0 0;font-variant-numeric:tabular-nums}
.csl2-kv-k{color:#7D8798}
.csl2-kv-v{color:#1F2733}
.csl2-readonly{color:#566174}
.csl2-portal{position:relative;z-index:2147483000}
.csl2-modal{position:fixed;left:0;right:0;top:0;bottom:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(15,22,35,.45)}
.csl2-modal-card{width:min(820px,calc(100vw - 32px));max-height:calc(100vh - 48px);overflow:auto;margin:0 auto;box-shadow:0 18px 60px rgba(12,20,35,.35)}
.csl2-modal-card:focus{outline:none}
.csl2-dialog-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}
.csl2-dialog-actions button{border:1px solid #C9D1DC;border-radius:8px;background:#F6F8FB;color:#33405A;font-size:12px;padding:6px 12px;cursor:pointer}
.csl2-dialog-actions button:hover{background:#EDF1F7}
@media (max-width:760px){.csl2-modal{align-items:flex-start;padding:8px}.csl2-modal-card{width:calc(100vw - 16px);max-height:calc(100vh - 16px)}}
@media (prefers-reduced-motion:reduce){.csl2-btn,.csl2-slider{transition:none}}
`;

    function insertStyles(ctx) {
      var target = null;
      // (a) 动态 Client half 的运行时内建
      try {
        if (typeof styles !== "undefined" && styles && typeof styles.insert === "function") target = styles;
      } catch (e) { /* 内建不存在：忽略 */ }
      // (b) ctx 上的 styles 服务（若当前 Client 合成提供）
      if (target === null && ctx && typeof ctx.get === "function") {
        try {
          var svc = ctx.get("styles");
          if (svc && typeof svc.insert === "function") target = svc;
        } catch (e) { /* 无该服务：忽略 */ }
      }
      if (target !== null) {
        try {
          target.insert(CSS);
          return true;
        } catch (e) { /* 落入兜底 */ }
      }
      // (c) document.head 兜底（与 dsh-univer-office 的 injectStyles 同款）
      if (typeof document === "undefined" || !document.head) return false;
      var id = "csl2-city-advisor/styles";
      try {
        if (document.querySelector('style[data-plugin-css=' + JSON.stringify(id) + ']') !== null) return true;
        var tag = document.createElement("style");
        tag.dataset.plugin = "csl2-city-advisor";
        tag.dataset.pluginCss = id;
        tag.textContent = CSS;
        document.head.appendChild(tag);
        return true;
      } catch (e) {
        return false;
      }
    }

    /* =====================================================================
     * 3) React：静态 bundle 走模块表 require('react')（dsh-univer-office 同款），
     *    动态 Client half 的 builtin React 作为兜底。
     * ===================================================================== */

    var R = null;

    /**
     * 诊断记录 + **最强的"能注册"保护**（见 apply 顶部注释）。
     * 运行时规则：bundle 若在 factory 阶段抛错，会被判 "loaded without registering"，
     * 整张卡片都不会出现；所以这里连"defineProperty 失败"也兜住。
     */
    var diag = { steps: [], react: null, styles: false, slots: null, registered: false, stylesError: null, registerError: null };

    // 兜底 1：静态 bundle 走 require('react')；但若宿主把 React 作为**全局符号**注入
    // （动态 half 的形态），这里把它接住，免得依赖 TDZ/初始化时序。
    try {
      if ((typeof globalThis.React === "undefined" || globalThis.React === null) && typeof React === "undefined") {
        // 什么都不做：defineProperty 失败也无所谓，只是记录一下
        diag.steps.push("no-global-react");
      } else {
        diag.steps.push("global-react-present");
      }
    } catch (e) { diag.steps.push("global-react-check-failed"); }

    function resolveReact() {
      try {
        if (typeof require === "function") {
          var mod = require("react");
          if (mod && typeof mod.createElement === "function") return mod;
          if (mod && mod.default && typeof mod.default.createElement === "function") return mod.default;
        }
      } catch (e) { /* 落入兜底 */ }
      try {
        if (typeof React !== "undefined" && React && typeof React.createElement === "function") return React;
      } catch (e) { /* 无内建：忽略 */ }
      return null;
    }

    /**
     * React 的"最后兜底"：只实现本插件真正用到的 4 个 API。
     * 存在的意义不是替代 React，而是**让 bundle 永远能注册成功**：
     * 静态 client bundle 若在 factory 阶段抛错，运行时会把它判为
     * "loaded without registering"，那整张卡片都不会出现；有了兜底至少能以最小形态渲染。
     */
    function makeFallbackReact() {
      var states = [];
      var seq = 0;
      return {
        createElement: function (type, props) {
          var children = Array.prototype.slice.call(arguments, 2);
          if (typeof type === "function") return type(Object.assign({}, props || {}, { children: children.length === 1 ? children[0] : children }));
          return { type: type, props: props || {}, children: children };
        },
        useState: function (initial) {
          var index = seq++;
          if (states[index] === undefined) states[index] = { value: typeof initial === "function" ? initial() : initial };
          var record = states[index];
          return [record.value, function (next) { record.value = typeof next === "function" ? next(record.value) : next; }];
        },
        useRef: function (initial) { return { current: initial }; },
        useEffect: function () { return undefined; },
        __fallback: true
      };
    }

    function el(type, props) {
      if (R === null) throw new Error("csl2: React 不可用");
      var children = Array.prototype.slice.call(arguments, 2);
      var flat = [];
      for (var i = 0; i < children.length; i += 1) {
        var c = children[i];
        if (Array.isArray(c)) {
          for (var j = 0; j < c.length; j += 1) flat.push(c[j]);
        } else {
          flat.push(c);
        }
      }
      var args = [type, props].concat(flat);
      return R.createElement.apply(R, args);
    }

    /* =====================================================================
     * 4) props 容错解析（纯函数，绝不对畸形输入抛错）
     * ===================================================================== */

    function tryParseObject(value) {
      if (value && typeof value === "object" && !Array.isArray(value)) return value;
      if (typeof value !== "string") return null;
      var text = value.trim();
      if (text === "") return null;
      try {
        var parsed = JSON.parse(text);
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
        return null;
      } catch (e) {
        return null;
      }
    }

    /** 从任一阶段的 block 里取工具参数（start 用 block.argsRaw/arguments，result 用 block.call.*）。 */
    function readArgs(block) {
      if (!block || typeof block !== "object") return null;
      var call = block.call && typeof block.call === "object" ? block.call : null;
      var candidates = [
        block.arguments,
        block.argsRaw,
        block.args,
        block.input,
        call ? call.arguments : undefined,
        call ? call.argsRaw : undefined
      ];
      for (var i = 0; i < candidates.length; i += 1) {
        var parsed = tryParseObject(candidates[i]);
        if (parsed !== null) return parsed;
      }
      return null;
    }

    function readString(value) {
      return typeof value === "string" && value.trim() !== "" ? value : null;
    }

    function readPanelIdFrom(block) {
      var args = readArgs(block);
      if (args !== null) {
        var direct = readString(args.panelId);
        if (direct !== null) return direct;
      }
      // 结果侧：canonical value 顶层也有 panelId
      if (block && typeof block === "object") {
        var top = readString(block.panelId);
        if (top !== null) return top;
      }
      return null;
    }

    /** 取工具结果里的 canonical value（回放时主要靠 block.meta = presentationMeta）。 */
    function readResultValue(block) {
      if (!block || typeof block !== "object") return null;
      var meta = block.meta && typeof block.meta === "object" ? block.meta : null;
      if (meta !== null) {
        if (readString(meta.status) !== null) return meta;
        if (meta.value && typeof meta.value === "object") return meta.value;
        if (meta.result && typeof meta.result === "object") return meta.result;
        if (meta.standard && typeof meta.standard === "object") {
          return { status: "provided", standard: meta.standard, message: readString(meta.message) };
        }
      }
      var content = Array.isArray(block.content) ? block.content : null;
      if (content !== null) {
        for (var i = 0; i < content.length; i += 1) {
          var item = content[i];
          if (!item || typeof item !== "object") continue;
          var parsed = tryParseObject(item.text);
          if (parsed !== null && readString(parsed.status) !== null) return parsed;
        }
      }
      var direct = readString(block.status) !== null ? block : null;
      return direct;
    }

    /* =====================================================================
     * 5) 同源 HTTP 通道（CONTRACT §2 的四个动作，承载方式为 POST /csl2-readings）
     * ===================================================================== */

    function endpoint() {
      var origin = "";
      try {
        if (typeof window !== "undefined" && window.location && typeof window.location.origin === "string") {
          origin = window.location.origin;
        }
      } catch (e) { origin = ""; }
      return origin + ROUTE;
    }

    function postOnce(body) {
      if (typeof fetch !== "function") {
        return Promise.resolve({ ok: false, unavailable: true, reason: "no-fetch" });
      }
      return fetch(endpoint(), {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
        credentials: "same-origin"
      }).then(
        function (res) {
          if (!res || !res.ok) {
            return { ok: false, unavailable: true, httpStatus: res ? res.status : 0 };
          }
          return res.json().then(
            function (data) { return { ok: true, data: data }; },
            function () { return { ok: false, unavailable: true, httpStatus: res.status }; }
          );
        },
        function () { return { ok: false, unavailable: true, httpStatus: 0 }; }
      );
    }

    /** 传输失败最多退避重试 MAX_RETRIES 次；业务失败（HTTP 2xx 且 ok:false）不重试。 */
    function post(body, retries) {
      var budget = typeof retries === "number" ? retries : MAX_RETRIES;
      var attempt = 0;
      function run() {
        return postOnce(body).then(function (res) {
          if (res.ok || !res.unavailable || attempt >= budget) return res;
          var delay = 400 * Math.pow(2, attempt);
          attempt += 1;
          return new Promise(function (resolve) { setTimeout(resolve, delay); }).then(run);
        });
      }
      return run();
    }

    /* =====================================================================
     * 6) 组件
     * ===================================================================== */

    var UNEMPLOYMENT_HINT_EMPTY = "留空 = 未提供（第 0 栏会列为缺项）";

    function buildRaw(bars, unemploymentText) {
      var raw = {
        rcio: {
          residential: clampBar(bars.residential),
          commercial: clampBar(bars.commercial),
          industrial: clampBar(bars.industrial),
          office: clampBar(bars.office)
        },
        unemploymentRate: null,
        confidence: {
          residential: "exact",
          commercial: "exact",
          industrial: "exact",
          office: "exact",
          unemploymentRate: "unknown"
        }
      };
      var text = typeof unemploymentText === "string" ? unemploymentText.trim().replace("%", "").trim() : "";
      if (text === "") return { value: raw };
      var num = Number(text);
      if (!isFinite(num) || num < 0 || num > 100) {
        return { error: "失业率请填 0–100 之间的数字，或留空表示未提供。" };
      }
      raw.unemploymentRate = Math.round(num * 10) / 10;
      raw.confidence.unemploymentRate = "exact";
      return { value: raw };
    }

    function VerticalSlider(props) {
      var value = clampBar(props.value);
      var level = classifyLevel(value);
      var color = value < 0 ? COLOR_NEG : value > 0 ? COLOR_POS : COLOR_ZERO;
      var ticks = [100, 50, 0, -50, -100];

      function onKeyDown(event) {
        var key = event && event.key;
        var next = value;
        if (key === "ArrowUp" || key === "ArrowRight") next = value + 1;
        else if (key === "ArrowDown" || key === "ArrowLeft") next = value - 1;
        else if (key === "PageUp") next = value + 10;
        else if (key === "PageDown") next = value - 10;
        else if (key === "Home") next = -100;
        else if (key === "End") next = 100;
        else return;
        if (event.preventDefault) event.preventDefault();
        props.onChange(clampBar(next));
      }

      function onChange(event) {
        var next = event && event.target ? Number(event.target.value) : value;
        props.onChange(clampBar(next));
      }

      return el(
        "div",
        { className: "csl2-zone" },
        el("div", { className: "csl2-zone-name" }, props.label),
        el("div", { className: "csl2-zone-value", style: { color: color } }, formatSignedBar(value)),
        el(
          "div",
          { className: "csl2-slider-row" },
          el(
            "div",
            { className: "csl2-ticks", "aria-hidden": "true" },
            ticks.map(function (t) {
              return el("span", { key: "tick-" + t, className: "csl2-tick" }, t > 0 ? "+" + t : String(t));
            })
          ),
          el(
            "div",
            { className: "csl2-track" },
            el("div", { className: "csl2-track-zero", "aria-hidden": "true" }),
            el("input", {
              type: "range",
              className: "csl2-slider",
              min: -100,
              max: 100,
              step: 1,
              value: value,
              role: "slider",
              "aria-valuemin": -100,
              "aria-valuemax": 100,
              "aria-valuenow": value,
              "aria-valuetext": formatSignedBar(value) + "，" + levelLabelOf(level),
              "aria-label": props.aria,
              "aria-orientation": "vertical",
              style: { accentColor: color },
              onChange: onChange,
              onKeyDown: onKeyDown
            })
          )
        ),
        el("div", { className: "csl2-zone-level", style: { color: color } }, levelLabelOf(level))
      );
    }

    function StatusLine(props) {
      if (!props.text) return null;
      return el(
        "div",
        { className: "csl2-status", role: "status", "aria-live": "polite" },
        props.text
      );
    }

    /**
     * Portal 容器：把模态挂到 `document.body`。
     *
     * 为什么必须这样做：面板原本渲染在**工具调用卡片内部**，而"未展开的工具行"不渲染 body
     * —— 实测（宿主 `?action=diag`）客户端半确实发起了 `open` 并每 1.5 s 稳定轮询，
     * 但用户看不到弹窗，因为卡片折叠时整棵子树（连同 `position:fixed` 的模态）根本没被挂载。
     * Portal 让面板脱离卡片布局，卡片是否展开都能出现。
     *
     * 降级：`react-dom` 取不到（或 SSR / 无 document）时返回 `props.fallback`
     * （调用方传内联卡片），保证"最差情况仍能用"，而不是白屏。
     */
    var portalNode = null;

    function getPortalNode() {
      if (portalNode !== null) return portalNode;
      if (typeof document === "undefined" || document === null || !document.body) return null;
      var node = document.createElement("div");
      node.className = "csl2-portal";
      node.setAttribute("data-csl2-portal", "1");
      document.body.appendChild(node);
      portalNode = node;
      return node;
    }

    function PortalPanel(props) {
      var state = R.useState(null);
      var node = state[0];
      var setNode = state[1];

      // react-dom 必须在**渲染期**就能取到：取不到就直接走 fallback（内联模态），
      // 完全不依赖 effect —— 这样在"effect 不运行"的环境（测试桩 / 回放）里也能渲染出面板。
      var reactDom = null;
      try {
        if (typeof require === "function") reactDom = require("react-dom");
      } catch (e) { reactDom = null; }
      var canPortal = reactDom !== null && reactDom !== undefined && typeof reactDom.createPortal === "function";

      if (!canPortal) {
        try { console.warn("csl2-city-advisor: 取不到 react-dom，弹窗退化为卡片内联形态"); } catch (e2) { /* ignore */ }
        return props.fallback === undefined ? null : props.fallback;
      }

      R.useEffect(function () {
        setNode(getPortalNode());
        return function () { setNode(null); };
      }, []);

      var container = node !== null ? node : getPortalNode();
      if (container === null) return props.fallback === undefined ? null : props.fallback;
      return reactDom.createPortal(props.children, container);
    }

    /* =====================================================================
     * 6.4) InteractivePanel —— 待填写卡片（模态形态走 Portal）
     *
     * 用户要求：不要为了填数而在对话流里来回滚动 —— 待填写时要像"弹窗"一样直接出现在眼前。
     * `modal: true` 时本卡片把自身包成 `position:fixed` 全屏居中外壳：
     * 遮罩 + 滚动锁定 + role="dialog"/aria-modal + Esc/点遮罩**不关闭**
     * （关掉只会让工具白等到超时），并用 PortalPanel 挂到 `document.body`。
     *
     * 纯函数纪律：除 useEffect 里的滚动锁定与 portal 挂载外无副作用；
     * 所有 document 访问都做了存在性判断（回放 / 无头环境安全）。
     * ===================================================================== */
    function InteractivePanel(props) {
      var block = props.block;
      var args = readArgs(block) || {};
      var city = readString(args.city);
      var reason = readString(args.reason);
      var savePath = readString(args.savePath);
      // callId 是 Host（task-1）建索引用的键：并发多个面板也不会串。
      var callId = readString(props.callId);

      var barsState = R.useState({ residential: 0, commercial: 0, industrial: 0, office: 0 });
      var bars = barsState[0];
      var setBars = barsState[1];

      var uoState = R.useState("");
      var unemployment = uoState[0];
      var setUnemployment = uoState[1];

      // panelId：props.argsRaw 里能拿到就用；通常拿不到（panelId 由 Host 生成），
      // 于是由 open 回填：Host 在"只有一个未结算面板"时返回 { ok:true, panel:{ panelId } }。
      var initialId = readPanelIdFrom(block);
      var idRef = R.useRef(initialId);

      // 弹窗体验：模态形态下锁住页面滚动，卸载时还原。
      R.useEffect(function () {
        if (props.modal !== true) return undefined;
        var previousOverflow = null;
        try {
          if (typeof document !== "undefined" && document.body && document.body.style) {
            previousOverflow = document.body.style.overflow;
            document.body.style.overflow = "hidden";
          }
        } catch (e) { /* ignore */ }
        return function () {
          try {
            if (typeof document !== "undefined" && document.body && document.body.style && previousOverflow !== null) {
              document.body.style.overflow = previousOverflow;
            }
          } catch (e) { /* ignore */ }
        };
      }, []);

      // ready：拿到 panelId（或 open 明确失败）之前禁用两个按钮，避免抢跑。
      var readyState = R.useState(initialId !== null);
      var ready = readyState[0];
      var setReady = readyState[1];

      var panelState = R.useState(null);
      var panel = panelState[0];
      var setPanel = panelState[1];

      // live | submitted | skipped | settled | unavailable | ambiguous | lost
      var flowState = R.useState("live");
      var flow = flowState[0];
      var setFlow = flowState[1];

      var noticeState = R.useState("");
      var notice = noticeState[0];
      var setNotice = noticeState[1];

      var busyState = R.useState(false);
      var busy = busyState[0];
      var setBusy = busyState[1];

      R.useEffect(function () {
        var cancelled = false;
        var timer = null;
        var openTimer = null;
        var polls = 0;
        var failures = 0;

        // 兜底：open 长时间无响应也不能把按钮永久锁死
        openTimer = setTimeout(function () {
          if (!cancelled) setReady(true);
        }, 8000);

        function stopPolling() {
          if (timer !== null) {
            clearInterval(timer);
            timer = null;
          }
        }

        function onSettled(result) {
          stopPolling();
          if (cancelled) return;
          setFlow("settled");
          setNotice(readSettledNotice(result));
        }

        function tick() {
          if (cancelled || idRef.current === null) return;
          polls += 1;
          if (polls > MAX_POLLS) {
            stopPolling();
            return;
          }
          post({ action: ACTION_POLL, panelId: idRef.current }, MAX_RETRIES).then(function (res) {
            if (cancelled) return;
            if (res.unavailable) {
              failures += 1;
              if (failures >= 3) {
                stopPolling();
                setFlow("unavailable");
                setNotice("面板通道不可用（Host 未响应 /csl2-readings），已停止轮询。");
              }
              return;
            }
            failures = 0;
            var data = res.data || {};
            if (data.status === "settled") onSettled(data.result);
          });
        }

        // 1) readings.open —— 优先用 callId 建索引（并发安全）；panelId 已知时一并带上。
        //    Host 在面板还没建好时返回 { ok:false, code:'no-panel', retry:true }，此时退避重试。
        var openAttempts = 0;
        function openPanel() {
          var body = { action: ACTION_OPEN };
          if (callId !== null) body.callId = callId;
          if (idRef.current !== null) body.panelId = idRef.current;
          return post(body, MAX_RETRIES).then(function (res) {
            if (cancelled) return;
            if (res.unavailable) {
              setReady(true);
              setFlow("unavailable");
              setNotice("面板通道不可用（POST " + ROUTE + "），本次按未提供处理。");
              return;
            }
            var data = res.data || {};
            if (data.ok !== true) {
              var code = readString(data.code);
              if (code === "no-panel" && openAttempts < OPEN_NOT_READY_RETRIES) {
                openAttempts += 1;
                // execute() 可能还没跑到建面板那一步：稍后重试，绝不无限重试。
                setTimeout(function () {
                  if (!cancelled) openPanel();
                }, 600 * openAttempts);
                return;
              }
              setReady(true);
              if (code === "ambiguous-panel") {
                setFlow("ambiguous");
                setNotice("当前有多个待填面板，无法自动对应；请重新发起本次调用。");
              } else if (code === "no-panel") {
                setFlow("lost");
                setNotice("Host 里没有这个待填面板（可能已结算）；请重新发起本次调用。");
              } else {
                setFlow("unavailable");
                setNotice(
                  "Host 拒绝了面板打开请求" + (code !== null ? "（" + code + "）" : "") +
                  (readString(data.error) !== null ? "：" + data.error : readString(data.message) !== null ? "：" + data.message : "。")
                );
              }
              return;
            }
            setReady(true);
            var nextPanel = data.panel && typeof data.panel === "object" ? data.panel : {};
            var resolvedId = readString(nextPanel.panelId) || readString(data.panelId) || idRef.current;
            if (resolvedId !== null) idRef.current = resolvedId;
            setPanel(nextPanel);
            if (idRef.current === null) {
              setFlow("lost");
              setNotice("未取到 panelId；请重新发起本次调用。");
              return;
            }
            setNotice("");
            timer = setInterval(tick, POLL_MS);
          });
        }

        openPanel();

        return function () {
          cancelled = true;
          if (openTimer !== null) clearTimeout(openTimer);
          stopPolling();
        };
      }, []);

      function changeZone(key, value) {
        setBars(function (prev) {
          var next = {};
          for (var i = 0; i < ZONE_KEYS.length; i += 1) next[ZONE_KEYS[i]] = prev[ZONE_KEYS[i]];
          next[key] = clampBar(value);
          return next;
        });
      }

      function send(action) {
        if (busy || flow !== "live") return;
        var targetId = idRef.current;
        if (targetId === null) {
          setFlow("lost");
          setNotice("未取到 panelId；请重新发起本次调用。");
          return;
        }
        var body = { action: action === "submit" ? ACTION_SUBMIT : ACTION_SKIP, panelId: targetId };
        if (action === "submit") {
          var built = buildRaw(bars, unemployment);
          if (built.error) {
            setNotice(built.error);
            return;
          }
          body.raw = built.value;
        }
        setBusy(true);
        setNotice(action === "submit" ? "正在提交…" : "正在跳过…");
        post(body, MAX_RETRIES).then(function (res) {
          if (res.unavailable) {
            setBusy(false);
            setNotice("面板通道不可用（POST " + ROUTE + "），本次按未提供处理。");
            return;
          }
          var data = res.data || {};
          if (data.ok === true) {
            setFlow(action === "submit" ? "submitted" : "skipped");
            setNotice(action === "submit" ? "已提交，等待分析" : "已跳过，等待分析");
            return;
          }
          var code = readString(data.code);
          if (code === "already-settled") {
            setBusy(false);
            setFlow("settled");
            setNotice("面板已结算（可能已在别处提交或已超时）。");
            return;
          }
          if (code === "no-panel") {
            setBusy(false);
            setFlow("lost");
            setNotice("Host 里没有这个待填面板；请重新发起本次调用。");
            return;
          }
          setBusy(false);
          setNotice(
            "Host 未接受本次" + (action === "submit" ? "提交" : "跳过") +
            (code !== null ? "（" + code + "）" : "") + "，可重试。"
          );
        });
      }

      var locked = flow !== "live" || busy || !ready;
      var titleCity = city !== null ? city : readString(panel && panel.city) !== null ? panel.city : "城市";
      var title = titleCity + " · 请先补 RCIO 需求条与失业率";

      var inner = el(
        "div",
        { className: "csl2-panel" },
        el("div", { className: "csl2-title" }, title),
        // 需求 8：顶部固定一行说明，永远显示（reason 另起一行，不替换这句）
        el("p", { className: "csl2-sub" }, "这一步只影响建议精度，不影响是否分析。可直接点『跳过，直接分析』。"),
        reason !== null ? el("p", { className: "csl2-meta" }, "原因：" + reason) : null,
        savePath !== null ? el("p", { className: "csl2-meta" }, "存档：" + savePath) : null,
        el(
          "div",
          { className: "csl2-grid" },
          ZONE_KEYS.map(function (key) {
            return el(VerticalSlider, {
              key: key,
              label: ZONE_LABELS[key],
              aria: ZONE_ARIA[key],
              value: bars[key],
              onChange: function (next) { changeZone(key, next); }
            });
          })
        ),
        el(
          "div",
          { className: "csl2-uo" },
          el("label", { className: "csl2-uo-label", htmlFor: "csl2-unemployment" }, "失业率"),
          el("input", {
            id: "csl2-unemployment",
            className: "csl2-uo-input",
            type: "number",
            min: 0,
            max: 100,
            step: 0.1,
            inputMode: "decimal",
            value: unemployment,
            placeholder: "例如 6.5",
            "aria-label": "失业率百分比（0–100，可留空）",
            disabled: locked,
            onChange: function (event) { setUnemployment(String(event.target.value)); }
          }),
          el("span", { className: "csl2-uo-hint" }, "%　" + UNEMPLOYMENT_HINT_EMPTY)
        ),
        el(
          "div",
          { className: "csl2-actions" },
          el(
            "button",
            {
              type: "button",
              className: "csl2-btn csl2-btn-primary",
              disabled: locked,
              onClick: function () { send("submit"); }
            },
            "提交并分析"
          ),
          el(
            "button",
            {
              type: "button",
              className: "csl2-btn csl2-btn-secondary",
              disabled: locked,
              onClick: function () { send("skip"); }
            },
            "跳过，直接分析"
          )
        ),
        el(StatusLine, { text: notice !== "" ? notice : !ready && flow === "live" ? "正在打开面板…" : "" })
      );

      // 非模态（老路径/测试）直接返回卡片；模态时把它套进 fixed + 遮罩外壳。
      if (props.modal !== true) return inner;

      var live = props.live;
      var warnBlocked = function (source) {
        // 点遮罩 / 按 Esc 都不关闭：panelId 一旦生成，关掉只会让工具白等到超时。
        // 用户不会被"静默无视"：卡片里常驻一行说明（csl2-uo-hint）。
        if (live && typeof live.warnBlocked === "function") live.warnBlocked(source);
      };
      var modal = el(
        "div",
        {
          className: "csl2-modal",
          role: "dialog",
          "aria-modal": "true",
          "aria-label": "RCIO 需求条与失业率输入",
          onMouseDown: function (event) { if (event.target === event.currentTarget) warnBlocked("backdrop"); }
        },
        null,
        el(
          "div",
          {
            className: "csl2-modal-card",
            tabIndex: -1,
            onKeyDown: function (event) { if (event.key === "Escape") { event.preventDefault(); warnBlocked("escape"); } }
          },
          null,
          inner,
          el(
            "div",
            { className: "csl2-dialog-actions" },
            el("span", { className: "csl2-uo-hint" }, "遮罩 / Esc 不会关闭本面板：请用上方两个按钮之一结束本次读数。")
          )
        )
      );

      // Portal 到 document.body（脱离卡片布局/折叠/裁切）；取不到 react-dom 时退回内联模态。
      return el(PortalPanel, { fallback: modal }, null, modal);
    }

    function readSettledNotice(result) {
      if (!result || typeof result !== "object") return "已结算。";
      if (result.status === "provided") return "已提交，等待分析";
      if (result.status === "skipped") return "已跳过（本次未提供 RCIO 需求条与失业率）。";
      if (result.status === "timeout") return "等待超时，已按未提供处理。";
      if (result.status === "unavailable") return "面板通道不可用，已按未提供处理。";
      return "已结算。";
    }

    function SettledPanel(props) {
      var block = props.block;
      var value = readResultValue(block);
      var status = value ? readString(value.status) : null;
      var standard = value && value.standard && typeof value.standard === "object" ? value.standard : null;
      var message = value ? readString(value.message) : null;

      var head;
      if (status === "provided") head = "本次已提供 RCIO 需求条与失业率（只读回放）。";
      else if (status === "skipped") head = "已跳过：本次未提供 RCIO 需求条与失业率。";
      else if (status === "timeout") head = "等待超时：本次按未提供处理，分析照常进行。";
      else if (status === "unavailable") head = "面板通道不可用：本次按未提供处理，分析照常进行。";
      else head = "本次调用已结束。";

      var rows = [];
      if (standard !== null && standard.rcio && typeof standard.rcio === "object") {
        for (var i = 0; i < ZONE_KEYS.length; i += 1) {
          var zoneKey = ZONE_KEYS[i];
          var entry = standard.rcio[zoneKey];
          if (!entry || typeof entry !== "object") continue;
          var bar = clampBar(entry.bar);
          var level = readString(entry.levelLabel) || levelLabelOf(classifyLevel(bar));
          rows.push(
            el("div", { className: "csl2-kv-k", key: "k-" + zoneKey }, ZONE_LABELS[zoneKey]),
            el("div", { className: "csl2-kv-v", key: "v-" + zoneKey }, formatSignedBar(bar) + "（" + level + "）")
          );
        }
        var uo = standard.unemployment && typeof standard.unemployment === "object" ? standard.unemployment : null;
        if (uo !== null) {
          var uoText = formatPercent(uo.percent);
          if (readString(uo.bandLabel) !== null) uoText += "（" + uo.bandLabel + "）";
          rows.push(el("div", { className: "csl2-kv-k", key: "k-uo" }, "失业率"));
          rows.push(el("div", { className: "csl2-kv-v", key: "v-uo" }, uoText));
        }
      }

      return el(
        "div",
        { className: "csl2-panel csl2-readonly" },
        el("div", { className: "csl2-title" }, "CSL2 RCIO 读数 · " + TOOL_NAME),
        el("p", { className: "csl2-sub" }, head),
        rows.length > 0 ? el("div", { className: "csl2-kv" }, rows) : null,
        standard !== null && readString(standard.summary) !== null
          ? el("p", { className: "csl2-meta" }, standard.summary)
          : null,
        message !== null ? el("p", { className: "csl2-meta" }, message) : null
      );
    }

    function HintPanel(props) {
      return el("div", { className: "csl2-panel" }, el("div", { className: "csl2-hint " + (props.tone || "") }, props.text));
    }

    /** tool.call.toolview 的注册组件：必须是 props 的纯函数。 */
    function CityReadingsPanel(props) {
      if (R === null) {
        // React 运行时缺失时无法渲染任何节点（apply 已 warn）；返回 null 而不是抛错。
        return null;
      }
      if (!props || typeof props !== "object") {
        return el(HintPanel, { text: "RCIO 面板：拿不到工具调用信息（回放安全提示）。", tone: "" });
      }
      if (props.phase === "preparing") {
        return el(HintPanel, { text: "RCIO 面板准备中：等待工具参数…", tone: "" });
      }
      if (props.phase === "result") {
        // 结果阶段不再拦截界面：只做只读回放（内联一行），避免挡住了用户看结论。
        return el(SettledPanel, { block: props.block, callId: props.callId });
      }
      if (props.phase === "start") {
        if (!props.block || typeof props.block !== "object") {
          return el(HintPanel, { text: "RCIO 面板：工具调用数据缺失（回放安全提示）。", tone: "csl2-hint-warn" });
        }
        // 待填写 = 弹窗形态（模态外壳由 InteractivePanel 自己套，见其 modal 分支）。
        return el(InteractivePanel, { block: props.block, callId: props.callId, modal: true, live: { warnBlocked: props.__warnBlocked } });
      }
      return el(HintPanel, { text: "RCIO 面板：未知的调用阶段「" + String(props.phase) + "」（回放安全提示）。", tone: "" });
    }

    /* =====================================================================
     * 7) 插件入口：只导出 apply / inject（静态 client half 的真实形态）
     * ===================================================================== */

    var inject = ["slots"];

    function registerPanel(ctx) {
      return ctx.slots.inject("tool.call.toolview", function () {
        return ctx.slots.register({ name: "tool.call.toolview", key: TOOL_NAME }, CityReadingsPanel);
      });
    }

    function apply(ctx) {
      // 关键：apply 本身**绝不抛错**。静态 client bundle 里一旦抛错，运行时会记
      // "loaded without registering" 并让整张卡片消失；这里全部兜住并把原因记进 __diag。
      diag.steps.push("apply");
      R = resolveReact();
      if (R === null) {
        R = makeFallbackReact();
        diag.react = "fallback";
        try { console.warn("csl2-city-advisor: 取不到 React，改用内置极简兜底（面板仍可渲染）"); } catch (e) { /* ignore */ }
      } else {
        diag.react = R.__fallback === true ? "fallback" : "real";
      }
      try {
        insertStyles(ctx);
        diag.styles = true;
      } catch (e) {
        diag.stylesError = String((e && e.message) || e);
        try { console.warn("csl2-city-advisor: 样式注入失败", e); } catch (e2) { /* ignore */ }
      }
      if (!ctx || !ctx.slots || typeof ctx.slots.inject !== "function") {
        diag.slots = false;
        try { console.warn("csl2-city-advisor: 当前 Client 没有 slots 服务，RCIO 面板未注册"); } catch (e) { /* ignore */ }
        return;
      }
      diag.slots = true;
      try {
        if (typeof ctx.effect === "function") ctx.effect(function () { return registerPanel(ctx); }, "csl2: RCIO readings panel");
        else registerPanel(ctx);
        diag.registered = true;
      } catch (e) {
        diag.registerError = String((e && e.message) || e);
        try { console.warn("csl2-city-advisor: tool.call.toolview 注册失败（将退回通用卡片）", e); } catch (e2) { /* ignore */ }
      }
    }

    exports.apply = apply;
    exports.inject = inject;
    exports.__panel = CityReadingsPanel; // 仅测试用
    exports.__diag = diag; // 仅诊断用：记录 apply 走到哪一步、React 来源、注册是否成功
    return module.exports;
  }
});

/* =========================================================================
 * 实现说明（Lead 需要的事实，供 task-4 独立验证引用）
 *
 * 1) 注册方式（实际采用，唯一路径，无回退分支）：
 *      exports.inject = ['slots']
 *      ctx.slots.inject('tool.call.toolview', () => ctx.slots.register({
 *        name: 'tool.call.toolview', key: 'csl2_city_readings'
 *      }, CityReadingsPanel))
 *    - 依据：_probe\DSH-CONTRACTS.md Q6 + dsh-client-ui-tool\lib\client.js:2340-2353
 *      （owner 在 ToolCallTree 用 renderSlot('tool.call.toolview', owner,
 *       { entryKey: toolName, hookContext, fallback: <GenericToolCard/> }) 派发）。
 *    - keyed 槽未命中只会退回通用卡片，不会崩；因此不存在"主方案/回退方案"两条路径。
 *    - 不声明 locale，文案全部由 React.createElement 自绘中文。
 *    - 包在 ctx.effect(...) 里注册（与 dsh-univer-office 同款），失败只 console.warn。
 *    - ⚠️ 该注册形态未在运行中的 GUI 里端到端验证过（Lead 负责端到端）；静态契约已核实。
 *
 * 2) 组件 props（依据 Q7 + Lead 更正 + dsh-client-ui-tool 渲染路径 ToolCall/ToolCallBranch）：
 *      { toolName, callId, entryKey, phase: 'preparing'|'start'|'result', block, hookContext, ... }
 *    - preparing: block = { phase, callId, name, turn, step, time, subCalls:[] }，无 argsRaw
 *                 -> 只渲染一行提示，绝不读 panelId。
 *    - start    : block = { phase, callId, name, argsRaw, ... }，argsRaw 是 JSON 字符串。
 *    - result   : block = { kind:'tool-result', callId, call:{name,argsRaw}, content[],
 *                 isError, error?, meta?, subCalls }；meta = presentationMeta({status, standard})。
 *    实现按 [arguments, argsRaw, args, input, call.arguments, call.argsRaw] 依次容错解析，
 *    缺失/畸形一律降级为提示行，绝不抛错（回放安全）。
 *
 * 3) Client→Host 通道（Host half = task-1 冻结的 wire 契约）：同源
 *      POST window.location.origin + '/csl2-readings'
 *      body: { action:'readings.open'|'readings.submit'|'readings.skip'|'readings.poll', panelId?, callId?, raw? }
 *    - open 带 callId（Host 用 exec.callId 建索引，并发 N 个面板也不会串），panelId 已知时一并带上；
 *      poll/submit/skip 用 Host 回填的 panelId。
 *    - Host 的业务失败也是 HTTP 200 + body.ok === false：
 *        · code:'no-panel'        -> open 退避重试 600/1200/1800ms（最多 3 次）；submit/skip 提示重新发起
 *        · code:'ambiguous-panel' -> 只显示一行"请重新发起"，不重试风暴
 *        · code:'already-settled' -> 提示已结算并停止
 *      只有 400/404/405 这类非 2xx 才算"通道不可用"。
 *    - 非 2xx / 网络异常 = 通道不可用：最多退避重试 2 次（400ms、800ms），
 *      仍失败则显示灰字提示并停止（轮询连续 3 次失败即停）。不抛错、不无限重试。
 *    - 拿到 panelId 之前两个按钮 disabled；open 8s 无响应也会解锁，不会永久锁死。
 *    - 挂载后 open，之后每 1500ms poll（上限 1200 次）；status==='settled' 或卸载即停
 *      （React.useEffect 的清理函数里 clearInterval/clearTimeout）。
 *    - result 阶段**不再** open/poll，只用 block.meta = { status, standard, panelId } 回放。
 *    - ⚠️ 该 HTTP 通道未端到端验证（Lead 承诺在 GUI 实调一次）；Host 侧路由
 *      为 ctx.webServer.register({ kind:'prefix', path:'/csl2-readings', handler })。
 *      但 tests/client-rcio-parity.mjs §8 用假 fetch 逐条锁住了上述 wire 形态。
 *
 * 4) 样式：优先运行时内建 styles.insert(css)（动态 Client half 才有），
 *    其次 ctx.get('styles')，两者都不可用时回退 document.head
 *    （与 dsh-univer-office\lib\client.js:23470 injectStyles 完全同款，已核实可用）。
 *    类名一律 csl2- 前缀；除 @media (prefers-reduced-motion) 外无全局选择器。
 *
 * 5) 档位口径（CONTRACT §4）在本文件内联，且**函数名/入参约定/返回形状与 lib/rcio.js 完全一致**：
 *    ZONE_KEYS/ZONE_LABELS/LEVELS/LEVEL_LABELS/BANDS/BAND_LABELS/clampBar/normalizeBar/
 *    classifyLevel(bar)/levelLabelOf/classifyUnemployment(percent)/bandLabelOf/describeZone/
 *    describeUnemployment/flagsOf/formatSignedBar/formatPercent/summarize/standardize。
 *    tests/client-rcio-parity.mjs 装载**真实的 client.js bundle** 与 lib/rcio.js 比对：
 *    常量表 6 项 + 逐函数 1000+ 点 + standardize 1055 组深度相等（含 summary/flags）。
 *
 * 6) 测试钩子：exports.__rcio（口径函数）与 exports.__panel（组件）仅供
 *    tests/client-rcio-parity.mjs 使用（含 apply(stubCtx) 注册形态断言、
 *    12 种畸形 props 浅渲染、滑条档位文字回归锁、wire 契约假 fetch 断言），运行时忽略。
 *    —— 已知回归陷阱：`classifyLevel(bar)` 收的是 bar，UI 里**不要**再写 `classifyLevel(value / 100)`
 *       （双重归一后 -100…100 全部落到 neutral，面板档位文字会永远显示「无需求」）；
 *       该回归已被 §7e 锁住（host-tool-dev 在交叉比对中发现并报告）。
 * ========================================================================= */
