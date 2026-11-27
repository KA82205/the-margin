"""The Senate back-test, step 2: forecast every race of 2018-2024 at fixed distances before the election, with ingredients
added one at a time, and score each version. Research only.

Each year is forecast from the other three (leave one year out), so no race helps fit the model that forecasts it. Four
years is a short record: every number here rests on four national environments, and should be read that way.

Versions, each built on the one before:
    lean         the state's presidential lean, and the generic-ballot average as the national environment
    +incumbent   whether the seat's holder is running, and for which party
    +polls       the race's polling average, mixed with the version above by a weight fitted for each distance
    +money       the two candidates' fundraising (last day only: the FEC's totals are for the whole cycle, see README)
    +polls by volume             the polls' weight rises with the amount of polling, between a floor and a cap
    +polls by volume, race sd    the same, with the error sized for each race (tested and not adopted, see README)
    +track, +polls by volume     each candidate's record in earlier Senate races added to the fundamentals (adopted, step 5)
    +national, +polls by volume  the national input half the generic ballot, half the approval-and-midterm fundamentals
                                 (national.py; adopted, step 8)
    president, our president, ticket ...   presidential years started from the presidential polls or from The Margin's own
                                 presidential forecast of the state (tested and not adopted, see README, step 4)

Scores, at each distance: the typical miss on the margin (root mean square, in points), races called, the Brier score
and log loss of the chance of winning, and how often the result fell inside the 50% and 80% intervals. FiveThirtyEight's
published forecasts (2018-2022, its lite, classic and deluxe versions) are scored on the same races and days.

    python senate/backtest.py      writes data/senate/backtest.json and prints the tables
"""
import json, math, os, sys
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
import model as M                                                    # the presidential model's poll weights, reused as they are
import national as NA                                                # the national fundamentals (step 8)
import fec_money as FM                                               # money raised by each date (step 13)

D = os.path.join(ROOT, 'data', 'senate')
YEARS = (2018, 2020, 2022, 2024)
DAYS = (365, 250, 120, 60, 30, 14, 7, 1)
ELECTION = {2018: '2018-11-06', 2020: '2020-11-03', 2022: '2022-11-08', 2024: '2024-11-05'}
# races decided on another day: the runoffs (Georgia) and Mississippi's 2018 special runoff
OTHER_DAY = {(2020, 'GA', False): '2021-01-05', (2020, 'GA', True): '2021-01-05', (2022, 'GA', False): '2022-12-06', (2018, 'MS', True): '2018-11-27'}
POP = {'lv': 'lv', 'rv': 'rv', 'v': 'rv', 'a': 'a'}
Z = {50: 0.6745, 80: 1.2816}


def eday(r):
    return pd.Timestamp(OTHER_DAY.get((r.year, r.state, bool(r.special)), ELECTION[r.year]))


def table(p, cols):
    """Polls in the shape model.weights reads: end, n, pop, pollster."""
    return pd.DataFrame({'end': pd.to_datetime(p[cols['end']], format='mixed'), 'n': pd.to_numeric(p[cols['n']], errors='coerce').fillna(600).clip(lower=50),
                         'pop': p[cols['pop']].map(POP).fillna('rv'), 'pollster': p[cols['pollster']].astype(str), 'x': p[cols['x']].astype(float)}).reset_index(drop=True)


def average(t, asof, d_out, floor=1.0):
    """The weighted average of the polls finished by asof, as the presidential model weights them; None when the weight
    of what there is falls below floor (about one fresh poll), so that a stale handful does not pass for an average."""
    t = t[t.end <= asof]
    if not len(t): return None, 0.0
    w = M.weights(t, asof, d_out)
    if w.sum() < floor * 1e-9 or w.sum() <= 0: return None, 0.0
    return float((w * t.x.values).sum() / w.sum()), float(w.sum())


def build():
    # the race polls: Wikipedia's race pages (polls_wikipedia.csv, senate/wiki_build.py), the source the forecast will
    # read live (step 11); FiveThirtyEight's archive (polls.csv) when SENATE_TRAIN_POLLS=538, as in steps 2-10
    pf = 'polls.csv' if os.environ.get('SENATE_TRAIN_POLLS') == '538' else 'polls_wikipedia.csv'
    MT = FM.table()
    R = pd.read_csv(os.path.join(D, 'races.csv')); P = pd.read_csv(os.path.join(D, pf)); G = pd.read_csv(os.path.join(D, 'generic.csv'))
    P = P[(P.partisan.fillna('') == '') & ~P.internal.astype(bool)]                       # as the presidential model does
    G = G[(G.partisan.fillna('') == '') & ~G.internal.fillna(False).astype(bool)]
    gen = {y: table(G[G.cycle == y], {'end': 'end_date', 'n': 'sample_size', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'}) for y in YEARS}
    H = pd.read_csv(os.path.join(D, 'president_polls.csv')); H = H[(H.partisan.fillna('') == '') & ~H.internal.astype(bool)]
    pc = {'end': 'end', 'n': 'n', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'}
    pres = {(y, st): table(h, pc) for (y, st), h in H.groupby(['year', 'state'])}
    rows = []
    for r in R.itertuples():
        E = eday(r); pr = P[(P.year == r.year) & (P.state == r.state) & (P.special == r.special)]
        pt = table(pr, {'end': 'end', 'n': 'n', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'}) if len(pr) else None
        for d in DAYS:
            asof = E - pd.Timedelta(days=d)
            g, _ = average(gen[r.year], asof, d)
            pa, pw = average(pt, asof, d) if pt is not None else (None, 0.0)
            hs = average(pres[(r.year, r.state)], asof, d)[0] if (r.year, r.state) in pres else None
            hn = average(pres[(r.year, 'US')], asof, d)[0] if (r.year, 'US') in pres else None
            md, mr = (r.dem_receipts if r.dem_receipts == r.dem_receipts else 0.0), (r.rep_receipts if r.rep_receipts == r.rep_receipts else 0.0)
            mt = FM.money_feature(*FM.raised(MT, r.year, r.state, bool(r.special), asof)) if MT is not None else 0.0
            rows.append({'year': r.year, 'state': r.state, 'special': bool(r.special), 'days': d, 'dem2': r.dem2, 'lean': r.lean,
                         'generic': g, 'inc_d': int(r.incumbent == 'D'), 'inc_r': int(r.incumbent == 'R'),
                         'money': math.log((md + 1e5) / (mr + 1e5)), 'money_t': mt, 'poll': pa, 'poll_w': pw, 'indep': bool(r.dem_independent),
                         'pres_state': hs, 'pres_nat': hn,
                         # each candidate's record in earlier Senate races in the state (build_data.track_records), Democratic side
                         # less Republican, 0 for a candidate without one
                         'track': (r.dem_track if r.dem_track == r.dem_track else 0.0) - (r.rep_track if r.rep_track == r.rep_track else 0.0)})
    X = pd.DataFrame(rows)
    X['generic'] = X.groupby(['year', 'days']).generic.transform(lambda s: s.fillna(s.mean()))
    # the state's presidential environment in a presidential year: its own presidential polling average, or failing that the
    # national presidential average plus the state's lean; in a midterm year, and when there is neither, the generic ballot
    # plus the lean, as before
    X['fund_env'] = X.generic + X.lean
    pres_env = X.pres_state.where(X.pres_state.notna(), X.pres_nat + X.lean)
    X['env'] = pres_env.where(pres_env.notna(), X.fund_env)
    X['pres_gap'] = X.env - X.fund_env
    # The Margin's own presidential forecast of the state, at the same distance (president_states.py); 2020 and 2024 only
    PF = pd.read_csv(os.path.join(D, 'president_forecast.csv')).rename(columns={'mean': 'margin_pres'})[['year', 'state', 'days', 'margin_pres']]
    X = X.merge(PF, on=['year', 'state', 'days'], how='left')
    X['our_env'] = X.margin_pres.where(X.margin_pres.notna(), X.fund_env)
    X['our_gap'] = X.our_env - X.fund_env
    # the national fundamentals (national.py): approval and the midterm, averaged half and half with the generic ballot
    return NA.add(X)


def split(cols):
    """A column named '@x' is an offset: taken as it is, with no coefficient fitted on it."""
    off = [c[1:] for c in cols if c.startswith('@')]; return [c for c in cols if not c.startswith('@')], off


def fit(train, cols):
    cols, off = split(cols); y = train.dem2.values - sum(train[c].values for c in off)
    A = np.column_stack([np.ones(len(train))] + [train[c].values for c in cols]); b = np.linalg.lstsq(A, y, rcond=None)[0]
    res = y - A @ b
    return b, float(np.sqrt(np.mean(res ** 2)))


def predict(b, df, cols):
    cols, off = split(cols)
    return b[0] + sum(b[i + 1] * df[c].values for i, c in enumerate(cols)) + sum(df[c].values for c in off)

K_GRID = np.exp(np.linspace(np.log(0.05), np.log(50), 60))
W_GRID = np.round(np.arange(0, 1.0001, 0.05), 2)
SD_FLOOR = 1.0


def poll_share(df, p):
    """The weight on the race's polling average: w0 for any average, rising toward w1 as the polling grows, by
    pw / (pw + k), where pw is the average's total weight. The cap w1 stands for the error polls share in a year, which
    more polls do not remove; the floor w0 for what even a thin or stale average says about a race."""
    w0, w1, k = p
    return np.where(df.poll.notna(), w0 + (w1 - w0) * df.poll_w.fillna(0).values / (df.poll_w.fillna(0).values + k), 0.0)


def blend(df, p):
    return df.f.values + poll_share(df, p) * (df.poll.fillna(df.f).values - df.f.values)


def volume_fit(af):
    """(w0, w1, k) for blend(), fitted on the training years at this distance: the grid point with the least squared error."""
    hp = af.poll.notna().values
    if hp.sum() < 10: return (0.0, 0.0, 1.0)
    f, y = af.f.values[hp], af.dem2.values[hp]; dx = af.poll.values[hp] - f; pw = af.poll_w.values[hp]
    pairs = np.array([(w0, w1) for w0 in W_GRID for w1 in W_GRID if w1 >= w0]); best = (np.inf, None)
    for k in K_GRID:
        W = pairs[:, :1] + (pairs[:, 1:] - pairs[:, :1]) * (pw / (pw + k))[None, :]
        sse = (((f + W * dx) - y) ** 2).sum(axis=1); i = int(np.argmin(sse))
        if sse[i] < best[0]: best = (float(sse[i]), (float(pairs[i, 0]), float(pairs[i, 1]), float(k)))
    return best[1]


def sd_features(df):
    hp = df.poll.notna().values.astype(float)
    return np.column_stack([np.ones(len(df)), np.abs(df.m.values - 50), hp, hp * np.log1p(df.poll_w.fillna(0).values)])


def sd_fit(af):
    """The error of each race, from the training years: the size of the miss regressed on how far the forecast is from
    even, whether the race has a polling average, and how much polling it has. For a normal error, sd = sqrt(pi/2) E|e|."""
    A = sd_features(af); e = np.abs(af.m.values - af.dem2.values)
    return np.linalg.lstsq(A, e, rcond=None)[0]


def sd_predict(c, df):
    return np.maximum(SD_FLOOR, math.sqrt(math.pi / 2) * (sd_features(df) @ c))


VERSIONS = {'lean': ['lean', 'generic'], '+incumbent': ['lean', 'generic', 'inc_d', 'inc_r'], '+money': ['lean', 'generic', 'inc_d', 'inc_r', 'money'],
            'president': ['env', 'inc_d', 'inc_r'], 'president gap': ['lean', 'generic', 'inc_d', 'inc_r', 'pres_gap'],
            'our president': ['our_env', 'inc_d', 'inc_r'], 'our president gap': ['lean', 'generic', 'inc_d', 'inc_r', 'our_gap'],
            # the Senate result as the state's presidential forecast plus how far the party's candidate runs ahead of the top
            # of the ticket, which depends on who holds the seat: the forecast is taken as it is, with no coefficient fitted on it
            'ticket': ['@our_env', 'inc_d', 'inc_r'],
            '+track': ['lean', 'generic', 'inc_d', 'inc_r', 'track'],
            '+national': ['lean', 'blend_approval', 'inc_d', 'inc_r', 'track'],
            '+national +money': ['lean', 'blend_approval', 'inc_d', 'inc_r', 'track', 'money_t']}
# the race-poll blend by volume, on each starting point: the fundamentals with incumbency, and the two presidential ones
BLENDS = {'+polls by volume': '+incumbent', 'president, +polls by volume': 'president', 'president gap, +polls by volume': 'president gap',
          'our president, +polls by volume': 'our president', 'our president gap, +polls by volume': 'our president gap', 'ticket, +polls by volume': 'ticket',
          '+track, +polls by volume': '+track', '+national, +polls by volume': '+national', '+national +money, +polls by volume': '+national +money'}


def run(X):
    """Leave-one-year-out forecasts for every version at every distance. Returns a frame of (race, days, version, mean, sd)."""
    out = []
    for y in YEARS:
        tr, te = X[X.year != y], X[X.year == y]
        for d in DAYS:
            a, b_ = tr[tr.days == d], te[te.days == d].copy()
            for name, cols in VERSIONS.items():
                if name == '+money' and d != 1: continue
                coef, sd = fit(a, cols); b_['m'] = predict(coef, b_, cols)
                out += [{'year': y, 'state': r.state, 'special': r.special, 'days': d, 'version': name, 'mean': r.m, 'sd': sd, 'dem2': r.dem2} for r in b_.itertuples()]
            # polls: the fundamentals version with incumbency, moved toward the race's polling average by a weight fitted on
            # the other years at this distance (least squares, held between 0 and 1); its error, too, from the other years
            cols = VERSIONS['+incumbent']; coef, _ = fit(a, cols)
            af = a.assign(f=predict(coef, a, cols)); has = af.poll.notna()
            if has.sum() >= 10:
                x = (af.poll - af.f)[has].values; yv = (af.dem2 - af.f)[has].values; w = float(np.clip((x * yv).sum() / (x * x).sum(), 0, 1))
                res = np.where(has, af.f + w * (af.poll.fillna(af.f) - af.f), af.f) - af.dem2; sd_p = float(np.sqrt(np.mean(res[has] ** 2))); sd_n = float(np.sqrt(np.mean(res[~has] ** 2))) if (~has).any() else sd_p
            else:
                w, sd_p, sd_n = 0.0, None, None
            bf = b_.assign(f=predict(coef, b_, cols))
            for r in bf.itertuples():
                hp = r.poll == r.poll and r.poll is not None
                out.append({'year': y, 'state': r.state, 'special': r.special, 'days': d, 'version': '+polls', 'mean': r.f + w * (r.poll - r.f) if hp else r.f,
                            'sd': (sd_p if hp else sd_n) or 5.0, 'dem2': r.dem2, 'poll_weight': w if hp else 0.0})
            # refinements: a poll weight that grows with the amount of polling, and an error sized for each race
            for bname, base_v in BLENDS.items():
                cols = VERSIONS[base_v]; coef, _ = fit(a, cols)
                af = a.assign(f=predict(coef, a, cols)); bf = b_.assign(f=predict(coef, b_, cols))
                p = volume_fit(af)
                af['m'] = blend(af, p); hv = af.poll.notna().values; rv = af.m.values - af.dem2.values
                sv_p = float(np.sqrt(np.mean(rv[hv] ** 2))) if hv.any() else 5.0; sv_n = float(np.sqrt(np.mean(rv[~hv] ** 2))) if (~hv).any() else sv_p
                sdc = sd_fit(af)
                bf['m'] = blend(bf, p); bf['sd'] = sd_predict(sdc, bf); bf['share'] = poll_share(bf, p)
                for r in bf.itertuples():
                    hp = r.poll == r.poll and r.poll is not None
                    base = {'year': y, 'state': r.state, 'special': r.special, 'days': d, 'mean': r.m, 'dem2': r.dem2, 'poll_weight': r.share, 'w0': p[0], 'w1': p[1], 'k': p[2]}
                    out.append({**base, 'version': bname, 'sd': sv_p if hp else sv_n})
                    if bname == '+polls by volume': out.append({**base, 'version': '+polls by volume, race sd', 'sd': r.sd})
    return pd.DataFrame(out)


def cdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def score(F):
    """Scores for each version and distance."""
    F = F.assign(p=[cdf((m - 50) / s) for m, s in zip(F['mean'], F['sd'])], won=(F.dem2 > 50).astype(int), err=2 * (F['mean'] - F.dem2))
    F['p'] = F.p.clip(0.001, 0.999)
    g = F.groupby(['version', 'days'])
    S = g.apply(lambda x: pd.Series({'races': len(x), 'margin_miss': float(np.sqrt(np.mean(x.err ** 2))), 'called': int(((x['mean'] > 50) == (x.dem2 > 50)).sum()),
                                     'brier': float(np.mean((x.p - x.won) ** 2)), 'log_loss': float(-np.mean(x.won * np.log(x.p) + (1 - x.won) * np.log(1 - x.p))),
                                     'inside50': float(np.mean(np.abs(x['mean'] - x.dem2) <= Z[50] * x.sd)), 'inside80': float(np.mean(np.abs(x['mean'] - x.dem2) <= Z[80] * x.sd)),
                                     'bias': float(np.mean(x.err))}), include_groups=False).reset_index()
    return F, S


OURS = ('+track, +polls by volume', '+national, +polls by volume')


def benchmark(F):
    """FiveThirtyEight's forecasts on the same races and days (2018-2022), scored the same way, beside this model's +polls
    version on exactly those races."""
    B = pd.read_csv(os.path.join(D, 'benchmark_538.csv.gz'))
    R = pd.read_csv(os.path.join(D, 'races.csv'))
    out = []
    for r in R[R.year < 2024].itertuples():
        E = eday(r); b = B[(B.year == r.year) & (B.state == r.state) & (B.special == r.special)]
        if not len(b): continue
        for d in DAYS:
            day = (E - pd.Timedelta(days=d)).strftime('%Y-%m-%d'); x = b[b.forecast_date == day]
            if not len(x): continue
            for v, xv in x.groupby('forecast_type'):
                dem = xv[xv.party.isin(['D']) | (xv.party.eq('I') & xv.candidate.str.upper().str.contains('|'.join(['SANDERS', 'KING', 'MCMULLIN'])))]
                rep = xv[xv.party == 'R']
                if not len(dem) or not len(rep): continue
                dv, rv = float(dem.projected_voteshare.max()), float(rep.projected_voteshare.max()); pdw = float(dem.probwin.max())
                out.append({'year': r.year, 'state': r.state, 'special': bool(r.special), 'days': d, 'version': '538 ' + v, 'mean': 100 * dv / (dv + rv), 'p': pdw, 'dem2': r.dem2})
    Bf = pd.DataFrame(out)
    if not len(Bf): return None
    Bf = Bf.assign(won=(Bf.dem2 > 50).astype(int), err=2 * (Bf['mean'] - Bf.dem2), p=Bf.p.clip(0.001, 0.999))
    ours = F[F.version.isin(OURS) & (F.year < 2024)].merge(Bf[['year', 'state', 'special', 'days']].drop_duplicates(), on=['year', 'state', 'special', 'days'])
    both = pd.concat([Bf, ours.assign(version='this model, ' + ours.version)[['year', 'state', 'special', 'days', 'version', 'mean', 'p', 'dem2', 'won', 'err']]])
    both = both.assign(close=(both.dem2 - 50).abs() < 10)
    Tc = both[both.close].groupby(['version', 'days']).apply(lambda x: pd.Series({'races': len(x), 'margin_miss': float(np.sqrt(np.mean(x.err ** 2))), 'log_loss': float(-np.mean(x.won * np.log(x.p) + (1 - x.won) * np.log(1 - x.p)))}), include_groups=False).reset_index()
    print('FiveThirtyEight and this model, competitive races, 2018-2022:'); print(Tc.pivot(index='days', columns='version', values='log_loss').round(3).sort_index(ascending=False)); print(Tc.pivot(index='days', columns='version', values='margin_miss').round(2).sort_index(ascending=False))
    T = both.groupby(['version', 'days']).apply(lambda x: pd.Series({'races': len(x), 'margin_miss': float(np.sqrt(np.mean(x.err ** 2))), 'called': int(((x['mean'] > 50) == (x.dem2 > 50)).sum()),
                                                                    'brier': float(np.mean((x.p - x.won) ** 2)), 'log_loss': float(-np.mean(x.won * np.log(x.p) + (1 - x.won) * np.log(1 - x.p)))}), include_groups=False).reset_index()
    return T


def main():
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 20)
    X = build(); F = run(X); F, S = score(F); T = benchmark(F)
    by_year = F[F.version == '+polls'].groupby(['year', 'days']).apply(lambda x: pd.Series({'bias': float(np.mean(x.err)), 'margin_miss': float(np.sqrt(np.mean(x.err ** 2)))}), include_groups=False).reset_index()
    # competitive races only: decided by under 20 points of margin, where a forecast is put to the test
    Sc = score(F[(F.dem2 - 50).abs() < 10].drop(columns=['p', 'won', 'err']))[1]
    weights = F[(F.version == '+polls') & (F.poll_weight > 0)].groupby('days').poll_weight.mean().round(3).to_dict()
    vol = F[F.version == '+polls by volume']
    k_by_days = vol.groupby(['days', 'year'])[['w0', 'w1', 'k']].first().reset_index().round(3).to_dict('records')
    vol_weights = vol[vol.poll_weight > 0].groupby('days').poll_weight.describe(percentiles=[.1, .5, .9])[['10%', '50%', '90%']].round(3).to_dict('index')
    coverage = X.groupby('days').apply(lambda x: float(x.poll.notna().mean()), include_groups=False).round(3).to_dict()
    out = {'scores': S.round(4).to_dict('records'), 'scores_competitive': Sc.round(4).to_dict('records'), 'benchmark': T.round(4).to_dict('records') if T is not None else None, 'by_year': by_year.round(3).to_dict('records'),
           'poll_weight': weights, 'volume_fit': k_by_days, 'volume_poll_weight': vol_weights, 'races_with_a_poll_average': coverage, 'races': int(X[['year', 'state', 'special']].drop_duplicates().shape[0])}
    json.dump(out, open(os.path.join(D, 'backtest.json'), 'w'), indent=1)
    print('Scores (leave one year out). margin_miss: typical miss on the margin, points; called: of', out['races'], 'races')
    print(S.pivot(index='days', columns='version', values='margin_miss').round(2).sort_index(ascending=False))
    print(S.pivot(index='days', columns='version', values='log_loss').round(3).sort_index(ascending=False))
    print(S[S.version == '+polls'][['days', 'called', 'brier', 'inside50', 'inside80', 'bias']].round(3).to_string(index=False))
    print('Competitive races (decided by under 20 points):'); print(Sc.pivot(index='days', columns='version', values='margin_miss').round(2).sort_index(ascending=False))
    for v in ('+polls', '+polls by volume', '+polls by volume, race sd'):
        print(v); print(Sc[Sc.version == v][['days', 'races', 'called', 'brier', 'log_loss', 'inside50', 'inside80']].round(3).to_string(index=False))
    print('All races:')
    for v in ('+polls', '+polls by volume, race sd'):
        print(v); print(S[S.version == v][['days', 'brier', 'log_loss', 'inside50', 'inside80']].round(3).to_string(index=False))
    print('poll weight by distance', weights); print(pd.DataFrame(k_by_days).pivot(index='days', columns='year').sort_index(ascending=False)); print(pd.DataFrame(vol_weights).T); print('share of races with a poll average', coverage)
    if T is not None: print(T.pivot(index='days', columns='version', values='log_loss').round(3).sort_index(ascending=False)); print(T.pivot(index='days', columns='version', values='margin_miss').round(2).sort_index(ascending=False))
    print(by_year.pivot(index='days', columns='year', values='bias').round(2).sort_index(ascending=False))
    return out


if __name__ == '__main__':
    main()
