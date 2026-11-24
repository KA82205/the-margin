"""The 2028 forecast as it stands today. Writes data/forecast_2028.json."""
import json, re, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F

HISTORY = 'data/history.csv'

def inputs():
    """Today's inputs (data/inputs.json). update.py refreshes the date and approval every day; the market price and the
    Fifty-Two Keys figures are entered by hand, with the date they were read."""
    return json.load(open('data/inputs.json'))

def nowcast():
    s = open('data/nowcast.js').read()
    return json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', s).group(1))

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
    return {'from': old['as_of'], 'p_prev': round(p0, 4), 'p': round(today_p, 4),
            'parts': [{'name': 'New polling', 'd': round(p1 - p0, 4)}, {'name': 'Presidential approval', 'd': round(p2 - p1, 4)}, {'name': 'Betting markets', 'd': round(p3 - p2, 4)}, {'name': 'State models and the calendar', 'd': round(today_p - p3, 4)}],
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
    S = out['states']; names = {s['abbr'].replace('-', ''): s.get('name', s['abbr']) for s in nc['states']}
    order = S.sort_values('mean', ascending=False); cum = order.ev.cumsum(); tip = order.state[cum >= 270].iloc[0]
    J = {'as_of': TODAY, 'days_out': (pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(TODAY)).days, 'p_dem': out['p_dem'], 'p_model': out['p_model'], 'market': NOW['market_dem'],
         'p_without_extras': plain['p_dem'], 'p_popular': out['p_popular'], 'national': out['national'], 'national_sd': out['national_sd'], 'ev_mean': out['ev_mean'], 'ev_median': out['ev_median'], 'ev_lo': out['ev_lo'], 'ev_hi': out['ev_hi'],
         'ev_dist': [round(float(x), 5) for x in out['ev_dist']], 'tipping_point': tip,
         'inputs': {'national_polls': info['national_polls'], 'polls_n': int(len(polls)), 'poll_share': info['poll_share'], 'fundamentals': fd, 'fundamentals_sd': sd, 'approval_model': parts['approval_model'], 'keys_model': parts['keys_model'],
                    'net_approval': NOW['net_approval'], 'market_note': NOW['market_note'], 'keys': NOW['keys'], 'nowcast_p_dem': nc['summary']['pDemWin'], 'nowcast_national': nc['summary']['demPopular'], 'nowcast_as_of': nc['as_of']},
         'states': [{'state': q['state'], 'ev': int(q['ev']), 'mean': round(float(q['mean']), 2), 'sd': round(float(np.sqrt(q['sd'] ** 2 + out['national_sd'] ** 2)), 2), 'p_dem': round(float(q['p_dem']), 4), 'prior': round(float(q['prior']), 2), 'lean': round(float(M.lean(res, 2028, q['state'])), 2), 'r2024': round(float(r.dem2[(2024, q['state'])]), 1), 'r2020': round(float(r.dem2[(2020, q['state'])]), 1), 'nowcast': round(float(extra[q['state']]), 1)} for _, q in S.iterrows()],
         'change': change(NOW, nc, res, errs, t, out['p_dem']), 'state_polls': int((polls.state != 'US').sum()),
         'funnel': funnel, 'market_sensitivity': msens, 'equation_error': fsd,
         'settings': {k: v for k, v in M.SET.items()}}
    json.dump(J, open('data/forecast_2028.json', 'w'), indent=1)
    # the day-by-day record: one row a day, today's row replaced if the forecast is run again
    row = {'date': TODAY, 'p_dem': round(J['p_dem'], 4), 'p_model': round(J['p_model'], 4), 'market': round(J['market'], 4), 'national': round(J['national'], 2), 'ev_median': int(J['ev_median']),
           'national_polls': round(J['inputs']['national_polls'], 2), 'polls_n': J['inputs']['polls_n'], 'net_approval': NOW['net_approval']}
    try:
        h = pd.read_csv(HISTORY); h = h[h.date != TODAY]
    except FileNotFoundError:
        h = pd.DataFrame()
    pd.concat([h, pd.DataFrame([row])]).sort_values('date').to_csv(HISTORY, index=False)
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J.items() if k not in ('ev_dist', 'states', 'settings', 'inputs')}); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in J['inputs'].items()})
    print(S.assign(lead=(S['mean'] - 50).abs()).sort_values('lead').head(12)[['state', 'ev', 'mean', 'p_dem']].round(3).to_string(index=False))

if __name__ == '__main__':
    main()
