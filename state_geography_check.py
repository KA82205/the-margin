"""Do the state-level models know where the states stand against each other, or only where the country stands?

A state forecast can be wrong in two ways: it can have the country wrong, and it can have the state's place in the country
wrong. This script takes the two apart for the state-level models on record (data/state_models.csv, from the Tipping Point
Nowcast): the approval and economy model of Enns and colleagues, DeSart's long-range polls model, and their average.

For every state and election, 2008 to 2024, each of these is scored:

    lean        this forecast's own rule: the national number plus the state's lean in the last two elections
    absolute    a state model's forecast of the state as it stands (its own national level included)
    centred     a state model's forecast of the state, moved so that its national figure equals another national number:
                only where it places the state against the country is used
    blends      a share of a state model (absolute or centred) with the rest on the lean

The national number is one of two things, and the two must not be confused:

    ORACLE      the actual national result. This is a diagnostic, not a forecast: nobody had it. It removes every national
                error, so what is left is geography alone.
    AVAILABLE   the national number this forecast itself held on each of seven days before the election (polls and
                fundamentals, from elections before it). This is the test of a real forecast.

Misses are in points of margin (twice the miss in points of share). An election counts once, whatever its number of
competitive states. Nothing here changes the forecast: the official setting stays as it is (model.SET).

    python state_geography_check.py        writes data/state_geography.json
"""
import json
import numpy as np, pandas as pd
import model as M, fundamentals as F, backtest as B

YEARS, DAYS = B.YEARS, B.DAYS
W = [0.2, 0.4, 0.5, 0.6, 0.8, 1.0]
MODELS = {'enns': 'approval_economy', 'combined': 'average', 'desart': 'long_range_polls'}
BATTLE = ['AZ', 'GA', 'MI', 'NV', 'NC', 'PA', 'WI']                      # the seven closest states of 2024, followed through all five elections


def load():
    res, polls, errs = B.load(); t = F.table(); sm = pd.read_csv('data/state_models.csv'); Y = {}
    for y in YEARS:
        r = res[(res.year == y) & (res.state.str.len() == 2)].set_index('state'); prev = res[res.year == y - 4].set_index('state')
        g = sm[sm.year == y].set_index('state'); st = [s for s in r.index if s in g.index]
        assert len(st) == 51, (y, len(st))
        d = pd.DataFrame({'actual': r.dem2[st], 'lean': [M.lean(res, y, s) for s in st], 'prev': prev.dem2.reindex(st)})
        for k, col in MODELS.items():
            d[k] = g[col].reindex(st); d[k + '_dev'] = d[k] - float(g[col]['US'])           # where the model puts the state against its own national figure
        tables, (fd, fsd, _) = M.error_tables(y, res, errs), F.forecast(y, t)
        nat = {}
        for dd in DAYS:
            out, _ = M.forecast(y, pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=dd), polls, res, tables, (fd, fsd), ev=M.ev_table(y, res))
            nat[dd] = out['national']
        Y[y] = {'d': d, 'actual_nat': float(r.nat2.iloc[0]), 'nat': nat, 'model_nat': {k: float(g[col]['US']) for k, col in MODELS.items()}, 'kind': g.kind.iloc[0]}
    return Y


def variants(d, n):
    """Every way of placing the states, given the national number n."""
    v = {'lean': n + d['lean']}
    for k in MODELS:
        v[k + ' absolute'] = d[k]; v[k + ' centred'] = n + d[k + '_dev']
        for w in W[:-1]:
            v[f'{k} absolute {w:.0%} + lean'] = w * d[k] + (1 - w) * (n + d['lean'])
            v[f'{k} centred {w:.0%} + lean'] = w * (n + d[k + '_dev']) + (1 - w) * (n + d['lean'])
    return v


def sets(d):
    return {'all': pd.Series(True, index=d.index), 'close': (d.actual - 50).abs() < 5,               # decided by under ten points
            'closer': (d.actual - 50).abs() < 2.5,                                                    # decided by under five
            'close_before': (d.prev - 50).abs() < 5,                                                  # decided by under ten points last time: known in advance
            'battle': pd.Series(d.index.isin(BATTLE), index=d.index)}


def score(Y, national):
    """{variant: {set: {year: miss}}}, with `national(y)` giving the national number used for year y."""
    out = {}
    for y in YEARS:
        d = Y[y]['d']; S = sets(d)
        for name, p in variants(d, national(y)).items():
            e = 2 * (p - d.actual)
            for s, m in S.items():
                out.setdefault(name, {}).setdefault(s, {})[y] = {'miss': float(e[m].abs().mean()), 'bias': float(e[m].mean()), 'n': int(m.sum()),
                                                                 'called': int(((p > 50) == (d.actual > 50))[m].sum())}
    return out


def table(sc, s):
    """For one set of states: each variant's miss averaged over the five elections, by election, with each election left out
    in turn, and its paired comparison with the lean election by election."""
    rows = {}
    base = np.array([sc['lean'][s][y]['miss'] for y in YEARS])
    for name, v in sc.items():
        m = np.array([v[s][y]['miss'] for y in YEARS]); diff = m - base
        se = float(diff.std(ddof=1) / np.sqrt(len(diff))) if name != 'lean' else 0.0
        rows[name] = {'miss': round(float(m.mean()), 2), 'by_year': {y: round(float(x), 2) for y, x in zip(YEARS, m)},
                      'without': {y: round(float(np.delete(m, i).mean()), 2) for i, y in enumerate(YEARS)},
                      'called': int(sum(v[s][y]['called'] for y in YEARS)), 'n': int(sum(v[s][y]['n'] for y in YEARS)),
                      'bias': round(float(np.mean([v[s][y]['bias'] for y in YEARS])), 2),
                      'vs_lean': {'mean': round(float(diff.mean()), 2), 'se': round(se, 2), 'better_in': int((diff < -1e-9).sum())}}
    return rows


if __name__ == '__main__':
    Y = load()
    out = {'years': YEARS, 'days': DAYS, 'weights': W, 'battle': BATTLE,
           'national': {y: {'actual': round(Y[y]['actual_nat'], 2), 'kind': Y[y]['kind'], 'models': {k: round(v, 2) for k, v in Y[y]['model_nat'].items()},
                            'available': {d: round(v, 2) for d, v in Y[y]['nat'].items()}} for y in YEARS},
           'n': {s: {y: int(m.sum()) for y in YEARS for m in [sets(Y[y]['d'])[s]]} for s in ('all', 'close', 'closer', 'close_before', 'battle')}}
    oracle = score(Y, lambda y: Y[y]['actual_nat'])
    out['oracle'] = {s: table(oracle, s) for s in ('all', 'close', 'closer', 'close_before', 'battle')}
    out['available'] = {}
    for d in DAYS:
        sc = score(Y, lambda y, d=d: Y[y]['nat'][d])
        out['available'][d] = {s: table(sc, s) for s in ('all', 'close', 'closer', 'close_before', 'battle')}
    # how each model's errors split: the miss of its national figure, and of its placing of the states
    out['split'] = {k: {y: {'national': round(2 * (Y[y]['model_nat'][k] - Y[y]['actual_nat']), 2),
                            'geography': round(float((2 * (Y[y]['d'][k + '_dev'] - (Y[y]['d'].actual - Y[y]['actual_nat']))).abs().mean()), 2),
                            'absolute': round(float((2 * (Y[y]['d'][k] - Y[y]['d'].actual)).abs().mean()), 2)} for y in YEARS} for k in MODELS}
    # how alike the placings are: each model's placing of a state against the lean's, and their errors
    al = {}
    for k in MODELS:
        dev = np.concatenate([Y[y]['d'][k + '_dev'].values for y in YEARS]); ln = np.concatenate([Y[y]['d']['lean'].values for y in YEARS])
        act = np.concatenate([(Y[y]['d'].actual - Y[y]['actual_nat']).values for y in YEARS])
        al[k] = {'placing_with_lean': round(float(np.corrcoef(dev, ln)[0, 1]), 3), 'errors_with_lean': round(float(np.corrcoef(dev - act, ln - act)[0, 1]), 2)}
    e, c = (np.concatenate([(Y[y]['d'][k + '_dev'] - (Y[y]['d'].actual - Y[y]['actual_nat'])).values for y in YEARS]) for k in ('enns', 'desart'))
    al['enns_with_desart_errors'] = round(float(np.corrcoef(e, c)[0, 1]), 2)
    out['alike'] = al
    json.dump(out, open('data/state_geography.json', 'w'), indent=1)

    pick = ['lean', 'enns absolute', 'combined absolute', 'desart absolute', 'enns centred', 'combined centred', 'desart centred',
            'enns centred 50% + lean', 'combined centred 50% + lean', 'enns absolute 50% + lean', 'combined absolute 50% + lean']
    def show(title, tab):
        print('\n' + title); print(f"  {'':34s} mean   " + '  '.join(str(y) for y in YEARS) + '   | without: ' + ' '.join(str(y) for y in YEARS) + '  | vs lean: mean (se) better in')
        for name in pick:
            r = tab[name]
            print(f"  {name:34s} {r['miss']:5.2f}  " + ' '.join(f"{r['by_year'][y]:5.2f}" for y in YEARS) + '   |          ' + ' '.join(f"{r['without'][y]:4.2f}" for y in YEARS) +
                  f"  |  {r['vs_lean']['mean']:+.2f} ({r['vs_lean']['se']:.2f}) {r['vs_lean']['better_in']}/5")
    print('national figures:', json.dumps(out['national']))
    print('split:', json.dumps(out['split'])); print('alike:', al); print('n:', out['n'])
    for s in ('all', 'close', 'closer', 'close_before', 'battle'):
        show(f'ORACLE (actual national result; a diagnostic, not a forecast) - {s}', out['oracle'][s])
    for d in (120, 30, 1):
        for s in ('all', 'close'):
            show(f'AVAILABLE national number, {d} days out - {s}', out['available'][d][s])
    for label, names in (('share of centred Enns', [f'enns centred {w:.0%} + lean' for w in W[:-1]] + ['enns centred']), ('share of centred combined', [f'combined centred {w:.0%} + lean' for w in W[:-1]] + ['combined centred']),
                         ('share of absolute Enns', [f'enns absolute {w:.0%} + lean' for w in W[:-1]] + ['enns absolute']), ('share of absolute combined', [f'combined absolute {w:.0%} + lean' for w in W[:-1]] + ['combined absolute'])):
        print(f'\n{label}: all / close, oracle and at 120, 30, 1 days')
        for kind, tab in (('oracle', out['oracle']), ('120', out['available'][120]), ('30', out['available'][30]), ('1', out['available'][1])):
            print(f"  {kind:>7s}  all: lean {tab['all']['lean']['miss']:.2f} | " + ' '.join(f"{tab['all'][n]['miss']:.2f}" for n in names) + f"   close: lean {tab['close']['lean']['miss']:.2f} | " + ' '.join(f"{tab['close'][n]['miss']:.2f}" for n in names))
