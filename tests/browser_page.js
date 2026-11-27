// The page as a visitor meets it, at a desk and on a phone, light and dark: every place is in the list and can be found,
// sorted and filtered; no figure is written +0.0, -0.0, D+0.0 or R+0.0 on any tab; the charts draw; nothing is wider than
// the window. Needs Playwright.        node tests/browser_page.js [url]
const { chromium } = require('playwright');
const url = process.argv[2] || 'file://' + require('path').join(__dirname, '..', 'docs', 'index.html');
(async () => { const b = await chromium.launch(); let bad = 0; const fail = (w, m) => { bad++; console.error('FAIL', w, m); };
  for (const [w, h, scheme] of [[1280, 900, 'light'], [390, 844, 'dark']]) { const tag = w + ' ' + scheme;
    const p = await b.newPage({ viewport: { width: w, height: h }, colorScheme: scheme }); const errs = []; p.on('pageerror', e => errs.push(String(e)));
    await p.route('https://api.github.com/**', r => r.abort());                       // the page must stand without GitHub's answer
    await p.goto(url); await p.waitForTimeout(500);
    const rows = () => p.$$eval('#strips [data-r]', els => els.map(e => e.dataset.r));
    let r = await rows(); if (r.length !== 56) fail(tag, 'the list has ' + r.length + ' places, not 56');
    const closest = await p.$$eval('#strips [data-r] .nm', els => els.slice(0, 3).map(e => e.textContent));
    await p.selectOption('#xp-sort', 'name'); r = await rows(); if (r[0] !== 'AL' || r.length !== 56) fail(tag, 'A to Z starts with ' + r[0]);
    await p.selectOption('#xp-sort', 'ev'); r = await rows(); if (r[0] !== 'CA') fail(tag, 'most votes first starts with ' + r[0]);
    await p.click('#xp-only [data-only="battle"]'); const nb = (await rows()).length; if (!(nb > 3 && nb < 30)) fail(tag, nb + ' battlegrounds');
    await p.click('#xp-only [data-only="dem"]'); const nd = (await rows()).length; await p.click('#xp-only [data-only="rep"]'); const nr = (await rows()).length; if (nd + nr !== 56) fail(tag, 'the two leanings do not make 56: ' + nd + ' + ' + nr);
    await p.click('#xp-only [data-only="all"]'); await p.fill('#xp-q', 'nebraska'); r = await rows(); if (r.join() !== ['NE', 'NE1', 'NE2', 'NE3'].sort((a, c) => r.indexOf(a) - r.indexOf(c)).join() || r.length !== 4) fail(tag, 'search for nebraska gave ' + r);
    await p.fill('#xp-q', 'zzz'); if ((await rows()).length !== 0) fail(tag, 'a search that matches nothing still lists places'); await p.fill('#xp-q', '');
    await p.click('#strips [data-r="WY"]'); const sp = await p.textContent('#sp'); if (!/Wyoming/.test(sp) || !/R\+\d/.test(sp)) fail(tag, 'choosing Wyoming did not show its panel');
    if (/\bin 100\b|in 1,000|four times (in|out of) five/i.test(await p.evaluate(() => document.body.innerText))) fail(tag, 'a chance is written as "in 100", or an interval as "four times in five"');
    for (const st of ['DC', 'WY', 'NE2']) { const t = await p.$eval('#strips [data-r="' + st + '"]', e => e.innerText); if (!/\d%/.test(t)) fail(tag, st + ' has no chance in the list'); }
    if (!(await p.$('#daily svg, #daily p'))) fail(tag, 'no history chart'); if (await p.$('#chg')) fail(tag, 'the updates section should be gone');
    for (const hash of ['#presidency', '#forecast', '#senate', '#polls', '#polls/senate', '#states', '#states/NJ', '#states/DC', '#states/NE2', '#model', '#model/senate', '#backtests', '#backtests/senate', '#research']) {
      await p.goto(url + hash); await p.waitForTimeout(250);
      const txt = await p.evaluate(() => document.body.innerText + ' ' + Array.from(document.querySelectorAll('svg text, title')).map(e => e.textContent).join(' '));
      const z = txt.match(/[+−-]0\.0(?![\d])|[DR]\+0\.0(?![\d])/g); if (z) fail(tag, hash + ' shows ' + z.slice(0, 3).join(' '));
      const over = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth); if (over > 1) fail(tag, hash + ' is ' + over + 'px wider than the window');
    }
    await p.goto(url + '#states/NJ'); await p.waitForTimeout(250);
    const chart = await p.evaluate(() => { const f = document.querySelector('#st-prof .st-charts figure'); return { title: f.querySelector('b').textContent, legend: f.querySelector('.lg').innerText, hits: f.querySelectorAll('[data-hy]').length }; });
    if (!/New Jersey: historical results and the 2028 forecast/.test(chart.title) || !/Democratic margin\s+Republican margin\s+National margin\s+2028 forecast\s+80% prediction interval/.test(chart.legend) || /black/i.test(chart.legend) || chart.hits < 10) fail(tag, 'state chart: ' + JSON.stringify(chart));
    if (errs.length) fail(tag, errs.join('; '));
    console.log(tag, 'closest:', closest.join(', '), '| battlegrounds', nb, '| leaning', nd, '+', nr); await p.close(); }
  console.log(bad ? 'FAIL: ' + bad : 'OK: the list, the charts and the zero rule hold on every tab'); await b.close(); process.exit(bad ? 1 : 0); })();
