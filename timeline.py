"""What a polling average has been worth at each distance from the election, and the weights that follow from it.

Erikson and Wlezien's work on the timeline of presidential elections shows that the polls say little about the result at
the start of the election year and more and more as the campaign brings the vote into line with the fundamentals. This
module measures that on the record in hand and turns it into two curves, each estimated only from elections before the one
being forecast:

    national   the best weight on the national polling average, set against a structural forecast, by days to the election
    state      the same for a state's polling average, set against the state's starting point

The record (data/timeline.csv): FiveThirtyEight's published polling averages for 1972 to 2016, national and state, at ten
distances from 250 days to the last day, and this model's own averages for 2020 and 2024. The structural forecast set
against the national average is the fundamentals forecast of fundamentals.py, made from earlier elections.

Beyond 250 days there is no long record, only the early polls of 2016, 2020 and 2024 (longrange()). The curves are carried
on past 250 days by their own shape, which takes them close to nothing. validate_phase_in.py tests that on those three.

    python timeline.py --build raw/pres_pollaverages_1968-2016.csv     rebuild data/timeline.csv (the file is FiveThirtyEight's,
                                                                        github.com/fivethirtyeight/data, polls/)
    python timeline.py                                                 print the curves for each forecast year
"""
import json, sys
import numpy as np, pandas as pd
import model as M, fundamentals as F

H = [1, 7, 14, 30, 60, 90, 120, 150, 200, 250]
GRID = {'top': np.round(np.arange(0.30, 0.96, 0.02), 2), 'half': np.arange(40, 420, 10), 'power': [1.0, 1.5, 2.0, 3.0, 4.0]}
FIRST = 1976                    # the first election with a fundamentals forecast made from elections before it


def build(path):
    """data/timeline.csv from FiveThirtyEight's averages (1972-2016) and this model's own (2020, 2024)."""
    res = pd.read_csv('data/results.csv'); polls = pd.read_csv('data/polls.csv', parse_dates=['end'])
    a = pd.read_csv(path, usecols=['cycle', 'state', 'modeldate', 'candidate_name', 'pct_estimate', 'election_date'])
    a['days'] = (pd.to_datetime(a.election_date) - pd.to_datetime(a.modeldate)).dt.days
    old = M.average_errors(res, a, H)[['cycle', 'st', 'days', 'avg', 'res']].assign(source='FiveThirtyEight')
    rows = []
    for y in (2020, 2024):
        P = M.Polls(polls, y); r = res[res.year == y].set_index('state')
        for d in H:
            asof = P.eday - pd.Timedelta(days=d); v, w = P.national(asof)
            rows.append({'cycle': y, 'st': 'US', 'days': d, 'avg': v, 'res': float(r.nat2.iloc[0]), 'source': 'this model'})
            for st in r.index[r.index.str.len() == 2]:
                v, w = P.state(st, asof)
                if v is not None and w >= 1.0:                                        # an average needs about one fresh poll's worth of weight
                    rows.append({'cycle': y, 'st': st, 'days': d, 'avg': v, 'res': float(r.dem2[st]), 'source': 'this model'})
    t = pd.concat([old, pd.DataFrame(rows)]).sort_values(['cycle', 'st', 'days'])
    t[['avg', 'res']] = t[['avg', 'res']].round(3); t['days'] = t.days.astype(int)
    t.to_csv('data/timeline.csv', index=False)
    print(t.groupby('cycle').agg(rows=('avg', 'size'), states=('st', 'nunique')).T.to_string())


def record():
    """The national and state records, with what each average was set against."""
    t = pd.read_csv('data/timeline.csv'); res = pd.read_csv('data/results.csv'); tab = F.table().set_index('year')
    n = t[t.st == 'US'].copy()
    def fund(y):
        f = F.one(tab.reset_index(), y)[0]; return f if tab.deminc[y] else 100 - f
    fd = {y: fund(y) for y in sorted(n.cycle.unique()) if y >= FIRST}
    n = n[n.cycle >= FIRST].assign(prior=lambda x: x.cycle.map(fd))
    s = t[t.st != 'US'].merge(n[['cycle', 'days', 'avg', 'res']].rename(columns={'avg': 'nat_avg', 'res': 'nat_res'}), on=['cycle', 'days'])
    s['lean'] = [M.lean(res, c, st) for c, st in zip(s.cycle, s.st)]
    s = s.dropna(subset=['lean']).assign(poll=lambda x: x.avg - x.nat_avg, actual=lambda x: x.res - x.nat_res)      # the state against the nation: in the polls, and in the result
    return n, s


curve = M.curve


def fit(poll, prior, actual, days):
    """The curve that would have done best: least squared error of weight x poll + (1 - weight) x prior."""
    poll, prior, actual, days = (np.asarray(x, float) for x in (poll, prior, actual, days)); best = None
    for power in GRID['power']:
        for half in GRID['half']:
            shape = 1 / (1 + (days / half) ** power)
            # for a given shape the best `top` has a closed form; it is then held to the grid's range
            x = shape * (poll - prior); top = float(np.clip((x * (actual - prior)).sum() / (x * x).sum(), GRID['top'][0], GRID['top'][-1]))
            sse = float(((prior + top * x - actual) ** 2).sum())
            if best is None or sse < best[0] - 1e-9: best = (sse, (round(top, 3), int(half), power))
    return best[1]


def monotone(days, values):
    """Sizes of error that never shrink as the election gets further away (pool adjacent violators, on the squares)."""
    v = [[float(x) ** 2, 1] for x in values]; i = 0
    while i < len(v) - 1:
        if v[i][0] > v[i + 1][0] + 1e-12:
            a, b = v[i], v.pop(i + 1); v[i] = [(a[0] * a[1] + b[0] * b[1]) / (a[1] + b[1]), a[1] + b[1]]; i = max(i - 1, 0)
        else:
            i += 1
    out = [x for x, n in v for _ in range(n)]
    return {int(d): float(np.sqrt(x)) for d, x in zip(days, out)}


_CACHE = {}


def curves(year):
    """Everything the phase-in needs for a forecast of `year`, from earlier elections only."""
    if year in _CACHE: return _CACHE[year]
    n, s = record(); n = n[n.cycle < year]; s = s[s.cycle < year]
    nat = fit(n.avg, n.prior, n.res, n.days); st = fit(s.poll, s.lean, s.actual, s.days)
    rm = lambda x: float(np.sqrt(np.mean(np.square(x))))
    mix = {d: rm(g.prior + curve(nat, d) * (g.avg - g.prior) - g.res) for d, g in n.groupby('days')}       # how far the mix itself stood from the result
    out = {'national': nat, 'state': st, 'elections': int(n.cycle.nunique()), 'state_elections': int(s.cycle.nunique()),
           'poll_error': monotone(H, [rm(n[n.days == d].avg - n[n.days == d].res) for d in H]),
           'state_poll_error': monotone(H, [rm(s[s.days == d].poll - s[s.days == d].actual) for d in H]),
           'mix_error': monotone(H, [mix[d] for d in H]), 'prior_error': rm(n[n.days == 1].prior - n[n.days == 1].res),
           'raw': {int(d): {'poll': round(rm(g.avg - g.res), 2), 'n': int(len(g)),
                            'best': round(float(np.clip(((g.avg - g.prior) * (g.res - g.prior)).sum() / ((g.avg - g.prior) ** 2).sum(), 0, 1)), 2)} for d, g in n.groupby('days')},
           'raw_state': {int(d): {'poll': round(rm(g.poll - g.actual), 2), 'lean': round(rm(g.lean - g.actual), 2), 'n': int(len(g)),
                                  'best': round(float(np.clip(((g.poll - g.lean) * (g.actual - g.lean)).sum() / ((g.poll - g.lean) ** 2).sum(), 0, 1)), 2)} for d, g in s.groupby('days')}}
    _CACHE[year] = out
    return out


def longrange(years=(2016, 2020, 2024), days=(300, 350, 400, 450, 500, 550, 600, 650)):
    """This model's own averages of the early polls of three elections, national and state: all there is beyond 250 days.
    The polls are of the two people who went on to be nominated (for 2024, of Biden and Trump), which nobody knew then."""
    polls = pd.read_csv('data/polls.csv', parse_dates=['end']); res = pd.read_csv('data/results.csv'); rows = []
    for y in years:
        P = M.Polls(polls, y); r = res[res.year == y].set_index('state')
        for d in days:
            asof = P.eday - pd.Timedelta(days=d); v, w = P.national(asof)
            if v is None: continue
            rows.append({'cycle': y, 'st': 'US', 'days': d, 'avg': v, 'w': w, 'res': float(r.nat2.iloc[0])})
            for st in r.index[r.index.str.len() == 2]:
                sv, sw = P.state(st, asof)
                if sv is not None: rows.append({'cycle': y, 'st': st, 'days': d, 'avg': sv, 'w': sw, 'res': float(r.dem2[st])})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    if '--build' in sys.argv:
        build(sys.argv[sys.argv.index('--build') + 1])
    for y in (2008, 2012, 2016, 2020, 2024, 2028):
        c = curves(y)
        print(y, f"from {c['elections']} elections | national: top {c['national'][0]}, half at {c['national'][1]} days, power {c['national'][2]} ->",
              ' '.join(f"{d}:{curve(c['national'], d):.2f}" for d in (1, 30, 60, 120, 180, 250, 365, 500, 715)),
              f"| state ({c['state_elections']} el.): top {c['state'][0]}, half {c['state'][1]}, power {c['state'][2]} ->", ' '.join(f"{d}:{curve(c['state'], d):.2f}" for d in (1, 30, 120, 250, 500, 715)))
    c = curves(2028)
    print('2028 raw national (rmse of the average, best weight):', c['raw']); print('2028 raw state:', c['raw_state'])
    print('poll_error', {k: round(v, 2) for k, v in c['poll_error'].items()}, '\nstate_poll_error', {k: round(v, 2) for k, v in c['state_poll_error'].items()},
          '\nmix_error', {k: round(v, 2) for k, v in c['mix_error'].items()}, 'prior_error', round(c['prior_error'], 2))
