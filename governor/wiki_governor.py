"""Reads Wikipedia's overview of a year's governor elections ("<year> United States gubernatorial elections"): its table of
the states' races, one row a race, each with the governor who held the seat, their party, what became of the seat (or,
before the election, what the governor has said), and the candidates.

    races(text, year) -> [{'state', 'special', 'governor', 'party', 'status', 'candidates_raw', 'candidates', 'last_race'}]

candidates is the candidates' cell read by the House forecast's reader (house/wiki_house.candidates): each candidate's
name, party, share once the votes are in, and whether marked as the winner. Wikipedia's text is CC BY-SA 4.0.
"""
import os, re, sys, unicodedata

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'house'))
import wiki_house as WH

PARTY_WORDS = {'Democratic': 'D', 'Republican': 'R', 'Independent': 'I', 'Libertarian': 'L', 'DFL': 'D', 'Democratic–Farmer–Labor': 'D'}


def overview(year):
    return f'{year} United States gubernatorial elections'


def race_title(year, st):
    return f'{year} {WH.NAMES[st]} gubernatorial election'


def fold(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()


def words(name):
    n = re.sub(r'\([^)]*\)|\b(jr|sr|ii|iii|iv)\b\.?', ' ', fold(name).replace('.', ' '))
    return [w for w in re.split(r'[\s,]+', n) if w]


def same_person(a, b):
    """The same person: a word of the surname in common and the same first two letters of the given name, or the same
    surname with a given name one starts like the other (Bob for Robert is not caught, but the surname and party nearly
    always suffice in a governor's race)."""
    wa, wb = words(a), words(b)
    if not wa or not wb: return False
    sa, sb = set(x for w in wa[1:] for x in [w] + w.split('-') if len(x) > 1), set(x for w in wb[1:] for x in [w] + w.split('-') if len(x) > 1)
    return bool(sa & sb) and (wa[0][:2] == wb[0][:2] or wa[0][0] == wb[0][0])


def party_of_cell(raw):
    m = re.search(r'[Pp]arty shading/(?:Text/)?([A-Za-z–\- ]+?)\s*(?:/|\}\})', raw)
    if m and m.group(1).strip() in PARTY_WORDS: return PARTY_WORDS[m.group(1).strip()]
    t = WH.plain(raw)
    for w, p in PARTY_WORDS.items():
        if re.search(r'\b' + w + r'\b', t): return p
    return None


def races(text, year):
    """The states' table of the overview: the first table after the race summary heading whose rows name states."""
    m = re.search(r'\n==+\s*(?:Race summary|States|Results summary|Summary)\s*==+', text or '')
    start = m.start() if m else 0
    out = []
    for tm in re.finditer(r'\n\{\|(.*?)\n\|\}', (text or '')[start:], re.S):
        body = tm.group(1)
        rows = re.split(r'\n\|-[^\n]*', body)
        got = []
        for row in rows:
            lines = row.strip('\n').split('\n')
            head = next((l for l in lines if l.startswith('!') and '[[' in l), None)
            if not head: continue
            sm = re.search(r'\[\[(?:[^\]|]*\|)?([^\]]+)\]\]', head)
            name = WH.plain(sm.group(1)) if sm else ''
            special = bool(re.search(r'special', head, re.I))
            name = re.sub(r'\s*\(special\)', '', name).strip()
            st = WH.STATES.get(name)
            if not st: continue
            cells = [c for c in WH.cells('\n'.join(l for l in lines if not l.startswith('!')))]
            r = {'state': st, 'special': special, 'governor': None, 'party': None, 'status': '', 'candidates_raw': '', 'last_race': None, 'first_elected': None}
            for c in cells:
                p = WH.plain(c)
                if re.search(r'[Pp]lainlist|[Pp]arty stripe|^\s*\*|\bTBD\b', c):
                    r['candidates_raw'] = (r['candidates_raw'] + '\n' + c).strip()
                elif re.search(r'Incumbent|New governor|term-limited|term limited|retir|resign|died|renominat|re-elected|elected to|intent|running|vacan', p, re.I):
                    r['status'] = (r['status'] + ' ' + p).strip(' |')
                elif re.search(r'(?:^|\|\s*)\d+(?:\.\d+)?%\s*[A-Z]', p):
                    r['last_race'] = re.search(r'\d+(?:\.\d+)?%\s*[A-Z/]+', p).group(0)
                elif re.match(r'^\(?\d{4}\b', p) and r['first_elected'] is None:
                    r['first_elected'] = int(p[:5].strip('('))
                elif r['governor'] is None and (re.search(r'[Ss]ortname|\[\[', c) or (p and len(p) < 50 and not party_of_cell(c))):
                    r['governor'] = re.sub(r'\s+', ' ', p).strip() or None
                elif r['party'] is None and party_of_cell(c):
                    r['party'] = party_of_cell(c)
            r['candidates'] = WH.candidates(r['candidates_raw'])
            got.append(r)
        if got:
            out = got; break
    return out


def nominees(r):
    """The race's two nominees, once the overview names one Democrat and one Republican among its candidates (in the
    general election's list); None before."""
    gen = [c for c in r['candidates'] if c['round'] == 'general']
    dm = [c['name'] for c in gen if c['party'] == 'D']; rp = [c['name'] for c in gen if c['party'] == 'R']
    return (dm[0], rp[0]) if len(dm) == 1 and len(rp) == 1 else None
