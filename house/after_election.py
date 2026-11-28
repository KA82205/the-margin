"""After each House election, on its own: the election's districts become training data and the model is refitted, so the
next cycle's forecast learns from the last one. Run every week by .github/workflows/house-after.yml; it does nothing until
the results have settled (seven weeks after election day, as for the Senate: past the runoffs and the states'
certification) and Wikipedia has every district's result, and nothing again once that election is in the training table.

For the election just held, from Wikipedia (CC BY-SA 4.0):
  1. the year's overview page: each district's lean as Cook published it before the election, the member who held it and
     what became of the seat (re-elected, defeated, retired, lost renomination), the candidates, the winner and, once the
     overview gives them, each candidate's share of the vote;
  2. where the overview has no shares yet, the district's general-election box on its state's page, or on the district's
     own page (California's state page has none);
  3. which states' maps changed for the election (the overview's table of map changes).

Each district becomes a row of data/house/training.csv as house/build_data.py makes them: the member on the November
ballot is read the same way, a runoff's winner wins, Louisiana's all-party first round counts each party's candidates
together; the money columns are left empty, since money is not part of the forecast. Then the model is refitted
(house/fit.py: data/house/model.json and the back-tests).

It checks what it read before writing anything: 435 districts, a winner in each, each party's seats as the overview's box
counts them (a box still giving a range means the count is not over), a share for all but a handful of the districts
both parties contested, shares in range; otherwise it writes nothing and tries again the next week.

    python house/after_election.py                      the elections due and not yet in the table
    python house/after_election.py --year 2026          that election, again if it is already in (its rows are replaced)
    python house/after_election.py --year 2026 --pages FILE.json --test
                                                        reads saved pages (tools/fetch_house_pages.py) and forecasts that
                                                        election from the years before it, scored on the winners; writes
                                                        nothing
"""
import json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import build_data as BD, live as LV, polls as PO, wiki_house as WH

D = os.path.join(ROOT, 'data', 'house')
WAIT_DAYS = 49
ORD = lambda n: f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}'


def election_day(y):
    d = pd.Timestamp(f'{y}-11-01'); return d + pd.Timedelta(days=(7 - d.weekday()) % 7 + 1)


def district_title(y, st, d):
    return f"{y} {WH.NAMES[st]}'s {ORD(d)} congressional district election"


# ----------------------------------------------------------------------------------------------------------- reading
def infobox(text):
    """The page's first infobox, matched brace for brace."""
    i = (text or '').find('{{Infobox')
    if i < 0: return ''
    depth, j = 0, i
    while j < len(text):
        if text.startswith('{{', j): depth += 1; j += 2; continue
        if text.startswith('}}', j):
            depth -= 1; j += 2
            if depth == 0: return text[i:j]
            continue
        j += 1
    return text[i:]


def seats_box(text):
    """Each party's seats after the election as the overview's box gives them: {'D': n, 'R': n}, a range as (low, high)."""
    box = infobox(text); out = {}
    for i in range(1, 6):
        party = re.search(r'\|\s*party%d\s*=\s*([^\n]*)' % i, box); seats = re.search(r'\|\s*seats%d\s*=\s*([^\n]*)' % i, box)
        if not party or not seats: continue
        p = WH.party_code(party.group(1)); v = WH.plain(re.sub(r'\{\{\s*[Ee]fn.*', '', seats.group(1)))
        n = [int(x) for x in re.findall(r'\d+', v)]
        if p in ('D', 'R') and n: out[p] = n[0] if len(n) == 1 else (min(n[:2]), max(n[:2]))
    return out


def gather(year, saved=None):
    """The overview, then the states' pages (titled by how many seats each has, as the overview lists them) and the
    district pages they point to: {title: page}."""
    if saved:
        S = json.load(open(saved)); get = lambda ts: {t: S[t] for t in ts if t in S}
    else:
        get = WH.fetch
    pages = get([WH.overview(year)])
    if WH.overview(year) not in pages: raise RuntimeError(f'The page "{WH.overview(year)}" could not be read')
    one = WH.one_seat(pages[WH.overview(year)]['text'], year)
    pages.update(get([t for t in WH.titles(year, True, one) if t not in pages]))
    links = sorted({t for p in list(pages.values()) for t in PO.main_links(p['text'], year)} - set(pages))
    if links: pages.update(get(links))
    return pages, get


def read(year, pages, get):
    """One row a district: the overview's account, with shares from the states' pages where the overview has none."""
    ov = pages[WH.overview(year)]['text']
    W = pd.DataFrame(WH.rows(ov, year))
    W['C'] = W.candidates_raw.map(WH.candidates)
    W['score'] = W.pvi.notna() * 2 + W.members.map(len) + W.C.map(bool)
    W = W.sort_values('score', ascending=False).groupby(['state', 'district'], as_index=False).first()
    one = set(W.state[W.district == 0])
    secs = {st: WH.district_sections(pages.get(WH.state_title(year, st, st in one), {}).get('text', ''), st, st in one) for st in WH.NAMES}
    # the district pages of districts the overview gives no shares for and their state's page has no section on
    need = []
    for r in W.itertuples():
        gen = [c for c in r.C if c['round'] == 'general']
        if not all(c['share'] is not None for c in gen if c['party'] in ('D', 'R')) and r.district not in secs[r.state]:
            need.append(district_title(year, r.state, r.district))
    extra = get(need) if need else {}
    changes = WH.map_changes(ov)
    rows = []
    for r in W.itertuples():
        gen = [c for c in r.C if c['round'] == 'general']; run = [c for c in r.C if c['round'] == 'runoff']
        sec = secs[r.state].get(r.district) or extra.get(district_title(year, r.state, r.district), {}).get('text')
        gbox, rbox = WH.general_box(sec) if sec else (None, None)
        share = lambda cs, p, k: sum(c[k] for c in cs if c['party'] == p and c[k] is not None) if any(c['party'] == p and c[k] is not None for c in cs) else None
        dv = rv = None; how = None
        ds, rs = share(gen, 'D', 'share'), share(gen, 'R', 'share')
        if gbox:
            dv, rv = share(gbox['candidates'], 'D', 'votes'), share(gbox['candidates'], 'R', 'votes')
            if (ds is None or rs is None) and (dv is None or rv is None):
                ds, rs = share(gbox['candidates'], 'D', 'share'), share(gbox['candidates'], 'R', 'share')
        has_d = any(c['party'] == 'D' for c in gen) or bool(gbox and any(c['party'] == 'D' for c in gbox['candidates']))
        has_r = any(c['party'] == 'R' for c in gen) or bool(gbox and any(c['party'] == 'R' for c in gbox['candidates']))
        contested = has_d and has_r
        if dv and rv: dem2, how = 100 * dv / (dv + rv), 'votes'
        elif ds is not None and rs is not None and ds + rs > 0: dem2, how = 100 * ds / (ds + rs), 'shares'
        else: dem2 = None
        # the winner: the overview's mark (the runoff's, when there was one), the box's, the status's, or the larger share
        won = [c['party'] for c in (run or gen) if c['won']]
        if not won and rbox: won = [c['party'] for c in rbox['candidates'] if c['won']]
        if not won and gbox and not run: won = [c['party'] for c in gbox['candidates'] if c['won']]
        st = r.status or ''
        if not won:
            m = re.search(r'(Democratic|DFL|Republican|Independent)\s+(?:gain|hold)', st)
            if m: won = [WH.party_code(m.group(1))]
            elif re.search(r'[Ii]ncumbent re-?elected', st) and len(r.members) == 1: won = [r.members[0][1]]
        if not won and dem2 is not None and not run and not (gbox and len([c for c in gbox['candidates'] if c['party'] == 'D']) + len([c for c in gbox['candidates'] if c['party'] == 'R']) > 2):
            won = ['D' if dem2 > 50 else 'R']
        if not contested and not won:
            ps = {c['party'] for c in gen} | ({c['party'] for c in gbox['candidates']} if gbox else set())
            if len(ps & {'D', 'R'}) == 1: won = list(ps & {'D', 'R'})
        cand = [(c['name'], c['party']) for c in gen] or ([(c['name'], c['party']) for c in gbox['candidates']] if gbox else [])
        rows.append({'year': year, 'state': r.state, 'district': int(r.district), 'dem': dv if contested and dv else np.nan, 'rep': rv if contested and rv else np.nan,
                     'dem2': round(dem2, 3) if contested and dem2 is not None else np.nan, 'contested': contested, 'winner': won[0] if won else None, 'how': how,
                     'pvi': r.pvi, 'pvi_stale': bool(r.pvi_stale), 'members': list(r.members), 'status': st, 'new_seat': bool(r.new_seat),
                     'moved_from': r.moved if isinstance(r.moved, list) else [], 'candidates': cand,
                     'redrawn': int(changes.get(r.state) == 'enacted' or (year % 10 == 2 and r.state not in one))})
    return pd.DataFrame(rows), ov


def members_on_ballot(R):
    """inc_d, inc_r and moved as build_data.py reads them."""
    inc_d, inc_r, moved = [], [], []
    for r in R.itertuples():
        mem = r.members; st = LV.clean_status(r.status)
        ran = re.search(r're-?elected|lost re-?election|defeated|lost (?:the )?general|ran for re-?election', st, re.I)
        out = re.search(r'retired|renominat|resigned|died|new seat|vacant|ran for (?!re-?election)|to run for', st, re.I)

        def same(n, p):
            for c, cp in r.candidates:
                if cp != p or not (BD.names(n) & BD.names(c)): continue
                f1, f2 = BD.fold(n).split()[0], BD.fold(c).split()[0]
                if f1[:2] == f2[:2] or len(mem) == 1 and ran: return True
            return False
        if len(mem) == 1 and (ran or out) and not (ran and out):
            on = [(mem[0][0], mem[0][1], 0)] if ran else []
        else:
            on = [(n, p, i) for i, (n, p) in enumerate(mem) if same(n, p)]
        inc_d.append(int(any(p == 'D' for _, p, _ in on))); inc_r.append(int(any(p == 'R' for _, p, _ in on)))
        mv = r.moved_from
        moved.append(int(any(i < len(mv) and mv[i] for _, _, i in on)))
    return inc_d, inc_r, moved


def table(year, R, T):
    """The year's rows in the training table's columns."""
    R = R.copy(); R['inc_d'], R['inc_r'], R['moved'] = members_on_ballot(R)
    c = R[R.contested & R.dem.notna() & R.rep.notna()]
    known = R[R.contested & R.dem2.notna()]
    # the Democratic share of the two parties' votes in the districts both contested: from the votes where the pages give
    # them, the rest at their share with the average district's vote
    if len(c) == len(known): nat = 100 * c.dem.sum() / (c.dem.sum() + c.rep.sum())
    else:
        avg = float((c.dem + c.rep).mean()) if len(c) else 1.0
        tot = (known.dem + known.rep).where(known.dem.notna() & known.rep.notna(), avg)
        nat = float((known.dem2 * tot).sum() / tot.sum())
    R['national'] = round(nat, 6)
    prev = T[T.year == year - 2].set_index(['state', 'district'])
    R['prev'] = [(prev.at[(s, d), 'dem2'] - prev.at[(s, d), 'national']) if (s, d) in prev.index and not rd else np.nan for s, d, rd in zip(R.state, R.district, R.redrawn)]
    for col in ('dem_money', 'rep_money', 'dem_fec', 'rep_fec'): R[col] = np.nan if 'money' in col else None
    cols = ['year', 'state', 'district', 'dem', 'rep', 'dem2', 'contested', 'winner', 'pvi', 'pvi_stale', 'inc_d', 'inc_r', 'moved', 'redrawn', 'new_seat', 'prev',
            'dem_money', 'rep_money', 'dem_fec', 'rep_fec', 'national']
    return R[cols].sort_values(['state', 'district']).reset_index(drop=True)


def check(year, R, ov, strict=True):
    """What must hold before the year goes into training; a list of what does not."""
    bad = []
    if len(R) != 435: bad.append(f'{len(R)} districts')
    if R.winner.isna().any(): bad.append(f'{int(R.winner.isna().sum())} districts without a winner: ' + ', '.join(f'{s}-{d}' for s, d in zip(R.state[R.winner.isna()], R.district[R.winner.isna()]))[:300])
    box = seats_box(ov); won = R.winner.value_counts().to_dict()
    for p in ('D', 'R'):
        b = box.get(p)
        if b is None: bad.append(f'no seat count for {p} in the overview\'s box')
        elif isinstance(b, tuple): bad.append(f'the overview still gives {p} a range of seats ({b[0]}-{b[1]})')
        elif won.get(p, 0) != b: bad.append(f'{won.get(p, 0)} {p} winners read against {b} in the overview\'s box')
    c = R[R.contested]; miss = c.dem2.isna()
    if miss.sum() > (4 if strict else 435): bad.append(f'{int(miss.sum())} contested districts without a share')
    if ((c.dem2 < 1) | (c.dem2 > 99)).any(): bad.append('a share out of range')
    if R.pvi.isna().sum() > 5: bad.append(f'{int(R.pvi.isna().sum())} districts without a lean')
    return bad


# ----------------------------------------------------------------------------------------------------------- testing
def earlier_years(year):
    """The years the model is fitted on that come before this one (house/fit.py's rule)."""
    import fit, simulate as S
    return [y for y in fit.years_fitted(S.load(cook75=True)) if y < year]


def year_polls(year, pages, R):
    """The year's district polls of its two nominees (each district's Democrat and Republican on the November ballot),
    averaged at each distance from election day, into data/house/polls_by_date.csv (its rows for the year replaced)."""
    nominees = {}
    for r in R.itertuples():
        dm = [n for n, p in r.candidates if p == 'D']; rp = [n for n, p in r.candidates if p == 'R']
        if len(dm) == 1 and len(rp) == 1: nominees[(r.state, int(r.district))] = (dm[0], rp[0])
    P = PO.from_pages(pages, year, nominees)
    A = PO.averages(P, year) if len(P) else pd.DataFrame(columns=['year', 'state', 'district', 'days', 'poll', 'poll_w', 'polls'])
    p = os.path.join(D, 'polls_by_date.csv'); old = pd.read_csv(p) if os.path.exists(p) else A.iloc[:0]
    pd.concat([old[old.year != year], A], ignore_index=True).sort_values(['year', 'state', 'district', 'days'], ascending=[True, True, True, False]).to_csv(p, index=False)
    print(f'{year}: {len(P)} district polls ({int((P.partisan.fillna("") == "").sum()) if len(P) else 0} not partisan) in {A[["state", "district"]].drop_duplicates().shape[0]} districts')
    return A


def test(year, R):
    """The forecast of the year from the years before it (none of it fitted on the year), at each distance, scored on
    the seats each party won and on each race's winner. The leans as published for the year's lines; the year's polls as
    year_polls() saved them."""
    import simulate as S
    T = S.load(cook75=True)
    R = R.copy(); R['lean'] = R.pvi; R['lean_from'] = np.where(R.pvi.notna() & ~R.pvi_stale.astype(bool), 'published', None)
    R['usable'] = R.contested & R.lean.notna() & R.lean_from.notna()
    T2 = pd.concat([T, R], ignore_index=True, sort=False)
    r = S.run(['lean', 'inc_d', 'inc_r'], T0=T2, tests=[year], train=earlier_years(year), polls=True)
    return r


def given_vote(year, R):
    """The seats the districts give once the national House vote is known: the fit on the years before, the year's
    level at its House vote plus the usual gap."""
    import simulate as S
    T = S.load(cook75=True); tr = earlier_years(year)
    w, lev, sd = S.fit(T, tr, ['lean', 'inc_d', 'inc_r'])
    nv = S.national().drop_duplicates('year').set_index('year').vote
    level = float(nv[year] + np.mean([lev[z] - nv[z] for z in tr]))
    R = R.assign(lean=R.pvi); m = R.contested & R.lean.notna()
    f = level + R[['lean', 'inc_d', 'inc_r']].fillna(0).values @ w
    return {'vote': float(nv[year]), 'level': round(level, 3), 'seats': int((f[m.values] > 50).sum() + (R.winner[~R.contested] == 'D').sum())}


def save_test(year, R, r):
    """The test of a year read before all its shares were in, kept in data/house/backtest.json until the year joins
    the training table and the back-tests proper."""
    bp = os.path.join(D, 'backtest.json'); B = json.load(open(bp)) if os.path.exists(bp) else {}
    B.setdefault('tests', {})[str(year)] = {
        'note': f'{year} forecast from the elections before it ({", ".join(str(y) for y in earlier_years(year))}), none of it fitted on {year}; scored on the winners as Wikipedia gave them on the day read',
        'read': str(pd.Timestamp.now(tz='America/New_York').date()), 'undecided': int(R.winner.isna().sum()),
        'dem_won': int((R.winner == 'D').sum()), 'rep_won': int((R.winner == 'R').sum()), 'given_vote': given_vote(year, R),
        'rows': r[['days', 'seats_mid', 'actual', 'low80', 'high80', 'p_majority', 'called', 'races', 'brier', 'level']].round(4).to_dict('records')}
    with open(bp, 'w') as f: json.dump(B, f, indent=1)
    print('saved the test of', year, 'to', bp)


# ----------------------------------------------------------------------------------------------------------- main
def due(today, T):
    have = set(T.year)
    return [y for y in range(2026, today.year + 1, 2) if y not in have and today >= election_day(y) + pd.Timedelta(days=WAIT_DAYS)]


def add(year, saved=None, strict=True):
    tp = os.path.join(D, 'training.csv'); T = pd.read_csv(tp, dtype={'dem_fec': str, 'rep_fec': str})
    pages, get = gather(year, saved)
    R, ov = read(year, pages, get)
    bad = check(year, R, ov, strict)
    if bad:
        print(f'{year}: not added yet: ' + '; '.join(bad)); return False
    new = table(year, R, T)
    T = pd.concat([T[T.year != year], new], ignore_index=True).sort_values(['year', 'state', 'district'])
    T.to_csv(tp, index=False)
    year_polls(year, pages, R)
    # the members: how many held a seat, how many were on the November ballot and how many lost their primary
    mp = os.path.join(D, 'members.csv'); M = pd.read_csv(mp)
    st = R.status.map(LV.clean_status)
    row = {'year': year, 'members': int(R.members.map(len).sum()), 'seats_with_member': int((R.members.map(len) > 0).sum()),
           'on_ballot': int((new.inc_d + new.inc_r).clip(upper=2).sum()), 'lost_primary': int(st.str.contains(r'lost (?:re-?)?nomination|lost (?:the )?primary', case=False).sum())}
    pd.concat([M[M.year != year], pd.DataFrame([row])], ignore_index=True).sort_values('year').to_csv(mp, index=False)
    print(f'{year}: {len(new)} districts added; seats', new.winner.value_counts().to_dict())
    import fit
    fit.main()
    return True


def main(argv):
    a = argv[1:]
    year = int(a[a.index('--year') + 1]) if '--year' in a else None
    saved = a[a.index('--pages') + 1] if '--pages' in a else None
    if '--test' in a:
        pages, get = gather(year, saved); R, ov = read(year, pages, get)
        print('checks:', check(year, R, ov) or 'all pass')
        new = table(year, R, pd.read_csv(os.path.join(D, 'training.csv')))
        print('winners:', new.winner.value_counts().to_dict(), '| shares for', int(new.dem2.notna().sum()), 'of', int(new.contested.sum()), 'contested | members on the ballot: D', int(new.inc_d.sum()), 'R', int(new.inc_r.sum()))
        year_polls(year, pages, R)
        r = test(year, new)
        print(r[['year', 'days', 'seats_mid', 'actual', 'low80', 'high80', 'p_majority', 'called', 'races', 'brier', 'level']].round(3).to_string(index=False))
        if '--save' in a: save_test(year, new, r)
        return r
    today = pd.Timestamp(os.environ.get('HOUSE_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    T = pd.read_csv(os.path.join(D, 'training.csv'))
    years = [year] if year else due(today, T)
    if not years: print('No House election is due to be added.'); return
    for y in years: add(y, saved)


if __name__ == '__main__':
    main(sys.argv)
