"""The 2028 forecast as it stands today. Writes data/forecast_2028.json."""
import json, re, sys
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

    def run(before):
        """The candidate with the long-range model treated, before its own polls exist, in one of the three ways."""
        old = dict(M.SET); M.SET.update(M.CANDIDATE, long_range_before=before)
        try:
            weight, load = M.long_range_weight(2028, today, tl, polls, fixed) if D is not None else (0.0, 0.0)
            S = F.three_models(E, D, K, weight) if D is not None else (E + K) / 2
            drift = float(np.sqrt(left) * (dE + dK) / ((2 + weight) if D is not None else 2))
            out, info = M.forecast(2028, today, allp, res, tables, (S, drift), market=NOW['market_dem'], extra_prior=extra, ev=ev, timeline=tl, pairing_spread=spread, prior_poll_load=load)
        finally:
            M.SET.clear(); M.SET.update(old)
        return out, info, S, drift, weight, load

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
            'other_ways': other, 'settings': dict(M.CANDIDATE)}

def poll_table(nc):
    """The Nowcast's head-to-head polls as the model's poll table. A poll that names a state is filed under that state."""
    names = {v['name']: k.replace('-', '') for k, v in json.load(open('data/results_2024.json')).items()}
    def where(p):
        s = str(p.get('state') or p.get('geo') or 'US').strip()
        return names.get(s, s.replace('-', '') if s.replace('-', '') in names.values() else 'US')
    return pd.DataFrame([{'year': 2028, 'state': where(p), 'pollster': p['pollster'], 'end': pd.Timestamp(p['date']), 'n': p.get('n') or 1000, 'pop': 'rv', 'dem2': p['share']} for p in nc['h2h']['polls']])

def chance(now, polls, states, date, res, errs, t, market=True):
    """The headline chance for one set of inputs: used to split a day's change between them."""
    base = dict(term1=1, deminc=0)
    fd, fsd, _ = F.forecast(2028, t, juneapp=now['net_approval'], keys=now['keys'], **base)
    up = F.forecast(2028, t, juneapp=now['net_approval'] + now['approval_drift'], keys=now['keys'], **base)[0]
    ku = F.forecast(2028, t, juneapp=now['net_approval'], keys=now['keys'] + now['keys_sd'], **base)[0]
    sd = float(np.sqrt(fsd ** 2 + (up - fd) ** 2 + (ku - fd) ** 2))
    extra = {s['abbr'].replace('-', ''): s['demShare'] for s in states}
    out, _ = M.forecast(2028, date, polls, res, M.error_tables(2028, res, errs), (fd, sd), market=now['market_dem'] if market else None, extra_prior=extra, ev=M.ev_table(2024, res))
    return out['p_dem']

def change(NOW, nc, res, errs, t, today_p):
    """What moved the chance since the previous day's inputs (data/prev_inputs.json, data/prev_nowcast.js): yesterday's
    inputs are replaced by today's one at a time, in the order polls, approval, markets, then everything else."""
    try:
        old = json.load(open('data/prev_inputs.json')); onc = json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', open('data/prev_nowcast.js').read()).group(1))
    except FileNotFoundError:
        return None
    if old['as_of'] >= NOW['as_of']: return None
    step = dict(old); p0 = chance(step, poll_table(onc), onc['states'], old['as_of'], res, errs, t)
    p1 = chance(step, poll_table(nc), onc['states'], old['as_of'], res, errs, t)
    step['net_approval'] = NOW['net_approval']; p2 = chance(step, poll_table(nc), onc['states'], old['as_of'], res, errs, t)
    step['market_dem'] = NOW['market_dem']; p3 = chance(step, poll_table(nc), onc['states'], old['as_of'], res, errs, t)
    step['keys'], step['keys_sd'] = NOW['keys'], NOW['keys_sd']; p4 = chance(step, poll_table(nc), onc['states'], old['as_of'], res, errs, t)
    return {'from': old['as_of'], 'p_prev': round(p0, 4), 'p': round(today_p, 4),
            'parts': [{'name': 'New polling', 'd': round(p1 - p0, 4)}, {'name': 'Presidential approval', 'd': round(p2 - p1, 4)}, {'name': 'Betting markets', 'd': round(p3 - p2, 4)}, {'name': 'Fifty-Two Keys', 'd': round(p4 - p3, 4)}, {'name': 'State models and the calendar', 'd': round(today_p - p4, 4)}],
            'keys': [old['keys'], NOW['keys']],
            'approval': [old['net_approval'], NOW['net_approval']], 'market': [round(old['market_dem'], 4), round(NOW['market_dem'], 4)], 'polls': [len(onc['h2h']['polls']), len(nc['h2h']['polls'])]}

def main():
    NOW = inputs(); TODAY = NOW['as_of']
    res = pd.read_csv('data/results.csv'); errs = pd.read_csv('data/average_errors.csv'); t = F.table(); nc = nowcast()
    polls = poll_table(nc)
    base = dict(term1=1, deminc=0)
    fd, fsd, parts = F.forecast(2028, t, juneapp=NOW['net_approval'], keys=NOW['keys'], **base)
    up = F.forecast(2028, t, juneapp=NOW['net_approval'] + NOW['approval_drift'], keys=NOW['keys'], **base)[0]
    ku = F.forecast(2028, t, juneapp=NOW['net_approval'], keys=NOW['keys'] + NOW['keys_sd'], **base)[0]
    sd = float(np.sqrt(fsd ** 2 + (up - fd) ** 2 + (ku - fd) ** 2))      # the equations' own error, plus two years of drift in their inputs
    tables = M.error_tables(2028, res, errs)
    extra = {s['abbr'].replace('-', ''): s['demShare'] for s in nc['states']}
    ev = M.ev_table(2024, res)
    out, info = M.forecast(2028, TODAY, polls, res, tables, (fd, sd), market=NOW['market_dem'], extra_prior=extra, ev=ev)
    plain, _ = M.forecast(2028, TODAY, polls, res, tables, (fd, sd), ev=ev)                       # without the Nowcast's state forecasts or the market
    # how the range should narrow: the same formulas at other distances from the election, with the drift in the fundamentals' inputs shrinking to nothing by June 2028
    d0 = (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days; funnel = []
    for d in [d0, 600, 500, 400, 300, 200, 150, 100, 60, 30, 14, 7, 1]:
        k = max(d - 130, 0) / (d0 - 130); sf = float(np.sqrt(fsd ** 2 + k * ((up - fd) ** 2 + (ku - fd) ** 2))); sp = M.at(tables['nat'], d)
        w = sf ** 2 / (sf ** 2 + sp ** 2); sn = float(np.sqrt(w ** 2 * sp ** 2 + (1 - w) ** 2 * sf ** 2))
        funnel.append({'days': d, 'half': round(2 * 1.2816 * sn, 2), 'poll_share': round(w, 3)})
    lo = lambda q: np.log(q / (1 - q))
    msens = [{'weight': w, 'p': round(float(1 / (1 + np.exp(-((1 - w) * lo(out['p_model']) + w * lo(NOW['market_dem']))))), 3)} for w in (0, 0.25, 0.5, 0.7, 1.0)]
    r = res.set_index(['year', 'state'])
    sp = state_poll_file()
    cand = candidate(NOW, nc, polls, sp, res, errs, t, tables, ev, TODAY)
    share = lambda q: round(100 * q['dem_pct'] / (q['dem_pct'] + q['rep_pct']), 1) if q.get('dem_pct') and q.get('rep_pct') else None
    S = out['states']; names = {s['abbr'].replace('-', ''): s.get('name', s['abbr']) for s in nc['states']}
    tip = S.state[S.tip.idxmax()]                       # the state that most often carries the winner past 270
    J = {'as_of': TODAY, 'days_out': (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days, 'p_dem': out['p_dem'], 'p_model': out['p_model'], 'market': NOW['market_dem'],
         'p_without_extras': plain['p_dem'], 'p_popular': out['p_popular'], 'national': out['national'], 'national_sd': out['national_sd'], 'ev_mean': out['ev_mean'], 'ev_median': out['ev_median'], 'ev_lo': out['ev_lo'], 'ev_hi': out['ev_hi'],
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
         'settings': {k: v for k, v in M.SET.items()}}
    json.dump(J, open('data/forecast_2028.json', 'w'), indent=1)
    # the day-by-day record: one row a day, today's row replaced if the forecast is run again
    row = {'date': TODAY, 'p_dem': round(J['p_dem'], 4), 'p_model': round(J['p_model'], 4), 'market': round(J['market'], 4), 'national': round(J['national'], 2), 'ev_median': int(J['ev_median']),
           'national_polls': round(J['inputs']['national_polls'], 2), 'polls_n': J['inputs']['polls_n'], 'net_approval': NOW['net_approval'],
           'candidate_p_dem': round(cand['p_dem'], 4), 'candidate_national': round(cand['national'], 2)}
    try:
        h = pd.read_csv(HISTORY); h = h[h.date != TODAY]
    except FileNotFoundError:
        h = pd.DataFrame()
    pd.concat([h, pd.DataFrame([row])]).sort_values('date').to_csv(HISTORY, index=False)
    quiet = ('ev_dist', 'states', 'settings', 'inputs', 'state_poll_list', 'state_poll_sources', 'candidate', 'funnel', 'market_sensitivity')
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J.items() if k not in quiet}); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J['inputs'].items()})
    print('under review:', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in cand.items() if k not in ('states', 'settings', 'parts')}, {k: round(v, 2) for k, v in cand['parts'].items() if v is not None})
    f = sp.get('found', {}); print(f"state polls: {f.get('state_polls', 0)} found in {f.get('states_polled', [])}, {f.get('usable_state_polls', 0)} meet the rules")
    print(S.assign(lead=(S['mean'] - 50).abs()).sort_values('lead').head(12)[['state', 'ev', 'mean', 'p_dem']].round(3).to_string(index=False))

if __name__ == '__main__':
    main()
