/**
 * tests/verification/harness.mjs —— 独立验证脚本的共享小工具
 *
 * 零第三方依赖，只用 Node 内建。**不含任何被测代码的副本**，只做输出/收集。
 *
 * 约定（供 run-all.mjs 聚合）：
 *   PASS <id> <detail> / FAIL <id> <detail> / INFO ... / UNVERIFIED <id> <detail>
 *   --json <path> 写机读汇总；退出码 0 = 无 FAIL，1 = 有 FAIL，2 = 前置条件不满足。
 *
 * 注意：本机沙箱下 Node 的 child_process 默认 'pipe' 会 EPERM，
 *       所以 runCapture() 用「文件描述符重定向」而不是管道来捕获子进程输出。
 */

import { mkdirSync, writeFileSync, openSync, closeSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const HERE = path.dirname(fileURLToPath(import.meta.url));
/** 工作区根：<root>/plugins/csl2-city-advisor/tests/verification -> <root> */
export const ROOT = path.resolve(HERE, '..', '..', '..', '..');
export const PLUGIN = path.join(ROOT, 'plugins', 'csl2-city-advisor');
export const LIB = path.join(PLUGIN, 'lib');
export const SKILL_PLUGIN = path.join(PLUGIN, 'skills', 'cities-skylines-2-city-advisor');
export const SKILL_ORIGINAL = path.join(ROOT, 'skill', 'cities-skylines-2-city-advisor');
export const VERIFY_DIR = path.join(ROOT, '_probe', 'verify');
export const CONTRACT = path.join(PLUGIN, 'CONTRACT.md');

export const NODE = process.execPath;

export function argValue(flag) {
  const index = process.argv.indexOf(flag);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : null;
}

let captureSeq = 0;

/**
 * 运行子进程并把 stdout+stderr 落盘后读回（不用管道，规避本机沙箱的 EPERM）。
 * @returns {{status:number|null, output:string, error:string|null, signal:string|null}}
 */
export function runCapture(command, args, options = {}) {
  const tmpDir = path.join(VERIFY_DIR, 'tmp');
  mkdirSync(tmpDir, { recursive: true });
  const log = path.join(tmpDir, `cap-${process.pid}-${(captureSeq += 1).toString(36)}.log`);
  const fd = openSync(log, 'w');
  let result;
  try {
    result = spawnSync(command, args, {
      cwd: options.cwd,
      stdio: ['ignore', fd, fd],
      timeout: options.timeout
    });
  } finally {
    closeSync(fd);
  }
  let output = '';
  try {
    output = readFileSync(log, 'utf8');
  } catch {
    output = '';
  }
  return {
    status: result.status,
    signal: result.signal ?? null,
    output,
    error: result.error ? String(result.error.code ?? result.error.message) : null
  };
}

export function createReport(script) {
  const items = [];
  const api = {
    items,
    pass(id, detail = '') {
      items.push({ id, status: 'PASS', detail });
      console.log(`PASS        ${id}${detail ? `  ::  ${detail}` : ''}`);
    },
    fail(id, detail = '') {
      items.push({ id, status: 'FAIL', detail });
      console.log(`FAIL        ${id}${detail ? `  ::  ${detail}` : ''}`);
    },
    unverified(id, detail = '') {
      items.push({ id, status: 'UNVERIFIED', detail });
      console.log(`UNVERIFIED  ${id}${detail ? `  ::  ${detail}` : ''}`);
    },
    info(text = '') {
      console.log(`INFO        ${text}`);
    },
    /** condition 为真 -> PASS，否则 FAIL。 */
    check(id, condition, detail = '', failDetail = '') {
      if (condition) api.pass(id, detail);
      else api.fail(id, failDetail === '' ? detail : failDetail);
      return condition === true;
    },
    fatal(message) {
      console.log(`FATAL       ${message}`);
      const target = argValue('--json');
      if (target) {
        mkdirSync(path.dirname(target), { recursive: true });
        writeFileSync(target, JSON.stringify({ script, fatal: message, pass: 0, fail: 1, unverified: 0, items }, null, 2));
      }
      process.exit(2);
    },
    finish() {
      const pass = items.filter((item) => item.status === 'PASS').length;
      const fail = items.filter((item) => item.status === 'FAIL').length;
      const unverified = items.filter((item) => item.status === 'UNVERIFIED').length;
      const target = argValue('--json');
      if (target) {
        mkdirSync(path.dirname(target), { recursive: true });
        writeFileSync(
          target,
          JSON.stringify({ script, pass, fail, unverified, items }, null, 2)
        );
      }
      console.log(`SUMMARY     ${script}: PASS=${pass} FAIL=${fail} UNVERIFIED=${unverified}`);
      process.exit(fail === 0 ? 0 : 1);
    }
  };
  return api;
}

/** 稳定 JSON 字符串（便于打印差异）。 */
export function show(value) {
  if (typeof value === 'number' && Object.is(value, -0)) return '-0';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' || typeof value === 'boolean' || value === null) return String(value);
  if (value === undefined) return 'undefined';
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/** 确定性 PRNG（mulberry32）——保证每次跑同一批随机输入。 */
export function makeRandom(seed) {
  let state = seed >>> 0;
  return function random() {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
