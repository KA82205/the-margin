"""The 2026 Senate elections, forecast by the working version as it stands, fitted on 2018-2024 only. Research only.

No part of the model was fitted on 2026: its weights, poll blend and error sizes all come from the four earlier years.

Inputs:
    data/senate/2026/races_2026.csv   the 32 races between a Democrat (or the Democrats' choice, Osborn in Nebraska) and a
                                      Republican, with the vote counts as reported after the election (state election
                                      offices, through Fox News's results pages, November 26, 2026; not all certified),
                                      and who held the seat and ran. Idaho, Montana and South Dakota are left out: no
                                      Democrat-side candidate was among the top two. All three went Republican.
    data/senate/2026/wiki_polls_2026.csv  the race polls from Wikipedia's race pages (senate/wiki_polls.py; CC BY-SA 4.0),
                                      used instead when SENATE_POLLS=wikipedia
    data/senate/2026_rcp/             the race polls and the weekly generic-ballot average, as RealClearPolling lists them.
                                      Kept out of the repository: they are RealClearPolling's compilation, not ours to
                                      republish. RealClearPolling's list is narrower than FiveThirtyEight's archive, which
                                      the model was fitted on, and its generic ballot is its own average, standing in for
                                      the model's.

    python senate/test_2026.py        writes data/senate/2026/test_2026.json
"""
import json, math, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import backtest as B, build_data as BD, fec_money as FM, national as NA, simulate as S

D26 = os.path.join(ROOT, 'data', 'senate', '2026'); RCP = os.path.join(ROOT, 'data', 'senate', '2026_rcp')
ELECTION = pd.Timestamp('2026-11-03')
HOLDOVER_DEM = 34                     # Democratic-caucus seats not up in 2026
LEFT_OUT_DEM = 0                      # Idaho, Montana, South Dakota: all Republican
TIE_GOES_TO = 'R'                     # Vice President Vance
SIMS = 40000


def races():
    R = pd.read_csv(os.path.join(D26, 'races_2026.csv'))
    R['year'] = 2026; R['dem2'] = 100 * R.dem_votes / (R.dem_votes + R.rep_votes)
    lean = BD.leans(); R['lean'] = [lean(2026, s) for s in R.state]
    return BD.track_records(R)


SOURCE = os.environ.get('SENATE_POLLS', 'wikipedia')   # 'wikipedia' (data/senate/2026/, CC BY-SA), or 'rcp' (kept out of the repository)


def poll_file():
    if SOURCE == 'wikipedia':                                  # partisan polls out, as in training (backtest.build)
        P = pd.read_csv(os.path.join(D26, 'wiki_polls_2026.csv')); return P[P.partisan.fillna('') == '']
    return pd.read_csv(os.path.join(RCP, 'senate_polls.psv'), sep='|')


def features(R):
    P = poll_file()
    P['dem2'] = 100 * P.dem_pct / (P.dem_pct + P.rep_pct); P['population'] = P.population.str.lower()
    if SOURCE == 'wikipedia':
        G = pd.read_csv(os.path.join(D26, 'wiki_generic_2026.csv'), parse_dates=['date']).rename(columns={'dem2_median': 'dem2'})
    else:
        G = pd.read_csv(os.path.join(RCP, 'generic_weekly.csv'), parse_dates=['date']); G['dem2'] = 100 * G.dem / (G.dem + G.rep)
    rows = []; MT = FM.table()
    for r in R.itertuples():
        pr = P[P.state == r.state]
        pt = B.table(pr, {'end': 'end', 'n': 'n', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'}) if len(pr) else None
        for d in B.DAYS:
            asof = ELECTION - pd.Timedelta(days=d)
            g = G[G.date <= asof]; gen = float(g.dem2.iloc[-1]) if len(g) else float(G.dem2.iloc[0])
            pa, pw = B.average(pt, asof, d) if pt is not None else (None, 0.0)
            mt = FM.money_feature(*FM.raised(MT, 2026, r.state, bool(r.special), asof)) if MT is not None else 0.0
            rows.append({'year': 2026, 'state': r.state, 'special': bool(r.special), 'days': d, 'dem2': r.dem2, 'lean': r.lean, 'generic': gen,
                         'inc_d': int(r.incumbent == 'D'), 'inc_r': int(r.incumbent == 'R'), 'poll': pa, 'poll_w': pw,
                         'track': (r.dem_track if r.dem_track == r.dem_track else 0.0) - (r.rep_track if r.rep_track == r.rep_track else 0.0),
                         'money_t': mt})
    return NA.add(pd.DataFrame(rows))


def polls_only(R):
    """The last RealClearPolling-listed polls as a plain benchmark: the simple average of each race's polls in its final 30
    days (or its last poll), as a Democratic two-party share."""
    P = poll_file(); P['end'] = pd.to_datetime(P.end); P['dem2'] = 100 * P.dem_pct / (P.dem_pct + P.rep_pct)
    out = {}
    for st, g in P.groupby('state'):
        last = g[g.end >= ELECTION - pd.Timedelta(days=30)]
        out[st] = float((last if len(last) else g.sort_values('end').tail(1)).dem2.mean())
    return out


def main():
    X = B.build(); R = races(); T = features(R); rng = np.random.default_rng(2026)
    oos = {(y, d): S.forecast(X[(X.year != y) & (X.days == d)], X[(X.year == y) & (X.days == d)])[1] for y in B.YEARS for d in B.DAYS}
    fits = {d: S.fold(X[X.days == d], T[T.days == d].copy(), {y: oos[(y, d)] for y in B.YEARS}, 'others') for d in B.DAYS}
    nearer = 0.0
    for d in sorted(B.DAYS):                                         # the shared error never shrinks with distance, as in simulate.py
        bf, sn = fits[d]; sn2 = max(sn, nearer); nearer = sn2
        if sn2 > sn:
            bf['sd_total'] = np.maximum(bf.sd_total.values, sn2 + 0.1); bf['sd_own'] = np.maximum(S.OWN_FLOOR, np.sqrt(np.maximum(bf.sd_total.values ** 2 - sn2 ** 2, 0)))
        fits[d] = (bf, sn2)
    S.SIMS = SIMS
    po = polls_only(R)
    rows, by_race = [], []
    nat = NA.National()
    for d in B.DAYS:
        bf, sn = fits[d]
        bf = S.combine(bf, HOLDOVER_DEM + LEFT_OUT_DEM, S.national_seats(nat, 2026, d))
        sim = S.simulate(bf, sn, rng, True); seats = (sim > 50).sum(axis=1); total = seats + HOLDOVER_DEM + LEFT_OUT_DEM
        control = np.where(total > 50, 1.0, np.where(total == 50, 1.0 if TIE_GOES_TO == 'D' else 0.0, 0.0))
        p = np.clip((sim > 50).mean(axis=0), 0.001, 0.999); won = (bf.dem2.values > 50).astype(float); err = 2 * (bf.m.values - bf.dem2.values)
        z = np.abs(bf.m.values - bf.dem2.values) / bf.sd_total.values
        lo, hi = np.percentile(seats, [10, 90]); actual = int(won.sum())
        close = np.abs(bf.dem2.values - 50) < 10
        rows.append({'days': d, 'shared_sd': round(sn, 3), 'margin_miss': round(float(np.sqrt(np.mean(err ** 2))), 2), 'bias_margin': round(float(np.mean(err)), 2),
                     'margin_miss_competitive': round(float(np.sqrt(np.mean(err[close] ** 2))), 2), 'bias_competitive': round(float(np.mean(err[close])), 2),
                     'called': int(((bf.m.values > 50) == (won == 1)).sum()), 'races': len(bf),
                     'log_loss': round(float(-np.mean(won * np.log(p) + (1 - won) * np.log(1 - p))), 3), 'brier': round(float(np.mean((p - won) ** 2)), 3),
                     'inside80': round(float(np.mean(z <= B.Z[80])), 3), 'inside50': round(float(np.mean(z <= B.Z[50])), 3),
                     'dem_seats_mean': round(float(seats.mean()), 2), 'low80': int(lo), 'high80': int(hi), 'actual': actual,
                     'p_actual_or_more': round(float(np.mean(seats >= actual)), 4), 'p_dem_control': round(float(control.mean()), 4)})
        for r, pp, e in zip(bf.itertuples(), p, err):
            by_race.append({'days': d, 'state': r.state, 'special': r.special, 'forecast_margin': round(2 * (r.m - 50), 2), 'result_margin': round(2 * (r.dem2 - 50), 2),
                            'p_dem': round(float(pp), 3)})
    Rs = pd.DataFrame(rows).sort_values('days', ascending=False); Br = pd.DataFrame(by_race)
    last = Br[Br.days == 1].copy(); last['polls_only_margin'] = [round(2 * (po[s] - 50), 2) if s in po else None for s in last.state]
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    print(Rs.to_string(index=False)); print(last.sort_values('result_margin').to_string(index=False))
    pm = last.dropna(subset=['polls_only_margin']); e = pm.polls_only_margin - pm.result_margin; f = pm.forecast_margin - pm.result_margin
    summary_po = {'races': len(pm), 'polls_only_miss': round(float(np.sqrt(np.mean(e ** 2))), 2), 'polls_only_bias': round(float(e.mean()), 2),
                  'model_miss_same_races': round(float(np.sqrt(np.mean(f ** 2))), 2), 'model_bias_same_races': round(float(f.mean()), 2),
                  'polls_only_called': int(((pm.polls_only_margin > 0) == (pm.result_margin > 0)).sum())}
    print(summary_po)
    with open(os.path.join(D26, 'test_2026.json' if SOURCE == 'wikipedia' else f'test_2026_{SOURCE}.json'), 'w') as fh:
        json.dump({'note': 'The 2026 Senate elections forecast by the working version fitted on 2018-2024 only. Margins are Democratic-side minus Republican, in points.',
                   'by_distance': Rs.to_dict('records'), 'by_race': Br.to_dict('records'), 'polls_only_last_day': summary_po}, fh, indent=1)
    return Rs, Br


if __name__ == '__main__':
    main()
