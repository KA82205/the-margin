"""The governor forecast's training table: one row for every regular governor election both major parties contested or
not, from FiveThirtyEight's results by candidate (CC BY 4.0; data/governor/raw/election_results_gubernatorial.csv, fetched
by tools/fetch_governor_data.py and kept out of the repository) and Wikipedia's overview of each year's elections
(CC BY-SA 4.0; the pages saved by tools/fetch_governor_pages.py):

    dem, rep, dem2      the two parties' votes (a candidate on several lines, as in New York, counted once, under the
                        major party; Louisiana's all-party first round counts each party's candidates together, a runoff
                        decides the winner) and the Democratic share of the two
    contested, winner   both parties ran; the party that won
    lean                the state's lean against the nation: its Democratic two-party presidential share less the
                        nation's, three quarters the last presidential election before the year and one quarter the one
                        before, as the presidential and Senate forecasts read it
    inc_d, inc_r        a sitting Democratic or Republican governor on the November ballot: the governor Wikipedia lists
                        for the seat, matched by name to the candidates
    vote                the Democratic share of the national House vote that year (data/senate/national_fundamentals.csv;
                        none in odd years)

    python governor/gov_data.py <folder of governor_pages/<year>.json>     writes data/governor/training.csv
"""
import glob, json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.append(os.path.join(ROOT, 'house'))
import wiki_governor as WG

D = os.path.join(ROOT, 'data', 'governor')
RAW = os.path.join(D, 'raw', 'election_results_gubernatorial.csv')
FIRST = 2006


def party_of(lines):
    return 'D' if 'DEM' in lines or 'DFL' in lines else 'R' if 'REP' in lines else 'I'


def results(path=RAW, first=FIRST):
    """One row a state's regular election each year: its two parties' votes, the winner and the candidates."""
    d = pd.read_csv(path, low_memory=False)
    d = d[(d.cycle >= first) & d.stage.isin(['general', 'jungle primary', 'runoff']) & d.candidate_id.notna()].copy()
    d['special'] = d.special.astype(str).str.lower() == 'true'
    run = d[d.stage == 'runoff']; d = d[d.stage != 'runoff']
    run_won = {(y, st): party_of(set(g.loc[g.winner.astype(str) == 'True', 'ballot_party'].dropna())) for (y, st), g in run.groupby(['cycle', 'state_abbrev']) if (g.winner.astype(str) == 'True').any()}
    rc = d.ranked_choice_round.fillna(0); d = d[rc == d.assign(rc=rc).groupby(['cycle', 'state_abbrev', 'special']).rc.transform('max')]
    out = []
    for (y, st, sp), g in d.groupby(['cycle', 'state_abbrev', 'special']):
        by = g.groupby('candidate_id').agg(name=('candidate_name', 'first'), lines=('ballot_party', lambda s: set(s.dropna())), votes=('votes', 'sum'),
                                           won=('winner', lambda s: bool((s.astype(str) == 'True').any())))
        by['party'] = by.lines.map(party_of)
        dv, rv = by.votes[by.party == 'D'].sum(), by.votes[by.party == 'R'].sum()
        nd, nr = int((by.party == 'D').sum()), int((by.party == 'R').sum())
        w = by[by.won]; winner = w.party.iloc[0] if len(w) else None
        if (y, st) in run_won: winner = run_won[(y, st)]
        out.append({'year': int(y), 'state': st, 'special': bool(sp), 'dem': float(dv) if nd else np.nan, 'rep': float(rv) if nr else np.nan,
                    'contested': bool(nd and nr and dv > 0 and rv > 0), 'winner': winner, 'candidates': list(zip(by.name, by.party))})
    r = pd.DataFrame(out); r['dem2'] = np.where(r.contested, 100 * r.dem / (r.dem + r.rep), np.nan)
    return r


def leans():
    """lean(year, state) as the Senate model reads it (senate/build_data.py), with the presidential results the after-election
    steps add."""
    r = pd.read_csv(os.path.join(ROOT, 'data', 'results.csv')); r = r[r.state.str.len() == 2]
    extra = os.path.join(ROOT, 'data', 'senate', 'pres_results.csv')
    if os.path.exists(extra):
        e = pd.read_csv(extra); r = pd.concat([r, e[~e.year.isin(r.year.unique())]], ignore_index=True)
    rel = r.assign(rel=r.dem2 - r.nat2).set_index(['year', 'state']).rel

    def lean(year, st):
        last = year - (year % 4) if year % 4 else year - 4
        try: return round(0.75 * float(rel[(last, st)]) + 0.25 * float(rel[(last - 4, st)]), 3)
        except KeyError: return np.nan
    return lean


def incumbents(pages_dir, years):
    """{(year, state, special): (governor, party, status)} from Wikipedia's overview of each year."""
    out = {}
    for y in years:
        p = os.path.join(pages_dir, f'{y}.json')
        if not os.path.exists(p): continue
        P = json.load(open(p)); ov = P.get(WG.overview(y))
        if not ov: continue
        for r in WG.races(ov['text'], y):
            out[(y, r['state'], r['special'])] = (r['governor'], r['party'], r['status'])
    return out


def main(pages_dir):
    R = results()
    lean = leans(); R['lean'] = [lean(y, s) for y, s in zip(R.year, R.state)]
    nf = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'national_fundamentals.csv')).set_index('year').house_vote_dem
    R['vote'] = R.year.map(nf)
    inc = incumbents(pages_dir, sorted(R.year.unique()))
    inc_d, inc_r, gov, gp, status = [], [], [], [], []
    for r in R.itertuples():
        g = inc.get((r.year, r.state, r.special)) or inc.get((r.year, r.state, not r.special))
        name, party, st = g if g else (None, None, None)
        on = bool(name) and any(p == party and WG.same_person(name, c) for c, p in r.candidates)
        inc_d.append(int(on and party == 'D')); inc_r.append(int(on and party == 'R')); gov.append(name); gp.append(party); status.append(st)
    R['inc_d'], R['inc_r'], R['governor'], R['governor_party'], R['status'] = inc_d, inc_r, gov, gp, status
    R['dem_candidate'] = [next((c for c, p in cs if p == 'D'), None) for cs in R.candidates]
    R['rep_candidate'] = [next((c for c, p in cs if p == 'R'), None) for cs in R.candidates]
    keep = ['year', 'state', 'special', 'dem', 'rep', 'dem2', 'contested', 'winner', 'lean', 'inc_d', 'inc_r', 'vote', 'governor', 'governor_party', 'status', 'dem_candidate', 'rep_candidate']
    R[keep].sort_values(['year', 'state', 'special']).to_csv(os.path.join(D, 'training.csv'), index=False)
    print(R.groupby('year').agg(races=('state', 'size'), contested=('contested', 'sum'), governor_known=('governor', lambda s: s.notna().sum()),
                                inc_d=('inc_d', 'sum'), inc_r=('inc_r', 'sum'), d_won=('winner', lambda s: (s == 'D').sum())).to_string())
    return R


if __name__ == '__main__':
    main(sys.argv[1])
