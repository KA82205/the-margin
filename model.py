"""The forecast: polling averages, a fundamentals prior, state leans, and a simulation of the Electoral College.

Shares are the Democratic share of the two-party vote, in points. Every setting below was written down before the back-test
was scored; none is fitted to the five elections it is tested on. Sizes of error come only from elections before the one
being forecast.
"""
import json
import numpy as np, pandas as pd

ELECTION = {2008: '2008-11-04', 2012: '2012-11-06', 2016: '2016-11-08', 2020: '2020-11-03', 2024: '2024-11-05', 2028: '2028-11-07'}
SET = dict(
    half_life=(7, 30, 5),      # a poll's weight halves every (days to the election / 5) days, held between 7 and 30
    pollster_repeat=0.5,       # each older poll from the same pollster counts half as much as the one after it
    pop_weight={'lv': 1.0, 'rv': 0.9, 'a': 0.7},
    n_ref=600, n_cap=1.5,      # sample size counts by its square root, relative to 600, up to 1.5
    prior_polls=1.5,           # a state's polls are averaged with its prior as if the prior were this many fresh polls
    state_model_weight=0.5,    # where a state-level model's forecast of the state is given (2028: the Tipping Point Nowcast), its share of the starting point
    state_model_mode='share',  # 'share': its forecast of the state as it stands. 'lean': only where it puts the state against its own national figure
    lean=(0.75, 0.25),         # state lean: last election and the one before
    region_share=0.4,          # share of a state's own error that it shares with its region
    t_df=5,                    # fat tails for the national error
    rating_weight=0.0,         # expert ratings: tested at 15% to 100% on 2008-2024 and left out; they did not improve the state forecasts (checks.py)
    market_weight=0.25,        # betting markets, pooled with the model's chance on the log-odds scale
    sims=40000, seed=538,
)
REGION = None

def regions():
    global REGION
    if REGION is None:
        c = pd.read_csv('data/state_region_crosswalk.csv')
        REGION = dict(zip(c.state_abb, c.region))
        REGION.update({'ME1': REGION['ME'], 'ME2': REGION['ME'], 'NE1': REGION['NE'], 'NE2': REGION['NE'], 'NE3': REGION['NE']})
    return REGION

# ------------------------------------------------------------------ polling averages
def weights(p, asof, d_out):
    lo, hi, k = SET['half_life']
    hl = float(np.clip(d_out / k, lo, hi))
    age = (asof - p.end).dt.days.values
    w = 0.5 ** (age / hl) * np.minimum(np.sqrt(p.n.values / SET['n_ref']), SET['n_cap']) * p['pop'].map(SET['pop_weight']).fillna(0.8).values
    order = p.assign(age=age).groupby('pollster').age.rank(method='first').values - 1          # 0 for a pollster's latest poll
    w = w * SET['pollster_repeat'] ** order
    w[age > 6 * hl] = 0
    return w

def average(p, asof, d_out, adj=None):
    """Weighted average of the polls in p that ended by asof. Returns (average, total weight)."""
    p = p[p.end <= asof]
    if not len(p): return None, 0.0
    w = weights(p, asof, d_out)
    if w.sum() <= 0: return None, 0.0
    x = p.dem2.values + (adj(p.end) if adj is not None else 0)
    return float((w * x).sum() / w.sum()), float(w.sum())

class Polls:
    def __init__(self, polls, year):
        self.year, self.eday = year, pd.Timestamp(ELECTION[year])
        self.p = polls[polls.year == year]
        self.nat = self.p[self.p.state == 'US']
        self._cache = {}
    def national(self, date):
        """National average as it stood on date."""
        date = pd.Timestamp(date)
        if date not in self._cache:
            self._cache[date] = average(self.nat, date, (self.eday - date).days)
        return self._cache[date]
    def state(self, st, asof):
        """State average, each poll moved by the change in the national average since it was taken."""
        asof = pd.Timestamp(asof); now = self.national(asof)[0]
        def adj(ends):
            if now is None: return 0
            return np.array([(now - (self.national(e)[0] if self.national(e)[0] is not None else now)) for e in ends])
        return average(self.p[self.p.state == st], asof, (self.eday - asof).days, adj)

# ------------------------------------------------------------------ sizes of error, from earlier elections only
H = [1, 7, 14, 30, 60, 90, 120, 150]

def average_errors(res, avg538):
    """How far 538's published polling averages of 1972-2016 stood from the result, by days out (run once, by prep.py)."""
    names = json.load(open('data/results_2024.json')); ab = {v['name']: k for k, v in names.items() if len(k) == 2}; ab['National'] = 'US'
    a = avg538[avg538.days.isin(H) & (avg538.cycle >= 1972)]
    a = a.assign(st=a.state.map(ab)).dropna(subset=['st'])
    DEM = {'George S. McGovern', 'Jimmy Carter', 'Walter F. Mondale', 'Michael S. Dukakis', 'Bill Clinton', 'Al Gore', 'John Kerry', 'Barack Obama', 'Hillary Rodham Clinton'}
    top = a.sort_values('pct_estimate', ascending=False).groupby(['cycle', 'st', 'days']).head(2)
    top = top.assign(dem=top.candidate_name.isin(DEM))
    g = top.groupby(['cycle', 'st', 'days'])
    d = g.apply(lambda x: 100 * x.pct_estimate[x.dem].sum() / x.pct_estimate.sum() if x.dem.sum() == 1 and len(x) == 2 else np.nan).rename('avg').reset_index().dropna()
    r = res.set_index(['year', 'state']); natres = res.groupby('year').nat2.first()
    d['res'] = [natres[c] if s == 'US' else r.dem2.get((c, s), np.nan) for c, s in zip(d.cycle, d.st)]
    d = d.dropna(subset=['res']); d['err'] = d.avg - d.res
    nat = d[d.st == 'US'].set_index(['cycle', 'days']).err
    d['rel'] = d.err - [nat.get((c, k), np.nan) for c, k in zip(d.cycle, d.days)]
    return d

def error_tables(year, res, errs):
    """Sizes of error by days out, from elections before `year` only: the national polling average, a state's polling average
    relative to the nation, and a state's lean. The first two are smoothed as variance = (error on the eve) + b x days."""
    d = errs[errs.cycle < year]; out = {}
    def smooth(sq):
        a = sq[1]; b = max(float(np.median([(sq[h] - a) / (h - 1) for h in H[1:]])), 0)      # the eve-of-election error, growing with the median slope
        return {h: float(np.sqrt(a + b * h)) for h in H + [400, 800]}
    out['nat'] = smooth({h: (d[(d.st == 'US') & (d.days == h)].err ** 2).mean() for h in H})
    out['state'] = smooth({h: (d[(d.st != 'US') & (d.days == h)].rel.dropna() ** 2).mean() for h in H})
    r = res.set_index(['year', 'state']); e = []
    for y in sorted(res.year.unique()):
        if y >= year or y < 1980: continue
        for st in res[res.year == y].state:
            l = lean(res, y, st)
            if l is not None and len(st) == 2: e.append(r.dem2[(y, st)] - r.nat2[(y, st)] - l)
    out['lean'] = float(np.sqrt(np.mean(np.square(e))))
    return out

def at(table, d):
    h = sorted(table); return float(np.interp(d, h, [table[k] for k in h]))

def lean(res, year, st):
    r = res.set_index(['year', 'state']); a, b = SET['lean']
    try:
        l1 = r.dem2[(year - 4, st)] - r.nat2[(year - 4, st)]
    except KeyError:
        return None
    try:
        l2 = r.dem2[(year - 8, st)] - r.nat2[(year - 8, st)]
    except KeyError:
        l2 = l1
    return a * l1 + b * l2

# ------------------------------------------------------------------ the forecast for one day
def forecast(year, asof, polls, res, tables, fund, ratings=None, market=None, extra_prior=None, ev=None):
    """fund = (Democratic share the fundamentals expect, its error). ratings = {state: implied share}. market = Democratic chance."""
    asof = pd.Timestamp(asof); P = Polls(polls, year); d_out = max((P.eday - asof).days, 1)
    pn, wn = P.national(asof)
    sp, sf = at(tables['nat'], d_out), fund[1]
    if pn is None: w, nat, s_nat = 0.0, fund[0], sf
    else:
        w = sf ** 2 / (sf ** 2 + sp ** 2); nat = w * pn + (1 - w) * fund[0]
        s_nat = float(np.sqrt(w ** 2 * sp ** 2 + (1 - w) ** 2 * sf ** 2))
    prev = res[res.year == year - 4]
    rows = []
    for st, ev0 in zip(prev.state, prev.ev):
        prior = nat + lean(res, year, st)
        if extra_prior and st in extra_prior:           # a state-level model's own forecast of the state shares the starting point
            x = extra_prior[st] if SET['state_model_mode'] == 'share' else nat + extra_prior[st] - extra_prior['US']      # 'lean': only where it puts the state against its own national figure
            prior = (1 - SET['state_model_weight']) * prior + SET['state_model_weight'] * x
        ps, ws = P.state(st, asof)
        v = ws / (ws + SET['prior_polls']) if ps is not None else 0.0
        est = v * ps + (1 - v) * prior if ps is not None else prior
        if ratings and st in ratings and ratings[st] is not None:
            est = (1 - SET['rating_weight']) * est + SET['rating_weight'] * ratings[st]
        sd = float(np.sqrt(v ** 2 * at(tables['state'], d_out) ** 2 + (1 - v) ** 2 * tables['lean'] ** 2))
        rows.append({'state': st, 'ev': ev0, 'mean': est, 'sd': sd, 'poll': ps, 'poll_weight': ws, 'prior': prior})
    S = pd.DataFrame(rows)
    return simulate(S, nat, s_nat, year, market, ev), {'national_polls': pn, 'poll_share': w, 'fundamentals': fund[0]}

def ev_table(year, res):
    """Electoral votes in force for `year` (the previous election's unless the census has moved them)."""
    return dict(zip(res[res.year == year].state, res[res.year == year].ev))

def simulate(S, nat, s_nat, year, market=None, ev=None):
    rng = np.random.default_rng(SET['seed'] + year); n = SET['sims']; R = regions()
    df = SET['t_df']; eN = rng.standard_t(df, n) * s_nat / np.sqrt(df / (df - 2))
    regs = sorted(set(R[s] for s in S.state)); eR = {g: rng.standard_normal(n) for g in regs}
    rs, ids = np.sqrt(SET['region_share']), np.sqrt(1 - SET['region_share'])
    evs = np.array([ev[s] for s in S.state]) if ev else S.ev.values
    sh = np.empty((len(S), n))
    for i, (st, m, sd) in enumerate(zip(S.state, S['mean'], S.sd)):
        sh[i] = m + eN + sd * (rs * eR[R[st]] + ids * rng.standard_normal(n))
    dem_ev = (evs[:, None] * (sh > 50)).sum(0); total = evs.sum()
    p = float((dem_ev > total / 2).mean() + 0.5 * (dem_ev == total / 2).mean())
    # the tipping point: line the states up from the winner's best to worst and count electoral votes; the state that takes the
    # winner past half is the one that decided it
    order = np.argsort(-sh, axis=0); col = np.arange(n)
    first = lambda o: o[(np.cumsum(evs[o], axis=0) > total / 2).argmax(0), col]
    dwin, rwin = dem_ev > total / 2, dem_ev < total / 2
    tipped = np.where(dwin, first(order), first(order[::-1]))[dwin | rwin]
    S = S.assign(p_dem=(sh > 50).mean(1), ev=evs, tip=np.bincount(tipped, minlength=len(S)) / max(1, len(tipped)))
    out = {'p_dem': p, 'p_model': p, 'ev_mean': float(dem_ev.mean()), 'ev_median': float(np.median(dem_ev)), 'ev_lo': float(np.percentile(dem_ev, 10)), 'ev_hi': float(np.percentile(dem_ev, 90)),
           'national': float(nat), 'national_sd': float(s_nat), 'states': S, 'ev_dist': np.bincount(dem_ev.astype(int), minlength=int(total) + 1) / n,
           'p_popular': float((nat + eN > 50).mean())}
    if market is not None:
        lo = lambda q: np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4)))
        z = (1 - SET['market_weight']) * lo(p) + SET['market_weight'] * lo(market); out['p_dem'] = float(1 / (1 + np.exp(-z))); out['market'] = market
    return out
