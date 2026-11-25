"""The 2028 forecast as it stands today. Writes data/forecast_2028.json."""
import hashlib, json, re, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F

HISTORY = 'data/history.csv'

def inputs():
    """Today's inputs (data/inputs.json). update.py refreshes all of them every day: the date, approval, the market price
    and the Fifty-Two Keys count, each with the date it was read. A source that cannot be read keeps its last value."""
    return json.load(open('data/inputs.json'))

def nowcast():
    s = open('data/nowcast.js').read()
    return json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', s).group(1))

def nominees(nc):
    """(Democrat, Republican) once the Nowcast has found both nominees; None before then."""
    t = nc.get('tickets') or {}
    d = ((t.get('dem') or {}).get('president') or {}).get('name'); r = ((t.get('rep') or {}).get('president') or {}).get('name')
    return (d, r) if d and r else None

def state_poll_file():
    """data/state_polls.json (polls.py): head-to-head polls of single states, each marked usable or not, with the reason."""
    try:
        return json.load(open('data/state_polls.json'))
    except FileNotFoundError:
        return {'polls': [], 'state_questions': [], 'found': {}, 'sources': {}}

def state_poll_table(sp):
    """The usable state polls as rows of the model's poll table."""
    return pd.DataFrame([{'year': 2028, 'state': p['place'], 'pollster': p['pollster'], 'end': pd.Timestamp(p['end']), 'n': p.get('n') or 600,
                          'pop': p.get('population') if p.get('population') in M.SET['pop_weight'] else 'rv', 'dem2': p['dem2']} for p in sp.get('polls', [])],
                        columns=['year', 'state', 'pollster', 'end', 'n', 'pop', 'dem2'])

def pairing_spread(nc):
    """How far apart the polled pairings stand, in points of share: the spread of the pairings' averages, each counted by
    its number of polls. None once both nominees are known, when only their pairing is polled."""
    if nominees(nc): return None
    by = {}
    for p in nc['h2h']['polls']: by.setdefault((p['d'], p['r']), []).append(p['share'])
    if len(by) < 2: return 0.0
    m = np.array([np.mean(v) for v in by.values()]); w = np.array([len(v) for v in by.values()], float)
    return float(np.sqrt((w * (m - (w * m).sum() / w.sum()) ** 2).sum() / w.sum()))

# ---- the candidate (model.CANDIDATE, README "The candidate"). Sizes written down on 2026-11-25, 713 days out.
APPROVAL_RESPONSE = 0.30      # the approval model's published coefficient: points of vote for each point of approval
DRIFT_FROM, DRIFT_TO = 713, 130   # the inputs' drift is sized for the 713 days then left, and is gone by late June 2028, when they are final

def approval_left(days_out):
    """The share of the approval allowance's variance still open at `days_out`, by the calendar alone: all of it at the 713
    days the allowance was sized for, none at the end of June 2028 (130 days out). In between it falls in a straight line,
    so the allowance itself falls with the square root of the time left, as the spread of a figure that drifts does."""
    return float(np.clip((days_out - DRIFT_TO) / (DRIFT_FROM - DRIFT_TO), 0, 1))


APPROVAL_FLOOR = 30 / (DRIFT_FROM - DRIFT_TO)      # a month's worth of drift: what stays open while the June polls are awaited


def june_approval_in(NOW):
    """Is the June 2028 approval reading a fact yet? It is when Fifty-Two Keys has scored its approval keys on the June
    polls (their state in its feed is provisional or settled), which that site does a week after the month ends and only
    if polls of all adults finished in June exist. The date alone never says so."""
    k = ((NOW.get('upstream') or {}).get('fifty_two_keys') or {})
    return bool(k.get('approval_in'))


def approval_open(days_out, observed):
    """The share of the approval allowance still open. It runs down with the calendar while June 2028 is ahead, and it
    closes only when the June reading is in. If the calendar runs out first (polls late, none taken, the feed not read),
    a month's worth stays open until the reading arrives."""
    if M.SET['drift_rule'] != 'calendar': return 1.0
    return 0.0 if observed else max(approval_left(days_out), APPROVAL_FLOOR)


TURNOUT = None
def turnout():
    """Two-party votes cast in each state in 2024: how much each state counts when the national vote is added up from the states."""
    global TURNOUT
    if TURNOUT is None: TURNOUT = {k: float(v['votes']) for k, v in json.load(open('data/results_2024.json')).items() if len(k) == 2 and v.get('votes')}
    return TURNOUT


def candidate(NOW, nc, polls, sp, res, errs, t, tables, ev, today):
    """The forecast under review, run on today's inputs. It is not the published forecast and is not shown as one.

    National number: the Nowcast's two national models and the Fifty-Two Keys line, a third each, with the national polling
    average phased in by the record of what it has been worth at this distance. The long-range model is built on polls: it
    is left out until the polls it is built on exist (October 2027), and after that the average gets only the weight that
    model does not already carry.
    States: the national number, the state's lean, and where the Nowcast's state models place the state against their own
    national figure. State polls count under a ceiling that falls with the distance from the election."""
    import timeline as T
    tl = T.curves(2028); base = dict(term1=1, deminc=0); d_out = max((pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(today)).days, 1)
    km = NOW.get('keys_mean', NOW['keys'])                                                   # the middle of that site's run ahead, not only its likeliest count
    line = lambda k: F.forecast(2028, t, juneapp=NOW['net_approval'], keys=k, **base)[2]['keys_model']
    K = line(km); E = float(nc['models']['enns']['demPopular']); ds = nc['models'].get('desart')
    D = float(ds['demPopular']) if ds else None
    fixed = bool((nc.get('desart_final') or {}).get('frozen'))
    spread = pairing_spread(nc)
    extra = {s['abbr'].replace('-', ''): s['demShare'] for s in nc['states']}; extra['US'] = float(nc['summary']['demPopular'])
    allp = pd.concat([polls[polls.state == 'US'], state_poll_table(sp)], ignore_index=True)
    # what the inputs may still move by: approval moves the approval model and the keys together, so the two are added
    left = float(np.clip((d_out - DRIFT_TO) / (DRIFT_FROM - DRIFT_TO), 0, 1))
    dE = APPROVAL_RESPONSE * NOW['approval_drift'] / 2; dK = abs(line(km + NOW['keys_sd']) - K)

    A = F.forecast(2028, t, juneapp=NOW['net_approval'], keys=km, **base)[2]['approval_model']          # the approval equation, as the published forecast runs it
    dA = abs(F.forecast(2028, t, juneapp=NOW['net_approval'] + NOW['approval_drift'], keys=km, **base)[2]['approval_model'] - A)

    def run(before, kind='three_models'):
        """The candidate with the long-range model treated, before its own polls exist, in one of the three ways. kind:
        'three_models' is the candidate; 'four_models' the hybrid, with the approval equation kept; 'structural' the hybrid
        without the long-range model at any date."""
        old = dict(M.SET); M.SET.update({'three_models': M.CANDIDATE, 'four_models': M.HYBRID, 'structural': M.STRUCTURAL}[kind], long_range_before=before)
        try:
            if kind == 'three_models':
                weight, load = M.long_range_weight(2028, today, tl, polls, fixed) if D is not None else (0.0, 0.0)
                S = F.three_models(E, D, K, weight) if D is not None else (E + K) / 2
                drift = float(np.sqrt(left) * (dE + dK) / ((2 + weight) if D is not None else 2))
            else:
                weight, load = M.long_range_weight(2028, today, tl, polls, fixed, others=3) if (D is not None and kind == 'four_models') else (0.0, 0.0)
                S = F.four_models(E, D if kind == 'four_models' else None, K, A, weight)
                drift = float(np.sqrt(left) * (dE + dK + dA) / (3 + weight))            # approval moves all three together, so the three are added
            out, info = M.forecast(2028, today, allp, res, tables, (S, drift), market=NOW['market_dem'], extra_prior=extra, ev=ev, timeline=tl, pairing_spread=spread, prior_poll_load=load)
        finally:
            M.SET.clear(); M.SET.update(old)
        return out, info, S, drift, weight, load

    def told(kind):
        o, i, S_, drift_, w_, load_ = run(M.SET['long_range_before'], kind); St_ = o['states']
        return {'p_dem': o['p_dem'], 'p_model': o['p_model'], 'p_popular': o['p_popular'], 'national': o['national'], 'national_sd': o['national_sd'], 'national_lo': o['national_lo'], 'national_hi': o['national_hi'],
                'ev_median': o['ev_median'], 'ev_lo': o['ev_lo'], 'ev_hi': o['ev_hi'], 'tipping_point': St_.state[St_.tip.idxmax()], 'prior': S_, 'drift': drift_, 'long_range_weight': w_,
                'parts': {'approval_and_economy': E, 'fifty_two_keys': K, 'approval_equation': A, 'long_range': D if w_ else None},
                'poll_share': i['poll_share'], 'poll_share_total': i['poll_share_total'], 'prior_moves_with_polls': load_,
                'states': {q['state']: [round(float(q['mean']), 2), round(float(q['p_dem']), 4), round(float(q['lo']), 2), round(float(q['hi']), 2)] for _, q in St_.iterrows()}}

    out, info, S, drift, weight, load = run(M.SET['long_range_before'])
    St = out['states']
    brief = lambda o, i: {'p_dem': round(o['p_dem'], 4), 'national': round(o['national'], 3), 'ev_median': int(o['ev_median']), 'polls_in_national': round(i['poll_share_total'], 3)}
    # the same forecast with the long-range model counted the two other ways, for comparison, until its own polls exist
    other = {} if (D is None or fixed) else {f'long_range_in_{k}': brief(*run(k)[:2]) for k in ('part', 'full') if k != M.SET['long_range_before']}
    return {'p_dem': out['p_dem'], 'p_model': out['p_model'], 'p_popular': out['p_popular'], 'national': out['national'], 'national_sd': out['national_sd'],
            'ev_median': out['ev_median'], 'ev_lo': out['ev_lo'], 'ev_hi': out['ev_hi'], 'tipping_point': St.state[St.tip.idxmax()],
            'prior': S, 'parts': {'approval_and_economy': E, 'long_range': D, 'fifty_two_keys': K}, 'long_range_weight': weight, 'long_range_fixed': fixed, 'keys_index': km, 'drift': drift,
            'national_polls': info['national_polls'], 'poll_share': info['poll_share'], 'poll_share_record': info['poll_share_record'], 'poll_share_total': info['poll_share_total'],
            'prior_moves_with_polls': load, 'pairing_spread': spread, 'nominees_known': nominees(nc) is not None,
            'state_poll_ceiling': float(M.curve(tl['state'], d_out) / M.curve(tl['state'], 1)), 'state_polls_counted': int(len(sp.get('polls', []))),
            'states': {q['state']: [round(float(q['mean']), 2), round(float(q['p_dem']), 4), round(float(q['poll_share']), 3)] for _, q in St.iterrows()},
            'other_ways': other, 'settings': dict(M.CANDIDATE),
            # the hybrid: the candidate with the approval equation kept (model.HYBRID). Also under review, also not published.
            'hybrid': dict(told('four_models'), settings=dict(M.HYBRID)),
            'keys_vote': keys_vote(NOW, t, base)}

def keys_vote(NOW, t, base, draws=40000, seed=52):
    """The national vote the Fifty-Two Keys count points to, as a spread and not one number: every count that site's run
    ahead gives, with its share of runs, put through the line fitted on earlier elections, with the line's own misses
    added. Three things are kept apart: where the count may end up (the spread of the count), how far the line has missed
    on past elections (equation_error), and the two together (sd). Democratic share of the two-party vote."""
    dist = NOW.get('keys_dist') or []
    past = t[t.year < 2028].dropna(subset=['keys']); slope, icept = np.polyfit(past['keys'], past.incvote, 1)
    resid = float(np.sqrt(np.mean(np.square(past.incvote - (icept + slope * past['keys'])))))
    if not dist: return {'from': 'the count and its spread only', 'equation_error': round(resid, 2), 'slope': round(float(slope), 2)}
    x = np.array([a for a, _ in dist], float); w = np.array([b for _, b in dist], float); w = w / w.sum()
    rng = np.random.default_rng(seed); idx = rng.choice(x, size=draws, p=w)
    inc = icept + slope * idx + rng.normal(0, resid, draws); dem = 100 - inc if not base.get('deminc') else inc
    q = lambda a: round(float(np.percentile(dem, a)), 2)
    return {'from': 'the spread of the count', 'mean': round(float(dem.mean()), 2), 'sd': round(float(dem.std()), 2), 'p10': q(10), 'p50': q(50), 'p90': q(90),
            'count_mean': round(float((x * w).sum()), 3), 'count_sd': round(float(np.sqrt((w * (x - (x * w).sum()) ** 2).sum())), 3), 'from_count': round(float(abs(slope)) * float(np.sqrt((w * (x - (x * w).sum()) ** 2).sum())), 2),
            'equation_error': round(resid, 2), 'slope': round(float(slope), 2), 'elections': int(len(past))}


def poll_table(nc):
    """The Nowcast's head-to-head polls as the model's poll table. A poll that names a state is filed under that state."""
    names = {v['name']: k.replace('-', '') for k, v in json.load(open('data/results_2024.json')).items()}
    def where(p):
        s = str(p.get('state') or p.get('geo') or 'US').strip()
        return names.get(s, s.replace('-', '') if s.replace('-', '') in names.values() else 'US')
    return pd.DataFrame([{'year': 2028, 'state': where(p), 'pollster': p['pollster'], 'end': pd.Timestamp(p['date']), 'n': p.get('n') or 1000, 'pop': 'rv', 'dem2': p['share']} for p in nc['h2h']['polls']])

def chance(now, polls, states, date, res, errs, t, market=False):
    """The chance of a Democratic win for one set of inputs: used to split a change between them. Every call draws the same
    simulated errors (the seed is fixed), so two calls differ only by what was changed between them."""
    base = dict(term1=1, deminc=0); days = (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(date)).days
    fd, fsd, _ = F.forecast(2028, t, juneapp=now['net_approval'], keys=now['keys'], **base)
    up = F.forecast(2028, t, juneapp=now['net_approval'] + now['approval_drift'], keys=now['keys'], **base)[0]
    ku = F.forecast(2028, t, juneapp=now['net_approval'], keys=now['keys'] + now['keys_sd'], **base)[0]
    sd = float(np.sqrt(fsd ** 2 + approval_open(days, june_approval_in(now)) * (up - fd) ** 2 + (ku - fd) ** 2))
    extra = {s['abbr'].replace('-', ''): s['demShare'] for s in states}
    out, _ = M.forecast(2028, date, polls, res, M.error_tables(2028, res, errs), (fd, sd), market=now['market_dem'] if market else None, extra_prior=extra, ev=M.ev_table(2024, res))
    return out['p_model']

PARTS = [('polls', 'National polls'), ('approval', 'Presidential approval'), ('keys', 'Fifty-Two Keys count'), ('models', "Tipping Point's models of the states"), ('time', 'Time until the election')]

def change(NOW, nc, res, errs, t, today_p, since=None):
    """What moved the simulations' chance since an earlier day's inputs (by default the previous day's: data/prev_inputs.json,
    data/prev_nowcast.js). Each part is credited with its average effect over every order in which the parts could have
    been changed, so the split does not depend on an order and the parts add up to the whole. Parts that did not change are
    left out of the sum: they are zero by construction. What is left over after the parts (an input outside these five) is
    reported as such and not given a name it has not earned."""
    from itertools import combinations
    from math import factorial
    try:
        old, onc = since or (json.load(open('data/prev_inputs.json')), json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', open('data/prev_nowcast.js').read()).group(1)))
    except FileNotFoundError:
        return None
    if old['as_of'] >= NOW['as_of']: return None
    opolls, npolls = poll_table(onc), poll_table(nc)
    sig = lambda pt: sorted(map(tuple, pt[['pollster', 'end', 'dem2', 'state']].astype(str).values.tolist()))
    moved = {'polls': sig(opolls) != sig(npolls), 'approval': old['net_approval'] != NOW['net_approval'], 'keys': (old['keys'], old['keys_sd']) != (NOW['keys'], NOW['keys_sd']),
             'models': [round(s['demShare'], 3) for s in onc['states']] != [round(s['demShare'], 3) for s in nc['states']], 'time': True}
    live = [k for k, _ in PARTS if moved[k]]; memo = {}
    def value(on):
        key = frozenset(on)
        if key not in memo:
            now = dict(old)
            if 'approval' in on: now['net_approval'] = NOW['net_approval']
            if 'keys' in on: now['keys'], now['keys_sd'] = NOW['keys'], NOW['keys_sd']
            if 'time' in on and NOW.get('upstream'): now['upstream'] = NOW['upstream']
            memo[key] = chance(now, npolls if 'polls' in on else opolls, (nc if 'models' in on else onc)['states'], NOW['as_of'] if 'time' in on else old['as_of'], res, errs, t)
        return memo[key]
    n = len(live); d = {k: 0.0 for k, _ in PARTS}
    for k in live:
        rest = [x for x in live if x != k]
        for size in range(n):
            for sub in combinations(rest, size):
                d[k] += factorial(size) * factorial(n - size - 1) / factorial(n) * (value(sub + (k,)) - value(sub))
    p0, p1 = value(()), value(tuple(live))
    parts = [{'key': k, 'name': name, 'd': round(d[k], 5)} for k, name in PARTS]
    return {'from': old['as_of'], 'p_prev': round(p0, 5), 'p': round(today_p, 5), 'explained': round(p1 - p0, 5), 'other': round(today_p - p1, 5), 'parts': parts, 'evaluated': len(memo),
            'keys': [old['keys'], NOW['keys']], 'approval': [old['net_approval'], NOW['net_approval']], 'market': [round(old['market_dem'], 4), round(NOW['market_dem'], 4)],
            'polls': [len(onc['h2h']['polls']), len(nc['h2h']['polls'])], 'days': [(pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(old['as_of'])).days, (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(NOW['as_of'])).days]}

def main():
    NOW = inputs(); TODAY = NOW['as_of']
    res = pd.read_csv('data/results.csv'); errs = pd.read_csv('data/average_errors.csv'); t = F.table(); nc = nowcast()
    polls = poll_table(nc)
    base = dict(term1=1, deminc=0)
    fd, fsd, parts = F.forecast(2028, t, juneapp=NOW['net_approval'], keys=NOW['keys'], **base)
    up = F.forecast(2028, t, juneapp=NOW['net_approval'] + NOW['approval_drift'], keys=NOW['keys'], **base)[0]
    ku = F.forecast(2028, t, juneapp=NOW['net_approval'], keys=NOW['keys'] + NOW['keys_sd'], **base)[0]
    open_ = approval_open((pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days, june_approval_in(NOW))
    sd = float(np.sqrt(fsd ** 2 + open_ * (up - fd) ** 2 + (ku - fd) ** 2))      # the equations' own error, plus what their inputs may still move by (the keys' part shrinks by itself: it is that site's own spread)
    tables = M.error_tables(2028, res, errs)
    extra = {s['abbr'].replace('-', ''): s['demShare'] for s in nc['states']}
    ev = M.ev_table(2024, res)
    out, info = M.forecast(2028, TODAY, polls, res, tables, (fd, sd), market=NOW['market_dem'], extra_prior=extra, ev=ev, turnout=turnout())
    plain, _ = M.forecast(2028, TODAY, polls, res, tables, (fd, sd), ev=ev)                       # without the Nowcast's state forecasts or the market
    # how the range should narrow: the same formulas at other distances from the election, with the drift in the fundamentals' inputs shrinking to nothing by June 2028
    d0 = (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days; funnel = []
    for d in [d0, 600, 500, 400, 300, 200, 150, 100, 60, 30, 14, 7, 1]:
        k = max(d - 130, 0) / (d0 - 130); sf = float(np.sqrt(fsd ** 2 + approval_open(d, False if d > DRIFT_TO else True) * (up - fd) ** 2 + k * (ku - fd) ** 2)); sp = M.at(tables['nat'], d)
        w = sf ** 2 / (sf ** 2 + sp ** 2); sn = float(np.sqrt(w ** 2 * sp ** 2 + (1 - w) ** 2 * sf ** 2))
        funnel.append({'days': d, 'half': round(2 * 1.2816 * sn, 2), 'poll_share': round(w, 3)})
    lo = lambda q: np.log(q / (1 - q))
    msens = [{'weight': w, 'p': round(float(1 / (1 + np.exp(-((1 - w) * lo(out['p_model']) + w * lo(NOW['market_dem']))))), 3)} for w in (0, 0.25, 0.5, 0.7, 1.0)]
    # the national vote of each simulated election, added up from that election's own states by the votes each cast in 2024:
    # the chance of winning the most votes, and of the vote and the Electoral College disagreeing, are counted from that
    ns = out['national_from_states']
    if ns: out.update(p_popular_national=out['p_popular'], p_popular=ns['p_popular'], p_vote_not_college=ns['p_vote_not_college'], p_college_not_vote=ns['p_college_not_vote'])
    r = res.set_index(['year', 'state'])
    sp = state_poll_file()
    cand = candidate(NOW, nc, polls, sp, res, errs, t, tables, ev, TODAY)
    share = lambda q: round(100 * q['dem_pct'] / (q['dem_pct'] + q['rep_pct']), 1) if q.get('dem_pct') and q.get('rep_pct') else None
    S = out['states']; names = {s['abbr'].replace('-', ''): s.get('name', s['abbr']) for s in nc['states']}
    tip = S.state[S.tip.idxmax()]                       # the state that most often carries the winner past 270
    J = {'as_of': TODAY, 'days_out': (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days, 'p_dem': out['p_dem'], 'p_model': out['p_model'], 'market': NOW['market_dem'],
         'p_rep': out['p_rep'], 'p_without_extras': plain['p_dem'], 'p_popular': out['p_popular'], 'p_tie': out['p_tie'], 'paths': out['paths'], 'national_from_states': out['national_from_states'], 'approval_open': open_, 'june_approval_in': june_approval_in(NOW), 'p_vote_not_college': out['p_vote_not_college'], 'p_college_not_vote': out['p_college_not_vote'], 'national': out['national'], 'national_sd': out['national_sd'], 'ev_mean': out['ev_mean'], 'ev_median': out['ev_median'], 'ev_lo': out['ev_lo'], 'ev_hi': out['ev_hi'],
         'ev_dist': [round(float(x), 5) for x in out['ev_dist']], 'tipping_point': tip,
         'inputs': {'national_polls': info['national_polls'], 'polls_n': int(len(polls)), 'poll_share': info['poll_share'], 'fundamentals': fd, 'fundamentals_sd': sd, 'approval_model': parts['approval_model'], 'keys_model': parts['keys_model'],
                    'net_approval': NOW['net_approval'], 'market_note': NOW['market_note'], 'keys': NOW['keys'], 'nowcast_p_dem': nc['summary']['pDemWin'], 'nowcast_national': nc['summary']['demPopular'], 'nowcast_as_of': nc['as_of']},
         'national_lo': out['national_lo'], 'national_hi': out['national_hi'],
         'states': [{'state': q['state'], 'ev': int(q['ev']), 'mean': round(float(q['mean']), 2), 'sd': round(float(np.sqrt(q['sd'] ** 2 + out['national_sd'] ** 2)), 2), 'lo': round(float(q['lo']), 2), 'hi': round(float(q['hi']), 2), 'p_dem': round(float(q['p_dem']), 4), 'tip': round(float(q['tip']), 4), 'prior': round(float(q['prior']), 2), 'lean': round(float(M.lean(res, 2028, q['state'])), 2), 'r2024': round(float(r.dem2[(2024, q['state'])]), 2), 'r2020': round(float(r.dem2[(2020, q['state'])]), 2), 'nowcast': round(float(extra[q['state']]), 1)} for _, q in S.iterrows()],
         'change': change(NOW, nc, res, errs, t, out['p_dem']), 'state_polls': int((polls.state != 'US').sum()),
         # every general-election poll of a single state that the sources hold, counted or not (polls.py). The published forecast
         # does not count state polls yet; the candidate does, under its ceiling.
         'state_poll_list': [{'state': q['place'], 'pollster': q['pollster'], 'end': q['end'], 'dem': share(q), 'pairing': f"{q['dem']} v {q['rep']}" if q.get('dem') and q.get('rep') else None,
                              'usable': bool(q['usable']), 'why': q['why_not'], 'url': q['url'] if str(q.get('url') or '').startswith(('https://', 'http://')) else None} for q in sp.get('state_questions', []) if q.get('place') and share(q) is not None],
         'state_poll_sources': {'found': sp.get('found', {}), 'answered': {k: bool(v.get('answered')) for k, v in sp.get('sources', {}).items()}, 'fetched': sp.get('fetched')},
         'candidate': cand,
         'funnel': funnel, 'market_sensitivity': msens, 'equation_error': fsd,
         'settings': {k: v for k, v in M.SET.items()},
         # what this forecast was made from (update.py records the other sites' versions) and with
         'upstream': NOW.get('upstream'),
         'model': {'settings': hashlib.sha256(json.dumps(M.SET, sort_keys=True, default=str).encode()).hexdigest()[:12], 'sims': M.SET['sims'], 'seed': M.SET['seed'], 'status': 'published',
                   'under_review': hashlib.sha256(json.dumps(M.CANDIDATE, sort_keys=True, default=str).encode()).hexdigest()[:12]}}
    json.dump(J, open('data/forecast_2028.json', 'w'), indent=1)
    # the day-by-day record: one row a day, today's row replaced if the forecast is run again
    row = {'date': TODAY, 'p_dem': round(J['p_dem'], 4), 'p_rep': round(J['p_rep'], 4), 'p_tie': round(J['p_tie'], 4), 'p_model': round(J['p_model'], 4), 'market': round(J['market'], 4), 'national': round(J['national'], 2), 'ev_median': int(J['ev_median']),
           'national_polls': round(J['inputs']['national_polls'], 2), 'polls_n': J['inputs']['polls_n'], 'net_approval': NOW['net_approval'],
           'candidate_p_dem': round(cand['p_dem'], 4), 'candidate_national': round(cand['national'], 2),
           'hybrid_p_dem': round(cand['hybrid']['p_dem'], 4), 'hybrid_national': round(cand['hybrid']['national'], 2)}
    try:
        h = pd.read_csv(HISTORY); h = h[h.date != TODAY]
    except FileNotFoundError:
        h = pd.DataFrame()
    pd.concat([h, pd.DataFrame([row])]).sort_values('date').to_csv(HISTORY, index=False)
    quiet = ('ev_dist', 'states', 'settings', 'inputs', 'state_poll_list', 'state_poll_sources', 'candidate', 'funnel', 'market_sensitivity')
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J.items() if k not in quiet}); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J['inputs'].items()})
    print('under review:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cand.items() if k not in ('states', 'settings', 'parts', 'hybrid', 'keys_vote')}, {k: round(v, 2) for k, v in cand['parts'].items() if v is not None})
    hy = cand['hybrid']; print('hybrid:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in hy.items() if k not in ('states', 'settings', 'parts')}, {k: round(v, 2) for k, v in hy['parts'].items() if v is not None}); print('keys vote:', cand['keys_vote'])
    f = sp.get('found', {}); print(f"state polls: {f.get('state_polls', 0)} found in {f.get('states_polled', [])}, {f.get('usable_state_polls', 0)} meet the rules")
    print(S.assign(lead=(S['mean'] - 50).abs()).sort_values('lead').head(12)[['state', 'ev', 'mean', 'p_dem']].round(3).to_string(index=False))

if __name__ == '__main__':
    main()
