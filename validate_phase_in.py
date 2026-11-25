"""Does the phase-in of polls do what it should? Writes data/phase_in.json.

Three tests, all on forecasts made only from what existed on the day.

  A  The usual distances (120 days to the last day) and three longer ones (250, 200, 150), 2008-2024: the published
     forecast, the candidate, and the candidate with one piece changed at a time.
  B  Far from the election (300 to 650 days out), on the only elections with early polls on file: 2016, 2020 and 2024.
     For the country: the published rule, and the candidate with the long-range model as it would have been run on the
     day, which reads the same early polls. For the states that had early polls: the starting point alone, the published
     rule (polls against a starting point worth 1.5 polls, whatever the distance) and the candidate rule (the same under
     a ceiling that falls with distance).
  C  A stress test: a state flooded with early polls that are all five points off. How far does each rule follow them?

What B cannot show: the early polls on file are of the two people who went on to be nominated (for 2024, of Biden and
Trump). Nobody knew that at the time, so real early polls, spread over pairings that never happened, are worse than these.
The approval model and the Fifty-Two Keys count are each year's final ones, which did not exist that early either. The
long-range model is rebuilt for the day by an approximation (early_long_range below).

    python validate_phase_in.py          all three (about a quarter of an hour)
    python validate_phase_in.py far      test B only
"""
import json
import numpy as np, pandas as pd
import model as M, fundamentals as F, backtest as B, timeline as T

res, polls, errs = B.load(); t = F.table()
NEAR = [250, 200, 150] + B.DAYS
FAR = [650, 600, 550, 500, 450, 400, 350, 300]
VARIANTS = {
    'published': {},
    'candidate': M.CANDIDATE,
    'candidate, polls by the published rule': dict(M.CANDIDATE, poll_weight='precision', state_poll_weight='volume'),
    'candidate, published national prior': dict(M.CANDIDATE, national_prior='fundamentals'),
    'candidate, state models as published': dict(M.CANDIDATE, state_model_mode='share'),
    'candidate, approval equation as a fourth model': dict(M.CANDIDATE, national_prior='four_models'),
}


def near():
    out = {}
    for name, sets in VARIANTS.items():
        old_v = dict(B.VERSIONS); B.VERSIONS['x'] = sets
        R = B.run(days=NEAR, version='x'); B.VERSIONS.clear(); B.VERSIONS.update(old_v)
        g = R.groupby('days')
        out[name] = {int(d): {'national': round(float(2 * x.national_error.abs().mean()), 2), 'state': round(float(2 * x.state_mae.mean()), 2), 'called': int(x.states_called.sum()),
                              'favored': int(x.called.sum()), 'p_winner': round(float(x.p_winner.mean()), 3), 'brier': round(float(x.brier.mean()), 4), 'cover80': round(float(x.cover80.mean()), 3),
                              'poll_share': round(float(x.poll_share.mean()), 3), 'by_year': {int(y): round(float(2 * e), 2) for y, e in zip(x.year, x.national_error)}} for d, x in g}
    return out


def early_long_range(y, asof, final):
    """The long-range model's national figure as it would have been run on the day. The forecast on record uses the polls
    of the October before the election year, fixed on November 7. Before then a run of it reads the polls of the day (the
    Tipping Point Nowcast takes the last 180 days), so the forecast on record is moved by 0.52 x (the polls of the day -
    the October polls). An approximation: the polls are the ones in data/polls.csv, averaged plainly, and 0.52 is used for
    every year."""
    nat = polls[(polls.year == y) & (polls.state == 'US')]
    if asof >= pd.Timestamp(f'{y - 1}{M.LONG_RANGE_FIXED}'): return final
    october = nat[(nat.end >= f'{y - 1}-10-01') & (nat.end <= f'{y - 1}-10-31')].dem2.mean()
    day = nat[(nat.end <= asof) & (nat.end > asof - pd.Timedelta(days=180))].dem2.mean()
    return final + M.LONG_RANGE_POLLS * (day - october)


def far():
    """Early polls of 2016, 2020 and 2024. Before the long-range model's own polls existed the candidate is run four ways,
    to show what each treatment of that model does with early polls:
        candidate    the model left out until its own polls exist; until then the prior is the other two models and polls
                     get the weight the record gives them
        in part      the model as run on the day, counted for part of its third (model.long_range_weight, 'part')
        in full      the model as run on the day, counted for its whole third, as the Nowcast shows it
        hindsight    the model as it finally stood, built on polls that had not yet been taken
    In the middle two the polls are counted once: the average gets only what the model does not already carry."""
    rows = []
    def candidate(y, asof, tl, E, D, K, before, **kw):
        old = dict(M.SET); M.SET.update(M.CANDIDATE, long_range_before=before)
        try:
            weight, load = M.long_range_weight(y, asof, tl, polls)
            out, info = M.forecast(y, asof, polls, fund=(F.three_models(E, D, K, weight), 0.0), timeline=tl, pairing_spread=None, prior_poll_load=load, **kw)
        finally:
            M.SET.clear(); M.SET.update(old)
        return out, info, weight
    for y in (2016, 2020, 2024):
        tables = M.error_tables(y, res, errs); fd, fsd, parts = F.forecast(y, t); ev = M.ev_table(y, res); extra, two = B.state_models(y); tl = T.curves(y)
        r = res[res.year == y].set_index('state'); act_nat = float(r.nat2.iloc[0]); E, D, K = two['US'][0], two['US'][1], parts['keys_model']
        kw = dict(res=res, tables=tables, ev=ev, extra_prior=extra)
        for d in FAR:
            asof = pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=d)
            if M.Polls(polls, y).national(asof)[0] is None: continue
            Dd = early_long_range(y, asof, D); live = asof < pd.Timestamp(f'{y - 1}{M.LONG_RANGE_FIXED}')
            got = {'published': M.forecast(y, asof, polls, res, tables, (fd, fsd), ev=ev, extra_prior=extra) + (None,),
                   'candidate': candidate(y, asof, tl, E, Dd, K, 'out', **kw), 'in_part': candidate(y, asof, tl, E, Dd, K, 'part', **kw), 'in_full': candidate(y, asof, tl, E, Dd, K, 'full', **kw)}
            old = dict(M.SET); M.SET.update(M.CANDIDATE)
            got['hindsight'] = M.forecast(y, asof, polls, fund=(F.three_models(E, D, K), 0.0), timeline=tl, **kw) + (1.0,)
            M.SET.clear(); M.SET.update(old)
            pn = got['published'][1]['national_polls']
            row = {'year': y, 'days': d, 'polls': round(2 * (pn - act_nat), 2), 'fundamentals': round(2 * (fd - act_nat), 2), 'long_range_live': bool(live), 'part': round(got['in_part'][2], 3)}
            for name, (out, info, _) in got.items():          # total: everything that moves with the polls of the day, the average itself and the long-range model's part of the prior
                row[name] = {'miss': round(2 * (out['national'] - act_nat), 2), 'prior': round(2 * (info['fundamentals'] - act_nat), 2), 'direct': round(info['poll_share'], 3), 'total': round(info['poll_share_total'], 3)}
            # the states that had polls on the day, against the nation: what the polls said, the starting point, and each rule's blend
            for name in ('published', 'candidate'):
                St = got[name][0]['states'].set_index('state'); St = St[(St.index.str.len() == 2) & St.poll.notna()]
                nat = got[name][0]['national']; a = (r.dem2.reindex(St.index) - act_nat)
                row[f'{name}_states'] = {'n': int(len(St)), 'share': round(float(St.poll_share.mean()), 3), 'max_share': round(float(St.poll_share.max()), 3),
                                         'start': round(float((2 * (St.prior - nat - a)).abs().mean()), 2), 'polls': round(float((2 * (St.poll - nat - a)).abs().mean()), 2),
                                         'blend': round(float((2 * (St['mean'] - nat - a)).abs().mean()), 2)}
            rows.append(row)
    live = [r for r in rows if r['long_range_live']]; names = ('published', 'candidate', 'in_part', 'in_full', 'hindsight')
    mean = lambda rs: {k: round(float(np.mean([abs(r[k]['miss']) for r in rs])), 2) for k in names}
    return {'rows': rows, 'before_its_polls_existed': {'dates': len(live), 'all': mean(live), 'by_year': {y: dict(mean([r for r in live if r['year'] == y]), dates=len([r for r in live if r['year'] == y])) for y in (2016, 2020, 2024)}}}


def flood():
    """A state with ten fresh polls, all five points of share too Democratic, at several distances: where each rule puts it."""
    out = []
    y = 2024; tables = M.error_tables(y, res, errs); fd, fsd, parts = F.forecast(y, t); ev = M.ev_table(y, res); extra, two = B.state_models(y); tl = T.curves(y)
    S = F.three_models(two['US'][0], two['US'][1], parts['keys_model']); r = res[res.year == y].set_index('state')
    for d in (700, 500, 365, 250, 120, 30, 7):
        asof = pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=d)
        fake = pd.DataFrame([{'year': y, 'state': 'PA', 'pollster': f'Made-up poll {i}', 'end': asof - pd.Timedelta(days=2 + i), 'n': 800, 'pop': 'lv', 'dem2': float(r.dem2['PA']) + 5.0} for i in range(10)])
        nat_only = polls[(polls.year == y) & (polls.state == 'US')]
        row = {'days': d}
        for name, sets, fund in (('published', {}, (fd, fsd)), ('candidate', M.CANDIDATE, (S, 0.0))):
            old = dict(M.SET); M.SET.update(sets)
            base, _ = M.forecast(y, asof, nat_only, res, tables, fund, ev=ev, extra_prior=extra, timeline=tl)
            out_, _ = M.forecast(y, asof, pd.concat([nat_only, fake]), res, tables, fund, ev=ev, extra_prior=extra, timeline=tl)
            out_u, _ = M.forecast(y, asof, pd.concat([nat_only, fake]), res, tables, fund, ev=ev, extra_prior=extra, timeline=tl, pairing_spread=3.0)
            M.SET.clear(); M.SET.update(old)
            b, f, u = (o['states'].set_index('state').loc['PA'] for o in (base, out_, out_u))
            row[name] = {'share': round(float(f.poll_share), 3), 'moved': round(float(2 * (f['mean'] - b['mean'])), 2), 'share_unsure': round(float(u.poll_share), 3), 'moved_unsure': round(float(2 * (u['mean'] - b['mean'])), 2)}
        out.append(row)
    return out


if __name__ == '__main__':
    import sys
    c = T.curves(2028)
    if 'far' in sys.argv:                         # only the far-out test again; the rest is kept as it was last written
        out = json.load(open('data/phase_in.json')); out['far'] = far()
        out['near'] = {k: {int(d): x for d, x in v_.items()} for k, v_ in out['near'].items()}
    else:
        out = {'curves': {y: {k: T.curves(y)[k] for k in ('national', 'state', 'elections', 'state_elections')} for y in (2008, 2012, 2016, 2020, 2024, 2028)},
               'weights': {'national': {d: round(float(M.curve(c['national'], d)), 3) for d in (1, 7, 14, 30, 60, 90, 120, 150, 200, 250, 300, 365, 500, 600, 715)},
                           'state_ceiling': {d: round(float(M.curve(c['state'], d) / M.curve(c['state'], 1)), 3) for d in (1, 7, 14, 30, 60, 90, 120, 150, 200, 250, 300, 365, 500, 600, 715)}},
               'record': {'national': c['raw'], 'state': c['raw_state'], 'mix_error': c['mix_error'], 'prior_error': round(c['prior_error'], 2)},
               'near': near(), 'far': far(), 'flood': flood()}
    json.dump(out, open('data/phase_in.json', 'w'), indent=1)
    print('weights 2028:', out['weights'])
    print('\nA. misses in points of margin; calls of 280; five elections')
    for name, v in out['near'].items():
        print(f'  {name}')
        print('     days:     ' + ' '.join(f'{d:>6d}' for d in NEAR))
        for k in ('national', 'state', 'called', 'favored', 'p_winner', 'brier', 'cover80', 'poll_share'):
            print(f'     {k:9s} ' + ' '.join(f'{v[d][k]:>6}' for d in NEAR))
    print('\nB. far out. National miss in points of margin (+ = too Democratic), and in brackets how much of the national number moves with the polls of the day')
    for r in out['far']['rows']:
        ps, cs = r['published_states'], r['candidate_states']; f = lambda k: f"{r[k]['miss']:+5.1f} ({r[k]['total']:.0%})"
        print(f"  {r['year']} {r['days']:3d}d  polls {r['polls']:+5.1f} | published {f('published')} | candidate {f('candidate')} | in part {f('in_part')} [{r['part']:.0%} of its third] | in full {f('in_full')} | hindsight {f('hindsight')}"
              f" || {ps['n']:2d} states: start {ps['start']:.1f}/{cs['start']:.1f} polls {ps['polls']:.1f} | published blend {ps['blend']:.1f} (polls {ps['share']:.0%}, max {ps['max_share']:.0%}) | candidate blend {cs['blend']:.1f} (polls {cs['share']:.0%}, max {cs['max_share']:.0%})")
    b = out['far']['before_its_polls_existed']
    print(f"  mean size of the national miss before the long-range model's own polls existed ({b['dates']} dates): " + ' | '.join(f'{k} {v}' for k, v in b['all'].items()))
    for y, v in b['by_year'].items(): print(f'    {y}: ' + ' | '.join(f'{k} {x}' for k, x in v.items()))
    print('\nC. ten made-up polls of Pennsylvania, all 10 points of margin too Democratic: share given to them, and how far the state moves (points of margin)')
    for r in out['flood']:
        print(f"  {r['days']:3d}d  published {r['published']['share']:.0%} -> {r['published']['moved']:+.1f} | candidate {r['candidate']['share']:.0%} -> {r['candidate']['moved']:+.1f} | candidate, nominees unknown {r['candidate']['share_unsure']:.0%} -> {r['candidate']['moved_unsure']:+.1f}")
