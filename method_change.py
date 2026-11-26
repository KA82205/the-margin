"""Where the change of November 25, 2026 came from. Writes data/method_change.json.

That day the published chance of a Democratic win went from about 60% to about 70%. Nothing had happened in the race: the
method had changed, in four ways at once. This script runs the forecast on the inputs of that day with each of the four
switched on and off in every combination (sixteen forecasts, all on the same random draws), and credits each change with its
average effect over every order in which the four could have been made. The parts then add up to the whole, and no part
depends on the order chosen. Where two changes work on each other, each gets half of what they do together.

    polls      early polls counted for what the record says polls at this distance are worth (3%), in place of a weight set by
               the sizes of the two errors (24%); state polls under a ceiling
    Enns       Tipping Point's approval-and-economy model added to the national starting point
    Keys       the Fifty-Two Keys line taken out of the national starting point
    centring   Tipping Point's state models used for where they place each state against their own national figure, not for
               their forecast of the state as it stands

A second, smaller change the same evening is split the same way: the approval allowance (10 to 15 points, counted by the
structural models' share) and the size of each state's error (the last five elections, state by state).

    python method_change.py
"""
import itertools, json, math
import numpy as np, pandas as pd
import model as M, fundamentals as F, run_2028 as R

DAY = '2026-11-25'
SWITCHES = ['polls', 'Enns', 'Keys', 'centring']


def setup():
    nc = R.nowcast() if hasattr(R, 'nowcast') else None
    return nc


def chance(on, inp, nc, sp, res, errs, t, allowance=10.0, lean_error='all', weigh_allowance=False):
    """The Democratic chance with the switches in `on` set to the new method and the rest to the old."""
    import timeline as T
    tl = T.curves(2028); base = dict(term1=1, deminc=0); d_out = max((pd.Timestamp(M.ELECTION[2028]) - pd.Timestamp(DAY)).days, 1)
    km = inp.get('keys_mean', inp['keys']); net = inp['net_approval']
    line = lambda k: F.forecast(2028, t, juneapp=net, keys=k, **base)[2]['keys_model']
    fd, fsd, parts = F.forecast(2028, t, juneapp=net, keys=km, **base); A, K = parts['approval_model'], line(km); E = float(nc['models']['enns']['demPopular'])
    dA = abs(F.forecast(2028, t, juneapp=net + allowance, keys=km, **base)[2]['approval_model'] - A); dK = abs(line(km + inp['keys_sd']) - K); dE = R.APPROVAL_RESPONSE * allowance / 2
    use = [(A, dA)] + ([(K, dK)] if 'Keys' not in on else []) + ([(E, dE)] if 'Enns' in on else [])
    S = float(np.mean([v for v, _ in use])); drift = float(sum(d for _, d in use) / len(use))                 # approval moves every part together, so their moves are added
    new_polls = 'polls' in on
    keep = dict(M.SET); real = M.forecast
    M.SET.update(poll_weight='timeline' if new_polls else 'precision', state_poll_weight='horizon' if new_polls else 'volume', state_model_mode='lean' if 'centring' in on else 'share', lean_error=lean_error)
    try:
        polls = R.poll_table(nc); allp = pd.concat([polls[polls.state == 'US'], R.state_poll_table(sp)], ignore_index=True)
        extra = {s['abbr'].replace('-', ''): s['demShare'] for s in nc['states']}; extra['US'] = float(nc['summary']['demPopular'])
        fund = (S, drift) if new_polls else (S, float(np.sqrt(fsd ** 2 + drift ** 2)))
        if new_polls and not weigh_allowance:                 # the method of that day added the allowance in full; it is weighted by the prior's share only from the later change
            w = M.discount(float(M.curve(tl['national'], d_out)), max(R.pairing_spread(nc), M.SET['pairing_spread_floor']), tl['prior_error']); fund = (S, drift / max(1e-9, 1 - w))
        out, info = M.forecast(2028, DAY, allp, res, M.error_tables(2028, res, errs), fund, extra_prior=extra, ev=M.ev_table(2024, res), timeline=tl, pairing_spread=R.pairing_spread(nc), turnout=R.turnout())
    finally:
        M.SET.clear(); M.SET.update(keep)
    return float(out['p_dem'])


def shapley(names, value):
    n = len(names); out = {k: 0.0 for k in names}
    for k in names:
        rest = [x for x in names if x != k]
        for r in range(n):
            for sub in itertools.combinations(rest, r):
                wgt = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                out[k] += wgt * (value[frozenset(sub) | {k}] - value[frozenset(sub)])
    return out


def main():
    import backtest as B, update as U
    res, _, errs = B.load(); t = F.table(); inp = json.load(open('data/inputs.json')); nc = U.parse(open('data/nowcast.js').read()); sp = R.state_poll_file()
    value = {frozenset(c): chance(set(c), inp, nc, sp, res, errs, t) for r in range(5) for c in itertools.combinations(SWITCHES, r)}
    old, new = value[frozenset()], value[frozenset(SWITCHES)]; parts = shapley(SWITCHES, value)
    alone = {k: value[frozenset([k])] - old for k in SWITCHES}; last = {k: new - value[frozenset(SWITCHES) - {k}] for k in SWITCHES}
    arch = json.load(open('docs/archive/index.json')); arch = arch if isinstance(arch, list) else arch.get('forecasts') or []
    kept = {a['file']: a['p_dem'] for a in arch if a['file'] in ('2026-11-25T2307Z.json', '2026-11-25T2314Z.json')}
    # the second change: the allowance and the size of a state's error
    v2 = {frozenset(c): chance(set(SWITCHES), inp, nc, sp, res, errs, t, allowance=15.0 if 'allowance' in c else 10.0, lean_error='recent' if 'state error' in c else 'all', weigh_allowance='allowance' in c)
          for r in range(3) for c in itertools.combinations(['allowance', 'state error'], r)}
    p2 = shapley(['allowance', 'state error'], v2)
    out = {'day': DAY, 'what': 'the Democratic chance on the inputs of the day, with each change of method switched on and off; every forecast on the same random draws',
           'before': round(old, 4), 'after': round(new, 4), 'change': round(new - old, 4), 'kept_that_day': kept,
           'parts': {k: round(v, 4) for k, v in parts.items()}, 'each_made_alone': {k: round(v, 4) for k, v in alone.items()}, 'each_made_last': {k: round(v, 4) for k, v in last.items()},
           'every_combination': {'+'.join(sorted(k)) or 'none': round(v, 4) for k, v in value.items()},
           'second_change': {'before': round(v2[frozenset()], 4), 'after': round(v2[frozenset(['allowance', 'state error'])], 4), 'parts': {k: round(v, 4) for k, v in p2.items()},
                             'what': 'the approval allowance from 10 to 15 points, counted by the structural models\' share; and each state\'s error sized from the last five elections, state by state'},
           'not_split': 'The headline was also taken off betting markets that day (62% to 60%): a change to what was shown, made before these four, and outside the simulation. The inputs are as they stood at the end of the day, so the first figure differs a little from the forecasts kept earlier in the day.'}
    json.dump(out, open('data/method_change.json', 'w'), indent=1)
    print(json.dumps({k: out[k] for k in ('before', 'after', 'change', 'kept_that_day', 'parts', 'each_made_alone', 'each_made_last', 'second_change')}, indent=1))


if __name__ == '__main__':
    main()
