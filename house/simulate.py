"""The House back-test as a forecast: each election 2018-2024 forecast at each distance from election day from the
other elections only, every seat simulated together, and scored on the seats, the races and the chances.

    the district equation   each contested race's Democratic share = the year's level + weights on the district's lean,
                            a member of either party on the ballot (and, to test, money); the weights fitted on the other
                            years with a level for each year, so they do not hang on how the national vote is measured
    the lean                Cook's, as Wikipedia lists it for the lines in use; where Wikipedia notes it was published
                            before the map (2024's redrawn states) or gives none, the 2020 presidential vote on the new
                            lines against the nation's (data/house/leans_alt.csv, from The Downballot's results by
                            district). With "cook75", 2018 and 2020 use the lean the way Cook has worked it out since 2022
                            (three parts the last presidential election to one part the one before) in place of the
                            even split Cook published then
    money                   with "money": each side's FEC receipts as they stood that day (data/house/money_by_date.csv),
                            as a log ratio; with "money_cycle", the totals of the whole cycle (which a forecast could not
                            have known)
    the year's level        the national mood at that distance (the Senate model's: approval and the generic ballot,
                            half and half; data/senate/training_rows.csv), plus the usual gap between the level and the
                            national House vote in the other years
    its error               shared by every district: t with 5 degrees of freedom, its scale the spread of the level's
                            misses (the national mood's miss of the House vote at that distance in the other years, and
                            the gap's own spread)
    each district's error   normal, the spread of the fit's misses
    uncontested seats       to the party that ran

    python house/simulate.py [cook75] [money | money_cycle]
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DAYS = [365, 250, 120, 60, 30, 14, 7, 1]
YEARS = [2018, 2020, 2022, 2024]
SIMS, T_DF = 10000, 5
D = os.path.join(ROOT, 'data', 'house')


def load(cook75=False):
    T = pd.read_csv(os.path.join(D, 'training.csv'), dtype={'dem_fec': str, 'rep_fec': str})
    T['lean'] = T.pvi; T['lean_from'] = np.where(T.pvi.notna() & ~T.pvi_stale.astype(bool), 'published', None)
    p = os.path.join(D, 'leans_alt.csv')
    if os.path.exists(p):
        A = pd.read_csv(p).set_index(['lines', 'state', 'district']).lean
        for i in T.index:
            y, k = T.at[i, 'year'], (T.at[i, 'state'], T.at[i, 'district'])
            if y == 2024 and (T.at[i, 'pvi_stale'] or pd.isna(T.at[i, 'pvi'])) and (2024, *k) in A.index:
                T.at[i, 'lean'] = A[(2024, *k)]; T.at[i, 'lean_from'] = '2020 on the new lines'
            if cook75 and y in (2018, 2020) and (y, *k) in A.index:
                T.at[i, 'lean'] = A[(y, *k)]; T.at[i, 'lean_from'] = 'three to one'
    T['usable'] = T.contested & T.lean.notna() & T.lean_from.notna()
    return T


def with_money(T, days, how):
    T = T.copy()
    if how == 'money_cycle':
        dm, rm = T.dem_money, T.rep_money
    else:
        M = pd.read_csv(os.path.join(D, 'money_by_date.csv'), dtype={'fec': str}); M = M[M.days == days].set_index(['year', 'fec']).receipts
        dm = pd.Series([M.get((y, f), np.nan) if isinstance(f, str) else np.nan for y, f in zip(T.year, T.dem_fec)], index=T.index)
        rm = pd.Series([M.get((y, f), np.nan) if isinstance(f, str) else np.nan for y, f in zip(T.year, T.rep_fec)], index=T.index)
    both = dm.notna() & rm.notna()
    T['money'] = np.where(both, np.log1p(dm.fillna(0).clip(lower=0)) - np.log1p(rm.fillna(0).clip(lower=0)), 0.0); T['has_money'] = both.astype(int)
    return T


def national():
    t = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'training_rows.csv')); nf = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'national_fundamentals.csv')).set_index('year')
    g = t.groupby(['year', 'days']).blend_approval.median().rename('mood').reset_index()
    g['vote'] = g.year.map(nf.house_vote_dem)
    return g


def fit(T, years, cols):
    a = T[T.year.isin(years) & T.usable]
    Y = pd.get_dummies(a.year).astype(float)
    X = np.column_stack([a[c].values for c in cols] + [Y[c].values for c in Y.columns])
    b = np.linalg.lstsq(X, a.dem2.values, rcond=None)[0]
    return b[:len(cols)], dict(zip(Y.columns, b[len(cols):])), float(np.std(a.dem2.values - X @ b))


def run(cols, cook75=False, money=None):
    T0 = load(cook75); N = national(); nv = N.drop_duplicates('year').set_index('year').vote; out = []
    for d in DAYS:
        T = with_money(T0, d, money) if money else T0
        for y in YEARS:
            train = [z for z in YEARS if z != y]
            w, lev, sd = fit(T, train, cols)
            gaps = [lev[z] - nv[z] for z in train]; gap, gap_sd = np.mean(gaps), float(np.std(gaps, ddof=1))
            te = T[T.year == y]; m = te.usable
            base = te[cols].fillna(0).values @ w
            real = int((te.winner == 'D').sum()); fixed_d = int((te.winner[~te.contested] == 'D').sum())
            unknown = te.contested & ~m                                       # contested races without a lean: left to chance
            mood_err = N[(N.days == d) & (N.year != y)].assign(e=lambda g: g.mood - g.vote).e
            shared = float(np.sqrt(np.mean(mood_err ** 2) + gap_sd ** 2))
            level = float(N[(N.year == y) & (N.days == d)].mood.iloc[0]) + gap
            rng = np.random.default_rng(2028 + y + d)
            L = level + shared * rng.standard_t(T_DF, SIMS) * np.sqrt((T_DF - 2) / T_DF)
            draws = L[:, None] + base[m.values][None, :] + sd * rng.standard_normal((SIMS, int(m.sum())))
            seats = (draws > 50).sum(1) + fixed_d + rng.binomial(int(unknown.sum()), 0.5, SIMS)
            p = (draws > 50).mean(0); won = (te.dem2[m] > 50).values
            out.append({'year': y, 'days': d, 'seats_mid': float(np.median(seats)), 'actual': real, 'low80': float(np.percentile(seats, 10)), 'high80': float(np.percentile(seats, 90)),
                        'p_majority': float((seats >= 218).mean()), 'called': int(((p > .5) == won).sum()), 'races': int(m.sum()), 'unknown': int(unknown.sum()),
                        'brier': float(np.mean((p - won) ** 2)), 'log_loss': float(-np.mean(np.log(np.clip(np.where(won, p, 1 - p), 1e-4, 1)))), 'level': level, 'shared': shared, 'sd': sd})
    r = pd.DataFrame(out); r['miss'] = r.seats_mid - r.actual; r['inside'] = (r.actual >= r.low80) & (r.actual <= r.high80)
    return r


def summary(r):
    return r.groupby('days').agg(seat_miss=('miss', lambda x: np.abs(x).mean()), bias=('miss', 'mean'), inside80=('inside', 'mean'), called=('called', 'sum'), races=('races', 'sum'),
                                 brier=('brier', 'mean'), log_loss=('log_loss', 'mean')).sort_index(ascending=False)


if __name__ == '__main__':
    a = sys.argv[1:]; money = 'money_cycle' if 'money_cycle' in a else 'money' if 'money' in a else None
    cols = ['lean', 'inc_d', 'inc_r'] + (['money', 'has_money'] if money else [])
    r = run(cols, cook75='cook75' in a, money=money)
    print(r[r.days.isin([365, 120, 1])][['year', 'days', 'seats_mid', 'actual', 'low80', 'high80', 'p_majority', 'called', 'races', 'unknown']].round(3).to_string(index=False))
    print(summary(r).round(3).to_string())
