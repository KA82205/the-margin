// The Polls page's words on very different days: every line and the paragraphs must say what the data say.
//   node tests/polls_page_cases.js
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'template.html'), 'utf8');
const grab = name => { const a = src.indexOf('  function ' + name + '('), b = src.indexOf('\n  }\n', a) + 4; return src.slice(a, b); };
const fns = new Function(grab('pollWhy') + grab('pollsIntro') + grab('pollsNote') + '; return {pollWhy, pollsIntro, pollsNote};')();
const F0 = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'forecast_2028.json')));
let bad = 0; const want = (name, text, ok, no = []) => { ok.forEach(r => { if (!r.test(text)) { bad++; console.error('FAIL ' + name + ': missing ' + r + '\n  ' + text); } }); no.forEach(r => { if (r.test(text)) { bad++; console.error('FAIL ' + name + ': should not say ' + r + '\n  ' + text); } }); if (/undefined|NaN|null/.test(text)) { bad++; console.error('FAIL ' + name + ': ' + text); } };
const W = fns.pollWhy;
want('national, counted', W({place: 'US', usable: true, share_of_average: 0.24, weight: 0.0062}, F0).text, [/^Counted: 24% of the national polling average, 0\.6% of the national vote estimate$/]);
want('state, counted', W({place: 'WI', where: 'Wisconsin', usable: true, share_of_average: 0.5, weight: 0.21}, F0).text, [/50% of the polls of Wisconsin, 21% of Wisconsin.s estimate/]);
want('too old', W({place: 'AK', where: 'Alaska', usable: true, share_of_average: 0, weight: 0}, F0).text, [/too old/], [/^Counted:/]);
want('tiny weight', W({place: 'US', usable: true, share_of_average: 0.0004, weight: 0.00001}, F0).text, [/under 0\.1% of the national polling average/]);
want('several reasons', W({place: 'NC', usable: false, why: 'a', why_all: ['Barack Obama cannot be elected again', 'paid for by a party or a campaign']}, F0).text, [/^Set aside: Barack Obama cannot be elected again; paid for by a party or a campaign$/]);
want('reason missing', W({place: 'NC', usable: false}, F0).text, [/no reason recorded/]);
want('no weight known (older file)', W({place: 'US', usable: true}, F0).text, [/^Counted in the national average$/]);
const I = (o, t = {}) => Object.assign({}, F0, t, {inputs: Object.assign({}, F0.inputs, o)});
const nat = n => Array.from({length: n}, () => ({place: 'US', usable: true}));
want('today', fns.pollsIntro(F0, nat(28), [{usable: true, share_of_average: 0}, {usable: false}]), [/28 polls of the national race and 2 polls of single states/, /hypothetical/, /2\.6%/, /0 carry weight, 1 meets the rules but is too old to count and 1 is set aside/]);
want('nominees known, polls dominant', fns.pollsIntro(I({poll_share: 0.58}, {nominees_known: true, nominees: ['Gretchen Whitmer', 'JD Vance']}), nat(40), [{usable: true, share_of_average: 0.3}, {usable: true, share_of_average: 0.2}]),
  [/Both nominees are known \(Gretchen Whitmer and JD Vance\)/, /58% of the national vote estimate today, most of it/, /2 carry weight/], [/hypothetical/, /too old/]);
want('no polls at all', fns.pollsIntro(I({poll_share: 0}), [], []), [/No poll of the 2028 general election is in hand yet/], [/count for/]);
want('one national poll', fns.pollsIntro(F0, nat(1), []), [/^1 poll of the national race and 0 polls of single states/]);
want('the note follows the rules list', fns.pollsNote(F0), [/generic ballot/, /22nd Amendment/, /own state/, /nominees are known/, /half as much/, /1\.5 polls/]);
want('the note with a changed rules list', fns.pollsNote(Object.assign({}, F0, {poll_rules: {state: ['rule one', 'rule two'], national_window_days: 90, prior_polls: 2}})), [/set aside when rule one; or rule two\./, /last 90 days/, /worth 2 polls/]);
if (bad) process.exit(1);
console.log('ok (the Polls page on counted, unweighted, set-aside and unknown lines, nominees known or not, no polls, and a changed rules list)');
