"""Do prediction markets add to the forecast? What can be checked, and what cannot. Writes data/market_study.json.

What exists to check against. Markets on every state with a price history that can still be read exist for one election:
2024, on Polymarket (real money) and Manifold (play money). data/market_history_2024.csv holds their prices at the
distances the back-test uses, read by tools/market_history.py from the providers' public records. For 2008 to 2020 no
free record of state markets was found, and nothing anywhere shows what markets said two years before an election.

What is compared, for 2024, at each distance, on the states both the forecast and the market cover:
    the forecast alone      the method as published, run for 2024 as the back-test runs it
    a market alone          Polymarket's price; Manifold's price
    half and half           the forecast's and Polymarket's chances averaged on the log-odds scale, state by state. (This is
                            the simple blend. It moves each state on its own, so its states no longer add up to one set of
                            simulated elections: it is here as a yardstick, not as something that could be published.)
    weighted elections      the forecast's own simulated elections, weighted toward the markets (markets.informed): toward
                            the national price only, toward the state prices only, toward both, and toward both at half strength

Scores: the Brier score and the log loss of the chances given to the party that won each state (lower is better), how many
states were called for the right party, and the chance given to the winner of the Electoral College.

One election is one election. Fifty states in it shared one national miss, so these are not fifty tests. Nothing here can
set a weight, and nothing here is used to set one.

    python market_study.py
"""
import json, math
import numpy as np, pandas as pd
import model as M, markets as K, interval_study as I

YEAR = 2024


def main():
    H = pd.read_csv('data/market_history_2024.csv'); inputs, res = I.capture(); r = res[res.year == YEAR].set_index('state'); won = (r.dem2 > 50)
    dem_won_ec = float(r.ev[r.dem2 > 50].sum()) > float(r.ev.sum()) / 2
    two = lambda d, rr: None if (pd.isna(d) and pd.isna(rr)) else K.two_party(None if pd.isna(d) else float(d), None if pd.isna(rr) else float(rr))
    out = {'year': YEAR, 'by_days': {}, 'what': 'chances for 2024 only; one election'}
    keep = M.SET['sims']; M.SET['sims'] = 40000
    try:
        for d in I.DAYS:
            S, nat, s_nat, year, ev = inputs[(YEAR, d)]; o = M.simulate(S, nat, s_nat, year, None, ev, keep=True); sims = o['sims']; st = o['states'].set_index('state')
            h = H[H.days == d]; pm = {x.place: two(x.dem, x.rep) for x in h[h.provider == 'Polymarket'].itertuples()}; mf = {x.place: two(x.dem, x.rep) for x in h[h.provider == 'Manifold'].itertuples()}
            pm_us = pm.pop('US', None); pm_us = None if pm_us is None else 1 - float(h[(h.provider == 'Polymarket') & (h.place == 'US')].rep.iloc[0]) if not pd.isna(h[(h.provider == 'Polymarket') & (h.place == 'US')].rep.iloc[0]) else pm_us
            both = [s for s in pm if pm[s] is not None and s in st.index and len(s) == 2]
            if len(both) < 20: out['by_days'][d] = {'states_with_a_polymarket_price': len(both), 'note': 'too few states were priced this far out'}; continue
            def score(p):
                p = {s: min(0.999, max(0.001, float(p[s]))) for s in both}; y = {s: bool(won[s]) for s in both}
                return {'brier': round(float(np.mean([(p[s] - y[s]) ** 2 for s in both])), 4), 'log_loss': round(float(np.mean([-math.log(p[s] if y[s] else 1 - p[s]) for s in both])), 4), 'called': int(sum((p[s] > 0.5) == y[s] for s in both))}
            ways = {'the forecast alone': {s: st.p_dem[s] for s in both}, 'Polymarket alone': pm}
            if all(mf.get(s) is not None for s in both): ways['Manifold alone'] = mf
            lg = lambda p: math.log(min(0.999, max(0.001, p)) / (1 - min(0.999, max(0.001, p))))
            ways['half and half with Polymarket, state by state'] = {s: 1 / (1 + math.exp(-(lg(st.p_dem[s]) + lg(pm[s])) / 2)) for s in both}
            targets = {f'winner:{s}': {'p': pm[s], 'quality': 1.0} for s in both}; natl = {'winner:US': {'p': pm_us, 'quality': 1.0}} if pm_us is not None else {}
            ec = {'the forecast alone': 1 - o['p_dem'] if not dem_won_ec else o['p_dem'], 'Polymarket alone': None if pm_us is None else (pm_us if dem_won_ec else 1 - pm_us)}; eff = {}
            for name, t, s_ in (('weighted elections: national price only', natl, 0.5), ('weighted elections: state prices only', targets, 0.5), ('weighted elections: national and state prices', {**targets, **natl}, 0.5), ('weighted elections: both, at half strength', {**targets, **natl}, 0.25)):
                if not t: continue
                x = K.informed(sims, t, strength=s_); ways[name] = x['states']; ec[name] = x['p_dem'] if dem_won_ec else x['p_rep']; eff[name] = x['effective']
            out['by_days'][d] = {'states': len(both), 'polymarket_national_democratic': None if pm_us is None else round(pm_us, 3), 'forecast_national_democratic': round(float(o['p_dem']), 3),
                                 'ways': {k: dict(score(v), winner_of_the_electoral_college=None if ec.get(k) is None else round(float(ec[k]), 3), **({'elections_effectively_kept': eff[k]} if k in eff else {})) for k, v in ways.items()}}
    finally:
        M.SET['sims'] = keep
    days = [d for d, v in out['by_days'].items() if 'ways' in v]; names = list(out['by_days'][days[-1]]['ways'])
    out['mean_over_days'] = {n: {m: round(float(np.mean([out['by_days'][d]['ways'][n][m] for d in days if n in out['by_days'][d]['ways']])), 4) for m in ('brier', 'log_loss', 'called')} for n in names}
    for n in names:
        v = [out['by_days'][d]['ways'][n]['winner_of_the_electoral_college'] for d in days if n in out['by_days'][d]['ways'] and out['by_days'][d]['ways'][n]['winner_of_the_electoral_college'] is not None]
        out['mean_over_days'][n]['winner_of_the_electoral_college'] = round(float(np.mean(v)), 3) if v else None
        out['mean_over_days'][n]['better_log_loss_than_the_forecast_at'] = int(sum(out['by_days'][d]['ways'][n]['log_loss'] < out['by_days'][d]['ways']['the forecast alone']['log_loss'] for d in days if n in out['by_days'][d]['ways'])); out['mean_over_days'][n]['of'] = len(days)
    out['days_scored'] = days
    out['cannot_be_checked'] = ['any election before 2024 at the level of the states: no free record of the prices was found', 'any distance beyond about 250 days: the 2024 state markets opened in the spring of that year',
                                'the quality rule (volume, traders, freshness, spread): the record gives only each market\'s final volume, not what it was on each day', 'whether 2024 was typical: it is one election, and in it the forecast and the markets missed in the same direction']
    json.dump(out, open('data/market_study.json', 'w'), indent=1)
    print('days scored', days); [print(f"{n[:52]:52s}", v) for n, v in out['mean_over_days'].items()]
    for d in days: print(d, out['by_days'][d]['states'], {k[:22]: (v['log_loss'], v['called'], v['winner_of_the_electoral_college']) for k, v in out['by_days'][d]['ways'].items()})


if __name__ == '__main__':
    main()
