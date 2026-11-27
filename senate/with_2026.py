"""Senate research, step 15: 2026 added as a fitting year. Research only.

Two questions:
    1. Does fitting on 2026 as well make the other years' forecasts better? Each of 2018-2024 is forecast leaving it
       out, once from the other three years (as before) and once from the other three and 2026. 2026 itself, left out,
       is forecast from 2018-2024, as test_2026.py does.
    2. How large is the error a year's races share once 2026 is among the years it is measured on, and do the simulated
       seat counts cover the results?

2026's races are those of test_2026.py (races_2026.csv, Wikipedia's polls and generic-ballot medians), with the
Democratic caucus after the election (56) and the tie-breaker (Vice President Vance) as known.

    python senate/with_2026.py        writes data/senate/with_2026.json
"""
import json, math, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import backtest as B, simulate as S, test_2026 as T

FOUR = tuple(B.YEARS); FIVE = FOUR + (2026,)


def data():
    X4 = B.build(); X26 = T.features(T.races())
    X5 = pd.concat([X4, X26], ignore_index=True, sort=False)
    return X4, X5


def race_scores(X, years, train_years):
    """Leave-one-year-out forecasts of the working version for each year in years, fitted on train_years less that year;
    each race's spread from the misses inside the fit, as in backtest.py."""
    out = []
    for y in years:
        for d in B.DAYS:
            a = X[(X.year != y) & X.year.isin(train_years) & (X.days == d)]; b = X[(X.year == y) & (X.days == d)]
            af, bf = S.forecast(a, b)
            e = af.m.values - af.dem2.values; hp = af.poll.notna().values
            sd = {True: float(np.sqrt(np.mean(e[hp] ** 2))), False: float(np.sqrt(np.mean(e[~hp] ** 2)))}
            for r in bf.itertuples():
                s = sd[bool(r.poll == r.poll and r.poll is not None)]
                p = min(max(0.5 * (1 + math.erf((r.m - 50) / (s * math.sqrt(2)))), 0.001), 0.999)
                out.append({'year': y, 'days': d, 'state': r.state, 'special': r.special, 'err': 2 * (r.m - r.dem2), 'p': p, 'won': int(r.dem2 > 50)})
    F = pd.DataFrame(out)
    F['ll'] = -(F.won * np.log(F.p) + (1 - F.won) * np.log(1 - F.p))
    return F


def summary(F, by):
    return F.groupby(by).apply(lambda x: pd.Series({'margin_miss': round(float(np.sqrt(np.mean(x.err ** 2))), 3), 'bias': round(float(x.err.mean()), 3),
                                                     'log_loss': round(float(x.ll.mean()), 4), 'called': int(((x.p > .5) == (x.won == 1)).sum()), 'races': len(x)}),
                               include_groups=False).reset_index()


def seats(X, years):
    """The simulation of simulate.py ('together', shared error never smaller further out, the national pull), for each
    year left out, its shared error measured on the other years' out-of-sample misses."""
    import national as NA
    nat = NA.National(); rng = np.random.default_rng(2028)
    ex_dem = {2018: 1, 2020: 0, 2022: 0, 2024: 0, 2026: T.LEFT_OUT_DEM}
    after = {**S.CAUCUS_AFTER, 2026: T.HOLDOVER_DEM + T.LEFT_OUT_DEM + int((X[(X.year == 2026) & (X.days == 1)].dem2 > 50).sum())}
    tie = {**S.TIE_GOES_TO, 2026: T.TIE_GOES_TO}
    oos = {(y, d): S.forecast(X[(X.year != y) & X.year.isin(years) & (X.days == d)], X[(X.year == y) & (X.days == d)])[1] for y in years for d in B.DAYS}
    rows = []
    for y in years:
        tr, te = X[(X.year != y) & X.year.isin(years)], X[X.year == y]
        fits = {d: S.fold(tr[tr.days == d], te[te.days == d].copy(), {yy: oos[(yy, d)] for yy in years if yy != y}, 'others') for d in B.DAYS}
        nearer = 0.0
        for d in sorted(B.DAYS):
            bf, sn = fits[d]; sn2 = max(sn, nearer); nearer = sn2
            if sn2 > sn:
                bf['sd_total'] = np.maximum(bf.sd_total.values, sn2 + 0.1); bf['sd_own'] = np.maximum(S.OWN_FLOOR, np.sqrt(np.maximum(bf.sd_total.values ** 2 - sn2 ** 2, 0)))
            fits[d] = (bf, sn2)
        for d in B.DAYS:
            bf, sn = fits[d]; actual = int((bf.dem2 > 50).sum()); holdover = after[y] - actual - ex_dem[y]
            bf = S.combine(bf, holdover + ex_dem[y], S.national_seats(nat, y, d))
            sim = S.simulate(bf, sn, rng, True); n = (sim > 50).sum(axis=1); total = n + holdover + ex_dem[y]
            control = np.where(total > 50, 1.0, np.where(total == 50, 1.0 if tie[y] == 'D' else 0.0, 0.0))
            lo, hi = np.percentile(n, [10, 90]); won = int(after[y] > 50 or (after[y] == 50 and tie[y] == 'D'))
            pc = min(max(float(control.mean()), 0.001), 0.999)
            rows.append({'year': y, 'days': d, 'shared_sd': round(sn, 3), 'dem_seats_mean': round(float(n.mean()), 2), 'low80': int(lo), 'high80': int(hi),
                         'actual': actual, 'inside80': bool(lo <= actual <= hi), 'p_actual_or_more': round(float(np.mean(n >= actual)), 4),
                         'p_actual_or_fewer': round(float(np.mean(n <= actual)), 4), 'p_dem_control': round(pc, 4), 'dem_won_control': won,
                         'log_loss_control': round(-(won * math.log(pc) + (1 - won) * math.log(1 - pc)), 4)})
    return pd.DataFrame(rows)


def live_shared(X, years):
    """The shared error a forecast fitted on all the years would use at each distance: measured on every year's
    out-of-sample misses, never smaller further out."""
    out, nearer = {}, 0.0
    for d in sorted(B.DAYS):
        o = pd.concat([S.forecast(X[(X.year != y) & X.year.isin(years) & (X.days == d)], X[(X.year == y) & (X.days == d)])[1] for y in years])
        sn = S.shared_sd(o.m.values - o.dem2.values, o.year.values); nearer = max(sn, nearer); out[d] = round(nearer, 3)
    return out


def main():
    X4, X5 = data()
    F4 = race_scores(X5, FOUR, FOUR); F5 = race_scores(X5, FOUR, FIVE)
    s4 = summary(F4, ['days']).assign(fit='2018-2024'); s5 = summary(F5, ['days']).assign(fit='2018-2026')
    y4 = summary(F4, ['year']).assign(fit='2018-2024'); y5 = summary(F5, ['year']).assign(fit='2018-2026')
    coef = {}
    for d in B.DAYS:
        for name, ys in (('2018-2024', FOUR), ('2018-2026', FIVE)):
            c, _ = B.fit(X5[X5.year.isin(ys) & (X5.days == d)], B.VERSIONS[S.WORKING]); coef[f'{name} {d}'] = dict(zip(['const'] + B.VERSIONS[S.WORKING], np.round(c, 3).tolist()))
    sim4 = seats(X5, FOUR); sim5 = seats(X5, FIVE)
    sh = {'2018-2024': live_shared(X5, FOUR), '2018-2026': live_shared(X5, FIVE)}
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    print(pd.concat([s4, s5]).pivot(index='days', columns='fit', values=['margin_miss', 'log_loss']).sort_index(ascending=False).to_string())
    print(pd.concat([y4, y5]).pivot(index='year', columns='fit', values=['margin_miss', 'bias', 'log_loss']).to_string())
    print(sh)
    print(sim5[['year', 'days', 'shared_sd', 'dem_seats_mean', 'low80', 'high80', 'actual', 'inside80', 'p_dem_control', 'dem_won_control']].to_string(index=False))
    for nm, sm in (('2018-2024', sim4), ('2018-2026', sim5)):
        print(nm, sm.groupby('days')[['inside80', 'log_loss_control']].mean().round(3).T.to_string())
    with open(os.path.join(ROOT, 'data', 'senate', 'with_2026.json'), 'w') as f:
        json.dump({'note': 'Step 15: 2026 as a fitting year. Race scores are the working version, 2018-2024 each left out, fitted on the other three years or on those and 2026.',
                   'by_distance': pd.concat([s4, s5]).to_dict('records'), 'by_year': pd.concat([y4, y5]).to_dict('records'),
                   'coefficients': coef, 'live_shared_sd': sh,
                   'seats_fit_2018_2024': sim4.to_dict('records'), 'seats_fit_2018_2026': sim5.to_dict('records')}, f, indent=1)


if __name__ == '__main__':
    main()
