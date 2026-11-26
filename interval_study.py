"""Are the prediction intervals the right width? Writes data/interval_study.json.

The published interval for a place is the 10th to the 90th of every hundred simulated results: an 80% prediction interval.
This script scores the intervals the method would have given for 2008 to 2024 at ten distances from the election.

    coverage      how often the result fell inside the 50%, 80%, 90% and 95% intervals, for states, the national vote and
                  the electoral votes; by distance and by election, and on which side the misses fell
    sharpness     the width of each interval
    both at once  the interval score (Gneiting and Raftery): the width, plus a penalty for a miss that grows with how far
                  outside the result fell and with how sure the interval claimed to be. The weighted interval score
                  averages it over the four levels and the middle. Lower is better; a narrow interval is rewarded only
                  if it still holds the result.
    alternatives  the same forecasts with the national error and the state error made smaller or larger, each scale chosen
                  on four elections and scored on the fifth. Fifty states in one election share that election's national
                  miss, so the unit is the election: five of them, not 250 states.
    by state      whether some states have been harder to place than others, tested forward in time with estimates pulled
                  toward the common size
    two years out the approval equation run with the approval reading of the midterm in place of June's, for every election
                  it can be fitted before: how far off it was, against what the forecast allows

    python interval_study.py
"""
import json, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F, backtest as B

DAYS = [250, 200, 150, 120, 90, 60, 30, 14, 7, 1]
SIMS = 12000


def capture(settings=None):
    """Every forecast of the back-test, as the inputs of its simulation: (year, days) -> (states, national, its error, electoral votes)."""
    kept = {}; real = M.simulate
    def spy(S, nat, s_nat, year, market=None, ev=None, turnout=None):
        kept['last'] = (S.copy(), nat, s_nat, year, ev); return real(S, nat, s_nat, year, market, ev, turnout)
    M.simulate = spy; keep = dict(M.SET); M.SET['sims'] = 2000; M.SET.update(settings or {}); out = {}
    try:
        res, polls, errs = B.load(); t = F.table(); import timeline as T
        for y in B.YEARS:
            tables = M.error_tables(y, res, errs); fd, fsd, parts = F.forecast(y, t); ev = M.ev_table(y, res); extra, two = B.state_models(y); tl = T.curves(y)
            E, D, A = two['US'][0], two['US'][1], parts['approval_model']
            for d in DAYS:
                asof = pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=d)
                weight, carried = M.long_range_weight(y, asof, tl, polls, others=2)
                M.forecast(y, asof, polls, res, tables, (F.mix([E, A, D], [1, 1, weight]), 0.0), ev=ev, extra_prior=extra, timeline=tl, prior_poll_load=carried)
                out[(y, d)] = kept['last']
    finally:
        M.simulate = real; M.SET.clear(); M.SET.update(keep)
    return out, res


def rows(inputs, res, national=1.0, state=1.0):
    """One row for each place, election and distance: the result and the simulated points."""
    old = M.SET['sims']; M.SET['sims'] = SIMS; M.STUDY.update(national=national, state=state); out = []
    try:
        for (y, d), (S, nat, s_nat, year, ev) in inputs.items():
            o = M.simulate(S, nat, s_nat, year, None, ev); r = res[res.year == y].set_index('state'); q = o['quantiles']
            for p in o['states'].itertuples():
                if len(p.state) == 2:
                    out.append({'year': y, 'days': d, 'place': p.state, 'actual': 2 * (float(r.dem2[p.state]) - 50), 'mid': 2 * (p.q50 - 50), 'sd': p.sd, 'poll_share': p.poll_share,
                                **{f'l{k}': 2 * (v - 50) for k, v in ((50, p.q25), (80, p.lo), (90, p.q05), (95, p.q025))}, **{f'u{k}': 2 * (v - 50) for k, v in ((50, p.q75), (80, p.hi), (90, p.q95), (95, p.q975))}})
            n = q['national']; out.append({'year': y, 'days': d, 'place': 'US', 'actual': 2 * (float(r.nat2.iloc[0]) - 50), 'mid': 2 * (n['50'] - 50),
                                           **{f'l{k}': 2 * (n[a] - 50) for k, a in ((50, '25'), (80, '10'), (90, '5'), (95, '2.5'))}, **{f'u{k}': 2 * (n[a] - 50) for k, a in ((50, '75'), (80, '90'), (90, '95'), (95, '97.5'))}})
            e = q['ev']; out.append({'year': y, 'days': d, 'place': 'EV', 'actual': float(r.ev[r.dem2 > 50].sum()), 'mid': e['50'],
                                     **{f'l{k}': e[a] for k, a in ((50, '25'), (80, '10'), (90, '5'), (95, '2.5'))}, **{f'u{k}': e[a] for k, a in ((50, '75'), (80, '90'), (90, '95'), (95, '97.5'))}})
    finally:
        M.SET['sims'] = old; M.STUDY.update(national=1.0, state=1.0)
    return pd.DataFrame(out)


def scores(R):
    R = R.copy(); total = 0.5 * (R.actual - R.mid).abs()
    for k in (50, 80, 90, 95):
        a = 1 - k / 100; l, u = R[f'l{k}'], R[f'u{k}']
        R[f'in{k}'] = (R.actual >= l) & (R.actual <= u); R[f'w{k}'] = u - l
        R[f'is{k}'] = (u - l) + (2 / a) * (l - R.actual).clip(lower=0) + (2 / a) * (R.actual - u).clip(lower=0); total = total + (a / 2) * R[f'is{k}']
    R['wis'] = total / 4.5; R['below'] = R.actual < R.l80; R['above'] = R.actual > R.u80
    return R


def tables(R):
    st = R[~R.place.isin(['US', 'EV'])]; r3 = lambda x: round(float(x), 3)
    by = lambda g: {**{f'cover{k}': r3(g[f'in{k}'].mean()) for k in (50, 80, 90, 95)}, **{f'width{k}': round(float(g[f'w{k}'].mean()), 1) for k in (50, 80, 90, 95)}, 'wis': round(float(g.wis.mean()), 2),
                    'more_republican_than_80': r3(g.below.mean()), 'more_democratic_than_80': r3(g.above.mean()), 'n': int(len(g))}
    out = {'states_by_days': {int(d): by(g) for d, g in st.groupby('days')}, 'states_by_year_last_day': {int(y): by(g) for y, g in st[st.days == 1].groupby('year')},
           'states_by_year_all_days': {int(y): by(g) for y, g in st.groupby('year')}, 'states_all': by(st)}
    for place in ('US', 'EV'):
        g = R[R.place == place]
        out[place] = {'by_days': {int(d): {**{f'inside{k}_of_5': int(x[f'in{k}'].sum()) for k in (50, 80, 90, 95)}, 'width80': round(float(x.w80.mean()), 1)} for d, x in g.groupby('days')},
                      'all': {f'cover{k}': r3(g[f'in{k}'].mean()) for k in (50, 80, 90, 95)}}
    polled = st[st.days == 1].assign(group=lambda x: np.where(x.poll_share >= 0.5, 'half or more from its own polls', np.where(x.poll_share > 0, 'some polls', 'no polls')))
    out['states_last_day_by_polls'] = {k: by(g) for k, g in polled.groupby('group')}
    close = st[st.days == 1].assign(group=lambda x: np.where(x.mid.abs() < 10, 'within 10 points', np.where(x.mid.abs() < 30, '10 to 30', '30 or more')))
    out['states_last_day_by_margin'] = {k: by(g) for k, g in close.groupby('group')}
    return out


def alternatives(inputs, res):
    """Scale the national and the state error, choose the scales on four elections, score on the fifth."""
    grid = [(n, s) for n in (0.6, 0.8, 1.0, 1.2) for s in (0.6, 0.7, 0.8, 0.9, 1.0, 1.1)]; got = {}
    for n, s in grid:
        R = scores(rows(inputs, res, n, s)); st = R[~R.place.isin(['US', 'EV'])]
        got[(n, s)] = {'wis': st.groupby('year').wis.mean(), 'c80': st.groupby('year').in80.mean(), 'c50': st.groupby('year').in50.mean(), 'c95': st.groupby('year').in95.mean(), 'w80': st.groupby('year').w80.mean(),
                       'nat80': R[R.place == 'US'].groupby('year').in80.mean(), 'ev80': R[R.place == 'EV'].groupby('year').in80.mean(), 'natwis': R[R.place == 'US'].groupby('year').wis.mean()}
    years = B.YEARS; base = got[(1.0, 1.0)]; out = {'grid': {f'{n} {s}': {'wis': round(float(v['wis'].mean()), 3), 'cover50': round(float(v['c50'].mean()), 3), 'cover80': round(float(v['c80'].mean()), 3), 'cover95': round(float(v['c95'].mean()), 3),
                                                                           'width80': round(float(v['w80'].mean()), 1), 'worst_year_cover80': round(float(v['c80'].min()), 3), 'national_inside_80': round(float(v['nat80'].mean()), 3),
                                                                           'electoral_votes_inside_80': round(float(v['ev80'].mean()), 3)} for (n, s), v in got.items()}, 'held_out': {}}
    for y in years:
        rest = [z for z in years if z != y]; pick = min(grid, key=lambda g: (got[g]['wis'][rest].mean() + got[g]['natwis'][rest].mean()))
        out['held_out'][y] = {'national_scale': pick[0], 'state_scale': pick[1], 'wis': round(float(got[pick]['wis'][y]), 3), 'wis_as_published': round(float(base['wis'][y]), 3),
                              'cover80': round(float(got[pick]['c80'][y]), 3), 'cover80_as_published': round(float(base['c80'][y]), 3), 'cover95': round(float(got[pick]['c95'][y]), 3), 'cover95_as_published': round(float(base['c95'][y]), 3),
                              'width80': round(float(got[pick]['w80'][y]), 1), 'width80_as_published': round(float(base['w80'][y]), 1), 'national_inside_80': round(float(got[pick]['nat80'][y]), 2), 'national_inside_80_as_published': round(float(base['nat80'][y]), 2),
                              'electoral_votes_inside_80': round(float(got[pick]['ev80'][y]), 2), 'electoral_votes_inside_80_as_published': round(float(base['ev80'][y]), 2)}
    h = out['held_out']; out['held_out_mean'] = {k: round(float(np.mean([v[k] for v in h.values()])), 3) for k in next(iter(h.values())) if k not in ('national_scale', 'state_scale')}
    out['held_out_better_in'] = int(sum(v['wis'] < v['wis_as_published'] for v in h.values()))
    return out


VARIANTS = {'until November 25, 2026: every election since 1980, one size for all states': dict(lean_error='all'),
            'last 5 elections, one size': dict(lean_error='recent', lean_window=5, lean_shrink=None),
            'as published: last 5 elections, each state its own, pulled as if by 4': dict(lean_error='recent', lean_window=5, lean_shrink=4),
            'last 5, pulled as if by 2': dict(lean_error='recent', lean_window=5, lean_shrink=2), 'last 5, pulled as if by 8': dict(lean_error='recent', lean_window=5, lean_shrink=8),
            'last 3 elections, pulled as if by 4': dict(lean_error='recent', lean_window=3, lean_shrink=4), 'last 7 elections, pulled as if by 4': dict(lean_error='recent', lean_window=7, lean_shrink=4),
            'every election since 1980, each state its own, pulled as if by 4': dict(lean_error='recent', lean_window=99, lean_shrink=4)}


def variants():
    """Other ways of sizing a state's error, each written down before it was scored, run through the whole simulation."""
    out = {}
    for name, settings in VARIANTS.items():
        inputs, res = capture(settings); R = scores(rows(inputs, res)); st = R[~R.place.isin(['US', 'EV'])]; ev = R[R.place == 'EV']
        y = st.groupby('year'); last = st[st.days == 1]
        out[name] = {'wis': round(float(st.wis.mean()), 3), 'wis_by_year': {int(k): round(float(v), 3) for k, v in y.wis.mean().items()}, **{f'cover{k}': round(float(st[f'in{k}'].mean()), 3) for k in (50, 80, 90, 95)},
                     'width80': round(float(st.w80.mean()), 1), 'cover80_by_year': {int(k): round(float(v), 3) for k, v in y.in80.mean().items()}, 'cover50_by_year': {int(k): round(float(v), 3) for k, v in y.in50.mean().items()},
                     'last_day': {**{f'cover{k}': round(float(last[f'in{k}'].mean()), 3) for k in (50, 80, 90, 95)}, 'width80': round(float(last.w80.mean()), 1), 'wis': round(float(last.wis.mean()), 3),
                                  'cover80_by_year': {int(k): round(float(v), 3) for k, v in last.groupby('year').in80.mean().items()}, 'narrowest_and_widest_state': [round(float(last.groupby('place').w80.mean().min()), 1), round(float(last.groupby('place').w80.mean().max()), 1)]},
                     'electoral_votes_inside_80': round(float(ev.in80.mean()), 3), 'electoral_votes_width80': round(float(ev.w80.mean()), 1), 'by_days': {int(d): {'cover50': round(float(g.in50.mean()), 3), 'cover80': round(float(g.in80.mean()), 3), 'cover95': round(float(g.in95.mean()), 3), 'width80': round(float(g.w80.mean()), 1), 'wis': round(float(g.wis.mean()), 3)} for d, g in st.groupby('days')}}
    base = out[next(iter(VARIANTS))]['wis_by_year']
    for v in out.values(): v['better_than_the_earlier_sizing_in'] = int(sum(v['wis_by_year'][k] < base[k] - 1e-9 for k in base))
    return out


def by_state(res):
    """Is a state's lean harder to place in some states than in others? Each election from 2000 on is scored with sizes
    estimated from the elections before it: one size for all, or each state's own pulled toward the common one."""
    r = res[res.state.str.len() == 2]; e = {}
    for y in sorted(r.year.unique()):
        if y < 1984: continue
        g = r[r.year == y].set_index('state')
        for st in g.index:
            l = M.lean(res, y, st)
            if l is not None: e[(y, st)] = 2 * (float(g.dem2[st] - g.nat2[st]) - l)
    E = pd.Series(e).unstack(); out = {'ways': {}}
    ll = lambda x, sd: float(np.mean(-0.5 * np.log(2 * np.pi * sd ** 2) - x ** 2 / (2 * sd ** 2)))
    ways = {'one size for every state': None, 'own size, pulled toward the common one as if by 2 elections': 2, 'pulled as if by 4 elections': 4, 'pulled as if by 8 elections': 8, 'own size, not pulled at all': 0}
    for name, k in ways.items():
        sc = {}
        for y in [z for z in E.index if z >= 2000]:
            past = E[E.index < y]; common = float(np.sqrt((past ** 2).stack().mean())); n = past.notna().sum(); own = (past ** 2).mean()
            sd = pd.Series(common, E.columns) if k is None else np.sqrt((n * own + k * common ** 2) / (n + k))
            x = E.loc[y].dropna(); sc[int(y)] = ll(x, sd[x.index].clip(lower=0.5))
        out['ways'][name] = {'log_score': round(float(np.mean(list(sc.values()))), 4), 'by_year': {y: round(v, 3) for y, v in sc.items()}}
    base = out['ways']['one size for every state']['by_year']
    for name, v in out['ways'].items(): v['better_than_one_size_in'] = int(sum(v['by_year'][y] > base[y] for y in base)); v['of'] = len(base)
    # the same question for kinds of state: by size and by how lopsided
    last = res[res.year == 2020].set_index('state'); big = last.ev.reindex(E.columns) >= 10
    lop = pd.Series({st: abs(2 * (M.lean(res, 2024, st) or 0)) for st in E.columns}) >= 20
    rm = lambda x: round(float(np.sqrt(np.nanmean(np.square(x.values)))), 2)
    out['typical_miss_of_the_lean'] = {'all states': rm(E), '10 electoral votes or more': rm(E.loc[:, big]), 'fewer than 10': rm(E.loc[:, ~big]), 'leans 20 points or more either way': rm(E.loc[:, lop]), 'leans less than 20': rm(E.loc[:, ~lop]),
                                       'most': dict((E ** 2).mean().pow(0.5).sort_values(ascending=False).round(1).head(6)), 'least': dict((E ** 2).mean().pow(0.5).sort_values().round(1).head(6)), 'elections': int(len(E))}
    # does a state that was hard to place in one half of the record stay hard in the other?
    a, b = (E[E.index <= 2004] ** 2).mean() ** 0.5, (E[E.index > 2004] ** 2).mean() ** 0.5
    out['first_half_against_second'] = round(float(np.corrcoef(a, b)[0, 1]), 2)
    return out


def two_years_out():
    """The approval equation with the midterm's approval reading in place of June's."""
    t = F.table(); moves = json.load(open('data/approval_moves.json'))['by_term']; out = []
    for y in sorted(int(k) for k in moves):
        row = t[t.year == y]
        if not len(row) or y < 1976: continue
        row = row.iloc[0]; base = dict(term1=int(row.term1), deminc=int(row.deminc)) if 'term1' in t.columns else {}
        try:
            june = F.forecast(y, t)[2]['approval_model']; mid = F.forecast(y, t, juneapp=float(row.juneapp) - moves[str(y)], **base)[2]['approval_model']
        except Exception:                                   # noqa: BLE001  not enough earlier elections to fit
            continue
        actual = float(row.incvote if row.deminc else 100 - row.incvote)
        out.append({'year': y, 'with_june': round(2 * (june - actual), 1), 'with_midterm': round(2 * (mid - actual), 1), 'moved_by_approval': round(2 * (mid - june), 1)})
    D = pd.DataFrame(out); rm = lambda x: round(float(np.sqrt(np.mean(np.square(x)))), 2)
    return {'by_election': out, 'elections': len(D), 'miss_with_june_approval': rm(D.with_june), 'miss_with_midterm_approval': rm(D.with_midterm), 'from_approval_moving': rm(D.moved_by_approval),
            'since_2000': {'miss_with_june_approval': rm(D[D.year >= 2000].with_june), 'miss_with_midterm_approval': rm(D[D.year >= 2000].with_midterm), 'from_approval_moving': rm(D[D.year >= 2000].moved_by_approval), 'elections': int((D.year >= 2000).sum())}}


def main():
    inputs, res = capture(); R = scores(rows(inputs, res)); out = {'levels': [50, 80, 90, 95], 'days': DAYS, 'elections': B.YEARS, 'units': 'points of margin; electoral votes for EV'}
    out.update(tables(R)); out['by_state'] = by_state(res); out['two_years_out'] = two_years_out()
    out['alternatives'] = json.load(open('data/interval_study.json'))['alternatives'] if '--quick' in sys.argv else alternatives(inputs, res)
    out['variants'] = variants()
    json.dump(out, open('data/interval_study.json', 'w'), indent=1)
    for k, v in out['variants'].items(): print(k, '|', v['wis'], v['better_than_the_earlier_sizing_in'], '| all days', v['cover50'], v['cover80'], v['cover95'], v['width80'], '| by year 80', list(v['cover80_by_year'].values()), '| last day', v['last_day']['cover50'], v['last_day']['cover80'], v['last_day']['cover95'], v['last_day']['width80'], list(v['last_day']['cover80_by_year'].values()), v['last_day']['narrowest_and_widest_state'], '| EV', v['electoral_votes_inside_80'], v['electoral_votes_width80'])


if __name__ == '__main__':
    main()
