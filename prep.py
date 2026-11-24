"""Builds the clean inputs in data/ from the downloaded sources in raw/ (see README for where each comes from)."""
import json, warnings
import numpy as np, pandas as pd
warnings.simplefilter('ignore')
RAW, OUT = 'raw/', 'data/'
KEYS = '../repo/data/'
ELECTION = {2008: '2008-11-04', 2012: '2012-11-06', 2016: '2016-11-08', 2020: '2020-11-03', 2024: '2024-11-05'}
POP = {'Likely Voters': 'lv', 'Registered Voters': 'rv', 'Adults': 'a', 'lv': 'lv', 'rv': 'rv', 'a': 'a', 'v': 'rv'}

# ---- results and electoral votes
e = pd.read_csv(KEYS + 'course/elec_full.csv')
e['abbr'] = e.abbr.str.replace('_full', '').str.replace('_d', '')
e['electors'] = pd.to_numeric(e.electors, errors='coerce')
res = e[['year', 'abbr', 'electors', 'd_2pv', 'd_2pv_nat']].rename(columns={'abbr': 'state', 'electors': 'ev', 'd_2pv': 'dem2', 'd_2pv_nat': 'nat2'})
res = res[res.year >= 1972].dropna(subset=['dem2'])
# the source has Maine's 2nd district for 2020 on the wrong side; Trump won it 52.3 to 44.8
res.loc[(res.year == 2020) & (res.state == 'ME2'), 'dem2'] = 46.1
s24 = json.load(open('../tpnew/pipeline/results_2024.json'))
names = {v['name']: k for k, v in s24.items() if len(k) == 2}
tot = sum(v['votes'] for k, v in s24.items() if len(k) == 2); nat24 = sum(v['votes'] * v['share'] for k, v in s24.items() if len(k) == 2) / tot
r24 = pd.DataFrame([{'year': 2024, 'state': k.replace('-', ''), 'ev': v['ev'], 'dem2': v['share'], 'nat2': nat24} for k, v in s24.items()])
res = pd.concat([res, r24]).sort_values(['year', 'state'])
res.to_csv(OUT + 'results.csv', index=False)
for y in ELECTION:
    r = res[res.year == y]; print(y, 'states', len(r), 'ev', int(r.ev.sum()), 'dem ev', int(r.ev[r.dem2 > 50].sum()), 'nat', round(r.nat2.iloc[0], 2))

# ---- polls
def clean(d, year):
    d = d.dropna(subset=['dem', 'rep', 'end']); d = d[(d.dem + d.rep) > 50]
    d['end'] = pd.to_datetime(d.end); d['year'] = year
    d = d[d.end < pd.Timestamp(ELECTION[year])]
    d['dem2'] = 100 * d.dem / (d.dem + d.rep); d['n'] = pd.to_numeric(d.n, errors='coerce').fillna(600).clip(100, 5000)
    return d[['year', 'state', 'pollster', 'end', 'n', 'pop', 'dem2', 'dem', 'rep']]

out = []
for year, f, dc, rc in [(2008, 'all_polls_2008', 'obama', 'mccain'), (2012, 'all_polls_2012', 'obama', 'romney'), (2016, 'all_polls', 'clinton', 'trump')]:
    d = pd.read_csv(RAW + f'TheEconomist_us-potus-model_master_data_{f}.csv')
    d = d[d.population.isin(POP)]
    d = pd.DataFrame({'state': d.state.replace('--', 'US'), 'pollster': d.pollster, 'end': pd.to_datetime(d['end.date']), 'n': d['number.of.observations'],
                      'pop': d.population.map(POP), 'dem': d[dc], 'rep': d[rc]})
    d = d.groupby(['state', 'pollster', 'end', 'pop'], as_index=False).mean(numeric_only=True)
    out.append(clean(d, year))
h = pd.read_csv(RAW + 'jc_president_polls_historical.csv', low_memory=False)
h['end'] = pd.to_datetime(h.end_date, format='%m/%d/%y')
ab = dict(names); ab.update({'Maine CD-1': 'ME1', 'Maine CD-2': 'ME2', 'Nebraska CD-1': 'NE1', 'Nebraska CD-2': 'NE2', 'Nebraska CD-3': 'NE3'})
h = h[h.state != 'Puerto Rico']; h['st'] = h.state.map(ab).fillna('US'); assert h.state.dropna().map(ab).notna().all()
h = h[h.partisan.isna()]
for year, pairs in [(2020, [('Biden', 'Trump', '2019-01-01', '2020-12-31')]), (2024, [('Biden', 'Trump', '2023-01-01', '2024-07-20'), ('Harris', 'Trump', '2024-07-21', '2024-12-31')])]:
    for dn, rn, a, b in pairs:
        x = h[(h.cycle == year) & (h.end >= a) & (h.end <= b)]
        q = x.pivot_table(index=['poll_id', 'question_id', 'st', 'pollster', 'end', 'sample_size', 'population'], columns='answer', values='pct', aggfunc='first').reset_index()
        q = q.dropna(subset=[dn, rn])
        q['rank'] = q.population.map({'lv': 0, 'rv': 1, 'v': 1, 'a': 2})
        q = q[q['rank'] == q.groupby('poll_id')['rank'].transform('min')]
        g = q.groupby(['poll_id', 'st', 'pollster', 'end', 'population'], as_index=False).agg(dem=(dn, 'mean'), rep=(rn, 'mean'), n=('sample_size', 'mean'))
        out.append(clean(pd.DataFrame({'state': g.st, 'pollster': g.pollster, 'end': g.end, 'n': g.n, 'pop': g.population.map(POP), 'dem': g.dem, 'rep': g.rep}), year))
polls = pd.concat(out).sort_values(['year', 'end', 'state'])
polls.to_csv(OUT + 'polls.csv', index=False)
print(polls.groupby('year').agg(polls=('dem2', 'size'), national=('state', lambda s: (s == 'US').sum()), states=('state', 'nunique'), first=('end', 'min'), last=('end', 'max')).to_string())

# ---- the long record of polling averages (538, 1968-2016), for sizing uncertainty
a = pd.read_csv(RAW + 'fivethirtyeight_data_master_polls_pres_pollaverages_1968-2016.csv', usecols=['cycle', 'state', 'modeldate', 'candidate_name', 'pct_estimate', 'election_date'])
a['date'] = pd.to_datetime(a.modeldate); a['days'] = (pd.to_datetime(a.election_date) - a.date).dt.days
print(a.groupby('cycle').candidate_name.unique().head(14).to_string())
import model
model.average_errors(res, a).to_csv(OUT + 'average_errors.csv', index=False)

# ---- final expert ratings: Cook Political Report (1988-2020) and Sabato's Crystal Ball (2004-2024), on one scale: 1 solid Democratic ... 4 toss-up ... 7 solid Republican
c = pd.read_csv(RAW + 'rt_cpr_ratings.csv'); s = pd.read_csv(RAW + 'rt_sabato_crystal_ball_ratings.csv')
scale = {'Solid D': 1, 'Likely D': 2, 'Lean D': 3, 'Toss Up': 4, 'Lean R': 5, 'Likely R': 6, 'Solid R': 7}
c = pd.DataFrame({'year': c.year, 'state': c.Abbreviation, 'cook': c.Rating.map(scale)})
rt = c.merge(s.rename(columns={'rating': 'sabato'}), on=['year', 'state'], how='outer')
rt = rt[rt.year >= 2008]; rt['rating'] = rt[['cook', 'sabato']].mean(axis=1)
rt.to_csv(OUT + 'ratings.csv', index=False)
print(rt.groupby('year').agg(states=('state', 'size'), cook=('cook', 'count'), sabato=('sabato', 'count'), cook_tossups=('cook', lambda x: (x == 4).sum()), sabato_tossups=('sabato', lambda x: (x == 4).sum())).to_string())
