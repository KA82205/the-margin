"""Checks on the choices in the model: do expert ratings help, does any setting matter much, are the stated chances honest.
Writes data/checks.json. Everything here is scored on the last day and thirty days out of 2008-2024."""
import json
import numpy as np, pandas as pd
import backtest as B, model as M

def summary(R, d):
    x = R[R.days == d]
    return {'favored': int(x.called.sum()), 'p_winner': round(float(x.p_winner.mean()), 3), 'state_miss': round(float(x.state_mae.mean()), 2), 'called': int(x.states_called.sum()), 'of': int(x.of.sum()),
            'brier': round(float(x.brier.mean()), 4), 'national_miss': round(float(x.national_error.abs().mean()), 2)}

out = {}
# 1. expert ratings, at the weight in the model and at heavier ones
out['ratings'] = []
for w in (0, 0.15, 0.3, 0.5, 1.0):
    R, S = B.run(days=[7, 1], ratings=w > 0, settings={'rating_weight': w}, keep_states=True)
    rt = pd.read_csv('data/ratings.csv'); S = S.merge(rt[['year', 'state', 'rating']], on=['year', 'state'], how='left')
    S['won'] = S.actual > 50; close = S[(S.rating > 2.5) & (S.rating < 5.5)]
    row = dict(weight=w, **summary(R, 1)); row['close_n'] = int(len(close)); row['close_called'] = int(((close.p_dem > 0.5) == close.won).sum()); row['close_miss'] = round(float((close['mean'] - close.actual).abs().mean()), 2)
    row['by_year'] = {int(y): int(v) for y, v in zip(R[R.days == 1].year, R[R.days == 1].states_called)}
    out['ratings'].append(row)
rt = pd.read_csv('data/ratings.csv').merge(pd.read_csv('data/results.csv'), on=['year', 'state'])
rt['k'] = rt.rating.round().astype(int).clip(1, 7); rt['dem'] = rt.dem2 > 50
out['rating_record'] = [{'rating': int(k), 'n': int(len(g)), 'dem_won': int(g.dem.sum()), 'share': round(float(g.dem2.mean()), 1)} for k, g in rt.groupby('k')]
# 2. every other setting, one at a time
ALT = {'prior_polls': [0.75, 3.0], 'half_life': [(7, 30, 3), (7, 30, 8)], 'pollster_repeat': [0.25, 1.0], 'lean': [(1.0, 0.0), (0.5, 0.5)], 'region_share': [0.2, 0.6], 't_df': [3, 30]}
base = B.run(days=[30, 1]); out['base'] = {'1': summary(base, 1), '30': summary(base, 30)}
out['settings'] = []
for k, alts in ALT.items():
    for a in alts:
        R = B.run(days=[30, 1], settings={k: a}); out['settings'].append({'setting': k, 'value': a, 'ours': M.SET[k], '1': summary(R, 1), '30': summary(R, 30)})
# 3. are the chances honest? state chances on the last day, grouped
S = pd.read_csv('data/backtest_states.csv'); S['p'] = np.maximum(S.p_dem, 1 - S.p_dem); S['hit'] = (S.p_dem > 0.5) == (S.actual > 50)
out['calibration'] = [{'lo': lo, 'hi': hi, 'n': int(len(g)), 'said': round(float(g.p.mean()), 3), 'happened': round(float(g.hit.mean()), 3)} for lo, hi in [(0.5, 0.6), (0.6, 0.75), (0.75, 0.9), (0.9, 0.99), (0.99, 1.001)] for g in [S[(S.p >= lo) & (S.p < hi)]] if len(g)]
json.dump(out, open('data/checks.json', 'w'), indent=1)
for r in out['ratings']: print('ratings', {k: v for k, v in r.items() if k != 'by_year'})
print('record', out['rating_record']); print('base', out['base'])
for s in out['settings']: print(s['setting'], s['value'], s['1']['favored'], s['1']['state_miss'], s['1']['called'], s['1']['brier'], '| 30d', s['30']['favored'], s['30']['state_miss'], s['30']['brier'])
print('calibration', out['calibration'])
