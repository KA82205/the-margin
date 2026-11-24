"""Numbers for the Research tab that are not about the model: how far polling averages have stood from the result.
Writes data/research.json. Uses FiveThirtyEight's published polling averages for 1972-2016 (data/average_errors.csv)."""
import json
import numpy as np, pandas as pd

e = pd.read_csv('data/average_errors.csv')
H = [150, 120, 90, 60, 30, 14, 7, 1]
by_day = []
for d in H:
    n = e[(e.st == 'US') & (e.days == d)]; s = e[(e.st != 'US') & (e.days == d)]
    by_day.append({'days': d, 'national': round(float(2 * n.err.abs().mean()), 1), 'states': round(float(2 * s.err.abs().mean()), 1), 'elections': int(n.cycle.nunique()), 'state_averages': int(len(s))})
last = e[(e.st == 'US') & (e.days == 1)].sort_values('cycle')
by_year = [{'year': int(r.cycle), 'polls': round(float(2 * (r.avg - 50)), 1), 'result': round(float(2 * (r.res - 50)), 1), 'miss': round(float(2 * r.err), 1)} for r in last.itertuples()]
dem = sum(1 for r in by_year if r['miss'] > 0)
out = {'by_day': by_day, 'by_year': by_year, 'toward_dem': dem, 'years': len(by_year), 'mean_signed': round(float(np.mean([r['miss'] for r in by_year])), 1)}
json.dump(out, open('data/research.json', 'w'), indent=1)
print(by_day); print(by_year); print(dem, len(by_year), out['mean_signed'])
