"""Reads Wikipedia's page of a House election ("<year> United States House of Representatives elections"). Each state's
section holds a table of its districts: the lean as Cook published it before the election (the PVI, in points for the
Democrats: R+7 is -7), the member who held the seat, their party, the year they were first elected, what became of
the seat, and the candidates. One row a district:

    rows(text, year) -> [{'state', 'district', 'pvi', 'pvi_stale', 'members': [(name, party)], 'status', 'new_seat', 'candidates'}]

district is the number, or 0 for a state's single at-large seat. pvi_stale marks a lean the page notes was published
before the map in use was drawn (2024's redrawn states), so it describes other lines. members lists the members who
held the seat (two when redistricting put two members in one district); status is what the page says became of the seat
("Incumbent re-elected.", "Incumbent retired. ...", "Incumbent's intent unknown"); candidates is the candidates' cell as
text.
"""
import re

STATES = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL',
          'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
          'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
          'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
          'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
          'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'}
PARTY = {'democratic': 'D', 'republican': 'R', 'independent': 'I', 'libertarian': 'L', 'democratic–farmer–labor': 'D', 'dfl': 'D'}


def plain(s):
    """What a wiki cell shows: links, templates, references and markup reduced to text."""
    s = re.sub(r'<ref[^>]*/>|<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    for _ in range(3): s = re.sub(r'\{\{\s*[Ee]fn[^{}]*\}\}', '', s)
    s = re.sub(r'\{\{\s*[Ss]ortname\s*\|([^|}]*)\|([^|}]*)[^}]*\}\}', r'\1 \2', s)
    s = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', s); s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\{\{\s*(?:[Ss]mall|[Nn]owrap|[Ss]ort|[Nn]obr)\s*\|(?:[^|{}]*\|)?([^{}]*)\}\}', r'\1', s)
    for _ in range(3): s = re.sub(r'\{\{[^{}]*\}\}', '', s)
    s = re.sub(r"'''?|<br\s*/?>|<[^>]+>", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def pvi(cell):
    m = re.search(r'[Ss]hading PVI\s*\|\s*([DR])\s*\|\s*([\d.]+)', cell) or re.search(r'\b([DR])\s*\+\s*([\d.]+)', cell)
    if m: return float(m.group(2)) * (1 if m.group(1) == 'D' else -1)
    if re.search(r'EVEN', cell, re.I): return 0.0
    return None


def party_of(text):
    t = plain(text).lower().strip(' .')
    return PARTY.get(t) or (PARTY.get(re.sub(r'[^a-z–-]', '', t)) if len(t) < 30 else None)


def content(raw):
    """A cell's content without its attributes (style=... | content)."""
    m = re.match(r'^\s*((?:style|class|rowspan|colspan|align|valign|nowrap|data-sort-value|scope)\b[^|\[\]{}]*?)\|(?!\|)(.*)$', raw, re.S)
    if m: return m.group(2)
    m = re.match(r'^\s*(nowrap)\s*\|(.*)$', raw, re.S)
    return m.group(2) if m else raw


def cells(chunk):
    out = []
    for line in chunk.split('\n'):
        t = line.rstrip()
        if t.startswith(('|-', '|}', '{|', '|+')): continue
        if t.startswith(('|', '!')):
            for c in re.split(r'\|\||!!', t[1:]): out.append(content(c))
        elif out and t.strip(): out[-1] += '\n' + t
    return out


def kind(c):
    p = plain(c)
    if re.search(r'Plainlist|plainlist|Party stripe|party stripe|^\s*\*|\bTBD\b|TBA', c): return 'candidates'
    if pvi(c) is not None and re.search(r'PVI|[DR]\s*\+\s*\d|EVEN', c): return 'pvi'
    if re.search(r'Incumbent|New seat|New member|seat (?:was|eliminated)|Vacant|died|resigned|retired|renominat|re-elected|special election|intent', p, re.I) and len(p) > 6: return 'status'
    if party_of(c) or re.search(r'Party shading', c, re.I) and len(p) < 25: return 'party'
    if re.match(r'^\d{4}\b', p) or re.match(r'^\(?\d{4}', p): return 'year'
    if re.search(r'None \(|^None$|^Vacant$|new district', p, re.I): return 'none'
    return 'name' if p and len(p) < 70 else 'other'


def rows(text, year):
    secs = re.split(r'\n==\s*([A-Z][A-Za-z ]+?)\s*==\s*\n', text); out = []
    for i in range(1, len(secs), 2):
        st = STATES.get(secs[i].strip())
        if not st: continue
        body = secs[i + 1]
        # the districts' table: from its first district row to the table's end (some tables open with a template)
        first = re.search(r'\n[!|][^\n]*\{\{\s*ushr', body, re.I)
        if not first: continue
        e = re.compile(r'\n\|\}(?!\})').search(body, first.start()); table = body[first.start():e.start() if e else len(body)]   # not a template's |}}
        cur = None
        for chunk in re.split(r'\n\|-[^\n]*', table):
            u = re.search(r'^[!|][^\n]*?\{\{\s*ushr\s*\|\s*([^|}]+?)\s*\|\s*([^|}]+)', chunk.strip('\n'), re.I)
            cs = cells(chunk)
            if u:
                dist = u.group(2).strip(); d = 0 if re.match(r'(?i)al|at', dist) else int(re.sub(r'\D', '', dist) or 0)
                if STATES.get(u.group(1).strip(), u.group(1).strip().upper()) != st: continue           # a row of another state's table
                cur = {'state': st, 'district': d, 'pvi': None, 'pvi_stale': False, 'members': [], 'status': '', 'new_seat': False, 'candidates': ''}
                out.append(cur); cs = cs[1:] if cs and 'ushr' in cs[0] else [c for c in cs if not re.match(r'\s*\{\{\s*ushr', c)]
            elif cur is None:
                continue
            for c in cs:
                k = kind(c)
                if k == 'pvi' and cur['pvi'] is None:
                    cur['pvi'] = pvi(c); cur['pvi_stale'] = bool(re.search(r'[Ee]fn', c)) and year >= 2024
                elif k == 'name' and not party_of(c):
                    moved = re.search(r'[Rr]edistricted from[^{]*\{\{\s*ushr\s*\|\s*([^|}]+?)\s*\|\s*([^|}]+)', c)
                    cur['members'].append([plain(re.sub(r'<br\s*/?>.*', '', c, flags=re.S)), None]); cur.setdefault('moved', []).append(moved.group(2).strip() if moved else None)
                elif k == 'party' and cur['members'] and cur['members'][-1][1] is None:
                    cur['members'][-1][1] = party_of(c) or party_of(re.sub(r'.*Party shading/(?:Text/)?([A-Za-z]+).*', r'\1', c, flags=re.S | re.I))
                elif k == 'status':
                    cur['status'] = (cur['status'] + ' ' + plain(c)).strip()
                elif k == 'none':
                    cur['new_seat'] = True
                elif k == 'candidates':
                    cur['candidates'] = (cur['candidates'] + '\n' + plain(c.replace('*', '\n*'))).strip()
    for r in out:
        r['members'] = [tuple(m) for m in r['members']]
        if re.search(r'New seat|new district', r['status'], re.I) and not r['members']: r['new_seat'] = True
    return out
