"""Reads Wikipedia's page of a House election ("<year> United States House of Representatives elections"). Each state's
section holds a table of its districts: the lean as Cook published it before the election (the PVI, in points for the
Democrats: R+7 is -7), the member who held the seat, their party, the year they were first elected, what became of
the seat, and the candidates. One row a district:

    rows(text, year) -> [{'state', 'district', 'pvi', 'pvi_stale', 'members': [(name, party)], 'status', 'new_seat', 'candidates'}]

district is the number, or 0 for a state's single at-large seat. pvi_stale marks a lean the page notes was published
before the map in use was drawn (2024's redrawn states), so it describes other lines. members lists the members who
held the seat (two when redistricting put two members in one district); status is what the page says became of the seat
("Incumbent re-elected.", "Incumbent retired. ...", "Incumbent's intent unknown"); candidates is the candidates' cell as
text, and candidates_raw the cell as written (its winner marks and shares; candidates() reads them).

Also: fetch() reads pages through Wikipedia's API; titles() names a year's overview and state pages; map_changes()
reads the overview's table of the states whose maps changed for the election.
"""
import json, re, time, urllib.error, urllib.parse, urllib.request

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
                    cur['candidates_raw'] = (cur.get('candidates_raw', '') + '\n' + c).strip()
    for r in out:
        r.setdefault('candidates_raw', '')
        r['members'] = [tuple(m) for m in r['members']]
        if re.search(r'New seat|new district', r['status'], re.I) and not r['members']: r['new_seat'] = True
    return out


# ------------------------------------------------------------------------------------------------------------ the cells
def party_code(s):
    """D, R, I or L from a party as a cell or a party stripe writes it ("Republican/Cons.", "DFL", "Democratic Party (US)")."""
    t = fold_plain(s)
    if re.search(r'democratic|\bdfl\b|farmer', t): return 'D'
    if re.search(r'republican|\bgop\b', t): return 'R'
    if re.search(r'libertarian', t): return 'L'
    if t: return 'I'
    return None


def fold_plain(s):
    return plain(str(s or '')).lower()


def number(s):
    m = re.search(r'\d[\d,]*(?:\.\d+)?', plain(str(s or '')).replace(' ', ''))
    return float(m.group(0).replace(',', '')) if m else None


def candidates(raw):
    """Each candidate in a district's candidates cell, as the overview writes them once the votes are in:
    [{'name', 'party', 'share' (per cent, or None before the count), 'won' (marked as the winner), 'runoff' (marked as
    going on to a runoff), 'round' ('general', or 'runoff' for those listed under a runoff)}]. One candidate a line, in
    every form the overview uses (a plain list, a collapsible list); a cell that only says the seat is to be decided
    gives []."""
    out, rnd = [], 'general'
    for line in (raw or '').split('\n'):
        p = plain(line).strip(' *|')
        if re.match(r'(?i)^(?:runoff|second round|general election runoff)\b', p): rnd = 'runoff'; continue
        if re.match(r'(?i)^(?:general election|first round)\b', p): rnd = 'general'; continue
        m = re.search(r'^(.*?)\(([^()]+)\)\s*(?:([\d.]+)\s*%)?', p)
        if not m or not m.group(1).strip(): continue
        stripe = re.search(r'[Pp]arty stripe\s*\|\s*([^}|]+)', line)
        party = party_code(m.group(2).split('/')[0]) or (party_code(stripe.group(1)) if stripe else None)
        out.append({'name': m.group(1).strip(' *'), 'party': party, 'share': float(m.group(3)) if m.group(3) else None,
                    'won': bool(re.search(r'\{\{\s*[Aa]ye\s*\}\}', line)) or bool(re.search(r"'''\s*\[\[", line)),
                    'runoff': bool(re.search(r'\{\{\s*mby\s*\}\}', line, re.I)), 'round': rnd})
    return out


def map_changes(text):
    """The overview's table of the states' maps for the election ("Summary district map changes", "Summary of mid-decade
    changes"): {state: 'enacted' | 'pending' | 'in place'}. A state the table does not list keeps its map."""
    out = {}
    for t in re.finditer(r'\n\{\|(.*?)\n\|\}', text or '', re.S):
        body = t.group(1)
        if not re.search(r'!\s*rowspan=\d\s*\|\s*Status', body) or not re.search(r'[Cc]hange in partisanship', body): continue
        for row in re.split(r'\n\|-[^\n]*', body):
            st = re.search(r'^!\s*\[\[#([^|\]]+)', row.strip(), re.M)
            if not st or st.group(1).strip() not in STATES: continue
            cells_ = [l for l in row.strip().split('\n') if l.startswith('|')]
            raw = cells_[0][1:] if cells_ else ''
            inner = re.findall(r'\{\{\s*[\w ]+\s*\|\s*(?:text\s*=)?((?:[^{}]|\{\{[^{}]*\}\})*)\}\}', raw)
            words = ' '.join(plain(re.sub(r'\[\[[^\]|]*\|', '[[', x)) for x in inner) or plain(raw)
            w = words.lower()
            kind = ('in place' if re.search(r'left in place|no change|rejected|struck|blocked|failed|declined|kept', w) else
                    'pending' if re.search(r'pending|proposed|in progress|tbd|awaiting|ongoing', w) else
                    'enacted' if re.search(r'enacted|new (?:districts|map)|adopted|approved|redrawn|ordered', w) else 'in place')
            out[STATES[st.group(1).strip()]] = kind
    return out


# ----------------------------------------------------------------------------------------------------------- fetching
UA = {'User-Agent': 'election-research (github.com/KA82205/the-margin)'}
API = 'https://en.wikipedia.org/w/api.php?'
NAMES = {v: k for k, v in STATES.items()}
ONE_SEAT = {'AK', 'DE', 'ND', 'SD', 'VT', 'WY'}                  # a single seat since 2022 (Montana has two)


def overview(year):
    return f'{year} United States House of Representatives elections'


def state_title(year, st):
    return f'{year} United States House of Representatives election{"" if st in ONE_SEAT else "s"} in {NAMES[st]}'


def titles(year, states=True):
    return [overview(year)] + ([state_title(year, st) for st in sorted(NAMES)] if states else [])


def _api(params, tries=5):
    url = API + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': '2'})
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'; time.sleep(60 if e.code == 429 else 5 * (i + 1))
        except Exception as e:                                     # noqa: BLE001 - retried, then reported
            err = type(e).__name__; time.sleep(5 * (i + 1))
    raise RuntimeError(f'Wikipedia could not be read: {err}')


def fetch(titles_, chunk=5, pause=1.5):
    """{requested title: {'title': the page it resolved to, 'timestamp', 'text'}}, redirects followed; a title with no
    page is left out. Large pages come back over several calls (the API's continuation)."""
    out = {}
    for i in range(0, len(titles_), chunk):
        part = titles_[i:i + chunk]; got, to, cont = {}, {}, {}
        while True:
            j = _api({'action': 'query', 'prop': 'revisions', 'rvprop': 'content|timestamp', 'rvslots': 'main', 'titles': '|'.join(part), 'redirects': '1', **cont})
            q = j.get('query', {})
            for r in q.get('normalized', []) + q.get('redirects', []): to[r['from']] = r['to']
            for p in q.get('pages', []):
                rv = (p.get('revisions') or [{}])[0]
                if p.get('missing') or 'slots' not in rv: continue
                got[p['title']] = {'title': p['title'], 'timestamp': rv['timestamp'], 'text': rv['slots']['main']['content']}
            if 'continue' not in j: break
            cont = j['continue']; time.sleep(pause)
        for t in part:
            f = t
            for _ in range(3): f = to.get(f, f)
            if f in got: out[t] = got[f]
        time.sleep(pause)
    return out


# ------------------------------------------------------------------------------------------------- the states' pages
def _field(block, k):
    m = re.search(r'\|\s*' + k + r'\s*=\s*((?:[^|{}]|\{\{[^{}]*\}\}|\[\[[^\]]*\]\])*)', block)
    return m.group(1).strip() if m else ''


def boxes(text):
    """Each election box in a stretch of a page: {'title', 'candidates': [{'name', 'party', 'votes', 'share', 'won'}]},
    a candidate on several lines (New York's fusion parties) once, under the major party among their lines."""
    out = []
    for b in re.finditer(r'\{\{\s*Election box begin(.*?)\{\{\s*Election box end\s*\}\}', text or '', re.S | re.I):
        body = b.group(0); title = plain(_field(b.group(1), 'title'))
        by = {}
        for c in re.finditer(r'\{\{\s*Election box (winning )?candidate[^|]*((?:[^{}]|\{\{[^{}]*\}\})*)\}\}', body, re.I):
            f = c.group(2); name = plain(_field(f, 'candidate')); party = _field(f, 'party')
            if not name or re.fullmatch(r'(?i)total|write-?ins?|others?|blank|none', name.strip()) or re.match(r'(?i)total', plain(party)): continue
            name = re.sub(r'\s*\((?:incumbent|inc\.)\)\s*', ' ', name).strip(" '")
            p = party_code(party); v = number(_field(f, 'votes')); s = number(_field(f, 'percentage'))
            k = re.sub(r'[^a-z]', '', name.lower())
            cur = by.setdefault(k, {'name': name, 'party': None, 'votes': None, 'share': None, 'won': False})
            if p in ('D', 'R') or cur['party'] is None: cur['party'] = p if p in ('D', 'R') or cur['party'] is None else cur['party']
            if v is not None: cur['votes'] = (cur['votes'] or 0) + v
            if s is not None: cur['share'] = (cur['share'] or 0) + s
            cur['won'] |= bool(c.group(1))
        out.append({'title': title, 'candidates': list(by.values())})
    return out


def district_sections(text, st):
    """{district: the stretch of a state's page about it}; a state with one seat is all one stretch (district 0)."""
    heads = list(re.finditer(r'\n(=+)\s*(?:\[\[[^\]|]*\|)?District\s+(\d+|at-large)\]?\]?\s*\1', text or '', re.I))
    if st in ONE_SEAT or not heads: return {0: text or ''}
    out = {}
    for i, h in enumerate(heads):
        level = len(h.group(1)); end = len(text)
        for h2 in heads[i + 1:]:
            if len(h2.group(1)) <= level: end = h2.start(); break
        else:
            m = re.compile(r'\n={1,%d}[^=]' % level).search(text, h.end()); end = m.start() if m else len(text)
        d = 0 if h.group(2).lower() == 'at-large' else int(h.group(2))
        out.setdefault(d, text[h.start():end])
    return out


def general_box(section):
    """The general election's box in a district's stretch, and the runoff's when there was one: the last box that is
    not a primary's, and the last whose title names a runoff."""
    bx = [b for b in boxes(section) if b['candidates']]
    gen = [b for b in bx if not re.search(r'primary|convention|caucus|runoff|special', b['title'], re.I)]
    if not gen:
        gen = [b for b in bx if not re.search(r'primary|convention|caucus', b['title'], re.I) and not re.search(r'runoff', b['title'], re.I)]
    run = [b for b in bx if re.search(r'runoff', b['title'], re.I) and not re.search(r'primary', b['title'], re.I)]
    return (gen[-1] if gen else None), (run[-1] if run else None)
