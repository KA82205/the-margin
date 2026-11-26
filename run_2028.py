"""The 2028 forecast as it stands today. Writes data/forecast_2028.json."""
import hashlib, json, os, re, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F

HISTORY = 'data/history.csv'

def inputs():
    """Today's inputs (data/inputs.json). update.py refreshes all of them every day: the date, approval, the market price
    and the Fifty-Two Keys count, each with the date it was read. A source that cannot be read keeps its last value."""
    return json.load(open('data/inputs.json'))

def read_js(path):
    """One of Tipping Point's files: a line of JavaScript that assigns one object."""
    s = open(path).read()
    return json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', s).group(1))

def read_js_text(s):
    return json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', s).group(1))

def with_live(nc, live):
    """The Nowcast with the parts that must stay current taken from Tipping Point's live feed (live.js): the national
    head-to-head polls, the approval average with every day of June of the election year, and the nominees.

    Tipping Point fixes its academic forecast for good on August 6, 2028 and its Nowcast file is not written again; the
    polls in that file stop a week earlier still. Its live feed goes on being written every hour to Election Day. So the
    forecast reads the models, their state forecasts and their national figure from the Nowcast, fixed or not, and the
    polls, approval and nominees from the feed. Until the summer of 2028 the two files hold the same polls, and this
    changes nothing. A feed older than the Nowcast in hand (it could not be read for a while) is not used."""
    if not live or str(live.get('as_of') or '') < str(nc.get('as_of') or ''): return nc
    out = dict(nc); h, a = live.get('h2h') or {}, live.get('approval') or {}
    out['h2h'] = dict(nc.get('h2h') or {}, **{k: h[k] for k in ('window', 'polls', 'people', 'stale') if k in h})
    out['approval'] = dict(nc.get('approval') or {}, **{k: a[k] for k in ('approve', 'disapprove', 'june') if k in a})
    if 'tickets' in live: out['tickets'] = live['tickets']
    if live.get('sitting_vp'): out['sitting_vp'] = live['sitting_vp']
    out['live'] = {'as_of': live.get('as_of'), 'generated_at': live.get('generated_at'), 'academic': live.get('academic')}
    return out

def nowcast(prev=False):
    """What the forecast reads of Tipping Point: its Nowcast, with the live feed laid over it (with_live). prev: the copies
    kept from the day before."""
    at = 'data/prev_' if prev else 'data/'
    return with_live(read_js(at + 'nowcast.js'), read_js(at + 'live.js') if os.path.exists(at + 'live.js') else None)

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
    df = pd.DataFrame([{'year': 2028, 'state': p['place'], 'pollster': p['pollster'], 'end': pd.Timestamp(p['end']), 'n': p.get('n') or 600,
                        'pop': p.get('population') if p.get('population') in M.SET['pop_weight'] else 'rv', 'dem2': p['dem2']} for p in sp.get('polls', [])],
                      columns=['year', 'state', 'pollster', 'end', 'n', 'pop', 'dem2'])
    # With no usable state poll (the day the nominees become known, every earlier poll is of another pairing) the table
    # is empty, and an empty table must still say its dates are dates, or adding it to the national polls spoils theirs.
    df['end'] = pd.to_datetime(df['end'])
    return df.astype({'year': 'int64', 'n': 'float64', 'dem2': 'float64'})

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


def june_approval(nc, today, year=2028):
    """Net approval in June of the election year, once it is a fact: the mean of the Nowcast's daily approval average over
    the days of June, taken from July 8 so that polls published late are in it. None until then, and None if the series has
    no day in June (the source was down, or nobody polled): a date alone never makes it a fact."""
    if str(today) < f'{year}-07-08': return None
    a = nc.get('approval') or {}                       # 'june': every day of the month, from the live feed; 'trend' is weekly and is the older source
    days = [x for x in a.get('june') or a.get('trend') or [] if str(x.get('d', '')).startswith(f'{year}-06') and x.get('a') is not None and x.get('dis') is not None]
    if len(days) < 10: return None
    return round(float(np.mean([x['a'] - x['dis'] for x in days])), 1)


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
        old = dict(M.SET); M.SET.update({'three_models': M.CANDIDATE, 'four_models': M.HYBRID, 'structural': M.STRUCTURAL, 'no_keys': M.RECOMMENDED}[kind], long_range_before=before)
        try:
            if kind == 'three_models':
                weight, load = M.long_range_weight(2028, today, tl, polls, fixed) if D is not None else (0.0, 0.0)
                S = F.three_models(E, D, K, weight) if D is not None else (E + K) / 2
                drift = float(np.sqrt(left) * (dE + dK) / ((2 + weight) if D is not None else 2))
            elif kind == 'no_keys':                                                            # no Fifty-Two Keys line: approval moves the two parts left together
                weight, load = M.long_range_weight(2028, today, tl, polls, fixed, others=2) if D is not None else (0.0, 0.0)
                S = F.mix([E, A, D], [1, 1, weight])
                drift = float(np.sqrt(left) * (dE + dA) / (2 + weight))
            else:
                weight, load = M.long_range_weight(2028, today, tl, polls, fixed, others=3) if (D is not None and kind == 'four_models') else (0.0, 0.0)
                S = F.four_models(E, D if kind == 'four_models' else None, K, A, weight)
                drift = float(np.sqrt(left) * (dE + dK + dA) / (3 + weight))            # approval moves all three together, so the three are added
            out, info = M.forecast(2028, today, allp, res, tables, (S, drift), market=NOW['market_dem'], extra_prior=extra, ev=ev, timeline=tl, pairing_spread=spread, prior_poll_load=load, turnout=turnout())
        finally:
            M.SET.clear(); M.SET.update(old)
        return out, info, S, drift, weight, load

    def told(kind):
        o, i, S_, drift_, w_, load_ = run(M.SET['long_range_before'], kind); St_ = o['states']
        return {'p_dem': o['p_dem'], 'p_rep': o['p_rep'], 'p_tie': o['p_tie'], 'p_model': o['p_model'], 'p_popular': (o['national_from_states'] or {}).get('p_popular', o['p_popular']), 'national_from_states': o['national_from_states'], 'national': o['national'], 'national_sd': o['national_sd'], 'national_lo': o['national_lo'], 'national_hi': o['national_hi'],
                'ev_median': o['ev_median'], 'ev_lo': o['ev_lo'], 'ev_hi': o['ev_hi'], 'tipping_point': St_.state[St_.tip.idxmax()], 'prior': S_, 'drift': drift_, 'long_range_weight': w_,
                'parts': {'approval_and_economy': E, 'fifty_two_keys': K if kind != 'no_keys' else None, 'approval_equation': A, 'long_range': D if w_ else None},
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
            # the hybrid without the Fifty-Two Keys line: the version recommended after keys_study.py. Under review.
            'recommended': dict(told('no_keys'), settings=dict(M.RECOMMENDED)),
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

def official(now, ncp, ncm, sp, res, errs, t, date, with_turnout=True, keep=False):
    """The published forecast for one set of inputs. ncp: the Nowcast file the national polls are taken from; ncm: the one
    the models, the state forecasts and approval's June reading are taken from (the same file, except when a change is being
    split between them).

    National number: the Nowcast's approval-and-economy model and the approval equation, half each; the long-range model
    joins as a third equal part once the polls it is built on exist, and the polls it shares with the average are then
    counted once. The national polling average gets the weight the record gives polls at this distance.
    States: the national number, each state's lean, and where the Nowcast's state models place the state against their own
    national figure. State polls count under a ceiling that falls with the distance from the election."""
    import timeline as T
    tl = T.curves(2028); base = dict(term1=1, deminc=0); d_out = max((pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(date)).days, 1)
    june = june_approval(ncm, date); net = june if june is not None else now['net_approval']
    A = F.forecast(2028, t, juneapp=net, **base)[2]['approval_model']
    dA = abs(F.forecast(2028, t, juneapp=net + now['approval_drift'], **base)[2]['approval_model'] - A); dE = APPROVAL_RESPONSE * now['approval_drift'] / 2
    E = float(ncm['models']['enns']['demPopular']); ds = ncm['models'].get('desart'); D = float(ds['demPopular']) if ds else None
    fixed = bool((ncm.get('desart_final') or {}).get('frozen')); polls = poll_table(ncp)
    weight, load = M.long_range_weight(2028, date, tl, polls, fixed, others=2) if D is not None else (0.0, 0.0)
    S = F.mix([E, A, D], [1, 1, weight]); open_ = approval_open(d_out, june is not None)
    drift = float(np.sqrt(open_) * (dE + dA) / (2 + weight))                       # approval moves both parts together, so the two are added
    extra = {s['abbr'].replace('-', ''): s['demShare'] for s in ncm['states']}; extra['US'] = float(ncm['summary']['demPopular'])
    allp = pd.concat([polls[polls.state == 'US'], state_poll_table(sp)], ignore_index=True)
    out, info = M.forecast(2028, date, allp, res, M.error_tables(2028, res, errs), (S, drift), market=now['market_dem'], extra_prior=extra, ev=M.ev_table(2024, res), timeline=tl,
                           pairing_spread=pairing_spread(ncp), prior_poll_load=load, turnout=turnout() if with_turnout else None, keep=keep)
    return out, info, {'prior': S, 'drift': drift, 'approval_equation': A, 'approval_and_economy': E, 'long_range': D, 'long_range_weight': weight, 'prior_moves_with_polls': load, 'approval_open': open_,
                       'june_approval': june, 'net_approval': net, 'timeline': tl, 'dE': dE, 'dA': dA}


def market_block(out, path='data/markets.json'):
    """Prediction markets beside the forecast: what each provider says, their average by quality for each place, and what the
    official simulated elections give when they are weighted toward the markets (markets.informed). The official figures
    are not touched; this block is for comparison and for the record."""
    import markets as MK
    if not os.path.exists(path) or not out.get('sims'): return None
    R = json.load(open(path)); C = R.get('combined') or {}; sims = out['sims']
    nat = {k: v for k, v in C.items() if k.endswith(':US')}; st = {k: v for k, v in C.items() if not k.endswith(':US')}
    brief = lambda x: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items() if k not in ('moved', 'states')}
    ways = {'national and state markets': (C, 0.5), 'national markets only': (nat, 0.5), 'state markets only': (st, 0.5), 'national and state markets, at half strength': (C, 0.25)}
    got = {name: MK.informed(sims, t, strength=s) for name, (t, s) in ways.items()}; main = got['national and state markets']
    return {'read': R.get('read'), 'counts': R.get('counts'), 'failed': R.get('failed'),
            'places': {k.split(':')[1]: {'p': v.get('p'), 'quality': v.get('quality'), 'real_money': v.get('real_money'), 'providers': v.get('providers'), 'thin': v.get('thin')} for k, v in C.items() if k.startswith('winner:')},
            'popular_vote': C.get('popular:US'), 'election_betting_odds': (C.get('winner:US') or {}).get('election_betting_odds'),
            'other': [{k: c.get(k) for k in ('provider', 'kind', 'place', 'title', 'url', 'answers', 'traders', 'volume', 'real_money')} for c in R.get('contracts') or [] if c.get('kind') in ('nomination', 'margin', 'electoral_votes')],
            'informed': dict(brief(main), states=main['states'], moved=main['moved']), 'other_ways': {k: brief(v) for k, v in got.items() if k != 'national and state markets'},
            'official': {'p_dem': out['p_dem'], 'p_rep': out['p_rep'], 'p_tie': out['p_tie']}}


def chance(now, ncp, ncm, sp, date, res, errs, t):
    """The chance of a Democratic win for one set of inputs: used to split a change between them. Every call draws the same
    simulated errors (the seed is fixed), so two calls differ only by what was changed between them."""
    return official(now, ncp, ncm, sp, res, errs, t, date, with_turnout=False)[0]['p_model']

PARTS = [('polls', 'National polls'), ('state_polls', 'State polls'), ('approval', 'Presidential approval'), ('models', "Tipping Point's models"), ('time', 'Time until the election')]

def change(NOW, nc, res, errs, t, today_p, since=None):
    """What moved the simulations' chance since an earlier day's inputs (by default the previous day's: data/prev_inputs.json,
    data/prev_nowcast.js). Each part is credited with its average effect over every order in which the parts could have
    been changed, so the split does not depend on an order and the parts add up to the whole. Parts that did not change are
    left out of the sum: they are zero by construction. What is left over after the parts (an input outside these five) is
    reported as such and not given a name it has not earned."""
    from itertools import combinations
    from math import factorial
    try:
        old, onc = since or (json.load(open('data/prev_inputs.json')), nowcast(prev=True))
    except FileNotFoundError:
        return None
    if old['as_of'] >= NOW['as_of']: return None
    sp_new = state_poll_file()
    try: sp_old = json.load(open('data/prev_state_polls.json'))
    except FileNotFoundError: sp_old = sp_new
    sig = lambda x: sorted([p.get('pollster'), p.get('date'), p.get('d'), p.get('r'), round(float(p['share']), 2)] for p in x['h2h']['polls'])
    mod = lambda x: [[round(float(v['demPopular']), 3) for v in x['models'].values() if isinstance(v, dict) and v.get('demPopular') is not None], [round(s['demShare'], 3) for s in x['states']]]
    moved = {'polls': sig(onc) != sig(nc), 'state_polls': sp_old.get('polls') != sp_new.get('polls'), 'approval': old['net_approval'] != NOW['net_approval'], 'models': mod(onc) != mod(nc), 'time': True}
    live = [k for k, _ in PARTS if moved[k]]; memo = {}
    def value(on):
        key = frozenset(on)
        if key not in memo:
            now = dict(old)
            if 'approval' in on: now['net_approval'] = NOW['net_approval']
            memo[key] = chance(now, nc if 'polls' in on else onc, nc if 'models' in on else onc, sp_new if 'state_polls' in on else sp_old, NOW['as_of'] if 'time' in on else old['as_of'], res, errs, t)
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
            'approval': [old['net_approval'], NOW['net_approval']], 'state_polls': [len(sp_old.get('polls') or []), len(sp_new.get('polls') or [])], 'market': [round(old['market_dem'], 4), round(NOW['market_dem'], 4)],
            'polls': [len(onc['h2h']['polls']), len(nc['h2h']['polls'])], 'days': [(pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(old['as_of'])).days, (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(NOW['as_of'])).days]}

def main():
    NOW = inputs(); TODAY = NOW['as_of']
    res = pd.read_csv('data/results.csv'); errs = pd.read_csv('data/average_errors.csv'); t = F.table(); nc = nowcast()
    polls = poll_table(nc); sp = state_poll_file(); tables = M.error_tables(2028, res, errs); ev = M.ev_table(2024, res)
    out, info, meta = official(NOW, nc, nc, sp, res, errs, t, TODAY, keep=True); tl = meta['timeline']
    MARKETS = market_block(out); out.pop('sims', None)
    fd, sd, open_ = meta['prior'], meta['drift'], meta['approval_open']
    # how the range should narrow: the same rule at other distances from the election. The error of the mix of polls and prior
    # comes from the record at each distance; what approval may still move by runs down as June 2028 approaches
    d0 = (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days; funnel = []
    for d in [d0, 600, 500, 400, 300, 200, 150, 100, 60, 30, 14, 7, 1]:
        left = approval_open(d, d <= DRIFT_TO) if d < d0 else open_
        sn = float(np.sqrt(M.at(tl['mix_error'], d) ** 2 + left * ((1 - float(M.curve(tl['national'], d))) * (meta['dE'] + meta['dA']) / (2 + (1.0 if d < 365 else meta['long_range_weight']))) ** 2))
        funnel.append({'days': d, 'half': round(2 * 1.2816 * sn, 2), 'poll_share': round(float(info['poll_share']) if d == d0 else float(M.curve(tl['national'], d)), 3)})
    lo = lambda q: np.log(q / (1 - q))
    msens = [{'weight': w, 'p': round(float(1 / (1 + np.exp(-((1 - w) * lo(out['p_model']) + w * lo(NOW['market_dem']))))), 3)} for w in (0, 0.25, 0.5, 0.7, 1.0)]
    # the national vote of each simulated election, added up from that election's own states by the votes each cast in 2024:
    # the chance of winning the most votes, and of the vote and the Electoral College disagreeing, are counted from that
    ns = out['national_from_states']
    if ns: out.update(p_popular_national=out['p_popular'], p_popular=ns['p_popular'], p_vote_not_college=ns['p_vote_not_college'], p_college_not_vote=ns['p_college_not_vote'])
    r = res.set_index(['year', 'state']); extra = {s['abbr'].replace('-', ''): s['demShare'] for s in nc['states']}
    cand = candidate(NOW, nc, polls, sp, res, errs, t, tables, ev, TODAY)
    share = lambda q: round(100 * q['dem_pct'] / (q['dem_pct'] + q['rep_pct']), 1) if q.get('dem_pct') and q.get('rep_pct') else None
    S = out['states']; names = {s['abbr'].replace('-', ''): s.get('name', s['abbr']) for s in nc['states']}
    tip = S.state[S.tip.idxmax()]                       # the state that most often carries the winner past 270
    J = {'as_of': TODAY, 'days_out': (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days, 'p_dem': out['p_dem'], 'p_model': out['p_model'], 'market': NOW['market_dem'],
         'p_rep': out['p_rep'], 'p_popular': out['p_popular'], 'p_tie': out['p_tie'], 'paths': out['paths'], 'national_from_states': out['national_from_states'], 'approval_open': open_, 'june_approval': meta['june_approval'], 'p_vote_not_college': out['p_vote_not_college'], 'p_college_not_vote': out['p_college_not_vote'], 'national': out['national'], 'national_sd': out['national_sd'], 'ev_mean': out['ev_mean'], 'ev_median': out['ev_median'], 'ev_lo': out['ev_lo'], 'ev_hi': out['ev_hi'],
         'ev_dist': [round(float(x), 5) for x in out['ev_dist']], 'tipping_point': tip,
         'inputs': {'national_polls': info['national_polls'], 'polls_n': int(len(polls)), 'poll_share': info['poll_share'], 'fundamentals': fd, 'fundamentals_sd': sd, 'approval_model': meta['approval_equation'], 'approval_and_economy': meta['approval_and_economy'], 'long_range': meta['long_range'], 'long_range_weight': meta['long_range_weight'], 'poll_share_record': info.get('poll_share_record'),
                    'net_approval': NOW['net_approval'], 'market_note': NOW['market_note'], 'keys': NOW['keys'], 'nowcast_p_dem': nc['summary']['pDemWin'], 'nowcast_national': nc['summary']['demPopular'], 'nowcast_as_of': nc['as_of']},
         'national_lo': out['national_lo'], 'national_hi': out['national_hi'],
         'states': [{'state': q['state'], 'ev': int(q['ev']), 'mean': round(float(q['mean']), 2), 'sd': round(float(np.sqrt(q['sd'] ** 2 + out['national_sd'] ** 2)), 2), 'lo': round(float(q['lo']), 2), 'hi': round(float(q['hi']), 2), 'p_dem': round(float(q['p_dem']), 4), 'tip': round(float(q['tip']), 4), 'prior': round(float(q['prior']), 2), 'lean': round(float(M.lean(res, 2028, q['state'])), 2), 'r2024': round(float(r.dem2[(2024, q['state'])]), 2), 'r2020': round(float(r.dem2[(2020, q['state'])]), 2), 'nowcast': round(float(extra[q['state']]), 1)} for _, q in S.iterrows()],
         'change': change(NOW, nc, res, errs, t, out['p_dem']), 'state_polls': int((polls.state != 'US').sum()),
         # every general-election poll of a single state that the sources hold, counted or not (polls.py). The published forecast
         # does not count state polls yet; the candidate does, under its ceiling.
         'state_poll_list': [{'state': q['place'], 'pollster': q['pollster'], 'end': q['end'], 'dem': share(q), 'pairing': f"{q['dem']} v {q['rep']}" if q.get('dem') and q.get('rep') else None,
                              'usable': bool(q['usable']), 'why': q['why_not'], 'url': q['url'] if str(q.get('url') or '').startswith(('https://', 'http://')) else None} for q in sp.get('state_questions', []) if q.get('place') and share(q) is not None],
         # every national head-to-head poll the average is made from, as Tipping Point's Nowcast lists them
         'national_poll_list': [{'pollster': q.get('pollster'), 'end': q.get('date'), 'dem': q.get('share'), 'pairing': f"{q.get('d')} v {q.get('r')}", 'added': q.get('added'),
                                 'url': q['url'] if str(q.get('url') or '').startswith(('https://', 'http://')) else None} for q in nc['h2h']['polls']],
         'nominees_known': nominees(nc) is not None,
         'state_poll_sources': {'found': sp.get('found', {}), 'answered': {k: bool(v.get('answered')) for k, v in sp.get('sources', {}).items()}, 'fetched': sp.get('fetched')},
         'candidate': cand,
         'funnel': funnel, 'markets': MARKETS, 'equation_error': tl['prior_error'],
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
           'hybrid_p_dem': round(cand['hybrid']['p_dem'], 4), 'hybrid_national': round(cand['hybrid']['national'], 2),
           'recommended_p_dem': round(cand['recommended']['p_dem'], 4), 'recommended_national': round(cand['recommended']['national'], 2),
           'markets_p_dem': ((MARKETS or {}).get('places') or {}).get('US', {}).get('p'), 'market_informed_p_dem': round(MARKETS['informed']['p_dem'], 4) if MARKETS else None}
    try:
        h = pd.read_csv(HISTORY); h = h[h.date != TODAY]
    except FileNotFoundError:
        h = pd.DataFrame()
    pd.concat([h, pd.DataFrame([row])]).sort_values('date').to_csv(HISTORY, index=False)
    quiet = ('ev_dist', 'states', 'settings', 'inputs', 'state_poll_list', 'state_poll_sources', 'candidate', 'funnel', 'markets', 'market_sensitivity')
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J.items() if k not in quiet}); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J['inputs'].items()})
    print('under review:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cand.items() if k not in ('states', 'settings', 'parts', 'hybrid', 'keys_vote', 'recommended')}, {k: round(v, 2) for k, v in cand['parts'].items() if v is not None})
    rc = cand['recommended']; print('recommended:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in rc.items() if k not in ('states', 'settings', 'parts')}, {k: round(v, 2) for k, v in rc['parts'].items() if v is not None})
    hy = cand['hybrid']; print('hybrid:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in hy.items() if k not in ('states', 'settings', 'parts')}, {k: round(v, 2) for k, v in hy['parts'].items() if v is not None}); print('keys vote:', cand['keys_vote'])
    f = sp.get('found', {}); print(f"state polls: {f.get('state_polls', 0)} found in {f.get('states_polled', [])}, {f.get('usable_state_polls', 0)} meet the rules")
    print(S.assign(lead=(S['mean'] - 50).abs()).sort_values('lead').head(12)[['state', 'ev', 'mean', 'p_dem']].round(3).to_string(index=False))

if __name__ == '__main__':
    main()
