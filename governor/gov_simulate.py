"""The governor back-test as a forecast: each election year the national mood was read for (2018 on) forecast at each
distance from election day from the other years only, every race simulated together, and scored on the races and on the
governorships each party won.

    each race's equation   the Democratic share = the year's level + weights on the state's lean and on a sitting governor
                           of either party on the ballot, fitted with a level for each year on the other years from FIRST on
    the year's level       50 + alpha + beta x (the national mood - 50): the other years' levels against their national
                           House vote (governor races follow the nation less than House races do, so beta is below one)
    the shared error       t with 5 degrees of freedom: beta x the national mood's miss of the House vote at that distance
                           (every other year it was read), with the levels' own spread about the line
    each race's error      normal: the spread of the fit's misses; with polls, the spread of the blended misses about
                           each year's average miss
    polls                  each race's polling average (governor/gov_polls.py) blended in as the Senate's and the House's
                           are, fitted at each distance on the other years' races with polls

    python governor/gov_simulate.py [nopolls]
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from house_mod import load
HS = load('simulate')                  # house/simulate.py: the poll blend and its fit

D = os.path.join(ROOT, 'data', 'governor')
DAYS = [365, 250, 120, 60, 30, 14, 7, 1]
FIRST = 2006
COLS = ['lean', 'inc_d', 'inc_r']
SIMS, T_DF = 10000, 5


def load():
    T = pd.read_csv(os.path.join(D, 'training.csv'))
    T['usable'] = T.contested.astype(bool) & T.lean.notna() & T.dem2.notna()
    return T


def national():
    """The national mood at each distance (the Senate model's, data/senate/training_rows.csv) and each year's House vote."""
    t = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'training_rows.csv'))
    nf = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'national_fundamentals.csv')).set_index('year')
    g = t.groupby(['year', 'days']).blend_approval.median().rename('mood').reset_index()
    g['vote'] = g.year.map(nf.house_vote_dem)
    return g


def votes():
    """The Democratic share of the national House vote in every year (data/senate/national_fundamentals.csv)."""
    return pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'national_fundamentals.csv')).set_index('year').house_vote_dem


def fit(T, years):
    """The weights, each year's level and the spread of the misses, fitted with a level for each year."""
    a = T[T.year.isin(years) & T.usable]
    Y = pd.get_dummies(a.year).astype(float)
    X = np.column_stack([a[c].values for c in COLS] + [Y[c].values for c in Y.columns])
    b = np.linalg.lstsq(X, a.dem2.values, rcond=None)[0]
    return b[:len(COLS)], dict(zip(Y.columns, b[len(COLS):])), float(np.std(a.dem2.values - X @ b))


def level_line(lev, vote):
    """alpha, beta and the spread about the line of the years' levels (less 50) against their House vote (less 50)."""
    ys = [y for y in lev if y in vote.index and pd.notna(vote[y])]
    x = np.array([vote[y] - 50 for y in ys]); l = np.array([lev[y] - 50 for y in ys])
    beta, alpha = np.polyfit(x, l, 1)
    return float(alpha), float(beta), float(np.std(l - (alpha + beta * x), ddof=2))


def with_polls(T, days):
    p = os.path.join(D, 'polls_by_date.csv')
    P = pd.read_csv(p) if os.path.exists(p) else pd.DataFrame(columns=['year', 'state', 'days', 'poll', 'poll_w'])
    P = P[P.days == days][['year', 'state', 'poll', 'poll_w']]
    return T.drop(columns=[c for c in ('poll', 'poll_w') if c in T.columns]).merge(P, on=['year', 'state'], how='left')


def poll_fit(T, train, w, alpha, beta, N, d):
    """The poll blend and the own error of races with polls at distance d, from the training years: each year's races
    placed at its level from the national mood at d, blended with their polls (house/simulate.py's fit)."""
    a = T[T.year.isin(train) & T.usable & T.poll.notna()].copy()
    mood = N[N.days == d].set_index('year').mood
    a = a[a.year.isin(mood.index)]
    if len(a) < 10: return (0.0, 0.0, 1.0), None, 0
    a['f'] = 50 + alpha + beta * (a.year.map(mood).values - 50) + a[COLS].fillna(0).values @ w
    p = HS.volume_fit(a.f.values, a.dem2.values, a.poll.values, a.poll_w.values)
    a['m'] = a.f + HS.poll_share(a.poll_w.values, p) * (a.poll - a.f); a['e'] = a.dem2 - a.m
    own = float(np.sqrt(np.mean((a.e - a.groupby('year').e.transform('mean')) ** 2)))
    return p, own, len(a)


def run(polls=True, T0=None, tests=None, fit_years=None):
    """Each test year (the years with a national mood, unless given) forecast at each distance from the other years."""
    T0 = load() if T0 is None else T0; N = national(); nv = votes()
    mood_years = sorted(set(N.year) & set(T0.year))
    out, races = [], []
    for d in DAYS:
        T = with_polls(T0, d)
        for y in tests or mood_years:
            tr = [z for z in (fit_years or sorted(T0.year.unique())) if z != y and z >= FIRST and z % 2 == 0]
            w, lev, sd = fit(T, tr)
            alpha, beta, lsd = level_line(lev, nv)
            mood_err = N[(N.days == d) & (N.year != y) & N.vote.notna()].assign(e=lambda g: g.mood - g.vote).e
            shared = float(np.sqrt(beta ** 2 * np.mean(mood_err ** 2) + lsd ** 2))
            te = T[(T.year == y)].copy(); m = te.usable.values
            mood = float(N[(N.year == y) & (N.days == d)].mood.iloc[0])
            level = 50 + alpha + beta * (mood - 50)
            f = level + te[COLS].fillna(0).values @ w; own = np.full(len(te), sd)
            if polls:
                pp, own_p, _ = poll_fit(T, tr, w, alpha, beta, N, d)
                hp = te.poll.notna().values & m
                share = np.where(hp, HS.poll_share(te.poll_w.fillna(0).values, pp), 0.0)
                f = f + share * (te.poll.fillna(0).values - f)
                if own_p is not None: own = np.where(hp, own_p, sd)
            rng = np.random.default_rng(2028 + y + d)
            L = shared * rng.standard_t(T_DF, SIMS) * np.sqrt((T_DF - 2) / T_DF)
            draws = f[m][None, :] + L[:, None] + own[m][None, :] * rng.standard_normal((SIMS, int(m.sum())))
            fixed_d = int((te.winner[~te.usable] == 'D').sum())
            seats = (draws > 50).sum(1) + fixed_d
            p = (draws > 50).mean(0); won = (te.winner[m] == 'D').values; dem2 = te.dem2.values[m]
            real = int((te.winner == 'D').sum())
            out.append({'year': y, 'days': d, 'races': int(m.sum()), 'called': int(((p > .5) == won).sum()), 'avg_miss': float(np.mean(np.abs(2 * f[m] - 2 * dem2))),
                        'brier': float(np.mean((p - won) ** 2)), 'dem_won_mean': float(seats.mean()), 'dem_won_low': float(np.percentile(seats, 10)), 'dem_won_high': float(np.percentile(seats, 90)),
                        'dem_won': real, 'level': level, 'shared': shared, 'sd': sd, 'beta': beta})
            for j, r in enumerate(te[m].itertuples()):
                races.append({'year': y, 'days': d, 'state': r.state, 'p_dem': float(p[j]), 'margin': float(2 * f[m][j] - 100), 'result': float(2 * r.dem2 - 100), 'won': bool(won[j]),
                              'poll': None if pd.isna(r.poll) else float(2 * r.poll - 100)})
    R = pd.DataFrame(out); R['inside'] = (R.dem_won >= R.dem_won_low) & (R.dem_won <= R.dem_won_high)
    return R, pd.DataFrame(races)


def summary(R):
    return R.groupby('days').agg(called=('called', 'sum'), races=('races', 'sum'), avg_miss=('avg_miss', 'mean'), brier=('brier', 'mean'),
                                 inside80=('inside', 'mean'), years=('year', 'nunique')).sort_index(ascending=False)


if __name__ == '__main__':
    R, X = run(polls='nopolls' not in sys.argv)
    print(R[R.days.isin([365, 60, 1])][['year', 'days', 'races', 'called', 'avg_miss', 'brier', 'dem_won_mean', 'dem_won', 'dem_won_low', 'dem_won_high', 'level', 'shared', 'beta']].round(3).to_string(index=False))
    print(summary(R).round(3).to_string())
