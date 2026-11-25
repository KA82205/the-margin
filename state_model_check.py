"""How much of a state's starting point should come from a state-level model? Writes data/state_model_check.json.

For 2028 half of every state's starting point is the Tipping Point Nowcast's forecast of that state; the other half is the
national number plus the state's lean. That half was a choice. This script tries other shares on 2008 to 2024, using the
state forecasts Tipping Point has on record for its two models (data/state_models.csv):

    approval_economy   the state approval and state economy model of Enns, Colner, Kumar and Lagodny
    long_range_polls   Jay DeSart's model, from head-to-head polls taken a year before the election
    average            the two averaged, which is what the Nowcast publishes once both exist

For 2020 and 2024 these are the forecasts the authors published before the election. For 2008, 2012 and 2016 nothing was
published; each model was refitted on the elections before that year and given that year's inputs. The approval model's
forecast is made about 100 days out, so at 120 days this test sees it a few weeks early.

Two ways of using a state model are tried: its forecast of the state as it stands ('share'), and only where it puts the
state against its own national figure ('lean'), which leaves the national level to this forecast's own number.

    python state_model_check.py
"""
import json
import numpy as np, pandas as pd
import model as M, fundamentals as F, backtest as B

SM = pd.read_csv('data/state_models.csv')
WEIGHTS = [0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]
DAYS = [120, 90, 60, 30, 14, 7, 1]
res, polls, errs = B.load(); t = F.table()
CTX = {y: (M.error_tables(y, res, errs), F.forecast(y, t), M.ev_table(y, res), res[res.year == y].set_index('state')) for y in B.YEARS}


def run(col, mode, w):
    old = dict(M.SET); M.SET.update(state_model_weight=w, state_model_mode=mode); rows = []
    for y in B.YEARS:
        tables, (fd, fsd, _), ev, r = CTX[y]
        g = SM[SM.year == y].dropna(subset=[col]); extra = dict(zip(g.state, g[col])) if w > 0 else None
        for d in DAYS:
            asof = pd.Timestamp(M.ELECTION[y]) - pd.Timedelta(days=d)
            out, _ = M.forecast(y, asof, polls, res, tables, (fd, fsd), ev=ev, extra_prior=extra)
            S = out['states'].set_index('state'); two = S.index.str.len() == 2; act = r.dem2.reindex(S.index); won = act > 50
            err, perr, close = (S['mean'] - act)[two], (S['prior'] - act)[two], ((act - 50).abs() < 5)[two]
            ok = ((S.p_dem > 0.5) == won)[two]; dem_won = r.ev[r.dem2 > 50].sum() > r.ev.sum() / 2
            v = (S.poll_weight / (S.poll_weight + M.SET['prior_polls'])).where(S.poll.notna(), 0.0)[two]
            rows.append({'year': y, 'days': d, 'miss': 2 * err.abs().mean(), 'miss_close': 2 * err[close].abs().mean(), 'start_miss': 2 * perr.abs().mean(), 'start_miss_close': 2 * perr[close].abs().mean(),
                         'called': int(ok.sum()), 'called_close': int(ok[close].sum()), 'n_close': int(close.sum()), 'brier': float(((S.p_dem - won) ** 2)[two].mean()),
                         'p_winner': out['p_dem'] if dem_won else 1 - out['p_dem'], 'ev_miss': abs(out['ev_median'] - int(r.ev[r.dem2 > 50].sum())), 'polls_share_close': float(v[close].mean())})
    M.SET.clear(); M.SET.update(old)
    return pd.DataFrame(rows)


if __name__ == '__main__':
    out = {'weights': WEIGHTS, 'days': DAYS, 'runs': {}}
    base = run('average', 'share', 0)
    out['polls_share_close'] = {int(d): round(float(g.polls_share_close.mean()), 2) for d, g in base.groupby('days')}
    for col in ('average', 'approval_economy', 'long_range_polls'):
        for mode in ('share', 'lean'):
            tab = []
            for w in WEIGHTS:
                R = base if w == 0 else run(col, mode, w)
                by = R.groupby('days'); yr = R[R.days == 120].set_index('year')
                tab.append({'w': w, 'miss': {int(d): round(float(g.miss.mean()), 2) for d, g in by}, 'miss_close': {int(d): round(float(g.miss_close.mean()), 2) for d, g in by},
                            'start_miss': round(float(R[R.days == 120].start_miss.mean()), 2), 'start_miss_close': round(float(R[R.days == 120].start_miss_close.mean()), 2),
                            'called': {int(d): int(g.called.sum()) for d, g in by}, 'called_close': {int(d): int(g.called_close.sum()) for d, g in by},
                            'brier': {int(d): round(float(g.brier.mean()), 4) for d, g in by}, 'p_winner': {int(d): round(float(g.p_winner.mean()), 3) for d, g in by},
                            'ev_miss': {int(d): round(float(g.ev_miss.mean()), 1) for d, g in by},
                            'start_by_year': {int(y): round(float(v), 2) for y, v in yr.start_miss.items()}, 'miss120_by_year': {int(y): round(float(v), 2) for y, v in yr.miss.items()}})
            out['runs'][f'{col}/{mode}'] = tab
            print(f'\n{col}, {mode}: miss in points of margin, all 51 | close states | calls of 255 | Brier')
            print('  share   start(120) close  ' + '  '.join(f'{d:>5d}' for d in DAYS) + '   close@120 @30   @1   calls@120 @1   brier@120  @1   start by year')
            for x in tab:
                print(f"  {x['w']:4.0%}   {x['start_miss']:6.2f}  {x['start_miss_close']:6.2f}   " + '  '.join(f"{x['miss'][d]:5.2f}" for d in DAYS) +
                      f"   {x['miss_close'][120]:6.2f} {x['miss_close'][30]:5.2f} {x['miss_close'][1]:5.2f}   {x['called'][120]:4d} {x['called'][1]:4d}    {x['brier'][120]:.4f} {x['brier'][1]:.4f}   " +
                      ' '.join(f"{v:.2f}" for v in x['start_by_year'].values()))
    out['n_close'] = int(base[base.days == 1].n_close.sum()); out['n'] = 51 * len(B.YEARS)
    json.dump(out, open('data/state_model_check.json', 'w'), indent=1)
    print('\npolls\' share of a close state\'s projection by days out:', out['polls_share_close'], '| close states:', out['n_close'])
