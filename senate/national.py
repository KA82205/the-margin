"""National fundamentals for Congress: the president's approval, income growth, midterm years and seats exposed, 1948-2026,
and the Lewis-Beck and Rice seat-change model as updated by Quinn, Brush and Smith ("Updating the Fundamentals:
Forecasting the 2026 Midterm Election Post-Gallup", PS: Political Science & Politics, 2026). Research only.

    python senate/national.py          writes data/senate/national_fundamentals.csv and data/senate/national_check.json

Sources (data/senate/raw/national/, fetched by tools/fetch_fundamentals.py through the "Source samples" workflow):
    Gallup approval   every reading, from the American Presidency Project, UC Santa Barbara (Gallup's own through 2025)
    Income            real disposable personal income, DPIC96, Bureau of Economic Analysis via FRED
    Seats and votes   each election's infobox on Wikipedia (seats after each election; the Senate's seats up by party;
                      the national House vote). 2010's House infobox did not parse and is entered by hand below.
"""
import json, os, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, 'data', 'senate', 'raw', 'national'); OUT = os.path.join(ROOT, 'data', 'senate')

# the president's party at each election, and the president whose approval counts (the one in office in June)
PRESIDENT = {1948: ('D', 'harry-s-truman'), 1950: ('D', 'harry-s-truman'), 1952: ('D', 'harry-s-truman'), 1954: ('R', 'dwight-d-eisenhower'),
             1956: ('R', 'dwight-d-eisenhower'), 1958: ('R', 'dwight-d-eisenhower'), 1960: ('R', 'dwight-d-eisenhower'), 1962: ('D', 'john-f-kennedy'),
             1964: ('D', 'lyndon-b-johnson'), 1966: ('D', 'lyndon-b-johnson'), 1968: ('D', 'lyndon-b-johnson'), 1970: ('R', 'richard-m-nixon'),
             1972: ('R', 'richard-m-nixon'), 1974: ('R', 'richard-m-nixon'), 1976: ('R', 'gerald-r-ford'), 1978: ('D', 'jimmy-carter'),
             1980: ('D', 'jimmy-carter'), 1982: ('R', 'ronald-reagan'), 1984: ('R', 'ronald-reagan'), 1986: ('R', 'ronald-reagan'),
             1988: ('R', 'ronald-reagan'), 1990: ('R', 'george-bush'), 1992: ('R', 'george-bush'), 1994: ('D', 'william-j-clinton'),
             1996: ('D', 'william-j-clinton'), 1998: ('D', 'william-j-clinton'), 2000: ('D', 'william-j-clinton'), 2002: ('R', 'george-w-bush'),
             2004: ('R', 'george-w-bush'), 2006: ('R', 'george-w-bush'), 2008: ('R', 'george-w-bush'), 2010: ('D', 'barack-obama'),
             2012: ('D', 'barack-obama'), 2014: ('D', 'barack-obama'), 2016: ('D', 'barack-obama'), 2018: ('R', 'donald-j-trump'),
             2020: ('R', 'donald-j-trump'), 2022: ('D', 'joseph-r-biden'), 2024: ('D', 'joseph-r-biden'), 2026: ('R', 'donald-j-trump-2nd-term')}
HOUSE_2010 = {'D_after': 193, 'R_after': 242, 'D_pct': 44.9, 'R_pct': 51.7}         # the infobox did not parse
# Quinn, Brush and Smith's proxy for Gallup after Gallup stopped (end of 2025): -2.56 + 1.06 x the RealClearPolling average,
# plus -5.90 for Trump's second term
PROXY = (-2.56, 1.06, -5.90)
PAPER = {'house_pi': {'const': -38.58, 'approval': 0.78, 'income': 1.39, 'midterm': -29.73},
         'senate_pi': {'const': 3.69, 'approval': 0.14, 'income': 0.23, 'midterm': -2.94, 'seats_up': -0.72}}


def approvals():
    """Every reading as (president, start, end, approve), Gallup's only (through 2025)."""
    G = json.load(open(os.path.join(RAW, 'gallup_approval_rows.json'))); rows = []
    for page, tab in G.items():
        pres = page.replace('-public-approval', '')
        for r in tab:
            if len(r) < 3 or not re.match(r'\d{1,2}/\d{1,2}/\d{4}', r[0]): continue
            try: rows.append({'president': pres, 'start': pd.Timestamp(r[0]), 'end': pd.Timestamp(r[1]), 'approve': float(r[2])})
            except ValueError: continue
    A = pd.DataFrame(rows)
    return A[A.end < pd.Timestamp('2026-01-01')]


def approval_on(A, pres, date, days=30):
    """The president's average Gallup approval over readings ending in the 30 days to the date (the latest reading, if none)."""
    a = A[(A.president == pres) & (A.end <= date)]
    if not len(a): return None
    w = a[a.end > date - pd.Timedelta(days=days)]
    return float((w if len(w) else a.sort_values('end').tail(1)).approve.mean())


def june_approval(A, year, pres):
    a = A[(A.president == pres) & (A.start.dt.year == year) & (A.start.dt.month == 6)]
    if len(a): return float(a.approve.mean())
    return approval_on(A, pres, pd.Timestamp(f'{year}-06-30'), 45)


def income():
    d = pd.read_csv(os.path.join(RAW, 'fred_DPIC96.csv'), parse_dates=['observation_date']).set_index('observation_date').DPIC96
    return d


def income_growth(d, year, q_end=2):
    """Annualized growth of real disposable income over the two quarters to quarter q_end of the year, from the quarter
    two before it (the paper's measure for June: Q4 of the year before to Q2)."""
    qs = {1: '01-01', 2: '04-01', 3: '07-01', 4: '10-01'}
    end = pd.Timestamp(f'{year}-{qs[q_end]}')
    start = end - pd.DateOffset(months=6)
    if end not in d.index or start not in d.index: return None
    return float(((d[end] / d[start]) ** 2 - 1) * 100)


def seats():
    W = pd.read_csv(os.path.join(RAW, 'wiki_parsed.csv'))
    H = W[W.ch == 'H'].set_index('year'); S = W[W.ch == 'S'].set_index('year')
    for k, v in HOUSE_2010.items(): H.loc[2010, k] = v
    return H, S


def build():
    A = approvals(); d = income(); H, S = seats(); rows = []
    for y, (party, pres) in PRESIDENT.items():
        other = 'R' if party == 'D' else 'D'
        h_after, h_prev = H.loc[y, party + '_after'], H.loc[y - 2, party + '_after']
        s_after, s_prev = S.loc[y, party + '_after'], S.loc[y, party + '_before']
        ja = june_approval(A, y, pres)
        if y == 2026: ja = PROXY[0] + PROXY[1] * 40.7 + PROXY[2]           # the paper's own 2026 input (RealClearPolling, June 30)
        rows.append({'year': y, 'pres_party': party, 'midterm': int(y % 4 == 2), 'june_approval': round(ja, 2) if ja is not None else None,
                     'income_growth': round(income_growth(d, y), 3), 'house_change': h_after - h_prev, 'senate_change': s_after - s_prev,
                     'senate_up': S.loc[y, party + '_up'],
                     'house_vote_pres': round(100 * H.loc[y, party + '_pct'] / (H.loc[y, party + '_pct'] + H.loc[y, other + '_pct']), 3),
                     'house_vote_dem': round(100 * H.loc[y, 'D_pct'] / (H.loc[y, 'D_pct'] + H.loc[y, 'R_pct']), 3)})
    return pd.DataFrame(rows)


ELECTION = {2018: '2018-11-06', 2020: '2020-11-03', 2022: '2022-11-08', 2024: '2024-11-05', 2026: '2026-11-03'}
RCP_APPROVAL = os.path.join(ROOT, 'data', 'senate', '2026_rcp', 'approval_weekly.csv')   # RealClearPolling's average, 2026 (kept out of the repository)


class National:
    def __init__(self):
        self.N = build().set_index('year'); self.A = approvals(); self.d = income()
        self.rcp = pd.read_csv(RCP_APPROVAL, parse_dates=['date']) if os.path.exists(RCP_APPROVAL) else None

    def approval(self, y, asof):
        """Gallup's, while it polled; after, the aggregators' median on Wikipedia less Gallup's 2025 offset
        (wiki_national.py), or with SENATE_POLLS=rcp RealClearPolling's average by the paper's proxy."""
        pres = PRESIDENT[y][1]
        if asof < pd.Timestamp('2026-01-01'): return approval_on(self.A, pres, asof)
        if os.environ.get('SENATE_POLLS', 'wikipedia') == 'wikipedia':
            w = pd.read_csv(os.path.join(ROOT, 'data', 'senate', '2026', 'wiki_approval_2026.csv'), parse_dates=['date'])
            return float(w[w.date <= asof].approve_median.iloc[-1]) - 3.35
        r = self.rcp[self.rcp.date <= asof].approve.iloc[-1]
        return PROXY[0] + PROXY[1] * r + PROXY[2]

    def income_at(self, asof):
        """Growth over the latest two quarters the BEA had published by then (about a month after each quarter ends)."""
        q = [t for t in self.d.index if t + pd.DateOffset(months=3) + pd.Timedelta(days=35) <= asof][-1]
        s = q - pd.DateOffset(months=6)
        return float(((self.d[q] / self.d[s]) ** 2 - 1) * 100)

    def forecast(self, y, days, income=True):
        """The Democratic share of the national House vote, two-party, forecast from 1948 to the election before y."""
        fit = self.N[self.N.index < y]
        cols = [np.ones(len(fit)), fit.june_approval] + ([fit.income_growth] if income else []) + [fit.midterm]
        b = np.linalg.lstsq(np.column_stack(cols), fit.house_vote_pres.values, rcond=None)[0]
        asof = pd.Timestamp(ELECTION[y]) - pd.Timedelta(days=days)
        x = [1, self.approval(y, asof)] + ([self.income_at(asof)] if income else []) + [int(y % 4 == 2)]
        v = float(b @ x)
        return v if PRESIDENT[y][0] == 'D' else 100 - v


def add(X, nat=None):
    """The national inputs for the race model: the fundamentals forecast with and without income ('fund',
    'fund_approval'), and each averaged half and half with the generic-ballot average ('blend', 'blend_approval')."""
    nat = nat or National()
    f = {(y, d): nat.forecast(y, d) for y in X.year.unique() for d in X.days.unique()}
    g = {(y, d): nat.forecast(y, d, income=False) for y in X.year.unique() for d in X.days.unique()}
    X = X.copy(); X['fund'] = [f[(y, d)] for y, d in zip(X.year, X.days)]; X['blend'] = (X.fund + X.generic) / 2
    X['fund_approval'] = [g[(y, d)] for y, d in zip(X.year, X.days)]; X['blend_approval'] = (X.fund_approval + X.generic) / 2
    return X


def ols(df, y, xs):
    X = np.column_stack([np.ones(len(df))] + [df[c].values.astype(float) for c in xs]); b = np.linalg.lstsq(X, df[y].values.astype(float), rcond=None)[0]
    e = df[y].values - X @ b; see = float(np.sqrt((e ** 2).sum() / (len(df) - len(b))))
    return dict(zip(['const'] + xs, b.round(3))), see


def main():
    N = build(); N.to_csv(os.path.join(OUT, 'national_fundamentals.csv'), index=False)
    fit = N[N.year <= 2024]
    h, hs = ols(fit, 'house_change', ['june_approval', 'income_growth', 'midterm'])
    s, ss = ols(fit, 'senate_change', ['june_approval', 'income_growth', 'midterm', 'senate_up'])
    n26 = N[N.year == 2026].iloc[0]
    fh = h['const'] + h['june_approval'] * n26.june_approval + h['income_growth'] * n26.income_growth + h['midterm']
    fs = s['const'] + s['june_approval'] * n26.june_approval + s['income_growth'] * n26.income_growth + s['midterm'] + s['senate_up'] * n26.senate_up
    out = {'house_pi': {'ours': h, 'see': round(hs, 2), 'paper': PAPER['house_pi'], 'forecast_2026': round(float(fh), 1), 'result_2026': float(n26.house_change)},
           'senate_pi': {'ours': s, 'see': round(ss, 2), 'paper': PAPER['senate_pi'], 'forecast_2026': round(float(fs), 1), 'result_2026': float(n26.senate_change)},
           'inputs_2026': {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v) for k, v in n26.items()}}
    with open(os.path.join(OUT, 'national_check.json'), 'w') as f: json.dump(out, f, indent=1)
    pd.set_option('display.width', 250); print(N.to_string(index=False)); print(json.dumps(out, indent=1, default=str))
    return N, out


if __name__ == '__main__':
    main()
