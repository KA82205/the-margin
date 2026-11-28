"""District polls for the House forecast: each district's polling average as it stood at each distance from election day,
weighed as the presidential model weighs polls (how recent, how large, of whom, and a pollster's older polls for less),
partisan polls (paid for by a party, a party committee or a campaign) left out, and only polls of the two nominees.

    2018-2024  FiveThirtyEight's House polls (CC BY 4.0), from the archived copy in github.com/jcervas/data (commit
               27d7b352bcf0361498f249a556656bb1535c0e32), saved by tools/fetch_house_polls.py as
               data/house/raw/538_house_polls_historical.csv and kept out of the repository
    later      Wikipedia's pages of each election (CC BY-SA 4.0): the general-election poll tables in each district's part
               of its state's page and on the district's own page (house/after_election.py adds each year once it is
               over; house/live.py reads the coming election's every hour)

    python house/polls.py      writes data/house/polls_by_date.csv: year, state, district, days, poll (the Democratic
                               share of the two nominees' support), poll_w (the average's total weight), polls
"""
import os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE); sys.path.append(os.path.join(ROOT, 'senate'))
import wiki_house as WH
import wiki_polls as WP          # the Senate's reader of Wikipedia's poll tables (senate/wiki_polls.py)

D = os.path.join(ROOT, 'data', 'house')
DAYS = [365, 250, 120, 60, 30, 14, 7, 1]
RAW_538 = os.path.join(D, 'raw', '538_house_polls_historical.csv')
POP = {'lv': 'lv', 'rv': 'rv', 'v': 'rv', 'a': 'a'}
# a pollster that is a party, a party committee or a campaign, and a footnote saying one paid for the poll
PARTY_POLLSTER = re.compile(r'\b(?:DCCC|NRCC|DNC|RNC|DSCC|NRSC|House Majority (?:PAC|Forward)|Congressional Leadership Fund|Democratic Party|Republican Party|'
                            r'for Congress|campaign)\b', re.I)
SPONSOR = re.compile(r'(?:sponsored|commissioned|paid for|conducted)\s+(?:by|for)\b[^}]*?\b(?:Democrat|Republican|DCCC|NRCC|DNC|RNC|campaign|for Congress|PAC|Party|'
                     r'Majority Forward|Leadership Fund)', re.I)


def election_day(y):
    d = pd.Timestamp(f'{y}-11-01'); return d + pd.Timedelta(days=(7 - d.weekday()) % 7 + 1)


# ----------------------------------------------------------------------------------------------- FiveThirtyEight's polls
def from_538(path=RAW_538, one_seat=None):
    """One row a poll question of a Democrat against a Republican in a general election: year, state, district, end, n,
    population, pollster, partisan ('D', 'R' or ''), dem_pct, rep_pct. one_seat: {(year, state)} of states with a single
    seat that year, written as district 0."""
    d = pd.read_csv(path, low_memory=False)
    d = d[(d.stage == 'general') & (d.hypothetical.astype(str).str.lower() != 'true')].copy()
    d['st'] = d.state.map(WH.STATES); d = d[d.st.notna()]
    rows = []
    for _, g in d.groupby('question_id'):
        dm, rp = g[g.party == 'DEM'], g[g.party == 'REP']
        if len(dm) != 1 or len(rp) != 1: continue
        r = g.iloc[0]; y = int(r.cycle)
        rows.append({'year': y, 'state': r.st, 'district': 0 if one_seat and (y, r.st) in one_seat else int(r.seat_number), 'end': r.end_date, 'n': r.sample_size,
                     'population': str(r.population).lower(), 'pollster': str(r.pollster), 'partisan': {'DEM': 'D', 'REP': 'R'}.get(r.partisan, 'P' if isinstance(r.partisan, str) and r.partisan else ''),
                     'dem_pct': float(dm.pct.iloc[0]), 'rep_pct': float(rp.pct.iloc[0])})
    P = pd.DataFrame(rows)
    P['end'] = pd.to_datetime(P.end, format='mixed').dt.date.astype(str)
    return dedupe(P)


def dedupe(P):
    """One row a poll and population: a poll asked several ways keeps the version with the most voters choosing between
    the two nominees (as the Senate's reader does)."""
    if P.empty: return P
    P = P.assign(both=P.dem_pct + P.rep_pct).sort_values('both', ascending=False)
    return P.drop_duplicates(['year', 'state', 'district', 'pollster', 'end', 'population']).drop(columns='both').reset_index(drop=True)


# ----------------------------------------------------------------------------------------------- Wikipedia's polls
def general_part(text):
    """The general election's part of a district's stretch of a page: from its heading on, or all of it without one."""
    m = re.search(r'\n=+\s*General election\s*=+', text or '', re.I)
    return (text or '')[m.start():] if m else (text or '')


def parse(text, dem, rep, state, district, year):
    """The polls of the two nominees in a stretch of a page, as the Senate's reader finds them (a table whose heading
    names both, poll averages skipped), with a poll marked partisan when Wikipedia writes (D) or (R) after the pollster,
    when a footnote says a party, a committee or a campaign paid for it, or when the pollster is one."""
    polls = []
    heads_all = re.findall(r'\n!([^\n]*)', text)
    loose = {}
    for side, nm in (('D', dem), ('R', rep)):
        last = WP.name_parts(nm)[1]
        firsts = set().union(*[WP.given_before(h, last) for h in heads_all]) if heads_all else set()
        loose[side] = len(firsts) <= 1
    for table in re.findall(r'\{\|.*?\n\|\}', text, flags=re.S):
        rows = WP.rows_of(table)
        if not rows: continue
        head = [c for c in rows[0] if c[0] == '!'] or rows[0]
        heads = [WP.clean(c[2]) for c in head]
        if not heads or any(WP.AGGREGATORS.search(h) for h in heads) or 'poll' not in heads[0].lower(): continue
        di = [i for i, h in enumerate(heads) if WP.surname_in(h, dem, 'D')] or [i for i, h in enumerate(heads) if loose['D'] and WP.surname_in(h, dem, 'D', True)]
        ri = [i for i, h in enumerate(heads) if WP.surname_in(h, rep, 'R')] or [i for i, h in enumerate(heads) if loose['R'] and WP.surname_in(h, rep, 'R', True)]
        if not di or not ri or di[0] == ri[0]: continue
        di, ri = di[0], ri[0]
        si = next((i for i, h in enumerate(heads) if 'sample' in h.lower()), 2); dt = next((i for i, h in enumerate(heads) if 'date' in h.lower()), 1)
        for r in rows[1:]:
            if len(r) <= max(di, ri, dt): continue
            raw = r[0][2]; src = WP.clean(raw)
            if not src or WP.AGGREGATORS.search(src): continue
            dv, rv = WP.number(r[di][2]), WP.number(r[ri][2]); e = WP.end_date(r[dt][2], year)
            if dv is None or rv is None or e is None or dv + rv <= 0: continue
            n, pop = WP.sample(r[si][2]) if si < len(r) else (None, None)
            mark = re.search(r'\((D|R)\)\s*$', src); name = re.sub(r'\s*\((D|R)\)\s*$', '', src).strip()
            partisan = mark.group(1) if mark else ('P' if SPONSOR.search(raw) or PARTY_POLLSTER.search(name) else '')
            polls.append({'year': year, 'state': state, 'district': district, 'end': e.date().isoformat(), 'n': n, 'population': pop or 'lv',
                          'pollster': name, 'partisan': partisan, 'dem_pct': dv, 'rep_pct': rv})
    return polls


def main_links(text, year):
    """The district's own pages that its stretch of the state's page points to ({{main|...}})."""
    return sorted(set(t.strip() for t in re.findall(r'\{\{\s*[Mm]ain\s*\|\s*([^}|]+)', text or '') if str(year) in t and 'congressional district' in t))


def from_pages(pages, year, nominees):
    """Every district's polls of its two nominees in a year's pages: nominees is {(state, district): (dem, rep)}. pages
    holds the state pages and the district pages they point to ({title: {'text'}})."""
    out = []
    for st in sorted({s for s, _ in nominees}):
        text = next((p['text'] for t, p in pages.items() if t.endswith(' in ' + WH.NAMES[st]) and ' House of Representatives election' in t), '')
        secs = WH.district_sections(text, st, any(d == 0 for s, d in nominees if s == st)) if text else {}
        for (s, d), (dem, rep) in nominees.items():
            if s != st or not dem or not rep: continue
            sec = secs.get(d, '') if len(secs) > 1 or d == 0 else ''
            parts = [general_part(sec)] + [general_part(pages[t]['text']) for t in main_links(sec, year) if t in pages]
            for part in parts:
                out += parse(part, dem, rep, st, d, year)
    P = pd.DataFrame(out, columns=['year', 'state', 'district', 'end', 'n', 'population', 'pollster', 'partisan', 'dem_pct', 'rep_pct'])
    return dedupe(P)


# ----------------------------------------------------------------------------------------------- averages
def prepared(P):
    P = P.copy()
    P['end'] = pd.to_datetime(P.end, format='mixed'); P['n'] = pd.to_numeric(P.n, errors='coerce').fillna(400).clip(lower=50)
    P['pop'] = P.population.map(POP).fillna('rv'); P['x'] = 100 * P.dem_pct / (P.dem_pct + P.rep_pct)
    return P[P.partisan.fillna('') == '']


def average(g, asof, d_out):
    """(average, total weight, polls counted) of the polls finished by asof, in the presidential model's weights; None
    when none counts."""
    import model as M
    t = g[g.end <= asof]
    if not len(t): return None
    w = M.weights(t[['end', 'n', 'pop', 'pollster']].reset_index(drop=True), asof, d_out)
    if w.sum() <= 0: return None
    return float((w * t.x.values).sum() / w.sum()), float(w.sum()), int((w > 0).sum())


def averages(P, year, days=DAYS):
    """Each district's average at each distance from election day: rows of year, state, district, days, poll, poll_w, polls."""
    P = prepared(P[P.year == year]); eday = election_day(year); out = []
    for (st, d), g in P.groupby(['state', 'district']):
        for dd in days:
            a = average(g, eday - pd.Timedelta(days=dd), dd)
            if a: out.append({'year': year, 'state': st, 'district': int(d), 'days': dd, 'poll': round(a[0], 3), 'poll_w': round(a[1], 4), 'polls': a[2]})
    return pd.DataFrame(out, columns=['year', 'state', 'district', 'days', 'poll', 'poll_w', 'polls'])


def main():
    T = pd.read_csv(os.path.join(D, 'training.csv'))
    one = set(map(tuple, T[T.district == 0][['year', 'state']].values))
    P = from_538(RAW_538, one)
    A = pd.concat([averages(P, y) for y in sorted(P.year.unique()) if y in set(T.year)], ignore_index=True)
    p = os.path.join(D, 'polls_by_date.csv')
    if os.path.exists(p):                                          # years added from Wikipedia after an election stay
        old = pd.read_csv(p); A = pd.concat([old[~old.year.isin(A.year.unique())], A], ignore_index=True)
    A.sort_values(['year', 'state', 'district', 'days'], ascending=[True, True, True, False]).to_csv(p, index=False)
    print(A.groupby(['year', 'days']).size().unstack().to_string())


if __name__ == '__main__':
    main()
