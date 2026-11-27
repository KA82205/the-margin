"""The fitted pieces the live Senate forecast (live.py) applies, made from every year 2018-2026 (step 15). Run again only
when the training data change (a new year added, a correction); the hourly job never refits.

The fit needs the raw sources kept out of the repository (data/senate/raw/: the MIT returns, Gallup, FRED), so it is
made here and its results committed:

    data/senate/2028/model.json    at each distance: the race equation's weights, the poll blend (w0, w1, k), the
                                   error of races with and without polls, and the shared error; the two national
                                   equations (the House vote from approval and the midterm; the Senate seat change from
                                   approval, the midterm and the seats up); and the link to the presidential simulation
    data/senate/past_races.csv     every Senate race 1978-2026 between the two sides, with how far the Democratic side
                                   ran ahead of the state's lean and the year (build_data.past_races), for candidates'
                                   records

    python senate/live_fit.py
"""
import json, math, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import backtest as B, build_data as BD, simulate as S, test_2026 as T, with_2026 as W

OUT = os.path.join(ROOT, 'data', 'senate', '2028'); os.makedirs(OUT, exist_ok=True)
# A state's Senate miss moves with its presidential miss in the same election: the within-year slope of one on the
# other, 2020 and 2024, The Margin's presidential forecast of each state against the Senate forecast of the same state
# (step 16). It runs 0.34 to 0.63 by distance, around 0.5, and is taken as 0.5 at every distance.
PRES_LINK = 0.5


def past_races():
    """build_data.past_races with the 2026 races added before the records are worked out."""
    R = T.races()
    extra = R.assign(year=2026)[['year', 'state', 'special', 'dem', 'rep', 'dem2', 'lean']]
    return BD.past_races(extra=extra)


def main():
    X4, X5 = W.data(); years = S.LIVE_YEARS; cols = B.VERSIONS[S.WORKING]
    shared = W.live_shared(X5, years)
    dist = {}
    for d in B.DAYS:
        a = X5[X5.year.isin(years) & (X5.days == d)]
        coef, _ = B.fit(a, cols)
        af = a.assign(f=B.predict(coef, a, cols)); p = B.volume_fit(af); af['m'] = B.blend(af, p)
        e = af.m.values - af.dem2.values; hp = af.poll.notna().values; sn = shared[d]
        tot = {'polls': float(np.sqrt(np.mean(e[hp] ** 2))), 'no_polls': float(np.sqrt(np.mean(e[~hp] ** 2)))}
        tot = {k: max(v, sn + 0.1) for k, v in tot.items()}
        own = {k: max(S.OWN_FLOOR, math.sqrt(max(v ** 2 - sn ** 2, 0.0))) for k, v in tot.items()}
        dist[str(d)] = {'coef': dict(zip(['const'] + cols, [round(float(c), 5) for c in coef])), 'blend': [round(float(v), 5) for v in p],
                        'sd_total': {k: round(v, 4) for k, v in tot.items()}, 'sd_own': {k: round(v, 4) for k, v in own.items()}, 'shared_sd': sn,
                        'races': int(len(a)), 'with_polls': int(hp.sum())}
    N = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'national_fundamentals.csv'))
    house = np.linalg.lstsq(np.column_stack([np.ones(len(N)), N.june_approval, N.midterm]), N.house_vote_pres.values, rcond=None)[0]
    seats = np.linalg.lstsq(np.column_stack([np.ones(len(N)), N.june_approval, N.midterm, N.senate_up]), N.senate_change.values, rcond=None)[0]
    P = past_races(); P[['year', 'state', 'special', 'dem', 'rep', 'dem2', 'lean', 'dem_over']].to_csv(os.path.join(ROOT, 'data', 'senate', 'past_races.csv'), index=False)
    # how often an incumbent eligible to run did run, 2018-2026: the incumbency counted for a senator whose plans are not known
    R5 = pd.concat([pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'races.csv'))[['year', 'incumbent']], T.races()[['year', 'incumbent']]])
    ran = float((R5.incumbent != 'open').mean())
    model = {'note': 'The live Senate forecast\'s fitted pieces (senate/live_fit.py): the working version (+national, polls by volume) fitted on '
                     + ', '.join(map(str, years)) + '. Shares are the Democratic side\'s two-party share, in points.',
             'years': list(years), 'version': S.WORKING, 'columns': cols, 'distances': dist,
             'national': {'house_vote': {'note': 'the president\'s party\'s two-party House vote from June approval (Gallup equivalent) and the midterm, 1948-2026',
                                         'coef': [round(float(v), 5) for v in house], 'years': [int(N.year.min()), int(N.year.max())]},
                          'senate_seats': {'note': 'the president\'s party\'s change in Senate seats from June approval, the midterm and its seats up, 1948-2026',
                                           'coef': [round(float(v), 5) for v in seats]},
                          'gallup_offset': -3.35, 'combine': S.COMBINE},
             'simulation': {'t_df': S.T_DF, 'shared_floor': S.SHARED_FLOOR, 'own_floor': S.OWN_FLOOR, 'pres_link': PRES_LINK},
             'incumbent_ran_share': round(ran, 4)}
    with open(os.path.join(OUT, 'model.json'), 'w') as f: json.dump(model, f, indent=1)
    print(json.dumps({d: (v['coef'], v['blend'], v['sd_total'], v['shared_sd']) for d, v in dist.items()}, indent=0)[:2500]); print('ran', ran, 'house', house, 'seats', seats)


if __name__ == '__main__':
    main()
