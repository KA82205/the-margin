"""Builds the Senate poll tables from Wikipedia's race pages (fetched by tools/fetch_wiki_polls.py into samples/).
Wikipedia's text is CC BY-SA 4.0; these tables are derived from it and carry the same licence.

    python senate/wiki_build.py <samples dir>
        data/senate/polls_wikipedia.csv          2018-2024, the races in races.csv (the model's training polls)
        data/senate/2026/wiki_polls_2026.csv     2026, the races in races_2026.csv

A race's page is found by year, state and whether it was a special election; its separate "Opinion polling for ..."
page, if it has one, is read too. Each table naming both nominees is read by wiki_polls.parse.
"""
import json, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import wiki_polls as WP

D = os.path.join(ROOT, 'data', 'senate')
# nominees whose name on Wikipedia differs from the results file's in a way the matching cannot bridge
NAME_ON_WIKIPEDIA = {(2026, 'SC', 'rep'): 'DARLINE GRAHAM'}


def state_names():
    a = pd.read_json(os.path.join(ROOT, 'data', 'results_2024.json')).T['name']
    return {k: v for k, v in a.items() if len(k) == 2}


def race_text(W, year, name, special):
    kinds = ('special election',) if special else ('election', 'elections')
    hits = [k for k in W if k.startswith(str(year)) and any(k.endswith(f'Senate {kind} in {name}') for kind in kinds)]
    text = '\n'.join(W[k]['text'] for k in hits)
    text += '\n'.join(p['text'] for t, p in W.items() if t.startswith('Opinion polling for') and name in t and str(year) in t)
    return text


def build(samples):
    names = state_names(); out = []
    R = pd.read_csv(os.path.join(D, 'races.csv'))
    for y in (2018, 2020, 2022, 2024):
        W = json.load(open(os.path.join(samples, f'wiki_senate{y}.json')))
        for r in R[R.year == y].itertuples():
            ps = WP.parse(race_text(W, y, names[r.state], r.special), r.dem, r.rep, r.state, y)
            out += [dict(p, year=y, special=bool(r.special)) for p in ps]
    T = pd.DataFrame(out); T['internal'] = False; T['partisan'] = T.partisan.fillna('')
    T['dem2'] = (100 * T.dem_pct / (T.dem_pct + T.rep_pct)).round(3)
    T[['year', 'state', 'special', 'end', 'n', 'population', 'pollster', 'partisan', 'internal', 'dem_pct', 'rep_pct', 'dem2']].to_csv(os.path.join(D, 'polls_wikipedia.csv'), index=False)
    R26 = pd.read_csv(os.path.join(D, '2026', 'races_2026.csv')); W = json.load(open(os.path.join(samples, 'wiki_senate2026.json'))); out = []
    for r in R26.itertuples():
        dem = NAME_ON_WIKIPEDIA.get((2026, r.state, 'dem'), r.dem); rep = NAME_ON_WIKIPEDIA.get((2026, r.state, 'rep'), r.rep)
        out += WP.parse(race_text(W, 2026, names[r.state], r.special), dem, rep, r.state, 2026)
    pd.DataFrame(out).to_csv(os.path.join(D, '2026', 'wiki_polls_2026.csv'), index=False)
    print(T.groupby('year').size().to_dict(), len(out))


if __name__ == '__main__':
    build(sys.argv[1])
