"""After each Senate election, on its own: the election's races become training data and the model is refitted, so the
next cycle's forecast learns from the last one. Run every week by .github/workflows/senate-after.yml; it does nothing
until an election's results have settled (seven weeks after election day: past Georgia's runoffs and the states'
certification), and nothing again once that election is in the training table.

For the election just held, from Wikipedia (CC BY-SA 4.0) and from what the live forecast recorded as the cycle went:
  1. each race's result, the deciding round (a runoff's, where there was one); a race that was not between the
     Democratic side and a Republican is left out of the table, as in training, and counted in the chamber;
  2. each race's inputs as they stood at each distance the model is fitted at, a year out to the last day: the state's
     lean; the national mood the live forecast recorded that day (history.csv); whether the senator ran (the nominees
     say); the candidates' records before the election; and the race's polls of the nominees finished by then, partisan
     ones left out, averaged in the presidential model's weights; added to training_rows.csv (table.py);
  3. the chamber after the election, the races left out that the Democratic side won and the party that breaks a 50-50
     tie (chamber_by_year.json), and the national seat model the live forecast recorded (seat_model_by_year.csv);
  4. the candidates' records: the races added to past_races.csv, scored as build_data.past_races scores them, with the
     slope and incumbency terms it fitted on 1978-2016 (past_races_fit.json);
  5. the national record: the year added to national_fundamentals.csv (June's approval from the live forecast's
     record, the national House vote and the change in the president's party's Senate seats);
  6. in a presidential year, each state's presidential vote, to pres_results.csv, which the state leans read beside
     data/results.csv;
  7. the refit, into the next cycle's model.json (live_fit.py), and the back-test figures again (site_data.py).

It checks what it read before writing anything: too few races with results, a share out of range, or a distance with
no national reading, and it writes nothing and tries again the next week.

    python senate/after_election.py                 the elections due and not yet in the table
    python senate/after_election.py --year 2028     that election, again if it is already in (its rows are replaced)
"""
import json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import backtest as B, build_data as BD, live as L, table as TB, wiki_2028 as W28, wiki_candidates as WC, wiki_polls as WP

D = os.path.join(ROOT, 'data', 'senate')
WAIT_DAYS = 49
GALLUP_OFFSET = -3.35


# ----------------------------------------------------------------------------------------------------------- results
def label(box, k):
    v = WC.field(box, f'{k}blank') or ''
    return WP.clean(v).lower()


def nominees(text):
    """Each nominee in the race page's box, with party and votes in each round the box gives ({round: votes}), and the
    rounds' labels ({round: 'first round' | 'runoff' | 'regular election' | ...})."""
    box = WC.infobox(text); out = []
    for i in range(1, 9):
        n = WC.field(box, f'nominee{i}') or WC.field(box, f'candidate{i}')
        if not n: continue
        rounds = {k: WC.number(WC.field(box, f'{k}data{i}')) for k in range(1, 5) if WC.field(box, f'{k}data{i}')}
        if not rounds and WC.field(box, f'popular_vote{i}'): rounds = {0: WC.number(WC.field(box, f'popular_vote{i}'))}
        out.append({'name': WC.name_of(n), 'party': WC.party_code(WC.field(box, f'party{i}')), 'rounds': rounds})
    labels = {k: label(box, k) for k in range(1, 5) if WC.field(box, f'{k}blank')}
    return out, labels, box


def which_rounds(labels, special):
    """(deciding round, first round): the runoff (or ranked-choice final round) decides where there was one; a page with
    a regular and a special election in one box gives each its own column."""
    if any('regular' in v or 'special' in v for v in labels.values()):
        k = next((k for k, v in labels.items() if ('special' in v) == bool(special) and ('regular' in v or 'special' in v)), None)
        return k, k
    last = max([k for k, v in labels.items() if re.search(r'runoff|two-round|final|second round', v)], default=None)
    first = next((k for k, v in labels.items() if 'first' in v), None)
    if last: return last, first or 1
    return (1, 1) if labels else (0, 0)


def result(text, state, special):
    """The race's result: the two sides' nominees and votes in the deciding round and in the first, whether it was
    between the Democratic side and a Republican (both rounds' top two), and which side won."""
    noms, labels, box = nominees(text)
    if not noms: return None
    dec, first = which_rounds(labels, special)
    votes = lambda x, k: x['rounds'].get(k) if k in x['rounds'] else (x['rounds'].get(0) if k in (0, 1) else None)
    c = {'nominees': [{'name': x['name'], 'party': x['party']} for x in noms], 'incumbent': WC.name_of(WC.field(box, 'before_election')),
         'incumbent_party': WC.party_code(WC.field(box, 'before_party'))}
    dem, rep, _ = WC.sides(c, state)
    ind = [x for x in c['nominees'] if x['party'] in ('I', 'O')]
    if dem is None and rep is not None and ind: dem = ind[0]       # no Democrat on the ballot: the independent against the Republican
    find = lambda s: next((x for x in noms if s and x['name'] == s['name']), None)
    dd, rr = find(dem), find(rep)
    def top_two_dr(k):
        vs = sorted(((votes(x, k) or 0, x['name']) for x in noms), reverse=True)[:2]
        return dd is not None and rr is not None and {n for _, n in vs} == {dd['name'], rr['name']} and all(v > 0 for v, _ in vs)
    lead = max(noms, key=lambda x: votes(x, dec) or 0)
    won = 'D' if (dem and lead['name'] == dem['name']) or (lead['party'] in ('D', 'I') and not rep) or (lead['party'] == 'D') else 'R' if lead['party'] == 'R' else 'O'
    out = {'dem': dd['name'] if dd else None, 'dem_party': dd['party'] if dd else None, 'rep': rr['name'] if rr else None, 'won': won,
           'incumbent': c['incumbent'], 'incumbent_party': c['incumbent_party'], 'dr': bool(dd and rr and top_two_dr(dec))}
    if dd and rr:
        a, b = votes(dd, dec), votes(rr, dec)
        out['dem2'] = 100 * a / (a + b) if a and b else None
        a1, b1 = votes(dd, first), votes(rr, first)
        out['dem2_first'] = 100 * a1 / (a1 + b1) if a1 and b1 else None
        out['dr_first'] = bool(top_two_dr(first))
    return out


# ---------------------------------------------------------------------------------------------------------- national
def party_counts(box, key):
    out = {}
    for i in range(1, 7):
        p = W28.party_code(WC.field(box, f'party{i}') or ''); v = WC.number(WC.field(box, f'{key}{i}') or '')
        if p and v is not None: out[p] = out.get(p, 0) + v
    return out


def house_vote(text):
    """The Democrats' two-party share of the national House vote, from the House elections page's box."""
    v = party_counts(L.infobox_any(text), 'popular_vote')
    return 100 * v['D'] / (v['D'] + v['R']) if v.get('D') and v.get('R') else None


def senate_seats(text):
    """{party: (seats before, seats after)} from the Senate elections page's box."""
    box = WC.infobox(text); b, a = party_counts(box, 'seats_before'), party_counts(box, 'seats_after')
    return {p: (b.get(p), a.get(p)) for p in set(b) | set(a)}


def pres_results(text):
    """({state: Democratic two-party share}, the nation's) from a presidential election page's results-by-state table;
    the nation summed from the states and D.C. (the districts of Maine and Nebraska are inside their states' counts)."""
    m = re.search(r'\n=+\s*Results by state\s*=+', text or '')
    if not m: return None, None
    names = {**W28.ABBR, 'District of Columbia': 'DC', 'Washington, D.C.': 'DC', 'D.C.': 'DC', 'Washington D.C.': 'DC'}
    for t in re.finditer(r'\{\|.*?\n\|\}', text[m.end():m.end() + 400000], flags=re.S):
        rows = WP.rows_of(t.group(0))
        if len(rows) < 30: continue
        head = [WP.clean(c[2]) for c in rows[0]]
        di = next((i for i, h in enumerate(head) if re.search(r'\bDemocratic\b', h)), None); ri = next((i for i, h in enumerate(head) if re.search(r'\bRepublican\b', h)), None)
        if di is None or ri is None: continue
        out, votes = {}, {}
        for r in rows[2:]:
            if len(r) <= max(di, ri): continue
            nm = re.sub(r'[†*‡§]+', '', WP.clean(r[0][2])).strip(); d, rp = WC.number(r[di][2]), WC.number(r[ri][2])
            if nm in names and d and rp: out[names[nm]] = 100 * d / (d + rp); votes[names[nm]] = (d, rp)
        if len(out) >= 45:
            return out, 100 * sum(d for d, _ in votes.values()) / sum(d + r for d, r in votes.values())
    return None, None


# ------------------------------------------------------------------------------------------------------------- build
def on(H, date, col, within=7):
    """The live forecast's reading of col on the day (or the last before it, within a week); None if there is none."""
    h = H[(H.date <= date) & (H.date > date - pd.Timedelta(days=within))]
    h = h[h[col].notna()] if col in h else h.iloc[0:0]
    return float(h[col].iloc[-1]) if len(h) else None


def build(year, pages, F, H, today):
    """Everything the election adds, nothing written: {'rows', 'chamber', 'seat_models', 'past', 'national', 'pres'}."""
    L.setup(L.election_day(year)); E = L.ELECTION
    past = pd.read_csv(os.path.join(D, 'past_races.csv')); past = past[past.year < year]
    lean = BD.leans(); rows, past_rows, left_out_dem, problems = [], [], 0, []
    for f in F['races']:
        st, sp = f['state'], bool(f['special'])
        pg = pages.get(L.race_title(st, sp))
        if not pg or pg['title'] == L.OVERVIEW: problems.append(f'{st}: no race page'); continue
        text = pg['text'] + '\n' + '\n'.join(p['text'] for t, p in pages.items() if t.startswith('Opinion polling for') and W28.NAMES[st] in t and ('special' in t) == sp)
        res = result(pg['text'], st, sp)
        if not res: problems.append(f'{st}: no result in the box'); continue
        if not res['dr'] or res.get('dem2') is None:
            left_out_dem += int(res['won'] == 'D'); continue
        dem, rep = res['dem'], res['rep']
        DU, RU = WP.plain(dem).upper(), WP.plain(rep).upper()          # as the record writes names: capitals, no accents (Luján is LUJAN)
        inc = res['incumbent'] or f.get('incumbent'); ip = res['incumbent_party'] or f.get('incumbent_party')
        inc_d = int(bool(inc) and ip in ('D', 'I') and L.same_person(inc, dem)); inc_r = int(bool(inc) and ip == 'R' and L.same_person(inc, rep))
        tr = BD.track_records(pd.DataFrame([{'year': year, 'state': st, 'dem': DU, 'rep': RU}]), P=past).iloc[0]
        track = (float(tr.dem_track) if pd.notna(tr.dem_track) else 0.0) - (float(tr.rep_track) if pd.notna(tr.rep_track) else 0.0)
        P = pd.DataFrame(WP.parse(text, dem.upper(), rep.upper(), st, year))
        t = None
        if len(P):
            P = P[P.partisan.fillna('') == ''] if 'partisan' in P else P
            if len(P):
                P = P.assign(dem2=100 * P.dem_pct / (P.dem_pct + P.rep_pct), population=P.population.astype(str).str.lower())
                t = B.table(P, {'end': 'end', 'n': 'n', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'})
        ln = lean(year, st)
        for d in B.DAYS:
            asof = E - pd.Timedelta(days=d)
            poll, pw = B.average(t, asof, d) if t is not None else (None, 0.0)
            rows.append({'year': year, 'state': st, 'special': sp, 'days': d, 'dem2': round(res['dem2'], 4), 'lean': ln,
                         'generic': on(H, asof, 'generic'), 'fund_approval': on(H, asof, 'fundamentals'), 'blend_approval': on(H, asof, 'national'),
                         'inc_d': inc_d, 'inc_r': inc_r, 'track': round(track, 4), 'poll': poll, 'poll_w': pw, 'money_t': None, 'appointed': 0})
        if res.get('dr_first') and res.get('dem2_first') is not None:
            past_rows.append({'year': year, 'state': st, 'special': sp, 'dem': DU, 'rep': RU, 'dem2': round(res['dem2_first'], 3), 'lean': ln})
    R = pd.DataFrame(rows)
    # the chamber after the election, from the year's page: the Democrats and the independents who sit with them
    seats = senate_seats(pages.get(L.OVERVIEW, {}).get('text', ''))
    after = (seats.get('D', (None, None))[1] or 0) + (seats.get('I', (None, None))[1] or 0) if seats.get('D', (None, None))[1] is not None else None
    pp = F['president_party']
    if year % 4 == 0:
        box = WC.infobox(pages.get(f'{year} United States presidential election', {}).get('text', ''))
        tie = W28.party_code(WC.field(box, 'after_party') or '')
    else:
        tie = pp
    ch = {'before': F['chamber_now']['dem_caucus'], 'after': after, 'left_out_dem': left_out_dem, 'tie': tie}
    sm = {d: on(H, E - pd.Timedelta(days=d), 'seat_model', within=30) for d in B.DAYS}
    # the national record: June's approval (as the live forecast read it, put on Gallup's scale), the House vote, and the
    # change in the president's party's seats (the party's own, as the record counts them)
    june = H[(H.date >= pd.Timestamp(f'{year}-06-01')) & (H.date <= pd.Timestamp(f'{year}-06-30'))]
    hv = house_vote(pages.get(f'{year} United States House of Representatives elections', {}).get('text', ''))
    sb = seats.get(pp, (None, None))
    # the seats the president's party had up, by the party that held them (a vacant seat too), independents apart
    cn = F['chamber_now']
    up = cn['rep_up'] if pp == 'R' else cn['dem_up'] - sum(1 for f in F['races'] if f.get('incumbent_party') == 'I')
    nat = {'year': year, 'pres_party': pp, 'midterm': int(year % 4 == 2),
           'june_approval': round(float(june.approval.mean()) + GALLUP_OFFSET, 2) if 'approval' in june and june.approval.notna().any() else None,
           'income_growth': None, 'house_change': None, 'senate_change': (sb[1] - sb[0]) if None not in sb else None, 'senate_up': up,
           'house_vote_pres': round(hv if pp == 'D' else 100 - hv, 3) if hv else None, 'house_vote_dem': round(hv, 3) if hv else None}
    pres = None
    if year % 4 == 0:
        st_sh, nat2 = pres_results(pages.get(f'{year} United States presidential election', {}).get('text', ''))
        if st_sh: pres = pd.DataFrame([{'year': year, 'state': s, 'ev': None, 'dem2': round(v, 6), 'nat2': round(nat2, 6)} for s, v in sorted(st_sh.items())])
    return {'rows': R, 'chamber': ch, 'seat_models': sm, 'past': pd.DataFrame(past_rows), 'national': nat, 'pres': pres, 'problems': problems}


def check(year, out, F):
    """Results complete enough to train on, or a list of what is missing."""
    bad = list(out['problems'])
    R = out['rows']; n = len(R[R.days == 1]) if len(R) else 0
    if n < 0.7 * len(F['races']): bad.append(f'results for only {n} of {len(F["races"])} races')
    if len(R) and not R.dem2.between(3, 97).all(): bad.append('a share out of range')
    if len(R) and R.blend_approval.isna().any(): bad.append('a distance with no national reading: ' + ', '.join(str(d) for d in sorted(R[R.blend_approval.isna()].days.unique())))
    c = out['chamber']
    if c['after'] is None or not 30 <= c['after'] <= 70 or c['tie'] not in ('D', 'R'): bad.append(f'the chamber after the election: {c}')
    if any(v is None for v in out['seat_models'].values()): bad.append('a distance with no national seat model reading')
    N = out['national']
    if N['june_approval'] is None or N['house_vote_dem'] is None or N['senate_change'] is None: bad.append(f'the national record: {N}')
    if year % 4 == 0 and (out['pres'] is None or len(out['pres']) < 51): bad.append('the presidential results by state')
    return bad


def score_past(new):
    """New races' records, as build_data.past_races scores them: the result less the lean and had-won terms (fitted on
    1978-2016, kept in past_races_fit.json), less the year's average of that."""
    if not len(new): return new
    fit = json.load(open(os.path.join(D, 'past_races_fit.json'))); P = pd.read_csv(os.path.join(D, 'past_races.csv'))
    key = lambda c, st, side: (st, side, BD.surname(c), (BD.tokens(c) or [''])[0][:1])
    won = {key(r.dem if r.dem2 > 50 else r.rep, r.state, 'D' if r.dem2 > 50 else 'R') for r in P[P.year < new.year.min()].itertuples()}
    new = new.copy()
    new['dem_had_won'] = [int(key(r.dem, r.state, 'D') in won) for r in new.itertuples()]; new['rep_had_won'] = [int(key(r.rep, r.state, 'R') in won) for r in new.itertuples()]
    x = new.dem2 - fit['lean'] * new.lean - fit['dem_had_won'] * new.dem_had_won - fit['rep_had_won'] * new.rep_had_won
    new['dem_over'] = (x - x.mean()).round(3)
    return new[['year', 'state', 'special', 'dem', 'rep', 'dem2', 'lean', 'dem_over']]


def write(year, out):
    X = TB.load(); X = X[X.year != year]
    pd.concat([X, out['rows']], ignore_index=True).sort_values(['year', 'state', 'special', 'days'], ascending=[True, True, True, False]).to_csv(TB.TRAIN, index=False)
    ch = json.load(open(TB.CHAMBER)); ch[str(year)] = out['chamber']; json.dump(dict(sorted(ch.items())), open(TB.CHAMBER, 'w'), indent=1)
    S = pd.read_csv(TB.SEATS); S = S[S.year != year]
    pd.concat([S, pd.DataFrame([{'year': year, 'days': d, 'seat_model': round(v, 4)} for d, v in out['seat_models'].items()])]).sort_values(['year', 'days'], ascending=[True, False]).to_csv(TB.SEATS, index=False)
    pp = os.path.join(D, 'past_races.csv'); P = pd.read_csv(pp); P = P[P.year != year]
    pd.concat([P, score_past(out['past'])], ignore_index=True).sort_values(['year', 'state', 'special']).to_csv(pp, index=False)
    np_ = os.path.join(D, 'national_fundamentals.csv'); N = pd.read_csv(np_); N = N[N.year != year]
    pd.concat([N, pd.DataFrame([out['national']])], ignore_index=True).sort_values('year').to_csv(np_, index=False)
    if out['pres'] is not None:
        pr = os.path.join(D, 'pres_results.csv'); Q = pd.read_csv(pr) if os.path.exists(pr) else pd.DataFrame()
        pd.concat([Q[Q.year != year] if len(Q) else Q, out['pres']], ignore_index=True).to_csv(pr, index=False)


def due(today):
    """The elections whose results have settled and that are not in the training table yet (from 2028, the first the
    live forecast followed)."""
    have = set(TB.load().year.unique())
    return [y for y in range(2028, today.year + 1, 2) if L.election_day(y) + pd.Timedelta(days=WAIT_DAYS) <= today and y not in have
            and os.path.exists(os.path.join(D, str(y), 'forecast.json'))]


def gather(year, F):
    L.setup(L.election_day(year))
    titles = [L.OVERVIEW, f'{year} United States House of Representatives elections'] + ([f'{year} United States presidential election'] if year % 4 == 0 else [])
    titles += [L.race_title(f['state'], f['special']) for f in F['races']]
    pages = L.fetch(titles)
    links = sorted(set(l for t, p in pages.items() if 'Senate' in t for l in L.polling_links(p['text']) if str(year) in l))
    pages.update(L.fetch(links))
    return pages


def main(years=None, force=False):
    import live_fit as LF, site_data as SD
    today = pd.Timestamp(os.environ.get('SENATE_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    todo = years or due(today)
    if not todo:
        print('No election to add: the last one is in the training table, or its results have not settled yet.'); return []
    done = []
    for year in todo:
        F = json.load(open(os.path.join(D, str(year), 'forecast.json'))); H = pd.read_csv(os.path.join(D, str(year), 'history.csv'), parse_dates=['date'])
        out = build(year, gather(year, F), F, H, today)
        bad = check(year, out, F)
        if bad:
            print(f'{year}: not added yet ({"; ".join(bad)}); the next run tries again.'); continue
        write(year, out)
        LF.main(out_path=os.path.join(D, str(year + 2), 'model.json'))
        SD.main()
        json.dump({'added': str(today.date()), 'races': int((out['rows'].days == 1).sum()), 'chamber': out['chamber'], 'national': out['national'],
                   'past_races': int(len(out['past'])), 'presidential_results': None if out['pres'] is None else int(len(out['pres']))},
                  open(os.path.join(D, str(year), 'after_election.json'), 'w'), indent=1, default=str)
        print(f'{year}: added {int((out["rows"].days == 1).sum())} races and refitted into data/senate/{year + 2}/model.json'); done.append(year)
    return done


if __name__ == '__main__':
    a = sys.argv[1:]
    main([int(a[a.index('--year') + 1])] if '--year' in a else None, '--year' in a)
