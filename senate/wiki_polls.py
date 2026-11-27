"""Reads Senate race polls from Wikipedia's race pages (wikitext), for the Senate forecast's poll feed. Research for now.

Each race page has a table of general-election polls for each matchup. A table is used when its header names both
nominees; every row is one poll question: the pollster, the dates, the sample and the two nominees' shares. Tables of
poll averages ("aggregation") are skipped. A pollster Wikipedia marks with a party, "(D)" or "(R)", is kept with that mark
as partisan. Wikipedia's text is CC BY-SA 4.0.

    parse(text, dem, rep, state)   -> list of polls
"""
import re, unicodedata
import pandas as pd

MONTHS = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
                                      'October', 'November', 'December'], 1)}
AGGREGATORS = re.compile(r'aggregat|270toWin|RealClear|Decision Desk|FiftyPlusOne|Silver Bulletin|Race to the WH|VoteHub average|^Average', re.I)


def top_split(s, sep='|'):
    """Split on sep outside [[...]] and {{...}}."""
    out, depth_l, depth_t, cur, i = [], 0, 0, '', 0
    while i < len(s):
        two = s[i:i + 2]
        if two == '[[': depth_l += 1; cur += two; i += 2; continue
        if two == ']]': depth_l = max(0, depth_l - 1); cur += two; i += 2; continue
        if two == '{{': depth_t += 1; cur += two; i += 2; continue
        if two == '}}': depth_t = max(0, depth_t - 1); cur += two; i += 2; continue
        if s.startswith(sep, i) and not depth_l and not depth_t:
            out.append(cur); cur = ''; i += len(sep); continue
        cur += s[i]; i += 1
    out.append(cur)
    return out


def clean(v):
    v = re.sub(r'<ref[^>]*/>', '', v); v = re.sub(r'<ref[^>]*>.*?</ref>', '', v, flags=re.S)
    v = re.sub(r'\{\{\s*(?:efn|Efn|efn-ua|efn-lr|refn)[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}', '', v)
    v = re.sub(r'\{\{\s*party shading[^}]*\}\}', '', v, flags=re.I); v = re.sub(r'\{\{\s*(?:nbsp|sdash|ndash|mdash)\s*\}\}', ' ', v, flags=re.I)
    v = re.sub(r'\{\{\s*nowrap\s*\|([^}]*)\}\}', r'\1', v, flags=re.I)
    v = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', v); v = re.sub(r'\[https?://\S+\s+([^\]]*)\]', r'\1', v)
    v = re.sub(r"'''?|<br\s*/?>|<wbr\s*/?>|&nbsp;", ' ', v); v = re.sub(r'<[^>]+>', '', v)
    return re.sub(r'\s+', ' ', v).strip()


def cell_value(raw):
    """A cell's content: after its attributes, if any (style=...| value)."""
    parts = top_split(raw, '|')
    if len(parts) > 1 and re.search(r'(style|rowspan|colspan|class|align|bgcolor|data-sort-value)\s*=', parts[0], re.I):
        return parts[0], '|'.join(parts[1:])
    if len(parts) > 1 and not parts[0].strip():
        return '', '|'.join(parts[1:])
    if len(parts) > 1 and re.match(r'\s*\{\{\s*party shading', parts[0], re.I):
        return parts[0], '|'.join(parts[1:])
    return '', raw


def rows_of(table):
    """The table as rows of (attributes, value) cells, with rowspans carried down."""
    chunks = re.split(r'\n\|-[^\n]*', table)
    rows, carry = [], {}
    for ch in chunks:
        cells = []
        for line in ch.split('\n'):
            line = line.rstrip()
            if not line or line.startswith('{|') or line.startswith('|}') or line.startswith('|+'): continue
            if line[0] in '|!':
                sep = '!!' if line[0] == '!' else '||'
                cells += [('!' if line[0] == '!' else '|', c) for c in top_split(line[1:], sep)]
            elif cells:                                                       # a cell continued on the next line
                cells[-1] = (cells[-1][0], cells[-1][1] + '\n' + line)
        if not cells: continue
        row, col, k = [], 0, 0
        while k < len(cells) or col in carry:
            if col in carry:
                v, left = carry[col]; row.append(v)
                if left > 1: carry[col] = (v, left - 1)
                else: del carry[col]
                col += 1; continue
            kind, raw = cells[k]; k += 1
            attr, val = cell_value(raw)
            m = re.search(r'rowspan\s*=\s*"?(\d+)', attr)
            item = (kind, attr, val)
            row.append(item)
            if m and int(m.group(1)) > 1: carry[col] = (item, int(m.group(1)) - 1)
            span = re.search(r'colspan\s*=\s*"?(\d+)', attr)
            for _ in range(int(span.group(1)) - 1 if span else 0): row.append(item); col += 1
            col += 1
        rows.append(row)
    return rows


def end_date(s, default_year=None):
    s = clean(s)
    years = re.findall(r'(19|20)(\d\d)', s)
    y = int(''.join(years[-1])) if years else default_year
    body = s[:s.rfind(''.join(years[-1]))] if years else s
    ms = [(m.start(), m.group(0)) for m in re.finditer('|'.join(MONTHS), body)]
    if not ms or y is None: return None
    pos, mon = ms[-1]
    days = re.findall(r'\b(\d{1,2})\b', body[pos:])
    try:
        return pd.Timestamp(year=y, month=MONTHS[mon], day=int(days[-1]) if days else 15)
    except ValueError:
        return None


def number(v):
    m = re.search(r'(\d+(?:\.\d+)?)\s*%', clean(v))
    return float(m.group(1)) if m else None


def sample(v):
    v = clean(v); n = re.search(r'(\d[\d,]*)', v); p = re.search(r'\((LV|RV|A|V)\)', v, re.I)
    return (int(n.group(1).replace(',', '')) if n else None), (p.group(1).lower() if p else None)


def plain(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()


def surname_in(header, name, side=None):
    """The header names this candidate: the surname, a word before it in the same heading starting like the first name
    (Ed for Edward, Mike for Michael; middle initials allowed), and, when the heading shows a party, the candidate's own
    (so Lindsey Graham is not taken for Darline Graham, nor Dan J. Sullivan (I) for Dan S. Sullivan (R))."""
    h = plain(clean(header)); words = re.findall(r"[A-Z][A-Z'.-]*", h)
    toks = plain(name).split(); last, first = toks[-1], toks[0]
    party = re.search(r'\(([A-Z])\)', h)
    if side and party and party.group(1) != side and not (side == 'D' and party.group(1) == 'I'): return False
    for i, w in enumerate(words):
        if w == last:
            before = words[max(0, i - 3):i]
            return i == 0 or any(x[:2] == first[:2] for x in before) or (len(toks) > 2 and any(x in toks for x in before))
    return False


def dedupe(polls):
    """One row per poll and population: a poll asked several ways (with leaners, ranked-choice rounds, with or without
    minor candidates) keeps the version with the most voters choosing between the two nominees."""
    best = {}
    for p in polls:
        k = (p['state'], p['pollster'], p['end'], p['population'])
        if k not in best or p['dem_pct'] + p['rep_pct'] > best[k]['dem_pct'] + best[k]['rep_pct']: best[k] = p
    return list(best.values())


def parse(text, dem, rep, state, year):
    polls = []
    for table in re.findall(r'\{\|.*?\n\|\}', text, flags=re.S):
        rows = rows_of(table)
        if not rows: continue
        head = [c for c in rows[0] if c[0] == '!'] or rows[0]
        heads = [clean(c[2]) for c in head]
        if any(AGGREGATORS.search(h) for h in heads): continue
        if not heads or 'poll' not in heads[0].lower(): continue
        di = [i for i, h in enumerate(heads) if surname_in(h, dem, 'D')]; ri = [i for i, h in enumerate(heads) if surname_in(h, rep, 'R')]
        if not di or not ri: continue
        di, ri = di[0], ri[0]
        si = next((i for i, h in enumerate(heads) if 'sample' in h.lower()), 2); dt = next((i for i, h in enumerate(heads) if 'date' in h.lower()), 1)
        for r in rows[1:]:
            if len(r) <= max(di, ri): continue
            src = clean(r[0][2])
            if not src or AGGREGATORS.search(src): continue
            d, rr = number(r[di][2]), number(r[ri][2])
            e = end_date(r[dt][2], year)
            if d is None or rr is None or e is None: continue
            n, pop = sample(r[si][2]) if si < len(r) else (None, None)
            party = re.search(r'\((D|R)\)\s*$', src)
            polls.append({'state': state, 'end': e.date().isoformat(), 'n': n, 'population': pop or 'lv',
                          'pollster': re.sub(r'\s*\((D|R)\)\s*$', '', src).strip(), 'partisan': party.group(1) if party else '',
                          'dem_pct': d, 'rep_pct': rr})
    return dedupe(polls)
