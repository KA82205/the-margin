"""The Margin's own presidential forecast of each state in 2020 and 2024, at the Senate back-test's distances, for testing
whether the Senate forecast should start from it. Research only.

It runs the presidential back-test (backtest.py at the root) exactly as published, and keeps each state's forecast at
every distance. Nothing in the presidential code is changed: the state forecasts are read as the model makes them.

    python senate/president_states.py      writes data/senate/president_forecast.csv
"""
import os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
os.chdir(ROOT)
import backtest as BT, model as M

DAYS = (365, 250, 120, 60, 30, 14, 7, 1)


def main():
    kept = []; real = M.forecast
    def keep(year, asof, *a, **k):
        out, info = real(year, asof, *a, **k)
        d = (pd.Timestamp(M.ELECTION[year]) - pd.Timestamp(asof)).days
        kept.extend({'year': year, 'days': d, 'state': q.state, 'mean': q.mean, 'p_dem': q.p_dem} for q in out['states'].itertuples() if len(q.state) == 2)
        return out, info
    BT.YEARS = [2020, 2024]; BT.M.forecast = keep
    try:
        BT.run(days=list(DAYS))
    finally:
        BT.M.forecast = real
    P = pd.DataFrame(kept).round(4)
    P.to_csv(os.path.join(ROOT, 'data', 'senate', 'president_forecast.csv'), index=False)
    print(P.groupby(['year', 'days']).size().unstack())
    return P


if __name__ == '__main__':
    main()
