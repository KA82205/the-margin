"""The Senate back-test, step 1: the 2018-2024 dataset. Research only; nothing here feeds the presidential forecast or the
site. Reads the raw files in data/senate/raw (as published, see SOURCES below) and writes:

    data/senate/races.csv     one row for each Senate general election of 2018-2024 decided between a Democrat (or an
                              independent the Democrats backed) and a Republican: the two candidates, the two-party result,
                              incumbency, money raised over the cycle, and the state's lean from earlier presidential votes
    data/senate/excluded.csv  the elections left out, each with the reason
    data/senate/polls.csv     every general-election poll question of those races that names both candidates, with the
                              two-party share, dates, sample, population and whether a party or campaign paid for it
    data/senate/generic.csv   generic-ballot poll questions (which party for Congress), 2018-2024
    data/senate/national.csv  the national House vote each year, two-party, from contested districts: the national
                              environment each race's result sits in
    data/senate/benchmark_538.csv  FiveThirtyEight's published Senate forecasts of 2018-2022, every day and version, for
                              scoring this model against a professional one

    python senate/build_data.py

SOURCES
    MIT Election Data and Science Lab, "U.S. Senate 1976-2024", doi:10.7910/DVN/PEJ5QU (CC0)
    Federal Election Commission, "All candidates" summary files weball18-26 (public domain; columns as in the FEC's
        data dictionary for that file)
    FiveThirtyEight polls and forecasts (CC BY 4.0), from the archived copy in github.com/jcervas/data (commit in
        data/senate/raw/SOURCE_jcervas_data_commit.txt): senate_polls_historical, generic_ballot_polls_historical,
        checking-our-work us_senate_elections
    data/results.csv and data/house_by_state.csv, as the rest of The Margin uses them
"""
import io, os, re, sys, zipfile
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, 'data', 'senate', 'raw'); OUT = os.path.join(ROOT, 'data', 'senate')
YEARS = (2018, 2020, 2022, 2024)

# Independents the Democrats backed and did not run a candidate against: counted on the Democratic side. (Written down,
# not inferred: each is a matter of record.)
DEM_ALIGNED = {('VT', 'SANDERS'), ('ME', 'KING'), ('UT', 'MCMULLIN'), ('NE', 'OSBORN')}          # (state, surname)
# Georgia decides by runoff when no one passes 50%; the runoff (January after the year) is the election that counted.
RUNOFF_DECIDES = {('GA', 2022, False)}
# Georgia's two 2020 races were decided by the runoffs of January 5, 2021, which the source files under the year 2021.
RUNOFF_NEXT_YEAR = {('GA', 2020, False), ('GA', 2020, True)}

# Which regular seat each special election filled: (state, year of the special) -> the year that seat is next up as a
# regular election. A special and a regular in the same state and year are two different seats unless they share a year here.
SPECIAL_SEAT = {('HI', 2014): 2016, ('OK', 2014): 2016, ('SC', 2014): 2016, ('AL', 2017): 2020, ('MN', 2018): 2020, ('MS', 2018): 2020,
                ('AZ', 2020): 2022, ('GA', 2020): 2022, ('OK', 2022): 2026, ('CA', 2022): 2022, ('CA', 2024): 2024, ('NE', 2024): 2026}
# Who held a seat on election day when that was not its last elected winner: senators appointed to a vacancy, and two
# changes of party. All matters of record. (state, year, special) -> (name, party as elected or appointed)
HELD_BY = {('MN', 2018, True): ('SMITH', 'D'), ('MS', 2018, True): ('HYDE-SMITH', 'R'), ('AZ', 2020, True): ('MCSALLY', 'R'),
           ('GA', 2020, True): ('LOEFFLER', 'R'), ('CA', 2022, False): ('PADILLA', 'D'), ('CA', 2022, True): ('PADILLA', 'D'),
           ('NE', 2024, True): ('RICKETTS', 'R'), ('CA', 2024, False): ('BUTLER', 'D'), ('CA', 2024, True): ('BUTLER', 'D'),
           ('NJ', 2024, False): ('HELMY', 'D'), ('OK', 2022, True): ('INHOFE', 'R')}
# Elected before the source's first year here, or in a special the source does not hold: the 2017 Alabama special.
EXTRA_WINNERS = {('AL', 2017, True): ('JONES', 'D')}

FEC_COLUMNS = ['CAND_ID', 'CAND_NAME', 'CAND_ICI', 'PTY_CD', 'CAND_PTY_AFFILIATION', 'TTL_RECEIPTS', 'TRANS_FROM_AUTH', 'TTL_DISB',
               'TRANS_TO_AUTH', 'COH_BOP', 'COH_COP', 'CAND_CONTRIB', 'CAND_LOANS', 'OTHER_LOANS', 'CAND_LOAN_REPAY', 'OTHER_LOAN_REPAY',
               'DEBTS_OWED_BY', 'TTL_INDIV_CONTRIB', 'CAND_OFFICE_ST', 'CAND_OFFICE_DISTRICT', 'SPEC_ELECTION', 'PRIM_ELECTION',
               'RUN_ELECTION', 'GEN_ELECTION', 'GEN_ELECTION_PRECENT', 'OTHER_POL_CMTE_CONTRIB', 'POL_PTY_CONTRIB', 'CVG_END_DT',
               'INDIV_REFUNDS', 'CMTE_REFUNDS']


SUFFIX = ('JR', 'SR', 'II', 'III', 'IV', 'MR', 'MRS', 'MS', 'DR', 'SEN', 'HON')


def tokens(name):
    """The words of a name, upper case, apostrophes and dots dropped (O'Rourke is OROURKE), titles and suffixes out."""
    w = re.sub(r"[^A-Z\s,-]", ' ', str(name).upper().replace("'", '').replace('.', ' ')).replace(',', ' , ').split()
    return [x for x in w if x != ',' and x not in SUFFIX and len(x) > 1]


def surname(name):
    """The last name: for "LAST, FIRST" (the FEC's form) the part before the comma, otherwise the last word."""
    n = str(name).upper().replace("'", '')
    if ',' in n:
        t = tokens(n.split(',')[0]); return t[-1] if t else ''
    t = tokens(n); return t[-1] if t else ''


# ------------------------------------------------------------------------------------------------------------- results
def results(t):
    d = pd.read_csv(os.path.join(RAW, 'mit_senate_1976_2024.tab'), sep='\t', low_memory=False)
    d = d[d.year.isin(YEARS + (2021,)) & (d['mode'].astype(str).str.lower() == 'total') & ~d.writein.astype(str).str.lower().eq('true')]
    d = d[d.candidate.notna() & ~d.candidate.astype(str).str.upper().isin(['OVER VOTES', 'UNDER VOTES', 'SCATTERING', 'BLANK VOTES'])]
    d['stage'] = d.stage.astype(str).str.lower().map(lambda x: 'runoff' if 'runoff' in x else x)
    # the simplified party is sometimes OTHER where the detailed one names a party (Illinois and Maryland, 2022)
    det = d.party_detailed.astype(str).str.upper()
    d.loc[d.party_simplified.eq('OTHER') & det.str.startswith('DEMOCRAT'), 'party_simplified'] = 'DEMOCRAT'
    d.loc[d.party_simplified.eq('OTHER') & det.str.startswith('REPUBLICAN'), 'party_simplified'] = 'REPUBLICAN'
    # a candidate whose party the source leaves blank takes it from the FEC's record of the same candidate
    blank = d.party_simplified.eq('OTHER') & d.party_detailed.isna()
    for i in d.index[blank]:
        f = t[(t.year == d.at[i, 'year']) & (t.CAND_OFFICE_ST == d.at[i, 'state_po']) & t['last'].isin(tokens(d.at[i, 'candidate']))]
        if len(f) and f.side.iloc[0] in ('D', 'R'): d.at[i, 'party_simplified'] = 'DEMOCRAT' if f.side.iloc[0] == 'D' else 'REPUBLICAN'; d.at[i, 'party_detailed'] = 'from the FEC'
    d['special'] = d.special.astype(str).str.lower().eq('true')
    races, out = [], []
    nxt = d[d.year == 2021]
    for (year, st, special), g in d[d.year.isin(YEARS)].groupby(['year', 'state_po', 'special']):
        stage = 'runoff' if (st, year, special) in RUNOFF_DECIDES and (g.stage == 'runoff').any() else 'gen'
        if (st, int(year), bool(special)) in RUNOFF_NEXT_YEAR:
            g = nxt[(nxt.state_po == st) & (nxt.special == special)].assign(stage='runoff'); stage = 'runoff'
        g = g[g.stage == stage]
        if not len(g): out.append({'year': year, 'state': st, 'special': special, 'why': 'no general-election rows'}); continue
        side = np.where(g.party_simplified.eq('DEMOCRAT').values | np.array([(st, w) in DEM_ALIGNED for c in g.candidate for w in [surname(c)]], dtype=bool), 'D', np.where(g.party_simplified.eq('REPUBLICAN'), 'R', 'O'))
        g = g.assign(side=side)
        top = g.sort_values('candidatevotes', ascending=False)
        d1, r1 = top[top.side == 'D'].head(1), top[top.side == 'R'].head(1)
        total = float(g.totalvotes.max())
        if not len(d1) or not len(r1):
            out.append({'year': year, 'state': st, 'special': special, 'why': 'no Democratic-side or no Republican candidate on the ballot (' + ', '.join(top.candidate.head(3)) + ')'}); continue
        dv, rv = float(d1.candidatevotes.iloc[0]), float(r1.candidatevotes.iloc[0])
        if dv <= 1 or rv <= 1:
            out.append({'year': year, 'state': st, 'special': special, 'why': 'uncontested'}); continue
        # a jungle or top-two ballot where the two leaders are not one of each: the general election is not D against R
        lead2 = top.head(2).side.tolist()
        if sorted(lead2) != ['D', 'R']:
            out.append({'year': year, 'state': st, 'special': special, 'why': 'the two leading candidates were not a Democrat-side candidate and a Republican (' + ', '.join(top.candidate.head(2)) + ')'}); continue
        races.append({'year': int(year), 'state': st, 'special': bool(special), 'stage': stage,  'dem': d1.candidate.iloc[0], 'rep': r1.candidate.iloc[0],
                      'dem_independent': bool(d1.party_simplified.iloc[0] != 'DEMOCRAT'), 'dem_votes': dv, 'rep_votes': rv, 'total_votes': total,
                      'dem2': round(100 * dv / (dv + rv), 3), 'others_share': round(100 * (1 - (dv + rv) / total), 2)})
    return pd.DataFrame(races), pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------------------- seats
def winners():
    """{(state, year, special): (winner's surname, party D/R/O)} for every Senate election in the source since 2010, from
    the round that decided it."""
    d = pd.read_csv(os.path.join(RAW, 'mit_senate_1976_2024.tab'), sep='\t', low_memory=False)
    d = d[(d.year >= 2010) & d.candidate.notna() & (d['mode'].astype(str).str.lower() == 'total')]
    d['special'] = d.special.astype(str).str.lower().eq('true'); d['stage'] = d.stage.astype(str).str.lower()
    det = d.party_detailed.astype(str).str.upper(); simp = d.party_simplified.astype(str)
    d['p'] = np.where(simp.eq('DEMOCRAT') | det.str.startswith('DEMOCRAT'), 'D', np.where(simp.eq('REPUBLICAN') | det.str.startswith('REPUBLICAN'), 'R', 'O'))
    out = dict(EXTRA_WINNERS)
    for (y, st, sp), g in d.groupby(['year', 'state_po', 'special']):
        if y == 2021: continue
        g2 = d[(d.year == 2021) & (d.state_po == st) & (d.special == sp)] if (st, int(y), bool(sp)) in RUNOFF_NEXT_YEAR else g[g.stage.str.contains('runoff')] if g.stage.str.contains('runoff').any() else g
        w = g2.sort_values('candidatevotes', ascending=False).iloc[0]
        out[(st, int(y), bool(sp))] = (surname(w.candidate), 'D' if (st, surname(w.candidate)) in DEM_ALIGNED else w.p)
    return out


def holder(st, year, special, W):
    """(surname, party) of the senator holding the seat on election day: an appointee or a change recorded in HELD_BY,
    otherwise the seat's last elected winner (its previous regular election, or a special held for it since)."""
    if (st, year, special) in HELD_BY: return HELD_BY[(st, year, special)]
    if special:
        regular = SPECIAL_SEAT.get((st, year))
        last = [(y, W[(st, y, False)]) for y in range(regular - 6, year) if (st, y, False) in W and y == regular - 6] if regular else []
    else:
        regular = year; last = [(year - 6, W[(st, year - 6, False)])] if (st, year - 6, False) in W else []
    for (s2, y2), r2 in SPECIAL_SEAT.items():            # a special for this seat since its last regular election
        if s2 == st and r2 == regular and year - 6 < y2 < year and (st, y2, True) in W: last.append((y2, W[(st, y2, True)]))
    return max(last)[1] if last else (None, None)


# ----------------------------------------------------------------------------------------------------------------- money
def fec():
    rows = []
    for y in YEARS:
        z = zipfile.ZipFile(os.path.join(RAW, f'fec_weball{str(y)[2:]}.zip'))
        t = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), sep='|', header=None, names=FEC_COLUMNS, dtype=str, encoding='latin-1')
        t = t[t.CAND_ID.str.startswith('S')].assign(year=y)
        rows.append(t)
    t = pd.concat(rows)
    for c in ('TTL_RECEIPTS', 'TTL_INDIV_CONTRIB', 'CAND_CONTRIB', 'CAND_LOANS', 'TRANS_FROM_AUTH'):
        t[c] = pd.to_numeric(t[c], errors='coerce').fillna(0.0)
    t['side'] = t.CAND_PTY_AFFILIATION.map(lambda p: 'D' if p in ('DEM', 'DFL') else 'R' if p == 'REP' else 'O')
    t['last'] = t.CAND_NAME.map(surname)
    return t


def money(race, side, t):
    """The candidate's FEC summary for the cycle: matched by state, year and surname; party is checked, not required (an
    independent the Democrats backed files as an independent)."""
    name = race['dem'] if side == 'D' else race['rep']
    c = t[(t.year == race['year']) & (t.CAND_OFFICE_ST == race['state']) & t['last'].isin(tokens(name))]      # any word: some names are written surname first
    if len(c) > 1: c = c[c.side == side] if (c.side == side).any() else c
    if len(c) > 1: c = c.sort_values('TTL_RECEIPTS', ascending=False).head(1)
    if not len(c): return {'match': False}
    r = c.iloc[0]
    return {'match': True, 'fec_id': r.CAND_ID, 'ici': r.CAND_ICI, 'receipts': float(r.TTL_RECEIPTS), 'indiv': float(r.TTL_INDIV_CONTRIB),
            'self': float(r.CAND_CONTRIB + r.CAND_LOANS)}


# ------------------------------------------------------------------------------------------------------------------ lean
def leans():
    """A state's lean in a given year, as The Margin reads it for the presidency: its Democratic two-party share against the
    nation's in the last presidential election (three quarters) and the one before (one quarter)."""
    r = pd.read_csv(os.path.join(ROOT, 'data', 'results.csv')); r = r[r.state.str.len() == 2]
    rel = r.assign(rel=r.dem2 - r.nat2).set_index(['year', 'state']).rel
    def lean(year, st):
        last = year - (year % 4) if year % 4 else year - 4                  # 2018 -> 2016, 2020 -> 2016, 2022 -> 2020, 2024 -> 2020
        return round(0.75 * float(rel[(last, st)]) + 0.25 * float(rel[(last - 4, st)]), 3)
    return lean


def national():
    h = pd.read_csv(os.path.join(ROOT, 'data', 'house_by_state.csv'))
    n = h[h.year.isin(YEARS)].groupby('year')[['dem', 'rep']].sum()
    return pd.DataFrame({'year': n.index, 'house_dem2': (100 * n.dem / (n.dem + n.rep)).round(3).values})


# ----------------------------------------------------------------------------------------------------------------- polls
def polls(races):
    p = pd.read_csv(os.path.join(RAW, '538_senate_polls_historical.csv.gz'), low_memory=False)
    p = p[p.cycle.isin(YEARS) & (p.stage.astype(str) == 'general')]
    abbr = {v: k for k, v in pd.read_json(os.path.join(ROOT, 'data', 'results_2024.json')).T['name'].items() if len(k) == 2} if os.path.exists(os.path.join(ROOT, 'data', 'results_2024.json')) else {}
    p['st'] = p.state.map(lambda s: abbr.get(s, s))
    out = []
    key = {(r.year, r.state, r.special): r for r in races.itertuples()}
    for qid, g in p.groupby('question_id'):
        r0 = g.iloc[0]; special = 'special' in str(r0.seat_name).lower() or bool(r0.get('seat_number', 0) == 2 and False)
        cands = [(int(r0.cycle), r0.st, s) for s in (False, True) if (int(r0.cycle), r0.st, s) in key]
        if not cands: continue
        race = None
        for c in cands:                                  # the race whose two candidates are both in the question
            rr = key[c]; names = set(g.candidate_name.astype(str).map(surname))
            if surname(rr.dem) in names and surname(rr.rep) in names: race = rr; break
        if race is None: continue
        pct = {surname(n): float(v) for n, v in zip(g.candidate_name, g.pct)}
        dp, rp = pct.get(surname(race.dem)), pct.get(surname(race.rep))
        if dp is None or rp is None or dp + rp <= 0: continue
        out.append({'year': race.year, 'state': race.state, 'special': race.special, 'poll_id': r0.poll_id, 'question_id': qid, 'pollster': r0.pollster,
                    'start': r0.start_date, 'end': r0.end_date, 'n': r0.sample_size, 'population': r0.population, 'partisan': r0.partisan if isinstance(r0.partisan, str) else '',
                    'internal': bool(r0.internal) if not pd.isna(r0.internal) else False, 'grade': r0.numeric_grade, 'hypothetical': bool(r0.hypothetical) if not pd.isna(r0.hypothetical) else False,
                    'dem_pct': dp, 'rep_pct': rp, 'dem2': round(100 * dp / (dp + rp), 3), 'candidates_named': int(g.candidate_name.nunique())})
    return pd.DataFrame(out)


def generic():
    g = pd.read_csv(os.path.join(RAW, '538_generic_ballot_polls_historical.csv.gz'), low_memory=False)
    g = g[g.cycle.isin(YEARS)].dropna(subset=['dem', 'rep'])
    g = g[['question_id', 'poll_id', 'cycle', 'pollster', 'start_date', 'end_date', 'sample_size', 'population', 'partisan', 'internal', 'numeric_grade', 'dem', 'rep']]
    return g.assign(dem2=(100 * g.dem / (g.dem + g.rep)).round(3))


def benchmark(races):
    b = pd.read_csv(os.path.join(RAW, '538_us_senate_forecasts.csv.gz'), low_memory=False)
    b = b[(b.office == 'Senate') & b.year.isin(YEARS) & b.party.isin(['D', 'R', 'I'])]
    b['special'] = b.special.astype(str).str.lower().eq('true')
    keep = ['year', 'state', 'special', 'forecast_date', 'forecast_type', 'party', 'candidate', 'projected_voteshare', 'probwin', 'probwin_outcome']
    return b[keep]


def main():
    t = fec(); races, excluded = results(t); lean = leans(); nat = national(); W = winners()
    rows = []
    for r in races.to_dict('records'):
        md, mr = money(r, 'D', t), money(r, 'R', t)
        hs, hp = holder(r['state'], r['year'], r['special'], W)
        running = 'D' if hs and hs in tokens(r['dem']) else 'R' if hs and hs in tokens(r['rep']) else 'open'
        inc = running
        rows.append(dict(r, lean=lean(r['year'], r['state']), incumbent=inc, seat_party=hp, seat_holder=hs, fec_ici_after=(md.get('ici'), mr.get('ici')), dem_fec=md.get('fec_id'), rep_fec=mr.get('fec_id'),
                         dem_receipts=md.get('receipts'), rep_receipts=mr.get('receipts'), dem_indiv=md.get('indiv'), rep_indiv=mr.get('indiv'),
                         dem_self=md.get('self'), rep_self=mr.get('self'), money_matched=bool(md['match'] and mr['match'])))
    races = pd.DataFrame(rows).merge(nat, on='year', how='left')
    races['dem2_vs_nation'] = (races.dem2 - races.house_dem2).round(3)
    os.makedirs(OUT, exist_ok=True)
    races.sort_values(['year', 'state', 'special']).to_csv(os.path.join(OUT, 'races.csv'), index=False)
    excluded.sort_values(['year', 'state']).to_csv(os.path.join(OUT, 'excluded.csv'), index=False)
    p = polls(races); p.to_csv(os.path.join(OUT, 'polls.csv'), index=False)
    generic().to_csv(os.path.join(OUT, 'generic.csv'), index=False)
    nat.to_csv(os.path.join(OUT, 'national.csv'), index=False)
    benchmark(races).to_csv(os.path.join(OUT, 'benchmark_538.csv.gz'), index=False, compression='gzip')
    print(f'races {len(races)} (by year {races.groupby("year").size().to_dict()}), excluded {len(excluded)}; money matched {int(races.money_matched.sum())}; '
          f'incumbents {races.incumbent.value_counts().to_dict()}; polls {len(p)} questions in {p.groupby(["year", "state", "special"]).ngroups} races')
    return races, excluded, p


if __name__ == '__main__':
    main()
