// The headline chances, the Model tab's account of the calculation and the markets study, read from the built page.
//   node tests/browser_model.js
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
const root = path.join(__dirname, '..'); const F = JSON.parse(fs.readFileSync(path.join(root, 'data/forecast_2028.json')));
const fail = m => { console.error('FAIL: ' + m); process.exit(1); };
// complementary rounding, on hard cases: always 100, and a tie in the simulations never shows
for (const [p, r] of [[0.692275, 0.3023], [0.4975, 0.4975], [0.5, 0.49], [0.004, 0.99], [0.995, 0.0049], [0.3351, 0.6549]]) {
  const d = Math.round(100 * p / (p + r)), q = 100 - d; if (d + q !== 100 || d < 0 || q < 0) fail('rounding ' + p + ' ' + r);
}
(async () => {
  const b = await chromium.launch();
  for (const vp of [{width: 1280, height: 900}, {width: 390, height: 844}]) {
    const p = await (await b.newContext({viewport: vp})).newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
    await p.goto('file://' + path.join(root, 'docs/index.html') + '#forecast'); await p.waitForTimeout(1200);
    const top = await p.evaluate(() => [...document.querySelectorAll('#top strong')].map(e => parseInt(e.textContent)));
    if (top.length !== 2 || top[0] + top[1] !== 100) fail('headline chances ' + top);
    const want = Math.round(100 * F.p_dem / (F.p_dem + F.p_rep)); if (top[0] !== want) fail('headline Democratic chance ' + top[0] + ' against ' + want);
    if (!(F.p_tie > 0) || F.p_dem + F.p_rep + F.p_tie < 0.999) fail('the tie must stay in the data');
    const hero = await p.evaluate(() => document.querySelector('.hero').innerText);
    if (!/Winning probabilities exclude Electoral College ties\./.test(hero) || /of simulations\n/.test(hero)) fail('tie note or old wording');
    if (await p.evaluate(() => document.querySelectorAll('#odds i').length) !== 2) fail('the headline bar has a tie segment');
    await p.goto('file://' + path.join(root, 'docs/index.html') + '#model'); await p.waitForTimeout(600);
    const m = await p.evaluate(() => ({ calc: document.querySelector('#calc').textContent, mk: !!document.querySelector('#t-model #mm-t, #t-model #ms-t, #t-model #market-method'),
      rows: [...document.querySelectorAll('#nat-calc tbody tr')].map(r => [...r.cells].map(c => c.textContent)), over: document.documentElement.scrollWidth - innerWidth }));
    if (m.mk) fail('market research is still on the Model tab'); if (/market/i.test(m.calc)) fail('markets in the calculation section');
    if (/the national number|the other 97|what polls have been worth/i.test(m.calc)) fail('old phrasing');
    if (m.over > 0) fail('page wider than the screen at ' + vp.width);
    const I = F.inputs, E = I.equation, sum = m.rows.slice(0, -1).reduce((a, r) => a + parseFloat(r[3]), 0);
    if (Math.abs(sum - 100 * 0 - I.national_start) > 0.01) fail('worked calculation ' + sum + ' against ' + I.national_start);
    if (Math.abs(E.party_in_office_share - (100 - I.approval_model)) > 1e-9) fail('the equation shown is not the one the forecast ran');
    if (!m.calc.includes(E.intercept.toFixed(3)) || !m.calc.includes(E.approval.toFixed(4)) || !m.calc.includes(E.first_term.toFixed(3))) fail('coefficients not shown');
    await p.goto('file://' + path.join(root, 'docs/index.html') + '#research'); await p.waitForTimeout(600);
    const r = await p.evaluate(() => ({ mm: document.querySelectorAll('#s-markets #mm-t tr').length, ms: document.querySelectorAll('#s-markets #ms-t tr').length, why: (document.querySelector('#mm-why') || {}).textContent || '' }));
    if (r.mm < 2 || r.ms < 2 || r.why.length < 100) fail('markets study incomplete in Research ' + JSON.stringify(r));
    if (errs.length) fail(errs.join('; '));
  }
  console.log('ok (headline chances add to 100 with the tie kept in the data; the calculation and the equation match the forecast; markets only in Research)');
  await b.close();
})();
