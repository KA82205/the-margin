"""Every general-election poll on a Senate race's Wikipedia pages, with each candidate's share, for the site's Polls tab.
Which of them the forecast counts is decided by wiki_polls.parse (the nominees' own matchup, polls paid for by a party
or a campaign left out), as in training; this module only lists them, and live.py says why a poll is not counted.

A table is a general-election table when its candidate columns, marked with their parties as Wikipedia writes them
("Jon Ossoff (D)"), hold at least one Democrat or independent and one Republican; a primary's table, all one party, is
not. Wikipedia's text is CC BY-SA 4.0.

    matchups(text, state, year) -> [{'state', 'pollster', 'partisan', 'end', 'n', 'pop', 'cands': [{'name', 'party', 'pct'}]}]
"""
import re
import wiki_polls as WP

PARTY = {'D': 'D', 'DFL': 'D', 'R': 'R', 'I': 'I', 'IND': 'I', 'IND.': 'I', 'L': 'L', 'LIB': 'L', 'LIB.': 'L', 'G': 'G', 'GRN': 'G', 'GRN.': 'G'}
TAG = re.compile(r'^(.*?)\s*\((D|DFL|R|I|Ind\.?|L|Lib\.?|G|Grn\.?)\)\s*$', re.I)


def candidates(heads):
    """[(column, name, party)] for the headings that name a candidate with a party."""
    out = []
    for i, h in enumerate(heads):
        m = TAG.match(h)
        if i and m and m.group(1).strip():
            out.append((i, m.group(1).strip(), PARTY[m.group(2).upper()]))
    return out


def matchups(text, state, year):
    seen = {}
    for table in re.findall(r'\{\|.*?\n\|\}', text or '', flags=re.S):
        rows = WP.rows_of(table)
        if not rows: continue
        head = [c for c in rows[0] if c[0] == '!'] or rows[0]
        heads = [WP.clean(c[2]) for c in head]
        if not heads or 'poll' not in heads[0].lower() or any(WP.AGGREGATORS.search(h) for h in heads): continue
        cands = candidates(heads)
        parties = {p for _, _, p in cands}
        if not ({'D', 'I'} & parties and 'R' in parties): continue          # a primary's table, or not a matchup
        si = next((i for i, h in enumerate(heads) if 'sample' in h.lower()), None); dt = next((i for i, h in enumerate(heads) if 'date' in h.lower()), 1)
        for r in rows[1:]:
            if len(r) <= max(i for i, _, _ in cands): continue
            src = WP.clean(r[0][2])
            if not src or WP.AGGREGATORS.search(src): continue
            e = WP.end_date(r[dt][2], year) if dt < len(r) else None
            vals = [{'name': nm, 'party': pt, 'pct': WP.number(r[i][2])} for i, nm, pt in cands]
            vals = [v for v in vals if v['pct'] is not None]
            if e is None or len(vals) < 2: continue
            n, pop = WP.sample(r[si][2]) if si is not None and si < len(r) else (None, None)
            tag = re.search(r'\((D|R)\)\s*$', src)
            poll = {'state': state, 'pollster': re.sub(r'\s*\((D|R)\)\s*$', '', src).strip(), 'partisan': tag.group(1) if tag else '',
                    'end': e.date().isoformat(), 'n': n, 'pop': (pop or 'lv').lower(), 'cands': vals}
            # one row per pollster, end date, population and matchup: the version with the most named support (leaners
            # pushed), as wiki_polls.dedupe keeps for the forecast
            key = (poll['pollster'], poll['end'], poll['pop'], tuple(sorted(v['name'] for v in vals)))
            total = sum(v['pct'] for v in vals)
            if key not in seen or total > seen[key][0]: seen[key] = (total, poll)
    return sorted((p for _, p in seen.values()), key=lambda p: (p['end'], p['pollster']), reverse=True)
