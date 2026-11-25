// Hover over states of both parties, safe and close, the District, the districts and nothing at all, at five window
// sizes, and check that the map, the electoral-vote bar and the headline do not move. Needs Playwright.
//     node tests/browser_hover.js [url]
const { chromium } = require('playwright');
const url = process.argv[2] || 'file://' + require('path').join(__dirname, '..', 'docs', 'index.html');
(async () => {
  const b = await chromium.launch(); let bad = 0;
  for (const [w, h] of [[1440, 900], [1280, 800], [1024, 768], [820, 1100], [390, 844]]) {
    const p = await b.newPage({ viewport: { width: w, height: h } }); await p.goto(url); await p.waitForTimeout(600);
    const rect = async sel => p.evaluate(s => { const r = document.querySelector(s).getBoundingClientRect(); return [r.x, r.y + scrollY, r.width, r.height].map(v => Math.round(v * 10) / 10); }, sel);
    const base = { map: await rect('#map-svg'), snake: await rect('#snake'), head: await rect('#headline') }; const seen = {};
    for (const st of ['CA', 'WY', 'MA', 'OK', 'NC', 'AZ', 'DC', 'ME2', 'NE2', 'PA', 'TX', null, 'DC', 'WY']) {
      if (st === null) { await p.mouse.move(2, 2); await p.waitForTimeout(80); }
      else {
        const el = await p.$('#map-svg [data-s="' + st + '"]') || await p.$('#chips [data-s="' + st + '"]') || await p.$('#snake [data-s="' + st + '"]');
        await el.scrollIntoViewIfNeeded(); const bb = await el.boundingBox();
        if (st === 'DC' || st.length > 2) { const c = await p.$('#chips [data-s="' + st + '"]'); const cb = await c.boundingBox(); await p.mouse.move(cb.x + cb.width / 2, cb.y + cb.height / 2); }
        else await el.hover({ force: true });
        await p.waitForTimeout(80);
      }
      const now = { map: await rect('#map-svg'), snake: await rect('#snake'), head: await rect('#headline') };
      const ro = await p.evaluate(() => { const r = document.getElementById('ro'); return { h: Math.round(r.getBoundingClientRect().height), t: r.innerText.replace(/\s+/g, ' ') }; });
      const moved = ['map', 'snake', 'head'].filter(k => now[k].some((v, i) => Math.abs(v - base[k][i]) > 0.5));
      if (moved.length) bad++;
      seen[st || 'none'] = ro.h + (moved.length ? ' MOVED ' + moved.join(',') : '') + ' | ' + ro.t.slice(0, 90);
    }
    console.log(w + 'x' + h, JSON.stringify(seen, null, 0).replace(/","/g, '"\n   "'));
    await p.close();
  }
  console.log(bad ? 'FAIL: ' + bad + ' moves' : 'OK: nothing moved');
  await b.close(); process.exit(bad ? 1 : 0);
})();
