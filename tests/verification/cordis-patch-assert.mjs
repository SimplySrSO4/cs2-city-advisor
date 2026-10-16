// A4 断言脚本：cordis.patch.yml（≤30 行，零第三方依赖 —— 本机无 js-yaml，捆绑 Python 无 PyYAML）
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const file = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'cordis.patch.yml');
const text = readFileSync(file, 'utf8');
const bad = [];
if (/\t/.test(text)) bad.push('包含 tab 字符');
const tops = text.split(/\r?\n/).filter((line) => /^-\s/.test(line));
if (tops.length !== 1 || !/^-\s*insert:\s*$/.test(tops[0])) bad.push(`顶层应为单元素数组 [- insert:]，实际 ${JSON.stringify(tops)}`);
if (text.split(/\r?\n/).filter((line) => /^\s+-\s+id:/.test(line)).length !== 1) bad.push('insert 列表项数 != 1');
const id = (text.match(/^\s*-\s*id:\s*(\S+)\s*$/m) ?? [])[1];
const name = (text.match(/^\s*name:\s*'?([^'\s]+)'?\s*$/m) ?? [])[1];
if (id !== 'csl2-city-advisor') bad.push(`insert[0].id 应为 csl2-city-advisor，实际 ${id}`);
if (name !== 'csl2-city-advisor') bad.push(`insert[0].name 应为 csl2-city-advisor，实际 ${name}`);
console.log(bad.length === 0
  ? 'PASS A4 cordis.patch.yml：单元素数组 + insert[0].id/name=csl2-city-advisor + 无 tab'
  : `FAIL A4 ${bad.join('；')}`);
process.exit(bad.length === 0 ? 0 : 1);
