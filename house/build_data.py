"""The House forecast's training table: one row for every district in every election, 2012-2024.

From the raw sources (tools/fetch_house.py, fetched into a folder kept out of the repository, data/house/raw/):
    election_results_house.csv   FiveThirtyEight's results by candidate (CC BY 4.0): the November vote. A candidate on
                                 several lines (New York's fusion parties) counts once, under the major party; a
                                 ranked-choice race counts its last round; Louisiana's November primary counts each
                                 party's candidates together
    wiki/<year>.wiki             Wikipedia's page of each election (CC BY-SA): the district's lean as Cook published it
                                 before the election, the member, their party, what became of the seat
    weball<yy>.txt               the FEC's summary of each candidate's money (public domain)

Each row: year, state, district; dem, rep (the two parties' votes; one may be missing when a party ran no one), dem2
(the Democratic share of the two); contested (a Democrat and a Republican both ran); winner (D, R or I); pvi (the lean:
R+7 is -7), pvi_stale (published before the map in use); inc_d, inc_r (a Democratic or Republican member is on the
November ballot here); moved (the member running here represented another district before the lines changed); redrawn
(the state's map changed for this election); prev (the district's last result on the same lines, less that year's
national vote); dem_money, rep_money (receipts of each side's candidate over the whole
cycle) and dem_fec, rep_fec (their FEC numbers); national (the Democratic share of the two-party House vote nationally, in contested districts).

    python house/build_data.py <raw folder>      writes data/house/training.csv
"""
import os, re, sys, unicodedata
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import wiki_house as WH

YEARS = list(range(2012, 2026, 2))
# States whose map changed for an election (court orders and mid-decade redraws); 2012 and 2022 are every state with
# more than one seat.
REDRAWN = {2016: {'FL', 'VA', 'NC'}, 2018: {'PA'}, 2020: {'NC'}, 2024: {'AL', 'GA', 'LA', 'NC', 'NY'}}
AT_LARGE = {'AK', 'DE', 'MT', 'ND', 'SD', 'VT', 'WY'}


def fold(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()


def names(name):
    """The words of a name that can identify the person: every word but the first and the suffixes, without accents
    ("Mario Díaz-Balart" -> {'diazbalart', 'diaz', 'balart'}; "Mary Bono Mack" -> {'bono', 'mack'})."""
    n = re.sub(r'\([^)]*\)|\b(Jr|Sr|II|III|IV)\b\.?', ' ', fold(name).replace('.', ' '))
    words = [w for w in re.split(r'[\s,]+', n) if w]
    out = set()
    for w in words[1:]:
        if len(w) > 1: out |= {re.sub(r'[^a-z]', '', w)} | set(x for x in w.split('-') if len(x) > 2)
    return out


def surname(name):
    n = [w for w in re.split(r'[\s]+', re.sub(r'\([^)]*\)|,? (Jr|Sr|II|III|IV)\.?$', '', fold(name)).strip()) if w]
    return re.sub(r'[^a-z]', '', n[-1]) if n else ''


def results(raw):
    d = pd.read_csv(os.path.join(raw, 'election_results_house.csv'), low_memory=False)
    d = d[d.cycle.isin(YEARS) & d.stage.isin(['general', 'jungle primary', 'runoff']) & (d.special.astype(str).str.lower() != 'true') & d.candidate_id.notna() & ~d.state_abbrev.isin(['PR', 'GU', 'VI', 'AS', 'MP', 'DC'])].copy()
    d['district'] = d.office_seat_name.str.extract(r'(\d+)')[0].astype(int)
    d.loc[d.state_abbrev.isin(AT_LARGE), 'district'] = 0
    # Montana had one seat until 2022
    d.loc[(d.state_abbrev == 'MT') & (d.cycle >= 2022), 'district'] = d.loc[(d.state_abbrev == 'MT') & (d.cycle >= 2022), 'office_seat_name'].str.extract(r'(\d+)')[0].astype(int)
    # a runoff after November (Louisiana's, Georgia's) decides the winner; the November vote stays the vote
    run = d[d.stage == 'runoff']; d = d[d.stage != 'runoff']
    run_won = {(y, st, di): g.loc[g.winner.astype(str) == 'True', 'ballot_party'].map(lambda p: 'D' if p in ('DEM', 'DFL') else 'R' if p == 'REP' else 'I').tolist()
               for (y, st, di), g in run.groupby(['cycle', 'state_abbrev', 'district'])}
    # ranked choice: the last round
    rc = d.ranked_choice_round.fillna(0); last = d.assign(rc=rc).groupby(['cycle', 'state_abbrev', 'district']).rc.transform('max'); d = d[rc == last]
    out = []
    for (y, st, di), g in d.groupby(['cycle', 'state_abbrev', 'district']):
        by = g.groupby('candidate_id').agg(name=('candidate_name', 'first'), lines=('ballot_party', lambda s: set(s.dropna())), votes=('votes', 'sum'), won=('winner', lambda s: bool((s.astype(str) == 'True').any())))
        by['party'] = by.lines.map(lambda s: 'D' if 'DEM' in s or 'DFL' in s else 'R' if 'REP' in s else 'I')
        dv, rv = by.votes[by.party == 'D'].sum(), by.votes[by.party == 'R'].sum()
        nd, nr = int((by.party == 'D').sum()), int((by.party == 'R').sum())
        w = by[by.won]; winner = w.party.iloc[0] if len(w) else None
        if run_won.get((y, st, di)): winner = run_won[(y, st, di)][0]
        cands = [(n, p) for n, p in zip(by.name, by.party)]
        out.append({'year': int(y), 'state': st, 'district': int(di), 'dem': dv if nd else np.nan, 'rep': rv if nr else np.nan, 'n_dem': nd, 'n_rep': nr,
                    'contested': bool(nd and nr and dv > 0 and rv > 0), 'winner': winner, 'candidates': cands})
    r = pd.DataFrame(out); r['dem2'] = np.where(r.contested, 100 * r.dem / (r.dem + r.rep), np.nan)
    return r


def wiki_rows(raw):
    rows = []
    for y in YEARS:
        for x in WH.rows(open(os.path.join(raw, 'wiki', f'{y}.wiki')).read(), y):
            rows.append({**x, 'year': y})
    w = pd.DataFrame(rows)
    # a district listed twice (a member redistricted from elsewhere): the row with the lean and the members
    w['score'] = w.pvi.notna() * 2 + w.members.map(len) + w.candidates.astype(bool)
    w = w.sort_values('score', ascending=False).groupby(['year', 'state', 'district'], as_index=False).first()
    return w.drop(columns='score')


def money(raw, year):
    cols = ['id', 'name', 'ici', 'pty', 'party', 'receipts'] + [f'c{i}' for i in range(12)] + ['st', 'dist']
    f = pd.read_csv(os.path.join(raw, f'weball{str(year)[2:]}.txt'), sep='|', header=None, usecols=range(20), names=cols, dtype=str, encoding='latin-1')
    f = f[f.id.str.startswith('H')].copy(); f['receipts'] = pd.to_numeric(f.receipts, errors='coerce').fillna(0)
    f['district'] = pd.to_numeric(f.dist, errors='coerce').fillna(0).astype(int); f['sur'] = f.name.map(lambda n: re.sub(r'[^a-z]', '', str(n).split(',')[0].lower()))
    f['p'] = f.party.map(lambda p: 'D' if p in ('DEM', 'DFL') else 'R' if p == 'REP' else 'I')
    return f


def main(raw):
    R = results(raw); W = wiki_rows(raw)
    T = R.merge(W[['year', 'state', 'district', 'pvi', 'pvi_stale', 'members', 'status', 'new_seat', 'moved']], on=['year', 'state', 'district'], how='left', indicator=True)
    print('districts:', T.groupby('year').size().to_dict(), '| without a Wikipedia row:', T[T._merge == 'left_only'].groupby('year').size().to_dict())
    T = T.drop(columns='_merge')
    inc_d, inc_r, moved = [], [], []
    for r in T.itertuples():
        mem = r.members if isinstance(r.members, list) else []; st = r.status if isinstance(r.status, str) else ''
        ran = re.search(r're-?elected|lost re-?election|defeated|lost (?:the )?general', st, re.I)
        out = re.search(r'retired|renominat|resigned|died|new seat|vacant|ran for|to run for', st, re.I)
        # a member is on the November ballot here: Wikipedia says so of the only member, or a member's name matches a
        # candidate of the same party (relatives who succeed a member are told apart by the first name)
        def same(n, p):
            for c, cp in r.candidates:
                if cp != p or not (names(n) & names(c)): continue
                f1, f2 = fold(n).split()[0], fold(c).split()[0]
                if f1[:2] == f2[:2] or len(mem) == 1 and ran: return True
            return False
        if len(mem) == 1 and (ran or out) and not (ran and out):
            on = [(mem[0][0], mem[0][1], 0)] if ran else []
        else:
            on = [(n, p, i) for i, (n, p) in enumerate(mem) if same(n, p)]
        inc_d.append(int(any(p == 'D' for _, p, _ in on))); inc_r.append(int(any(p == 'R' for _, p, _ in on)))
        mv = r.moved if isinstance(r.moved, list) else []
        moved.append(int(any(i < len(mv) and mv[i] for _, _, i in on)))
    T['inc_d'], T['inc_r'], T['moved'] = inc_d, inc_r, moved
    T['redrawn'] = [int(y in (2012, 2022) and s not in AT_LARGE or s in REDRAWN.get(y, ())) for y, s in zip(T.year, T.state)]
    for col in ('dem_money', 'rep_money', 'dem_fec', 'rep_fec'): T[col] = np.nan if 'money' in col else None
    for y in YEARS:
        F = money(raw, y)
        for i in T.index[T.year == y]:
            for party, col, idc in (('D', 'dem_money', 'dem_fec'), ('R', 'rep_money', 'rep_fec')):
                cand = [n for n, p in T.at[i, 'candidates'] if p == party]
                if not cand: continue
                g = F[(F.st == T.at[i, 'state']) & (F.district == T.at[i, 'district']) & (F.p == party) & F.sur.isin([surname(n) for n in cand])]
                if len(g): top = g.loc[g.receipts.idxmax()]; T.at[i, col] = float(top.receipts); T.at[i, idc] = top.id
    c = T[T.contested]; nat = c.groupby('year').apply(lambda g: 100 * g.dem.sum() / (g.dem.sum() + g.rep.sum())).rename('national')
    T = T.merge(nat, on='year')
    # the district's last result on the same lines, against the nation that year (not when the lines changed, or when
    # one party ran no one)
    prev = T[['year', 'state', 'district', 'dem2', 'national']].assign(year=T.year + 2, prev=T.dem2 - T.national)[['year', 'state', 'district', 'prev']]
    T = T.merge(prev, on=['year', 'state', 'district'], how='left'); T.loc[T.redrawn == 1, 'prev'] = np.nan
    os.makedirs(os.path.join(ROOT, 'data', 'house'), exist_ok=True)
    keep = ['year', 'state', 'district', 'dem', 'rep', 'dem2', 'contested', 'winner', 'pvi', 'pvi_stale', 'inc_d', 'inc_r', 'moved', 'redrawn', 'new_seat', 'prev', 'dem_money', 'rep_money', 'dem_fec', 'rep_fec', 'national']
    T[keep].sort_values(['year', 'state', 'district']).to_csv(os.path.join(ROOT, 'data', 'house', 'training.csv'), index=False)
    return T


if __name__ == '__main__':
    T = main(sys.argv[1])
    print(T.groupby('year').agg(races=('state', 'size'), contested=('contested', 'sum'), pvi=('pvi', lambda s: s.notna().sum()), inc_d=('inc_d', 'sum'), inc_r=('inc_r', 'sum'),
                                dmoney=('dem_money', lambda s: s.notna().sum()), rmoney=('rep_money', lambda s: s.notna().sum()), national=('national', 'first')).to_string())
