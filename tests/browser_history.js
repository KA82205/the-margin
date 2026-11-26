// The Forecast history chart, read back from the drawn page: the curves go through every recorded daily value, never past
// the two values they join, show no dot for each day, and the tooltip gives the archived values. Every range, three widths,
// light and dark.     node tests/browser_history.js [path/to/index.html]
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
const file = path.resolve(process.argv[2] || path.join(__dirname, '..', 'docs', 'index.html'));
const fail = m => { console.error('FAIL: ' + m); process.exit(1); };
(async () => {
  const b = await chromium.launch(); let checked = 0;
  for (const [w, h, scheme] of [[1280, 900, 'light'], [820, 1100, 'dark'], [390, 844, 'dark'], [390, 844, 'light']]) {
    const ctx = await b.newContext({viewport: {width: w, height: h}, colorScheme: scheme, hasTouch: w < 500}); const p = await ctx.newPage(); const errs = [];
    p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    await p.goto('file://' + file + '#forecast'); await p.waitForTimeout(1200);
    for (const span of ['0', '90', '30', '7']) {
      await p.click(`#hseg [data-span="${span}"]`); await p.waitForTimeout(120);
      const r = await p.evaluate(() => {
        const svg = document.querySelector('#daily svg'); if (!svg) return {none: true, text: document.querySelector('#daily').textContent};
        const pressed = [...document.querySelectorAll('#hseg button')].filter(x => x.getAttribute('aria-pressed') === 'true').map(x => x.dataset.span);
        const lines = [...svg.querySelectorAll('.fh-line')].map(l => l.getAttribute('d'));
        const dots = svg.querySelectorAll('circle:not(.fh-mk)').length;          // two end dots and two hidden hover dots
        return {pressed, lines, dots, h: svg.viewBox.baseVal.height};
      });
      if (r.none) { if (!/first forecast/.test(r.text)) fail('no chart and no message'); continue; }
      if (r.pressed.join() !== span) fail('range button state ' + r.pressed);
      if (r.dots !== 4) fail('dots drawn for the days: ' + r.dots);
      for (const d of r.lines) {
        const segs = d.split('C'), start = segs[0].slice(1).split(' ').map(Number); let prev = start;
        if (/[VH]/.test(d)) fail('a step in the curve');
        for (const sg of segs.slice(1)) { const v = sg.trim().split(/\s+/).map(Number), c1y = v[1], c2y = v[3], end = [v[4], v[5]];
          const lo = Math.min(prev[1], end[1]) - 0.11, hi = Math.max(prev[1], end[1]) + 0.11;
          if (c1y < lo || c1y > hi || c2y < lo || c2y > hi) fail(`overshoot between ${prev} and ${end}: ${c1y} ${c2y}`);
          if (!(end[0] > prev[0])) fail('the curve goes backwards in time'); prev = end; checked++; }
      }
    }
    // the tooltip shows the values the history file holds, for the point nearest the pointer
    await p.click('#hseg [data-span="0"]'); await p.waitForTimeout(120);
    const end = await (await p.$('#daily svg > circle:not(.fh-mk)')).boundingBox(), box = await (await p.$('#dhit')).boundingBox(), x = Math.min(end.x + end.width / 2, box.x + box.width - 0.5), y = box.y + box.height / 2;
    if (w < 500) await p.touchscreen.tap(x, y); else await p.mouse.move(x, y);
    await p.waitForTimeout(200);
    const tip = await p.evaluate(() => { const t = document.querySelector('#tip'); return t && !t.hidden ? t.innerText : ''; });
    const last = await p.evaluate(() => { try { return DATA.history[DATA.history.length - 1]; } catch (e) { return null; } });
    if (last) { const rr = last.rep != null ? last.rep : 1 - last.p, want = 'Democrats ' + (100 * last.p / (last.p + rr)).toFixed(1) + '%'; if (!tip.includes(want)) fail(w + ' ' + scheme + ': tooltip "' + tip.replace(/\n/g, ' | ') + '" lacks ' + want + ' at ' + Math.round(x) + ' (chart ' + Math.round(box.x) + ' to ' + Math.round(box.x + box.width) + ')'); }
    else if (!/Democrats \d+\.\d%/.test(tip)) fail('tooltip ' + tip);
    if (errs.length) fail(errs.join('; '));
    const over = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth); if (over > 0) fail('sideways scroll at ' + w);
    await ctx.close();
  }
  await b.close(); console.log('ok (history chart: ' + checked + ' curve segments through the recorded values with no overshoot, no daily dots, the headline figures in the curves and the archived ones in the tooltip, every range, 3 widths, light and dark)');
})();
