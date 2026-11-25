// The page's margin text and colour come from one routine. A margin that rounds to 0.0 is written "0.0", with no
// party letter and no sign, in the neutral colour; anything else keeps its party.      node tests/test_page.js
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'template.html'), 'utf8');
const grab = name => { const m = src.match(new RegExp('^\\s*const ' + name + ' = .*$', 'm')); if (!m) throw new Error('not found: ' + name); return m[0]; };
const { pts, pcl, mg, cls, signed } = new Function(grab('side') + '\n' + grab('pts') + '\n' + grab('pcl') + '\n' + grab('mg') + '\n' + grab('signed') + '\nreturn {pts, pcl, mg, cls, signed};')();
const eq = (a, b, what) => { if (a !== b) { console.error('FAIL', what, JSON.stringify(a), '!==', JSON.stringify(b)); process.exit(1); } };
for (const v of [0, -0, 0.04, -0.04, 0.049, -0.049, 1e-12, -1e-12]) { eq(pts(v), '0.0', 'text of ' + v); eq(pcl(v), 'even', 'colour of ' + v); }
eq(pts(0.05), 'D+0.1', '0.05'); eq(pts(-0.05), 'R+0.1', '-0.05'); eq(pcl(0.05), 'dem', '0.05'); eq(pcl(-0.05), 'rep', '-0.05');
eq(pts(0.1), 'D+0.1', '0.1'); eq(pts(-0.1), 'R+0.1', '-0.1'); eq(pts(12.34), 'D+12.3', '12.34'); eq(pts(-42.95), 'R+43.0', '-42.95'); eq(pts(100), 'D+100.0', '100');
eq(mg(50), '0.0', 'share 50'); eq(mg(50.02), '0.0', 'share 50.02'); eq(cls(49.98), 'even', 'share 49.98'); eq(mg(50.03), 'D+0.1', 'share 50.03'); eq(mg(49.16), 'R+1.7', 'share 49.16'); eq(cls(49.16), 'rep', 'share 49.16');
for (let v = -3; v <= 3; v += 0.001) { const t = pts(v), c = pcl(v); if (/[+-]0\.0|^-/.test(t)) eq(t, 'never', 'a signed zero at ' + v); eq(c === 'even', t === '0.0', 'text and colour disagree at ' + v); }
// changes and differences: the same rule. Never +0.0 or a minus before 0.0; the colour follows the rounded figure
for (const v of [0, -0, 0.04, -0.04, 0.049, -0.049, 1e-9, -1e-9]) { eq(signed(v), '0.0', 'change of ' + v); eq(pcl(v), 'even', 'colour of change ' + v); }
eq(signed(0.05), '+0.1', 'change 0.05'); eq(signed(-0.05), '\u22120.1', 'change -0.05'); eq(signed(2.34), '+2.3', 'change 2.34'); eq(signed(-12), '\u221212.0', 'change -12');
for (let v = -2; v <= 2; v += 0.001) { if (/^[+\u2212-]0\.0$/.test(signed(v))) eq(signed(v), 'never', 'a signed zero change at ' + v); }
if (/\(x >= 0 \? '\+'|>= 0 \? 'dem' : 'rep'/.test(src)) { console.error('FAIL: a sign is taken before rounding somewhere in the template'); process.exit(1); }
if (/D\+0\.0|R\+0\.0/.test(src)) { console.error('FAIL: an old zero format is still in the template'); process.exit(1); }
console.log('ok (margins: one routine, a neutral 0.0, text and colour agree)');
