"""Would the states be placed better with trends or midterm results? Writes data/state_trend_study.json.

A state's lean is its share less the national share. The forecast's starting point for a state uses the lean of the last
two elections, the latest counting three times as much (0.75 and 0.25). This script asks, for every state and every election
on record, whether another rule made from what was known beforehand would have landed closer:

    other weightings of past leans      the last election alone; the last two evenly; the last three
    a trend carried forward             the last lean plus a share of its change from the election before (a quarter, a half)
    a trend with its share fitted       the share that would have done best on all earlier elections, applied to the next
    the midterm in between              the state's lean in the House vote two years earlier: its level, or how far it moved
                                        between the last two midterms; with a set share and with a fitted one

Every rule is written down here before it is scored, and a fitted share for election y is fitted on elections before y only.
The House lean of a state counts only districts where both parties stood (so an uncontested seat does not pass for a
landslide), needs half of the state's districts to be so, and is taken against the national House vote counted the same way
(so the difference between a midterm and a presidential electorate nationwide drops out). Senate and governor's races are
left out: one race a state, decided as much by who is running as by the state.

Scores are the mean miss of the lean in points of margin, by election. An election counts once however many states it has;
a rule "beats" the one in use in an election when its mean miss there is smaller.

    python state_trend_study.py
"""
import json
import numpy as np, pandas as pd

RES = pd.read_csv('data/results.csv'); RES = RES[RES.state.str.len() == 2]
LEAN = RES.assign(lean=RES.dem2 - RES.nat2).pivot(index='state', columns='year', values='lean')          # points of share
SHARE = RES.pivot(index='state', columns='year', values='dem2')
HOUSE = pd.read_csv('data/house_by_state.csv')
YEARS = [y for y in LEAN.columns if y >= 1984]


def house_lean():
    """{year: state lean in the House vote}, in points of share, from districts both parties contested."""
    out = {}
    for y, g in HOUSE.groupby('year'):
        nat = 100 * g.dem.sum() / (g.dem.sum() + g.rep.sum()); ok = g[g.contested >= 0.5 * g.districts]
        out[int(y)] = (100 * ok.dem / (ok.dem + ok.rep) - nat).set_axis(ok.state.values)
    return out


HL = house_lean()
L = lambda y, back: LEAN[y - 4 * back]


def fitted(y, x_of, base_of, first):
    """The share of x that would have done best on the elections before y: least squares of (actual - base) on x, no intercept."""
    num = den = 0.0
    for z in [v for v in LEAN.columns if first <= v < y]:
        x, d = x_of(z), LEAN[z] - base_of(z); ok = x.notna() & d.notna(); num += float((x[ok] * d[ok]).sum()); den += float((x[ok] ** 2).sum())
    return num / den if den > 0 else 0.0


used = lambda y: 0.75 * L(y, 1) + 0.25 * L(y, 2)
trend = lambda y: L(y, 1) - L(y, 2)
mid_level = lambda y: HL[y - 2].reindex(LEAN.index) - used(y) if y - 2 in HL else pd.Series(np.nan, LEAN.index)
mid_move = lambda y: (HL[y - 2] - HL[y - 6]).reindex(LEAN.index) if y - 2 in HL and y - 6 in HL else pd.Series(np.nan, LEAN.index)
fill = lambda s, y: s.where(s.notna(), used(y))          # a state with no reading keeps the rule in use

RULES = {
    'as used: 0.75 and 0.25': used,
    'the last election alone': lambda y: L(y, 1),
    'the last two evenly': lambda y: 0.5 * L(y, 1) + 0.5 * L(y, 2),
    'the last three: 0.6, 0.3, 0.1': lambda y: 0.6 * L(y, 1) + 0.3 * L(y, 2) + 0.1 * L(y, 3),
    'trend, a quarter carried forward': lambda y: L(y, 1) + 0.25 * trend(y),
    'trend, a half carried forward': lambda y: L(y, 1) + 0.5 * trend(y),
    'trend, share fitted on earlier elections': lambda y: L(y, 1) + fitted(y, trend, lambda z: L(z, 1), 1984) * trend(y),
    'midterm House lean, a fifth of the way to it': lambda y: fill(used(y) + 0.2 * mid_level(y), y),
    'midterm House lean, share fitted': lambda y: fill(used(y) + fitted(y, mid_level, used, 2000) * mid_level(y), y),
    'move between the last two midterms, a quarter of it': lambda y: fill(used(y) + 0.25 * mid_move(y), y),
    'move between midterms, share fitted': lambda y: fill(used(y) + fitted(y, mid_move, used, 2004) * mid_move(y), y),
}
SINCE = {k: (2000 if 'midterm House' in k else 2004 if 'midterms' in k or 'between' in k else 1984) for k in RULES}
SINCE['midterm House lean, share fitted'] = 2004; SINCE['move between midterms, share fitted'] = 2008


def score(rule, years, sub=None):
    out = {}
    for y in years:
        e = 2 * (rule(y) - LEAN[y]); m = e.notna()
        if sub == 'close': m &= (SHARE[y] - 50).abs() < 5
        out[int(y)] = float(e[m].abs().mean())
    return out


def main():
    out = {'rules': {}, 'years': [int(y) for y in YEARS]}
    for name, rule in RULES.items():
        years = [y for y in YEARS if y >= SINCE[name]]
        s, c, b = score(rule, years), score(rule, years, 'close'), score(used, years); bc = score(used, years, 'close')
        diff = np.array([s[y] - b[y] for y in s])
        out['rules'][name] = {'since': SINCE[name], 'elections': len(years), 'miss': round(float(np.mean(list(s.values()))), 2), 'as_used_same_years': round(float(np.mean(list(b.values()))), 2),
                              'close': round(float(np.mean(list(c.values()))), 2), 'as_used_close': round(float(np.mean(list(bc.values()))), 2),
                              'better_in': int((diff < -1e-9).sum()), 'difference': round(float(diff.mean()), 2), 'se': round(float(diff.std(ddof=1) / np.sqrt(len(diff))), 2) if len(diff) > 1 else None,
                              'by_year': {y: round(v, 2) for y, v in s.items()}}
    out['fitted_shares'] = {'trend': {int(y): round(fitted(y, trend, lambda z: L(z, 1), 1984), 2) for y in YEARS if y >= 1992}, 'midterm level': {int(y): round(fitted(y, mid_level, used, 2000), 2) for y in YEARS if y >= 2004},
                            'midterm move': {int(y): round(fitted(y, mid_move, used, 2004), 2) for y in YEARS if y >= 2008}}
    # do trends persist? the change in a state's lean against its change the election before, all states and elections
    xs, ys = [], []
    for y in YEARS:
        a, b = L(y, 1) - L(y, 2), LEAN[y] - L(y, 1); ok = a.notna() & b.notna(); xs += list(a[ok]); ys += list(b[ok])
    out['persistence'] = {'correlation': round(float(np.corrcoef(xs, ys)[0, 1]), 2), 'n': len(xs),
                          'since_2008': round(float(np.corrcoef(*zip(*[(L(y, 1)[s] - L(y, 2)[s], LEAN[y][s] - L(y, 1)[s]) for y in YEARS if y >= 2008 for s in LEAN.index]))[0, 1]), 2)}
    # with the state models in: the starting point as the forecast builds it (half lean, half the models' placing), 2008 to 2024
    sm = pd.read_csv('data/state_models.csv'); sm = sm[sm.state.str.len() == 2]; us = pd.read_csv('data/state_models.csv'); us = us[us.state == 'US'].set_index('year').average
    place = sm.assign(p=sm.average - sm.year.map(us)).pivot(index='state', columns='year', values='p')
    out['with_state_models'] = {}
    for name in ('as used: 0.75 and 0.25', 'the last election alone', 'trend, a quarter carried forward', 'trend, share fitted on earlier elections', 'midterm House lean, a fifth of the way to it', 'move between the last two midterms, a quarter of it'):
        v = [float((2 * (0.5 * RULES[name](y) + 0.5 * place[y].reindex(LEAN.index) - LEAN[y])).abs().mean()) for y in (2008, 2012, 2016, 2020, 2024)]
        out['with_state_models'][name] = {'miss': round(float(np.mean(v)), 2), 'by_year': dict(zip((2008, 2012, 2016, 2020, 2024), [round(x, 2) for x in v]))}
    # Texas and Florida: the parts as they stand, and what each rule would say for 2028. A reading of the rules, not a reason to pick one.
    LEAN[2028] = np.nan; tf = {}
    for st in ('TX', 'FL'):
        tf[st] = {'margin': {int(y): round(float(2 * (SHARE[y][st] - 50)), 1) for y in (2012, 2016, 2020, 2024)}, 'lean': {int(y): round(float(2 * LEAN[y][st]), 1) for y in (2012, 2016, 2020, 2024)},
                  'house_lean': {int(y): round(float(2 * HL[y][st]), 1) for y in (2018, 2020, 2022, 2024) if st in HL[y].index}, 'rules_2028': {}}
        for name, rule in RULES.items():
            if 'fitted' in name and 'trend' not in name: continue
            try: tf[st]['rules_2028'][name] = round(float(2 * rule(2028)[st]), 1)
            except Exception: pass                      # noqa: BLE001  the 2026 House vote is not in the file yet
    out['texas_florida'] = tf
    json.dump(out, open('data/state_trend_study.json', 'w'), indent=1)
    for k, v in out['rules'].items(): print(f"{k:52s} since {v['since']} ({v['elections']:2d}): {v['miss']:.2f} vs {v['as_used_same_years']:.2f} as used | close {v['close']:.2f} vs {v['as_used_close']:.2f} | better in {v['better_in']}/{v['elections']} | diff {v['difference']:+.2f} ({v['se']})")
    print(out['fitted_shares']); print(out['persistence']); print(out['with_state_models']); print(json.dumps(tf))


if __name__ == '__main__':
    main()
