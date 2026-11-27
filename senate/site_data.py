"""The Senate back-test as the site's Back-tests tab shows it, and the list of what was tried. Research data, made here
because it needs the raw sources kept out of the repository; run again when the model or the training years change.

Every Senate election of 2018-2026 is forecast by the working version fitted on the other four years (the live
forecast is fitted on all five), at each distance from a year out to the last day, race by race and as a whole chamber
(with_2026.py's simulation: the races drawn together, the seat total pulled toward the national seat model), and each
race scored as it came out of that simulation, as the live forecast reports it.

    python senate/site_data.py        writes data/senate/site_backtests.json
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import simulate as S, with_2026 as W

DAYS_SHOWN = (365, 120, 60, 14, 1)

# what was tried, in the order it was tried; each with the README step that records it
TESTED = [
    {'step': 2, 'idea': 'Race polls added to the state\'s lean and the national mood', 'adopted': True,
     'result': 'The typical miss on the margin of competitive races fell from 7.4 to 5.3 points on the last day.'},
    {'step': 3, 'idea': 'The polls\' weight growing with the amount of polling, up to a cap', 'adopted': True,
     'result': 'Competitive races, last day: 4.9 points against 5.3 with one weight for every race.'},
    {'step': 4, 'idea': 'Starting each race from the presidential forecast of its state', 'adopted': False,
     'result': 'Three forms tried on 2020 and 2024; none beat the current version overall, and the best did better only two months out.'},
    {'step': 5, 'idea': 'Each candidate\'s record in earlier Senate races', 'adopted': True,
     'result': 'How far a candidate ran ahead of their state and year before: the chances got sharper at every distance; the typical miss barely moved.'},
    {'step': 6, 'idea': 'The races simulated together, with an error they share', 'adopted': True,
     'result': 'Measured on misses made out of sample; it keeps the seat ranges honest when polls miss everywhere at once.'},
    {'step': 8, 'idea': 'The national mood from the president\'s approval as well as the generic ballot', 'adopted': True,
     'result': 'Half and half: the five-year miss fell at every distance.'},
    {'step': 9, 'idea': 'Income growth, inflation, GDP and years in power in the national model', 'adopted': False,
     'result': 'None beat approval and the midterm out of sample, 1978-2026.'},
    {'step': 10, 'idea': 'Pulling the seat total toward a national model of seat change', 'adopted': True,
     'result': 'A quarter of the way: the seat totals and the race chances improved over the five years.'},
    {'step': 13, 'idea': 'Money raised by each date (FEC reports)', 'adopted': False,
     'result': 'Tested twice, the second time with 2026 in the fit: the chances got worse at every distance.'},
    {'step': 14, 'idea': 'A smaller edge for senators appointed to the seat', 'adopted': False,
     'result': 'Appointees do run worse, but nine races are too few: no better overall.'},
    {'step': 15, 'idea': '2026 as a fitting year', 'adopted': True,
     'result': 'The national mood now counts fully in every race, and the error races share is wider.'},
    {'step': 16, 'idea': 'The Senate simulated inside the presidential forecast\'s elections', 'adopted': True,
     'result': 'A state\'s Senate race moves about half a point with each point of its presidential vote, as in 2020 and 2024.'},
    {'step': 17, 'idea': 'Wider errors two years out', 'adopted': False,
     'result': 'Four checks of the record found no case for them; senators\' retirements are now drawn in each simulated election.'},
]


def scored(X5):
    """with_2026.seats(), keeping each race's forecast as simulated (after the pull toward the national seat model): its
    chance is the share of simulated elections it wins, its forecast margin the simulations' average."""
    kept, orig = [], S.simulate
    def keep(bf, sn, rng, joint=True):
        X = orig(bf, sn, rng, joint); kept.append((bf.copy(), X)); return X
    S.simulate = keep
    try: sm = W.seats(X5, W.FIVE)
    finally: S.simulate = orig
    rows = []
    for (bf, X), (_, r) in zip(kept, sm.iterrows()):                # seats() simulates in the order of its rows
        assert len(bf) and int(bf.year.iloc[0]) == r.year and int(bf.days.iloc[0]) == r.days
        for j, b in enumerate(bf.itertuples()):
            p = min(max(float((X[:, j] > 50).mean()), 0.0005), 0.9995)
            rows.append({'year': int(r.year), 'days': int(r.days), 'state': b.state, 'special': b.special, 'err': 2 * (float(X[:, j].mean()) - b.dem2),
                         'p': p, 'won': int(b.dem2 > 50)})
    F = pd.DataFrame(rows); F['ll'] = -(F.won * np.log(F.p) + (1 - F.won) * np.log(1 - F.p))
    return F, sm


def main():
    X4, X5 = W.data(); S.WORKING = '+national'
    F, sm = scored(X5)
    F['miss'] = F.err.abs(); F['called'] = (F.p > 0.5) == (F.won == 1)
    after = {**S.CAUCUS_AFTER, 2026: 56}
    sm['caucus_actual'] = sm.year.map(after); off = sm.caucus_actual - sm.actual
    sm['caucus_mean'] = (sm.dem_seats_mean + off).round(1); sm['caucus_low'] = sm.low80 + off; sm['caucus_high'] = sm.high80 + off
    by_year = []
    for (y, d), g in F[F.days.isin(DAYS_SHOWN)].groupby(['year', 'days']):
        s = sm[(sm.year == y) & (sm.days == d)].iloc[0]
        by_year.append({'year': int(y), 'days': int(d), 'races': int(len(g)), 'called': int(g.called.sum()), 'avg_miss': round(float(g.miss.mean()), 1),
                        'bias': round(float(g.err.mean()), 1), 'log_loss': round(float(g.ll.mean()), 3),
                        'missed': sorted(g[~g.called].state.tolist()),
                        'caucus_mean': float(s.caucus_mean), 'caucus_low': int(s.caucus_low), 'caucus_high': int(s.caucus_high), 'caucus_actual': int(s.caucus_actual),
                        'inside80': bool(s.inside80), 'p_dem_control': round(float(s.p_dem_control), 3), 'dem_won_control': int(s.dem_won_control)})
    by_days = []
    for d, g in F.groupby('days'):
        s = sm[sm.days == d]
        by_days.append({'days': int(d), 'races': int(len(g)), 'called': int(g.called.sum()), 'avg_miss': round(float(g.miss.mean()), 1),
                        'close_miss': round(float(g[g.p.between(0.2, 0.8)].miss.mean()), 1), 'log_loss': round(float(g.ll.mean()), 3),
                        'seats_inside80': int(s.inside80.sum()), 'years': int(len(s)), 'control_called': int(((s.p_dem_control > 0.5) == (s.dem_won_control == 1)).sum())})
    fav = np.maximum(F.p, 1 - F.p); won = np.where(F.p >= 0.5, F.won, 1 - F.won)
    cal = []
    for lo, hi in ((0.5, 0.65), (0.65, 0.8), (0.8, 0.9), (0.9, 0.97), (0.97, 1.0001)):
        k = (fav >= lo) & (fav < hi)
        if k.sum(): cal.append({'low': lo, 'high': min(hi, 1.0), 'races': int(k.sum()), 'forecast': round(float(fav[k].mean()), 3), 'won': round(float(won[k].mean()), 3)})
    out = {'note': 'Each Senate election of 2018-2026 forecast by the working version fitted on the other four years. Misses are in points of margin; '
                   'the caucus counts the independents who sit with the Democrats. Calibration pools every race at every distance.',
           'years': list(W.FIVE), 'days': sorted(int(d) for d in F.days.unique()), 'by_year': by_year, 'by_days': sorted(by_days, key=lambda r: -r['days']),
           'calibration': cal, 'calibration_races': int(len(F)), 'tested': TESTED}
    with open(os.path.join(ROOT, 'data', 'senate', 'site_backtests.json'), 'w') as f: json.dump(out, f, indent=1)
    print(pd.DataFrame(by_days).to_string(index=False)); print(pd.DataFrame([r for r in by_year if r['days'] == 1]).drop(columns=['missed']).to_string(index=False)); print(cal)


if __name__ == '__main__':
    main()
