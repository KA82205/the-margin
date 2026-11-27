"""The seats up in a coming Senate election, read from Wikipedia's page for the year ("2028 United States Senate
elections"): each seat's state, whether it is a special election, the senator holding it and their party, whether the
senator is running ("Incumbent running", "Incumbent retiring", "intent unknown"), and the candidates declared so far
with their parties. Wikipedia's text is CC BY-SA 4.0.

    seats(text) -> list of {'state', 'special', 'incumbent', 'incumbent_party', 'status', 'running', 'declared'}
"""
import re
import wiki_polls as WP

ABBR = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
        'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY',
        'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
        'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
        'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
        'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
        'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'}
NAMES = {v: k for k, v in ABBR.items()}
PARTY = (('Democratic', 'D'), ('Republican', 'R'), ('Independent', 'I'), ('Libertarian', 'L'), ('Green', 'G'))


def party_code(v):
    for name, code in PARTY:
        if name in (v or ''): return code
    return None


def tables(text):
    """The wikitables after the 'Race summary' heading, special elections first: (is_special, table text)."""
    i = text.find('Race summary')
    if i < 0: return []
    out = []
    for m in re.finditer(r'\{\|.*?\n\|\}', text[i:], flags=re.S):
        head = text[i:i + m.start()]
        special = head.rfind('Special election') > head.rfind('Elections leading')
        out.append((special, m.group(0)))
        if len(out) == 2: break
    return out


def cells(row):
    """A row's cells: each line starting with | or ! begins one; 'attributes | value' keeps the value."""
    out = []
    for line in re.split(r'\n(?=[|!])', row.strip()):
        line = line.lstrip('|!').strip()
        if not line or line.startswith('-'): continue
        parts = WP.top_split(line, '|')
        out.append(parts[-1].strip() if len(parts) > 1 and ('=' in parts[0] or 'Party shading' in parts[0]) else line)
    return out


def senator(v):
    m = re.search(r'\{\{\s*Sort ?name\s*\|\s*([^|}]+)\|\s*([^|}]+)', v or '', flags=re.I)
    if m: return f'{m.group(1).strip()} {m.group(2).strip()}'
    v = WP.clean(v or '').strip()
    return None if not v or v.lower().startswith(('to be appointed', 'vacant', 'tbd')) else v


def declared(v):
    out = []
    for item in re.findall(r'\*([^\n]+)', v or ''):
        if 'TBD' in item and '[[' not in item: continue
        party = party_code((re.search(r'\(([^)]*)\)\s*(?:<ref|$)', re.sub(r'<ref[^>]*/>', '', item)) or [None, ''])[1]) or party_code(item)
        name = re.search(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', item)
        nm = (name.group(2) or name.group(1)).strip() if name else WP.clean(re.sub(r'<ref.*', '', item)).split('(')[0].strip()
        if nm: out.append({'name': re.sub(r'\s*\(.*', '', nm), 'party': party})
    return out


def status_of(v):
    s = WP.clean(v or '').strip(); low = s.lower()
    running = True if re.search(r'\brunning\b', low) and 'not running' not in low else False if re.search(r'retir|not running|not seek|declin|lost|defeat|resign|term.limited|running for (?:governor|president|another)', low) else None
    return s, running


def seats(text):
    out = []
    for special, tab in tables(text):
        for row in tab.split('\n|-')[1:]:
            st = re.search(r'^\s*!\s*\[\[[^\]|]*\|\s*([A-Za-z ]+?)\s*\]\]', row)
            if not st or st.group(1) not in ABBR: continue
            c = cells(row); c = c[1:]                           # the state's own cell first
            sen, party = c[0] if c else '', party_code(c[1]) if len(c) > 1 else None
            cand = next((x for x in c if 'Plainlist' in x or x.lstrip().startswith('*')), '')
            stat_cell = next((x for x in reversed(c) if x is not cand and re.search(r'incumbent|appointee|retir|running|elected|open', WP.clean(x), flags=re.I)), '')
            status, running = status_of(stat_cell)
            out.append({'state': ABBR[st.group(1)], 'special': special, 'incumbent': senator(sen), 'incumbent_party': party,
                        'status': status, 'running': running, 'declared': declared(cand)})
    return out
