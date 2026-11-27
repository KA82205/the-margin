"""Reads each Senate race's summary box (the infobox) on Wikipedia: the nominees and their parties, their votes once
counted, and who held the seat before the election. Research for now; Wikipedia's text is CC BY-SA 4.0.

    race(text) -> {'nominees': [{'name', 'party', 'votes', 'pct'}], 'incumbent': name, 'incumbent_party': 'D'|'R'|'I'|None}

The race model's two sides (as build_data.py sets them): the Democrat, or an independent the Democrats backed when
they ran no one (DEM_ALIGNED in build_data.py, entered by hand), and the Republican. A race where the top two are not
one of each is left out, as before.
"""
import re
import wiki_polls as WP

PARTY = (('Democratic', 'D'), ('Republican', 'R'), ('Independent', 'I'), ('Libertarian', 'L'), ('Green', 'G'))


def infobox(text):
    """The box's text, matched brace for brace (templates inside it can end a line with }})."""
    text = text or ''; m = re.search(r'\{\{\s*Infobox election', text, flags=re.I)
    if not m: return ''
    depth, i = 0, m.start()
    while i < len(text):
        if text.startswith('{{', i): depth += 1; i += 2; continue
        if text.startswith('}}', i):
            depth -= 1; i += 2
            if depth == 0: return text[m.end():i - 2]
            continue
        i += 1
    return text[m.end():]


def field(box, key):
    """A field's value: to the end of its line, or to the next field when several share a line."""
    m = re.search(r'(?:^|\n|\|)\s*' + re.escape(key) + r'\s*=\s*([^\n]*)', box)
    return WP.top_split(m.group(1), '|')[0].strip() if m else None


def party_code(v):
    v = v or ''
    for name, code in PARTY:
        if name in v: return code
    return 'O' if v.strip() else None


def name_of(v):
    v = re.sub(r'<!--.*?-->', '', v or '', flags=re.S)
    v = re.sub(r'\(replaced[^)]*\)', '', v)
    return WP.clean(v).strip(" '") or None


def number(v):
    m = re.search(r'(\d[\d,]*\.?\d*)', WP.clean(v or ''))
    return float(m.group(1).replace(',', '')) if m else None


def race(text):
    box = infobox(text); out = {'nominees': [], 'incumbent': None, 'incumbent_party': None}
    if not box: return out
    for i in range(1, 7):
        n = field(box, f'nominee{i}') or field(box, f'candidate{i}')
        if not n: continue
        out['nominees'].append({'name': name_of(n), 'party': party_code(field(box, f'party{i}')),
                                'votes': number(field(box, f'popular_vote{i}')), 'pct': number(field(box, f'percentage{i}'))})
    out['incumbent'] = name_of(field(box, 'before_election')); out['incumbent_party'] = party_code(field(box, 'before_party'))
    return out


def sides(c, state):
    """(Democratic side, Republican side, incumbent side or 'open') from race(); None for a side nobody fills. The
    Democratic side is the Democrat, unless an independent the Democrats back (build_data.DEM_ALIGNED) is running, as
    King in Maine when a Democrat also ran."""
    import build_data as BD
    noms = c['nominees']
    sur = lambda n: BD.surname(WP.plain(n or ''))
    aligned = [x for x in noms if x['party'] in ('I', 'O') and (state, sur(x['name'])) in BD.DEM_ALIGNED]
    dem = (aligned or [x for x in noms if x['party'] == 'D'] or [None])[0]
    rep = ([x for x in noms if x['party'] == 'R'] or [None])[0]
    inc = 'open'
    if c['incumbent']:
        last = sur(c['incumbent'])
        if dem and sur(dem['name']) == last: inc = 'D'
        elif rep and sur(rep['name']) == last: inc = 'R'
    return dem, rep, inc
