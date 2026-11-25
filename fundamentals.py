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

def three_models(enns, desart, keys_line, long_range=1.0):
    """The candidate's national prior: the two national models of the Tipping Point Nowcast (approval and economy, after
    Enns and colleagues; long-range polls, after DeSart) and the Fifty-Two Keys line, a third each. Three models, each
    counted once. No weights are fitted: with five elections on record for two of them there is nothing to fit to. The
    approval equation above is left out here: its June approval is already in the first model and in six of the keys.

    long_range is how much of its third the long-range model gets (model.long_range_weight): all of it once the polls it
    is built on exist, less while it is being run early on the polls of the day."""
    return (enns + keys_line + long_range * desart) / (2 + long_range)


def keys_line(t, year, window=None):
    """The Democratic share the Fifty-Two Keys count of `year` points to, from a line fitted on the elections before it.
    window: fit on only that many of the latest elections (None: all of them, as the forecast does)."""
    past = t[t.year < year].dropna(subset=['keys']); row = t[t.year == year].iloc[0]
    if window: past = past.tail(window)
    s, i = np.polyfit(past['keys'], past.incvote, 1); inc = float(i + s * row['keys'])
    return inc if int(row.deminc) else 100 - inc


def mix(parts, weights):
    """A weighted mean of national forecasts, leaving out any that are missing or have no weight."""
    use = [(p, w) for p, w in zip(parts, weights) if p is not None and w]
    return sum(p * w for p, w in use) / sum(w for _, w in use)


def four_models(enns, desart, keys_line, approval_equation, long_range=1.0):
    """The hybrid's national prior: the Nowcast's approval-and-economy model, the Fifty-Two Keys line and the approval
    equation, with the long-range model as a fourth equal part for as much of its part as `long_range` gives it (none
    before the polls it is built on exist). With long_range = 0 this is the structural prior: three models, none of them
    built on polls of the race."""
    w = long_range if desart is not None else 0.0
    return (enns + keys_line + approval_equation + (w * desart if w else 0.0)) / (3 + w)


if __name__ == '__main__':
    t = table()
    for y in (2008, 2012, 2016, 2020, 2024):
        d, sd, x = forecast(y, t); act = float(t.incvote[t.year == y].iloc[0]); act = act if int(t.deminc[t.year == y].iloc[0]) else 100 - act
        print(y, 'fundamentals', round(d, 1), '+/-', round(sd, 1), 'actual', round(act, 1), {k: (round(v, 1) if v is not None else None) for k, v in x.items()})
