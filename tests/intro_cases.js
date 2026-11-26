// The Forecast tab's introduction on very different days: it must say what the inputs say, and nothing fixed.
//   node tests/intro_cases.js
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'template.html'), 'utf8');
const a = src.indexOf('  function introText(F) {'), b = src.indexOf('\n  }\n', a) + 4;
const introText = new Function(src.slice(a, b) + '; return introText;')();
const F0 = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'forecast_2028.json')));
const day = (over, top = {}) => Object.assign({}, F0, top, { inputs: Object.assign({}, F0.inputs, over) });
const cases = [
  ['today', day({}), [/more disapprove/, /point the other way/, /Republicans ahead/, /Both structural models favor the Democrats/, /possible matchups/]],
  ['popular president, models R', day({net_approval: 12.4, approval_and_economy: 47.5, approval_model: 48.2}), [/more approve of the president than disapprove/, /favor the Republicans/, /\+12\.4/], [/unpopular/, /disapprove of the president than approve/]],
  ['approval near zero', day({net_approval: -1.2, approval_and_economy: 50.2, approval_model: 49.9}), [/near zero \(\u22121\.2\)/, /close to even/]],
  ['models disagree', day({approval_and_economy: 51.5, approval_model: 48.6}), [/disagree/, /approval-and-economy model D\+3\.0/, /approval equation R\+2\.8/]],
  ['polls agree', day({national_polls: 52.5}), [/agree, with the Democrats ahead \(D\+5\.0\)/], [/other way/]],
  ['polls close', day({national_polls: 50.2}), [/close race/]],
  ['no polls', day({national_polls: null, polls_n: 0, poll_share: 0}), [/No national poll counts yet/]],
  ['DeSart in', day({long_range: 49.0, long_range_weight: 1}), [/All three structural models|disagree|lean/, /long-range|R\+2\.0/]],
  ['official forecasts', day({long_range: 51.0, long_range_weight: 1, model_sources: {enns: "authors' forecast", desart: "authors' forecast"}}), [/All three structural models favor/, /The approval-and-economy and long-range figures are the authors' own published forecasts\./], []],
  ['official, models disagree', day({approval_and_economy: 48.0, long_range: 51.0, long_range_weight: 1, model_sources: {enns: "authors' forecast", desart: "authors' forecast"}}), [/published approval-and-economy forecast of Enns/, /DeSart's published long-range forecast/]],
  ['nominees known, polls dominant', day({poll_share: 0.6, national_polls: 49.0}, {nominees_known: true}), [/^National polls of the two nominees/, /carry most of the national vote estimate \(60%\)/], [/possible matchups/, /not yet known/]],
  ['June approval observed', day({june_approval: -8.0, net_approval: -9.5}), [/June 2028 net approval of −8\.0/]],
  ['polls midway', day({poll_share: 0.24}, {nominees_known: true}), [/count for 24% of the national vote estimate/]],
];
let bad = 0;
for (const [name, F, must, mustNot = []] of cases) {
  const t = introText(F);
  must.forEach(r => { if (!r.test(t)) { bad++; console.error('FAIL ' + name + ': missing ' + r + '\n  ' + t); } });
  mustNot.forEach(r => { if (r.test(t)) { bad++; console.error('FAIL ' + name + ': should not say ' + r + '\n  ' + t); } });
  if (/market/i.test(t) || /undefined|NaN/.test(t)) { bad++; console.error('FAIL ' + name + ': ' + t); }
  const sentences = t.split(/\.\s/).length; if (sentences > 3) { bad++; console.error('FAIL ' + name + ': too long'); }
  if (process.argv.includes('-v')) console.log('[' + name + '] ' + t);
}
if (bad) process.exit(1);
console.log('ok (the introduction on ' + cases.length + ' different days says what the inputs say)');
