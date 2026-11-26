// The summary under the Forecast tab's headline on very different days.     node tests/stand_cases.js
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'template.html'), 'utf8');
const a = src.indexOf('  function standText('), b = src.indexOf('\n  }\n', a) + 4;
const standText = new Function(src.slice(a, b) + '; return standText;')();
const F0 = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'forecast_2028.json')));
const day = o => Object.assign({}, F0, o);
const cases = [
  ['today', day({days_out: 712, p_tie: 0.0054}), 70, 30, [/^Two years out and with no nominees yet, the Democratic candidate has a 70% chance of winning and the Republican a 30% chance\./, /0\.5% of simulated elections/, /lean, not a call\.$/]],
  ['a year and a half', day({days_out: 520}), 58, 42, [/^A year and a half out and with no nominees yet/, /lean, not a call/]],
  ['toss-up', day({days_out: 400}), 52, 48, [/^About a year out/, /close to even\.$/]],
  ['Republicans favored', day({days_out: 200}), 22, 78, [/^7 months out/, /The Democrats still win about one simulated election in five\.$/]],
  ['nominees known', day({days_out: 70, nominees_known: true, nominees: ['Gretchen Whitmer', 'JD Vance']}), 81, 19, [/^2 months out, Gretchen Whitmer has an 81% chance of winning and JD Vance a 19% chance\./, /JD Vance still wins about one simulated election in five\.$/], [/no nominees/, /Democratic candidate/]],
  ['weeks', day({days_out: 21, nominees_known: true, nominees: ['A Person', 'B Person']}), 50, 50, [/^3 weeks out, A Person/, /close to even/]],
  ['lopsided, no tie', day({days_out: 5, p_tie: 0.0001}), 99, 1, [/^5 days out/, /Almost no simulated elections end in a 269 to 269 tie/, /fewer than one simulated election in 50/]],
  ['eve', day({days_out: 1}), 64, 36, [/^The day before the election/]],
  ['articles', day({days_out: 100}), 89, 11, [/has an 89% chance of winning and the Republican an 11% chance/]],
  ['articles 2', day({days_out: 100}), 18, 82, [/has an 18% chance of winning and the Republican an 82% chance/]],
  ['Election Day', day({days_out: 0}), 64, 36, [/^On Election Day/]],
];
let bad = 0;
for (const [name, F, hd, hr, must, no = []] of cases) { const t = standText(F, hd, hr);
  must.forEach(r => { if (!r.test(t)) { bad++; console.error('FAIL ' + name + ': missing ' + r + '\n  ' + t); } });
  no.forEach(r => { if (r.test(t)) { bad++; console.error('FAIL ' + name + ': should not say ' + r + '\n  ' + t); } });
  if (/undefined|NaN/.test(t)) { bad++; console.error('FAIL ' + name + ': ' + t); }
  if (process.argv.includes('-v')) console.log('[' + name + '] ' + t); }
if (bad) process.exit(1);
console.log('ok (the summary under the headline on ' + cases.length + ' different days)');
