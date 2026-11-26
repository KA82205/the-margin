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
    state_model_mode='lean',   # 'share': its forecast of the state as it stands. 'lean': only where it puts the state against its own national figure
    lean=(0.75, 0.25),         # state lean: last election and the one before
    lean_error='recent',       # how far a state lands from its starting point: 'all' = every election since 1980, one size for every state;
    lean_window=5,             # 'recent' = the last `lean_window` elections, each state by its own record pulled toward the common
    lean_shrink=4,             # size as if it had `lean_shrink` more elections at that size (interval_study.py)
    region_share=0.4,          # share of a state's own error that it shares with its region
    t_df=5,                    # fat tails for the national error
    rating_weight=0.0,         # expert ratings: tested at 15% to 100% on 2008-2024 and left out; they did not improve the state forecasts (checks.py)
    market_weight=0.0,         # betting markets are shown beside the forecast and do not move it (0.25 until November 25, 2026, pooled on the log-odds scale)
    sims=40000, seed=538,
    # ---- how the national number is put together, and how polls are phased in. The first value of each is the forecast as
    # published; the second is the candidate under review (CANDIDATE below, README "The candidate").
    national_prior='no_keys',        # 'fundamentals': the approval equation and the Fifty-Two Keys line, averaged.
                                     # 'three_models': the Tipping Point Nowcast's two national models and the Fifty-Two Keys line, a third each
                                     # 'four_models': the same with the approval equation, each an equal part (HYBRID below)
                                     # 'structural': the approval-and-economy model, the Keys line and the approval equation; no long-range model
                                     # 'no_keys': the approval-and-economy model, the approval equation and, once eligible, the long-range model (RECOMMENDED)
    poll_weight='timeline',          # 'precision': polls against the prior by the size of each one's past errors, as if the two were unrelated.
                                     # 'timeline': by what the polling average has been worth at this distance from the election (timeline.py)
    state_poll_weight='horizon',      # 'volume': a state's polls against a starting point worth prior_polls, whatever the distance.
                                     # 'horizon': the same, under a ceiling that falls with the distance from the election (timeline.py)
    drift_rule='calendar',              # what approval may still move by before June 2028. 'fixed': the figure in data/inputs.json at every distance.
                                     # 'calendar': that figure today, shrinking with the square root of the time left and gone by the end of June 2028,
                                     # and closed for good only when the June polls are actually in (run_2028.approval_open). In use from November 25, 2026.
    pairing_spread_floor=1.5,        # 'timeline' and 'horizon' only: until both nominees are known, polls are of pairings that may never happen.
                                     # The spread between pairings counts as extra error in the polls, and is never taken as less than this (points of share)
    long_range_before='out',         # 'three_models' only: the long-range model before the polls it is built on exist (long_range_weight below).
                                     # 'out': left out until they do. 'part': counted for part of its third. 'full': counted in full, as the Nowcast shows it
)
# the candidate: every setting that differs from the published forecast
# The forecast as published until November 25, 2026: the approval equation and the Fifty-Two Keys line averaged, polls weighed
# by their precision, state polls by their number, half of each state's starting point from the state models as they stand.
# Kept so that the back-tests can still be run on it (backtest.py previous).
PREVIOUS = dict(national_prior='fundamentals', poll_weight='precision', state_poll_weight='volume', state_model_mode='share', lean_error='all')
CANDIDATE = dict(national_prior='three_models', poll_weight='timeline', state_poll_weight='horizon', state_model_mode='lean')
# The hybrid: the candidate with the approval equation kept, as the published forecast keeps it. Its national prior is the
# Nowcast's approval-and-economy model, the Fifty-Two Keys line and the approval equation, a third each; the long-range
# model joins as a fourth, equal part once the polls it is built on exist (four_models). Nothing else differs from the
# candidate: polls by the timeline, state polls under the ceiling, the state models used for their placing only.
# STRUCTURAL is the same without the long-range model at any date: polls then reach the national number by one road only.
# Neither is the published forecast. No weight in either was fitted.
HYBRID = dict(CANDIDATE, national_prior='four_models')
# RECOMMENDED: the hybrid without the Fifty-Two Keys line (keys_study.py: every score was better without it, and better
# still the less of it there was). Its prior is the approval-and-economy model and the approval equation, with the
# long-range model as a third equal part once the polls it is built on exist. Under review until approved.
RECOMMENDED = dict(CANDIDATE, national_prior='no_keys')
STRUCTURAL = dict(CANDIDATE, national_prior='structural')
# The long-range model inside the Tipping Point Nowcast reads national head-to-head polls: its forecast moves by this much
# for each point in their average (DeSart's equation as that site runs it, docs/combine.js there). It is up to a third of
# the candidate's national prior, so up to a third of this is in the prior before a poll is counted here.
LONG_RANGE_POLLS = 0.522
LONG_RANGE_FIXED = '-11-07'      # the day, in the year before the election, on which that model's polls (those of October) are fixed
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

def average_errors(res, avg538, days=None):
    """How far 538's published polling averages of 1972-2016 stood from the result, by days out (run once, by prep.py)."""
    days = days or H
    names = json.load(open('data/results_2024.json')); ab = {v['name']: k for k, v in names.items() if len(k) == 2}; ab['National'] = 'US'
    a = avg538[avg538.days.isin(days) & (avg538.cycle >= 1972)]
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
    if SET.get('lean_error', 'all') == 'recent':
        # How far states have landed from their leans, from the last few elections only (states have held their place
        # better since 2000 than before), and each state by its own record, pulled toward the common size as if every state
        # had `lean_shrink` further elections at that size: no state's figure rests on its own handful of results alone.
        years = [y for y in sorted(res.year.unique()) if 1980 <= y < year][-SET['lean_window']:]; own = {}
        for y in years:
            for st in res[res.year == y].state:
                l = lean(res, y, st)
                if l is not None and len(st) == 2: own.setdefault(st, []).append(r.dem2[(y, st)] - r.nat2[(y, st)] - l)
        common = float(np.sqrt(np.mean(np.square([x for v in own.values() for x in v])))); k = SET['lean_shrink']
        out['lean'] = common
        out['lean_by_state'] = {st: float(np.sqrt((np.sum(np.square(v)) + k * common ** 2) / (len(v) + k))) for st, v in own.items()} if k is not None else {}
    return out

def at(table, d):
    h = sorted(table); return float(np.interp(d, h, [table[k] for k in h]))

def curve(p, d):
    """A weight that is p[0] on the last day, half of that p[1] days out, and falls away beyond with power p[2]."""
    return p[0] / (1 + (np.asarray(d, float) / p[1]) ** p[2])

def discount(w, extra_sd, base_sd):
    """A weight on polls, cut for extra error in them. The weight w is read as a ratio of error sizes (polls to prior);
    extra_sd, measured against the prior's own error base_sd, is added to the polls' side."""
    if w <= 0 or not extra_sd: return float(max(w, 0.0))
    return float(1 / (1 + (1 - w) / w + (extra_sd / base_sd) ** 2))

def october_share(polls, year, asof):
    """Of the weight in the national polling average on `asof`, the share on polls taken in the October before the election
    year: the polls the long-range model is built on."""
    P = Polls(polls, year); asof = pd.Timestamp(asof); nat = P.nat[P.nat.end <= asof]
    if not len(nat): return 0.0
    w = weights(nat, asof, max((P.eday - asof).days, 1))
    october = ((nat.end >= f'{year - 1}-10-01') & (nat.end <= f'{year - 1}-10-31')).values
    return float(w[october].sum() / w.sum()) if w.sum() > 0 else 0.0


def long_range_weight(year, asof, timeline, polls=None, fixed=None, others=2):
    """How much of its third the long-range model gets in the candidate's prior, and how far that prior then moves when the
    polls being averaged move by a point: (weight, load).

    The model is built on the national polls of the October before the election year.
      Once they are fixed the model counts in full. The polls in it are then the October ones, and the average shares them
        only for as long as they still weigh in it: a few months.
      Before then the model has made no forecast. What the Nowcast shows for it is the model run early, on today's polls,
        which is early polling with a coefficient of a half. SET['long_range_before'] says what is done with that:
          'out'   it is left out, and polls reach the national number only by the weight the record gives them
          'part'  it counts for as much of its third as polls this far out are worth against polls on the day the model
                  reads them (timeline.py)
          'full'  it counts in full
        In the last two every poll in the average is also in the model.
    fixed: True or False where it is known (the Nowcast says when its polls are fixed); None to go by the calendar.
    others: how many other models share the prior with it (two in the candidate, three in the hybrid)."""
    asof = pd.Timestamp(asof); eday = pd.Timestamp(ELECTION[year]); day = pd.Timestamp(f'{year - 1}{LONG_RANGE_FIXED}')
    if fixed is None: fixed = asof >= day
    if fixed: return 1.0, LONG_RANGE_POLLS / (others + 1) * (october_share(polls, year, asof) if polls is not None else 0.0)
    w = {'out': 0.0, 'full': 1.0}.get(SET['long_range_before'])
    if w is None: w = float(min(1.0, curve(timeline['national'], max((eday - asof).days, 1)) / curve(timeline['national'], (eday - day).days)))
    return w, LONG_RANGE_POLLS * w / (others + w)


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
def forecast(year, asof, polls, res, tables, fund, ratings=None, market=None, extra_prior=None, ev=None, timeline=None, pairing_spread=None, prior_poll_load=0.0, turnout=None, keep=False):
    """fund = (Democratic share the national prior expects, its error). ratings = {state: implied share}. market = Democratic chance.
    extra_prior = {state: a state-level model's forecast of it, 'US': that model's national figure}.
    timeline = timeline.curves(year), needed by the 'timeline' and 'horizon' settings. pairing_spread = how far the polled
    pairings stand apart, in points of share, while the nominees are not known (None once they are).
    prior_poll_load = how far the national prior itself moves when the polls being averaged here move by a point (the
    long-range model inside it reads national polls). Used by the 'timeline' setting only, so that no poll counts twice."""
    asof = pd.Timestamp(asof); P = Polls(polls, year); d_out = max((P.eday - asof).days, 1)
    pn, wn = P.national(asof)
    sf = fund[1]
    extra_sd = max(pairing_spread, SET['pairing_spread_floor']) if pairing_spread is not None else 0.0
    if SET['poll_weight'] == 'timeline':
        # what the national average has been worth at this distance, against a structural forecast with no polls in it
        record = discount(float(curve(timeline['national'], d_out)), extra_sd, timeline['prior_error'])
        # the polls already inside the prior are part of that weight, not extra to it: the average gets only what is left.
        # Where the prior carries more than the record supports, the average gets nothing and the excess counts as error
        g = float(prior_poll_load or 0.0)
        w = max(0.0, (record - g) / (1 - g)) if pn is not None else 0.0
        total = w + (1 - w) * g
        nat = w * pn + (1 - w) * fund[0] if pn is not None else fund[0]
        over = max(total - record, 0.0) * float(np.sqrt(at(timeline['poll_error'], d_out) ** 2 + timeline['prior_error'] ** 2))
        # the error is the one the mix itself has made on the record, with whatever the prior may still drift by (fund[1]
        # carries only that drift here)
        base = at(timeline['mix_error'], d_out) if (pn is not None or g > 0) else timeline['prior_error']
        # The drift is in the prior, and the prior is only part of the national number: it counts by the prior's share. (The
        # polls' share already carries its own drift, inside the record's error for a mix at this distance.)
        s_nat = float(np.sqrt(base ** 2 + over ** 2 + ((1 - w) * sf) ** 2))
    else:
        sp = at(tables['nat'], d_out); record = total = None
        if pn is None: w, nat, s_nat = 0.0, fund[0], sf
        else:
            w = sf ** 2 / (sf ** 2 + sp ** 2); nat = w * pn + (1 - w) * fund[0]
            s_nat = float(np.sqrt(w ** 2 * sp ** 2 + (1 - w) ** 2 * sf ** 2))
    horizon = SET['state_poll_weight'] == 'horizon'
    ceiling = float(curve(timeline['state'], d_out) / curve(timeline['state'], 1)) if horizon else 1.0
    tau = at(timeline['state_poll_error'], d_out) if horizon else at(tables['state'], d_out)
    prev = res[res.year == year - 4]
    rows = []
    for st, ev0 in zip(prev.state, prev.ev):
        prior = nat + lean(res, year, st)
        if extra_prior and st in extra_prior:           # a state-level model's own forecast of the state shares the starting point
            x = extra_prior[st] if SET['state_model_mode'] == 'share' else nat + extra_prior[st] - extra_prior['US']      # 'lean': only where it puts the state against its own national figure
            prior = (1 - SET['state_model_weight']) * prior + SET['state_model_weight'] * x
        ps, ws = P.state(st, asof)
        v = ws / (ws + SET['prior_polls']) if ps is not None else 0.0
        if horizon and v > 0: v = discount(ceiling * v, extra_sd, tables['lean'])
        est = v * ps + (1 - v) * prior if ps is not None else prior
        if ratings and st in ratings and ratings[st] is not None:
            est = (1 - SET['rating_weight']) * est + SET['rating_weight'] * ratings[st]
        sd = float(np.sqrt(v ** 2 * tau ** 2 + (1 - v) ** 2 * (tables.get('lean_by_state') or {}).get(st, tables['lean']) ** 2))
        rows.append({'state': st, 'ev': ev0, 'mean': est, 'sd': sd, 'poll': ps, 'poll_weight': ws, 'poll_share': v, 'prior': prior})
    S = pd.DataFrame(rows)
    return simulate(S, nat, s_nat, year, market, ev, turnout, keep), {'national_polls': pn, 'poll_share': w, 'fundamentals': fund[0],
                                                       'poll_share_record': w if record is None else record, 'poll_share_total': w if total is None else total}

def ev_table(year, res):
    """Electoral votes in force for `year` (the previous election's unless the census has moved them)."""
    return dict(zip(res[res.year == year].state, res[res.year == year].ev))

def bound(x):
    """Keep simulated shares inside 0 to 100. The errors are drawn on an open scale, so a place as lopsided as the District
    of Columbia could otherwise be handed more than every vote. A share past 90 is folded smoothly into the last ten points
    (and one under 10 into the first ten), never reaching 100 or 0. Nothing between 10 and 90 is touched, and the fold
    never moves a share across 50 or past another state's, so no chance, electoral count or tipping point changes."""
    x = np.asarray(x, float)
    x = np.where(x > 90, 100 - 10 * np.exp(-(np.maximum(x, 90) - 90) / 10), x)
    return np.where(x < 10, 10 * np.exp((np.minimum(x, 10) - 10) / 10), x)


# For interval_study.py only: the national and the state error sizes multiplied by these. Both are 1 in every forecast.
STUDY = {'national': 1.0, 'state': 1.0}
Q = [2.5, 5, 25, 50, 75, 95, 97.5]                     # further points of each place's simulated results, kept beside the 10th and 90th
QN = ['q025', 'q05', 'q25', 'q50', 'q75', 'q95', 'q975']

def simulate(S, nat, s_nat, year, market=None, ev=None, turnout=None, keep=False):
    """turnout: {state: two-party votes cast last time}. With it the national vote of each simulated election is also added
    up from that election's own state results, each state counting by its votes (the districts are inside their states and
    are not counted again)."""
    rng = np.random.default_rng(SET['seed'] + year); n = SET['sims']; R = regions()
    s_nat = s_nat * STUDY['national']; S = S.assign(sd=S.sd * STUDY['state']) if STUDY['state'] != 1.0 else S
    df = SET['t_df']; eN = rng.standard_t(df, n) * s_nat / np.sqrt(df / (df - 2))
    regs = sorted(set(R[s] for s in S.state)); eR = {g: rng.standard_normal(n) for g in regs}
    rs, ids = np.sqrt(SET['region_share']), np.sqrt(1 - SET['region_share'])
    evs = np.array([ev[s] for s in S.state]) if ev else S.ev.values
    sh = np.empty((len(S), n))
    for i, (st, m, sd) in enumerate(zip(S.state, S['mean'], S.sd)):
        sh[i] = m + eN + sd * (rs * eR[R[st]] + ids * rng.standard_normal(n))
    sh = bound(sh); natv = bound(nat + eN)
    dem_ev = (evs[:, None] * (sh > 50)).sum(0); total = evs.sum()
    # a win is more than half of the electoral votes. An even split is counted on its own: who then becomes president is
    # settled by the House, and nothing here models that
    p = float((dem_ev > total / 2).mean())
    # the tipping point: line the states up from the winner's best to worst and count electoral votes; the state that takes the
    # winner past half is the one that decided it
    order = np.argsort(-sh, axis=0); col = np.arange(n)
    first = lambda o: o[(np.cumsum(evs[o], axis=0) > total / 2).argmax(0), col]
    dwin, rwin = dem_ev > total / 2, dem_ev < total / 2
    tipped = np.where(dwin, first(order), first(order[::-1]))[dwin | rwin]
    # the range given for each place is read off the simulated results themselves: the 10th and 90th of every hundred
    lo, hi = np.percentile(sh, [10, 90], axis=1)
    S = S.assign(p_dem=(sh > 50).mean(1), ev=evs, tip=np.bincount(tipped, minlength=len(S)) / max(1, len(tipped)), lo=lo, hi=hi)
    S = S.assign(**dict(zip(QN, np.percentile(sh, Q, axis=1))))
    # paths: among the closest places, how often each side wins the election when it carries one, and the commonest sets of
    # them behind each side's wins. Counted from the simulated elections themselves, never by multiplying chances.
    pd_ = (sh > 50).mean(1); close = [i for i in np.argsort(np.abs(pd_ - 0.5)) if 0.1 < pd_[i] < 0.9 and evs[i] >= 3][:10]
    paths = {'places': [str(S.state.iloc[i]) for i in close], 'given': {}, 'dem': [], 'rep': []}
    for i in close:
        w = sh[i] > 50
        paths['given'][str(S.state.iloc[i])] = {'dem_if_dem': float(dwin[w].mean()) if w.any() else None, 'dem_if_rep': float(dwin[~w].mean()) if (~w).any() else None}
    if close:
        code = (sh[close] > 50).T @ (1 << np.arange(len(close)))
        for side_, win in (('dem', dwin), ('rep', rwin)):
            if win.any():
                vals, cnt = np.unique(code[win], return_counts=True)
                for j in np.argsort(-cnt)[:5]:
                    carried = [str(S.state.iloc[i]) for k, i in enumerate(close) if (int(vals[j]) >> k) & 1]
                    paths[side_].append({'dem_carries': carried, 'share_of_wins': float(cnt[j] / win.sum()), 'share_of_all': float(cnt[j] / n)})
    from_states = None
    if turnout:
        idx = [i for i, st in enumerate(S.state) if len(st) == 2 and st in turnout]; w = np.array([turnout[S.state.iloc[i]] for i in idx], float); w = w / w.sum()
        nv = w @ sh[idx]
        from_states = {'mean': float(nv.mean()), 'lo': float(np.percentile(nv, 10)), 'hi': float(np.percentile(nv, 90)), 'p_popular': float((nv > 50).mean()),
                       'of_means': float(w @ S['mean'].values[idx]), 'gap': float(w @ S['mean'].values[idx] - nat),
                       'p_vote_not_college': float(((nv > 50) & rwin).mean()), 'p_college_not_vote': float(((nv < 50) & dwin).mean())}
    out = {'p_dem': p, 'p_model': p, 'p_rep': float(rwin.mean()), 'paths': paths, 'national_from_states': from_states, 'ev_mean': float(dem_ev.mean()), 'ev_median': float(np.median(dem_ev)), 'ev_lo': float(np.percentile(dem_ev, 10)), 'ev_hi': float(np.percentile(dem_ev, 90)),
           'national': float(nat), 'national_sd': float(s_nat), 'states': S, 'ev_dist': np.bincount(dem_ev.astype(int), minlength=int(total) + 1) / n,
           'p_popular': float((natv > 50).mean()), 'national_lo': float(np.percentile(natv, 10)), 'national_hi': float(np.percentile(natv, 90)),
           # counted from the same simulated elections: an even split of the electoral votes (half of it goes to each side in
           # p_model), and the two ways the national vote and the Electoral College can disagree
           'p_tie': float((dem_ev == total / 2).mean()), 'p_vote_not_college': float(((natv > 50) & rwin).mean()), 'p_college_not_vote': float(((natv < 50) & dwin).mean())}
    if keep:                                              # the simulated elections themselves, for markets.informed(): read, never changed
        out['sims'] = {'states': [str(s) for s in S.state], 'dem': sh > 50, 'ev': dem_ev, 'total': float(total), 'vote': nv if turnout else natv}
    out['quantiles'] = {'national': dict(zip([str(q) for q in Q + [10, 90]], [float(v) for v in np.percentile(natv, Q + [10, 90])])), 'ev': dict(zip([str(q) for q in Q + [10, 90]], [float(v) for v in np.percentile(dem_ev, Q + [10, 90])]))}
    if market is not None and SET['market_weight'] > 0:
        lo = lambda q: np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4)))
        z = (1 - SET['market_weight']) * lo(p) + SET['market_weight'] * lo(market); out['p_dem'] = float(1 / (1 + np.exp(-z)))
    if market is not None: out['market'] = market
    return out
