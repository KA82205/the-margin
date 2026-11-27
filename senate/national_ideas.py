"""Testing ideas from the 2026 academic forecasts on the long national record. Research only.

Each candidate forecasts the president's party's share of the national two-party House vote. Every election from 1978
to 2026 is forecast from a fit on 1948 up to the election before it only (rolling origin, as Quinn, Brush and Smith test
theirs), at two points: June of the election year (their timing) and a year out (the November before). The candidates
were set before any was scored:

    approval, midterm                     the national input the race model uses now (step 8)
    + income                              Quinn, Brush and Smith's economy: real disposable income growth
    + inflation                           Fair's point that prices count apart from growth: consumer prices, 12 months
    + GDP                                 the other economy measure in their paper
    + years in power                      Tien and Lewis-Beck's "cost of ruling": years the president's party has held
                                          the White House without a break
    + inflation + years in power          the two new ideas together

    python senate/national_ideas.py       writes data/senate/national_ideas.json
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import national as NA

RAW = NA.RAW
# when the president's party's unbroken hold on the White House began (inauguration)
HOLD_SINCE = [(1933, 'D'), (1953, 'R'), (1961, 'D'), (1969, 'R'), (1977, 'D'), (1981, 'R'), (1993, 'D'), (2001, 'R'), (2009, 'D'),
              (2017, 'R'), (2021, 'D'), (2025, 'R')]
CANDIDATES = {'approval, midterm': ['approval', 'midterm'],
              '+ income': ['approval', 'income', 'midterm'],
              '+ inflation': ['approval', 'inflation', 'midterm'],
              '+ GDP': ['approval', 'gdp', 'midterm'],
              '+ years in power': ['approval', 'years', 'midterm'],
              '+ inflation + years in power': ['approval', 'inflation', 'years', 'midterm']}


def series(name):
    d = pd.read_csv(os.path.join(RAW, f'fred_{name}.csv'), parse_dates=['observation_date'])
    return d.set_index('observation_date')[name].replace('.', np.nan).astype(float).dropna()


def years_in_power(y):
    start = max(s for s, _ in HOLD_SINCE if s <= y)
    return y + 10 / 12 - start                                                # inauguration in January, election in November


def inputs(N, A, when):
    """The inputs for each year as known in June of the election year ('june') or in November of the year before ('year')."""
    inc, gdp, cpi = NA.income(), series('A191RL1Q225SBEA'), series('CPIAUCSL')
    rows = []
    for y in N.index:
        if when == 'june':
            appr = N.loc[y, 'june_approval']; income = N.loc[y, 'income_growth']
            g = gdp[(gdp.index >= f'{y}-01-01') & (gdp.index <= f'{y}-04-01')].mean()
            asof_cpi = pd.Timestamp(f'{y}-05-01')
        else:
            asof = pd.Timestamp(f'{y - 1}-11-01')
            a = A[(A.end <= asof) & (A.end > asof - pd.Timedelta(days=30))]      # the sitting president, whoever it was
            appr = float(a.approve.mean()) if len(a) else float(A[A.end <= asof].sort_values('end').approve.iloc[-1])
            q = pd.Timestamp(f'{y - 1}-07-01'); s = q - pd.DateOffset(months=6)  # Q3 of the year before, published by late October
            income = float(((inc[q] / inc[s]) ** 2 - 1) * 100)
            g = gdp[(gdp.index >= f'{y - 1}-04-01') & (gdp.index <= f'{y - 1}-07-01')].mean()
            asof_cpi = pd.Timestamp(f'{y - 1}-09-01')
        c = cpi[cpi.index <= asof_cpi]; c0 = cpi[cpi.index <= asof_cpi - pd.DateOffset(months=12)]
        rows.append({'year': y, 'approval': appr, 'income': income, 'gdp': float(g), 'inflation': float((c.iloc[-1] / c0.iloc[-1] - 1) * 100) if len(c0) else np.nan,
                     'years': years_in_power(y), 'midterm': N.loc[y, 'midterm'], 'vote': N.loc[y, 'house_vote_pres'],
                     'house_change': N.loc[y, 'house_change'], 'senate_change': N.loc[y, 'senate_change'], 'senate_up': N.loc[y, 'senate_up']})
    return pd.DataFrame(rows).set_index('year')


def rolling(I, cols, target='vote', extra=(), first=1978):
    out = {}
    for y in I.index[I.index >= first]:
        c = list(cols) + list(extra); fit = I[I.index < y].dropna(subset=c + [target])
        X = np.column_stack([np.ones(len(fit))] + [fit[k].values for k in c]); b = np.linalg.lstsq(X, fit[target].values, rcond=None)[0]
        out[y] = float(b @ np.r_[1, I.loc[y, c].values.astype(float)])
    return pd.Series(out)


def main():
    N = NA.build().set_index('year'); A = NA.approvals()
    res, detail = [], {}
    for when in ('june', 'year'):
        I = inputs(N, A, when)
        if when == 'year':
            I.loc[2026, 'approval'] = float(A[(A.end <= pd.Timestamp('2025-11-01')) & (A.end > pd.Timestamp('2025-10-02'))].approve.mean())
        for name, cols in CANDIDATES.items():
            for target, extra in (('vote', ()), ('house_change', ()), ('senate_change', ('senate_up',))):
                f = rolling(I, cols, target, extra); e = f - I.loc[f.index, target]
                recent = e[e.index >= 2002]
                res.append({'when': when, 'candidate': name, 'target': target, 'rmse_1978_2026': float(np.sqrt((e ** 2).mean())),
                            'rmse_2002_2026': float(np.sqrt((recent ** 2).mean())), 'error_2026': float(e.get(2026, np.nan)),
                            'error_2020': float(e.get(2020, np.nan)), 'error_2022': float(e.get(2022, np.nan))})
                if target == 'vote': detail[f'{when}|{name}'] = e.round(2).to_dict()
        detail[f'{when}|inputs'] = I.round(3).reset_index().to_dict('records')
    R = pd.DataFrame(res)
    pd.set_option('display.width', 250)
    for t in ('vote', 'house_change', 'senate_change'):
        print(t); print(R[R.target == t].pivot(index='candidate', columns='when', values=['rmse_1978_2026', 'rmse_2002_2026', 'error_2026']).round(2))
    with open(os.path.join(ROOT, 'data', 'senate', 'national_ideas.json'), 'w') as fh:
        json.dump({'note': 'Rolling-origin forecasts of the president\'s party\'s two-party House vote and seat changes, 1978-2026; errors are forecast minus result.',
                   'scores': R.round(3).to_dict('records'), 'errors_by_year': {k: {str(a): b for a, b in v.items()} if isinstance(v, dict) else v for k, v in detail.items()}},
                  fh, indent=1, default=str)
    return R, detail


if __name__ == '__main__':
    main()
