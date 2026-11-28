"""The House back-test as a forecast: each election 2018-2024 forecast at each distance from the election day from the
other elections only, every seat simulated together, and scored on the seats, the races and the chances.

    the district equation   each contested race's Democratic share = the year's level + weights on the district's lean,
                            a member of either party on the ballot (and, to test, money); the weights fitted on the other
                            years with a level for each year, so they do not hang on how the national vote is measured
    the year's level        the national mood at that distance (the Senate model's: approval and the generic ballot,
                            half and half; data/senate/training_rows.csv), plus the usual gap between the level and the
                            national House vote in the other years
    its error               shared by every district: t with 5 degrees of freedom, its scale the spread of the level's
                            misses (the national mood's miss of the House vote at that distance, 2018-2026, and the gap's
                            own spread)
    each district's error   normal, the spread of the fit's misses
    uncontested seats       to the party that ran

    python house/simulate.py [money]
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DAYS = [365, 250, 120, 60, 30, 14, 7, 1]
YEARS = [2018, 2020, 2022, 2024]
SIMS, T_DF = 10000, 5


def load():
    T = pd.read_csv(os.path.join(ROOT, 'data', 'house', 'training.csv'))
    T['money'] = np.where(T.dem_money.notna() & T.rep_money.notna(), np.log1p(T.dem_money.fillna(0)) - np.log1p(T.rep_money.fillna(0)), 0.0)
    T['has_money'] = (T.dem_money.notna() & T.rep_money.notna()).astype(int)
    T['lean'] = T.pvi
    return T


def national():
    t = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'training_rows.csv')); nf = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'national_fundamentals.csv')).set_index('year')
    g = t.groupby(['year', 'days']).blend_approval.median().rename('mood').reset_index()
    g['vote'] = g.year.map(nf.house_vote_dem)
    return g


def fit(T, years, cols):
    a = T[T.year.isin(years) & T.contested & T.lean.notna() & ~T.pvi_stale.astype(bool)]
    Y = pd.get_dummies(a.year).astype(float)
    X = np.column_stack([a[c].values for c in cols] + [Y[c].values for c in Y.columns])
    b = np.linalg.lstsq(X, a.dem2.values, rcond=None)[0]
    w, lev = b[:len(cols)], dict(zip(Y.columns, b[len(cols):]))
    sd = float(np.std(a.dem2.values - X @ b))
    return w, lev, sd


def run(cols, money=False):
    T = load(); N = national(); out = []
    for y in YEARS:
        train = [z for z in YEARS if z != y]
        w, lev, sd = fit(T, train, cols)
        nv = N.drop_duplicates('year').set_index('year').vote
        gap = np.mean([lev[z] - nv[z] for z in train])                       # the level against the House vote
        gap_sd = float(np.std([lev[z] - nv[z] for z in train], ddof=1))
        te = T[T.year == y].copy(); m = te.contested & te.lean.notna() & ~te.pvi_stale.astype(bool)
        base = te[cols].fillna(0).values @ w
        real = int((te.winner == 'D').sum()); fixed_d = int((te.winner[~m] == 'D').sum())
        for d in DAYS:
            mood_err = N[(N.days == d) & N.year.isin([z for z in N.year.unique() if z != y])].assign(e=lambda g: g.mood - g.vote).e
            shared = float(np.sqrt(np.mean(mood_err ** 2) + gap_sd ** 2))
            mood = float(N[(N.year == y) & (N.days == d)].mood.iloc[0])
            level = mood + gap
            rng = np.random.default_rng(2028 + y + d)
            L = level + shared * rng.standard_t(T_DF, SIMS) * np.sqrt((T_DF - 2) / T_DF)
            mean = base[m.values]
            draws = L[:, None] + mean[None, :] + sd * rng.standard_normal((SIMS, int(m.sum())))
            seats = (draws > 50).sum(1) + fixed_d
            p = (draws > 50).mean(0); won = (te.dem2[m] > 50).values
            out.append({'year': y, 'days': d, 'seats_mid': float(np.median(seats)), 'actual': real, 'low80': float(np.percentile(seats, 10)), 'high80': float(np.percentile(seats, 90)),
                        'p_majority': float((seats >= 218).mean()), 'called': int(((p > .5) == won).sum()), 'races': int(m.sum()),
                        'brier': float(np.mean((p - won) ** 2)), 'level': level, 'shared': shared})
    return pd.DataFrame(out)


if __name__ == '__main__':
    cols = ['lean', 'inc_d', 'inc_r'] + (['money', 'has_money'] if 'money' in sys.argv[1:] else [])
    r = run(cols)
    r['miss'] = r.seats_mid - r.actual; r['inside'] = (r.actual >= r.low80) & (r.actual <= r.high80)
    print(r[r.days.isin([365, 120, 30, 1])][['year', 'days', 'seats_mid', 'actual', 'low80', 'high80', 'p_majority', 'called', 'races', 'brier', 'shared']].round(3).to_string(index=False))
    s = r.groupby('days').agg(seat_miss=('miss', lambda x: np.abs(x).mean()), inside80=('inside', 'mean'), called=('called', 'sum'), brier=('brier', 'mean')).sort_index(ascending=False)
    print(s.round(3).to_string())
