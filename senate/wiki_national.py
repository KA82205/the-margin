"""The national inputs from Wikipedia: the median of the poll aggregators its pages list, for presidential approval and
for the generic congressional ballot. Research for now; Wikipedia's text is CC BY-SA 4.0.

Wikipedia shows only the aggregators' current figures, so a history is rebuilt from the pages as they stood on each
date (tools/fetch_wiki_polls.py, group history2026 and generic2026); in a live pipeline the figure is read each day.
The median is used, not the mean, because the aggregators listed change from month to month.

Approval is turned into a Gallup equivalent for the national fundamentals (national.py) by the offset between the two
while Gallup still polled: in 2025 Gallup ran 3.35 points below the aggregators' median (spread 2.0 points, 22
half-monthly readings). That offset is for Trump's second term; a new president would need it measured again.

    python senate/wiki_national.py <history json> <generic json>   writes data/senate/2026/wiki_approval_2026.csv and
                                                                   data/senate/2026/wiki_generic_2026.csv
"""
import json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import wiki_polls as WP

GALLUP_OFFSET = -3.35
SECTIONS_APPROVAL = r'===\s*Aggregate polls\s*==='           # the approval page's table of aggregators


def table_rows(section):
    m = re.search(r'\{\|.*?\n\|\}', section or '', flags=re.S)
    return WP.rows_of(m.group(0)) if m else []


def approval(H):
    out = []
    for k, v in H.items():
        title, d = k.split('|')
        if not title.startswith('Opinion polling on'): continue
        vals = [WP.number(r[2][2]) for r in table_rows(v.get('section'))[1:] if len(r) > 2 and 'Average' not in WP.clean(r[0][2])]
        vals = [x for x in vals if x]
        if vals: out.append({'date': d, 'aggregators': len(vals), 'approve_median': round(float(np.median(vals)), 2)})
    return pd.DataFrame(out).sort_values('date')


def generic(H):
    out = []
    for k, v in H.items():
        title, d = k.split('|')
        if 'House' not in title: continue
        R = table_rows(v.get('section'))
        if not R: continue
        heads = [WP.clean(c[2]) for c in R[0]]
        try:
            di = next(i for i, h in enumerate(heads) if 'Democrat' in h); ri = next(i for i, h in enumerate(heads) if 'Republican' in h)
        except StopIteration:
            continue
        vals = []
        for r in R[1:]:
            if len(r) <= max(di, ri) or 'Average' in WP.clean(r[0][2]): continue
            a, b = WP.number(r[di][2]), WP.number(r[ri][2])
            if a and b: vals.append(100 * a / (a + b))
        if vals: out.append({'date': d, 'aggregators': len(vals), 'dem2_median': round(float(np.median(vals)), 3)})
    return pd.DataFrame(out).sort_values('date')


if __name__ == '__main__':
    hist, gen = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    D = os.path.join(ROOT, 'data', 'senate', '2026')
    approval(hist).to_csv(os.path.join(D, 'wiki_approval_2026.csv'), index=False)
    generic(gen).to_csv(os.path.join(D, 'wiki_generic_2026.csv'), index=False)
    print(approval(hist).tail(3)); print(generic(gen).tail(3))
