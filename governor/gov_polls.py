"""Governor race polls for the governor forecast: each race's polling average as it stood at each distance from election
day, weighed as the presidential model weighs polls, partisan polls (paid for by a party, a party committee or a
campaign) left out, and only polls of the two nominees. The House forecast's reader and averages are used as they are
(house/polls.py), a state's race standing as one district.

    2018-2024  FiveThirtyEight's governor polls (CC BY 4.0), from the archived copy in github.com/jcervas/data (commit
               27d7b352bcf0361498f249a556656bb1535c0e32), saved by tools/fetch_governor_data.py as
               data/governor/raw/538_governor_polls_historical.csv and kept out of the repository
    later      Wikipedia's page of each race and the polling pages it points to (CC BY-SA 4.0): governor/after_election.py
               adds each year once it is over; governor/gov_live.py reads the coming races every hour

    python governor/gov_polls.py     writes data/governor/polls_by_date.csv: year, state, days, poll, poll_w, polls
"""
import os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.append(os.path.join(ROOT, 'house'))
from house_mod import load
HP = load('polls')                     # house/polls.py: the poll reader, the partisan rules and the averages
import wiki_house as WH

D = os.path.join(ROOT, 'data', 'governor')
RAW_538 = os.path.join(D, 'raw', '538_governor_polls_historical.csv')
DAYS = HP.DAYS


def from_538(path=RAW_538):
    """One row a poll question of a Democrat against a Republican in a regular general election for governor."""
    d = pd.read_csv(path, low_memory=False)
    d = d[(d.stage == 'general') & (d.hypothetical.astype(str).str.lower() != 'true')].copy()
    d['st'] = d.state.map(WH.STATES); d = d[d.st.notna()]
    rows = []
    for _, g in d.groupby('question_id'):
        dm, rp = g[g.party == 'DEM'], g[g.party == 'REP']
        if len(dm) != 1 or len(rp) != 1: continue
        r = g.iloc[0]
        rows.append({'year': int(r.cycle), 'state': r.st, 'district': 0, 'end': r.end_date, 'n': r.sample_size, 'population': str(r.population).lower(), 'pollster': str(r.pollster),
                     'partisan': {'DEM': 'D', 'REP': 'R'}.get(r.partisan, 'P' if isinstance(r.partisan, str) and r.partisan else ''),
                     'dem_pct': float(dm.pct.iloc[0]), 'rep_pct': float(rp.pct.iloc[0]), 'dem_name': str(dm.candidate_name.iloc[0]), 'rep_name': str(rp.candidate_name.iloc[0])})
    P = pd.DataFrame(rows)
    P['end'] = pd.to_datetime(P.end, format='mixed').dt.date.astype(str)
    return P


def nominees_only(P, T):
    """Polls of the two candidates who were on the November ballot (the training table's), by surname."""
    if P.empty: return P
    sur = lambda n: re.sub(r'[^a-z]', '', str(n).lower().split()[-1]) if isinstance(n, str) and n.split() else ''
    key = {(int(y), s): (sur(dn), sur(rn)) for y, s, dn, rn in zip(T.year, T.state, T.dem_candidate, T.rep_candidate)}
    ok = [key.get((y, s)) == (sur(dn), sur(rn)) for y, s, dn, rn in zip(P.year, P.state, P.dem_name, P.rep_name)]
    return P[ok]


def poll_links(text, year):
    """The polling pages a race's page points to ("Opinion polling for the ... gubernatorial election")."""
    return sorted(set(t.strip() for t in re.findall(r'\[\[\s*(Opinion polling for the [^\]|#]+)', text or '') +
                      re.findall(r'\{\{\s*(?:main|see also|further)\s*\|\s*(Opinion polling for the [^}|#]+)', text or '', flags=re.I)
                      if str(year) in t and 'gubernatorial' in t))


def from_pages(pages, year, nominees, titles):
    """Each race's polls of its two nominees: nominees is {state: (dem, rep)}; titles is {state: [the race's page and its
    polling pages]}, all in pages."""
    out = []
    for st, (dem, rep) in nominees.items():
        if not dem or not rep: continue
        for t in titles.get(st, []):
            if t in pages: out += HP.parse(HP.general_part(pages[t]['text']), dem, rep, st, 0, year)
    P = pd.DataFrame(out, columns=['year', 'state', 'district', 'end', 'n', 'population', 'pollster', 'partisan', 'dem_pct', 'rep_pct'])
    return HP.dedupe(P)


def averages(P, year, days=DAYS):
    A = HP.averages(P, year, days)
    return A.drop(columns='district')


def main():
    T = pd.read_csv(os.path.join(D, 'training.csv'))
    P = nominees_only(from_538(), T)
    P = HP.dedupe(P.drop(columns=['dem_name', 'rep_name']))
    A = pd.concat([averages(P, y) for y in sorted(P.year.unique()) if y in set(T.year)], ignore_index=True)
    p = os.path.join(D, 'polls_by_date.csv')
    if os.path.exists(p):                                          # years added from Wikipedia after an election stay
        old = pd.read_csv(p); A = pd.concat([old[~old.year.isin(A.year.unique())], A], ignore_index=True)
    A.sort_values(['year', 'state', 'days'], ascending=[True, True, False]).to_csv(p, index=False)
    print(A.groupby(['year', 'days']).size().unstack().fillna(0).astype(int).to_string())


if __name__ == '__main__':
    main()
