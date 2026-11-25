"""The fundamentals: what two academic approaches expect of the national vote, each fitted only on earlier elections.

1. Approval and time for change (after Abramowitz): the party in office's share of the two-party vote from the president's
   net approval in June and whether the party is finishing its first term. Second-quarter growth is left out because the
   2020 figure (the shutdown) is far outside anything the equation was built on.
2. Fifty-Two Keys: the share of keys in the party's favor, turned into a vote share by the straight line through earlier
   elections.
The two are averaged. The error attached is the root-mean-square miss of that average in the elections before the one
being forecast, each of those forecasts itself made only from elections before it.
"""
import numpy as np, pandas as pd

def table():
    a = pd.read_csv('data/abramowitz_data.csv')[['year', 'deminc', 'incvote', 'juneapp', 'term1']]
    add = pd.DataFrame([{'year': 2020, 'deminc': 0, 'incvote': 100 - 52.27, 'juneapp': -19, 'term1': 1},
                        {'year': 2024, 'deminc': 1, 'incvote': 49.25, 'juneapp': -20, 'term1': 1}])
    a = pd.concat([a, add], ignore_index=True)
    k = pd.read_csv('data/keys_index.csv')[['year', 'index']].rename(columns={'index': 'keys'})
    p = pd.read_csv('data/nh_primaries.csv'); p['primary'] = p.office_share - p.challenger_share      # New Hampshire: the party in office's candidate against the challenger
    return a.merge(k, on='year', how='left').merge(p[['year', 'primary']], on='year', how='left')

PRIMARY = False        # research only: add a primary equation to the average (see research.py and the README). The forecast does not use it.

def one(t, year, juneapp=None, term1=None, keys=None):
    """Fundamentals forecast of the party in office's share in `year`, from elections before it."""
    past = t[t.year < year]; row = t[t.year == year]
    juneapp = float(row.juneapp.iloc[0]) if juneapp is None else juneapp
    term1 = float(row.term1.iloc[0]) if term1 is None else term1
    keys = (float(row['keys'].iloc[0]) if len(row) else np.nan) if keys is None else keys
    X = np.column_stack([np.ones(len(past)), past.juneapp, past.term1]); b = np.linalg.lstsq(X, past.incvote.values, rcond=None)[0]
    f1 = float(b @ [1, juneapp, term1])
    pk = past.dropna(subset=['keys'])
    f2 = None
    if len(pk) >= 6 and not np.isnan(keys):
        s, i = np.polyfit(pk['keys'], pk.incvote, 1); f2 = float(i + s * keys)
    f = f1 if f2 is None else 0.5 * (f1 + f2)
    if PRIMARY:
        pp = past.dropna(subset=['primary']); gap = float(row['primary'].iloc[0])
        b3 = np.linalg.lstsq(np.column_stack([np.ones(len(pp)), pp.primary, pp.term1]), pp.incvote.values, rcond=None)[0]
        f = float(np.mean([x for x in (f1, f2, float(b3 @ [1, gap, term1])) if x is not None]))
    return f, f1, f2

def forecast(year, t=None, **now):
    """(Democratic share expected, its error) for `year`. `now` gives this year's inputs when the year is not in the table."""
    t = table() if t is None else t
    deminc = now.pop('deminc', None)
    f, f1, f2 = one(t, year, **now)
    errs = [one(t, y)[0] - float(t.incvote[t.year == y].iloc[0]) for y in t.year if 1976 <= y < year]
    sd = float(np.sqrt(np.mean(np.square(errs))))
    if deminc is None: deminc = int(t.deminc[t.year == year].iloc[0])
    dem = f if deminc else 100 - f
    return dem, sd, {'approval_model': f1 if deminc else 100 - f1, 'keys_model': (f2 if deminc else 100 - f2) if f2 is not None else None, 'party_in_office_share': f}

if __name__ == '__main__':
    t = table()
    for y in (2008, 2012, 2016, 2020, 2024):
        d, sd, x = forecast(y, t); act = float(t.incvote[t.year == y].iloc[0]); act = act if int(t.deminc[t.year == y].iloc[0]) else 100 - act
        print(y, 'fundamentals', round(d, 1), '+/-', round(sd, 1), 'actual', round(act, 1), {k: (round(v, 1) if v is not None else None) for k, v in x.items()})
