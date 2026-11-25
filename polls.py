"""Head-to-head polls of the 2028 presidential general election, state by state. Writes data/state_polls.json.

Where the polls come from
    PollResults.org   api.pollresults.org/v1.0/politics/results/president. The New York Times's poll data, CC BY 4.0, served
                      100 polls a page with a cursor to the next. Every poll carries the state it was taken in ("US" for the
                      country) and each question says whether it is a primary or the general election.
    VoteHub           api.votehub.com (CC BY 4.0). It lists no presidential general-election polls yet. Its list of poll types
                      is read on every run, and the run says so when one for the presidential general election appears.
    Tipping Point     its saved copy of the PollResults feed, read only when PollResults cannot be reached.

What is done with them
    1. Every general-election question becomes one row, with its place worked out from every field that could name one.
       A row whose place cannot be worked out is kept, listed and not used. Nothing is guessed.
    2. Rows that are the same question of the same poll are counted once: the feed repeats polls across pages, and gives
       one sample under two labels.
    3. Each row is either usable or not, with the reason. Not usable: no named Democrat or no named Republican ("generic"
       ballots), a person who cannot be elected again, a poll paid for by a party or a campaign, and, while the nominees are
       not known, a poll of somebody's own state. Those are the rules the national polls already follow.
    4. The usable rows of one poll in one state are averaged into one line, so a poll that asked about ten pairings counts
       once, among its most likely voters.

The file says for each source whether it answered, how much it returned and how much of that was about the states. "No state
polls" in the forecast then means one of three different things, and the file says which: the source could not be reached,
the source has none, or it has some and none is usable.

    python polls.py            fetch and write data/state_polls.json
    python polls.py --offline  rebuild from data/cache/pollresults_general.json
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, 'data')
PR_URL = 'https://api.pollresults.org/v1.0/politics/results/president'
PR_FALLBACK = 'https://raw.githubusercontent.com/KA82205/tipping-point/main/pipeline/cache/pollresults_president.json'
VH_TYPES = 'https://api.votehub.com/poll-types'
CANDIDATES_URL = 'https://raw.githubusercontent.com/KA82205/tipping-point/main/pipeline/candidates.json'
AGENT = {'User-Agent': 'the-margin/1.0 (state polls)'}
CYCLE = '2028'
TERM_LIMITED = {'donald trump', 'barack obama', 'george w. bush', 'bill clinton'}          # cannot be elected president again
POP_RANK = {'lv': 0, 'rv': 1, 'v': 1, 'a': 2}

NAMES = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia',
         'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine',
         'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
         'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
         'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia',
         'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}
BY_NAME = {v.lower(): k for k, v in NAMES.items()}; BY_NAME.update({'washington, d.c.': 'DC', 'washington dc': 'DC', 'd.c.': 'DC'})
DISTRICTS = {'ME': 2, 'NE': 3}                         # the two states that award electoral votes by congressional district
NATIONAL = {'us', 'u.s.', 'usa', 'national', 'nationwide', 'united states'}


# ------------------------------------------------------------------------------------------------------------------ fetching
def get(url, tries=3, wait=2.0, timeout=30):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
                return r.read().decode('utf-8-sig')
        except urllib.error.HTTPError as err:
            if (err.code < 500 and err.code != 429) or attempt == tries - 1: raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt == tries - 1: raise
        time.sleep(wait * 2 ** attempt)


def fetch_pollresults(fetch=get, max_pages=40):
    """Every page of the feed, newest first. Stops at the last page, or when a page brings nothing new (a cursor that
    loops), or at max_pages, and says which."""
    out, seen, cursor, pages, why = [], set(), None, 0, 'the last page'
    for _ in range(max_pages):
        page = json.loads(fetch(PR_URL + '?limit=100' + (f'&cursor={urllib.parse.quote(cursor)}' if cursor else '')))
        pages += 1
        new = [r for r in page.get('results', []) if r.get('pollId') not in seen]
        seen.update(r.get('pollId') for r in new); out.extend(new)
        cursor = page.get('cursor')
        if not cursor: break
        if not new: why = 'a page with nothing new'; break
    else:
        why = f'the limit of {max_pages} pages: older polls may be missing'
    return out, {'pages': pages, 'stopped_at': why}


KEEP = ('pollId', 'pollster', 'displayName', 'sponsors', 'partisan', 'internal', 'startDate', 'endDate', 'createdAt', 'state', 'cycle', 'numericGrade', 'url', 'urlArticle')
KEEP_Q = ('questionId', 'sampleSize', 'population', 'stage', 'seatName', 'seatNumber', 'district')


def slim(records):
    """The part of the feed this script reads: the general-election questions of the cycle, and the fields used. The whole
    feed is two megabytes, most of it primaries; this is what is saved in data/cache/."""
    out = []
    for r in records:
        if str(r.get('cycle') or CYCLE) != CYCLE: continue
        qs = [dict({k: q.get(k) for k in KEEP_Q if k in q}, answers=[{k: a.get(k) for k in ('party', 'pct', 'candidateName')} for a in (q.get('answers') or [])])
              for q in (r.get('questions') or []) if str(q.get('stage') or '').lower() == 'general']
        if qs: out.append(dict({k: r.get(k) for k in KEEP if k in r}, questions=qs))
    return sorted(out, key=lambda r: (str(r.get('endDate')), str(r.get('pollId'))))


# ---------------------------------------------------------------------------------------------------------------- geography
def place(state, seat_name='', seat_number='', district=''):
    """Where a poll was taken: 'US', a state's postal code, a district such as 'ME2', or None if it cannot be told.
    Reads the state field first, then the fields that can carry a district. Returns (place, how it was read)."""
    raw = ' '.join(str(x or '').strip() for x in (state,)).strip()
    low = re.sub(r'\s+', ' ', raw.lower())
    extra = ' '.join(str(x or '').strip() for x in (seat_name, seat_number, district)).strip()
    code = None
    if low in NATIONAL: code = 'US'
    elif raw.upper() in NAMES: code = raw.upper()
    elif low in BY_NAME: code = BY_NAME[low]
    else:
        m = re.match(r'^(maine|nebraska|me|ne)[\s\-]*(?:cd|district|congressional district)?[\s\-]*0?([1-3])(?:st|nd|rd)?(?: district)?$', low)
        if m:
            st = {'maine': 'ME', 'nebraska': 'NE'}.get(m.group(1), m.group(1).upper()); n = int(m.group(2))
            return (f'{st}{n}', 'the state field names a district') if n <= DISTRICTS[st] else (None, f'no such district: {raw!r}')
    if code is None:
        return None, f'unreadable place: {raw!r}' if raw else 'no place given'
    if code in DISTRICTS:                                # a district may be named in another field
        m = re.search(r'(?:^|[^\d])0?([1-3])(?:st|nd|rd)?(?:$|[^\d])', ' ' + extra + ' ') if re.search(r'\d', extra) else None
        if m and re.search(r'cd|district|^\s*0?[1-3]\s*$', extra.lower()):
            n = int(m.group(1))
            if n <= DISTRICTS[code]: return f'{code}{n}', 'a district named beside the state'
    if code != 'US' and extra and extra.strip().lower() in NATIONAL:
        return None, f'the state field says {raw!r} and another field says {extra!r}'
    return code, 'the state field'


# ------------------------------------------------------------------------------------------------------------ normalising
def iso(s):
    """'11/9/26', '2026-11-09' or '2026-11-09T..' -> '2026-11-09'; '' if it cannot be read."""
    s = str(s or '').strip()
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})', s)
    try:
        if m:
            y = int(m.group(3)); y += 2000 if y < 100 else 0
            return datetime.date(y, int(m.group(1)), int(m.group(2))).isoformat()
        return datetime.date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        return ''


FILLER = {'the', 'of', 'and', 'for', 'at', 'college', 'university', 'poll', 'polls', 'polling', 'research', 'center', 'centre', 'survey', 'surveys', 'institute', 'strategies', 'strategy',
          'group', 'news', 'inc', 'co', 'company', 'llc', 'insights', 'opinion', 'public', 'department', 'school', 'law'}


def pollster_key(name):
    """A pollster's name with the differences in spelling taken out ('Marist College', 'Marist University')."""
    words = sorted({w for w in re.findall(r'[a-z0-9]+', str(name or '').lower()) if w not in FILLER})
    return ' '.join(words) or str(name or '').strip().lower()


def rows_from_pollresults(records):
    """One row for each general-election question of the cycle."""
    out = []
    for r in records:
        if str(r.get('cycle') or CYCLE) != CYCLE: continue
        for q in r.get('questions') or []:
            if str(q.get('stage') or '').lower() != 'general': continue
            where, how = place(r.get('state'), q.get('seatName'), q.get('seatNumber'), q.get('district'))
            ans = [a for a in (q.get('answers') or []) if isinstance(a.get('pct'), (int, float))]
            dem = [a for a in ans if a.get('party') == 'DEM']; rep = [a for a in ans if a.get('party') == 'REP']
            others = [a for a in ans if a.get('party') not in ('DEM', 'REP', 'NONE', None, '')]
            try: n = float(q.get('sampleSize')) if q.get('sampleSize') not in (None, '') else None
            except (TypeError, ValueError): n = None
            out.append({'source': 'PollResults.org', 'poll_id': str(r.get('pollId')), 'question_id': str(q.get('questionId')), 'place': where, 'place_read_from': how,
                        'pollster': r.get('pollster') or r.get('displayName') or '', 'sponsors': r.get('sponsors') or '', 'partisan': str(r.get('partisan') or '').strip(),
                        'internal': str(r.get('internal') or '').strip().lower() in ('true', '1', 'yes', 'internal'), 'start': iso(r.get('startDate')), 'end': iso(r.get('endDate')),
                        'added': iso(r.get('createdAt')), 'population': str(q.get('population') or '').lower(), 'n': n,
                        'dem': dem[0]['candidateName'] if len(dem) == 1 else None, 'dem_pct': dem[0]['pct'] if len(dem) == 1 else None,
                        'rep': rep[0]['candidateName'] if len(rep) == 1 else None, 'rep_pct': rep[0]['pct'] if len(rep) == 1 else None,
                        'n_dem': len(dem), 'n_rep': len(rep), 'others': sorted(a.get('candidateName') or '' for a in others),
                        'grade': r.get('numericGrade'), 'url': r.get('url') or r.get('urlArticle') or ''})
    return out


def dedupe(rows):
    """Count one question of one poll once. Two rows are the same when they share a poll and question id, or when they are
    one pollster's figures for one pairing in one place, ending on one day, and either the same people were asked (same
    group and size) or the same answer came back from the same number of people under two labels."""
    out, seen_ids, dropped = [], set(), 0
    for r in rows:
        k = (r['source'], r['poll_id'], r['question_id'])
        if k in seen_ids: dropped += 1; continue
        same = False
        for o in out:
            if (pollster_key(o['pollster']) == pollster_key(r['pollster']) and o['place'] == r['place'] and o['end'] == r['end'] and o['dem'] == r['dem'] and o['rep'] == r['rep']
                    and o['dem_pct'] is not None and r['dem_pct'] is not None):
                same_result = abs(o['dem_pct'] - r['dem_pct']) <= 0.6 and abs((o['rep_pct'] or 0) - (r['rep_pct'] or 0)) <= 0.6
                same_size = o['n'] is not None and o['n'] == r['n']
                if (o['population'] == r['population'] and same_size and same_result and o['poll_id'] != r['poll_id']) or (o['population'] != r['population'] and same_size and same_result):
                    same = True; break
        if same: dropped += 1; continue
        seen_ids.add(k); out.append(r)
    return out, dropped


# -------------------------------------------------------------------------------------------------------------- eligibility
def homes(registry, people=()):
    """{name in lower case: home state} from Tipping Point's list of possible candidates and the people in its polls."""
    h = {}
    for c in list(registry or []) + list(people or []):
        if c.get('state'):
            for name in [c.get('name')] + list(c.get('aliases') or []):
                if name: h[name.lower()] = c['state']
    return h


def usable(r, home, nominees=None):
    """(True, '') or (False, the reason). `nominees` = (Democrat, Republican) once both are known."""
    if r['place'] is None: return False, 'its place could not be read: ' + r['place_read_from']
    if not r['end']: return False, 'no end date'
    if r['n_dem'] != 1 or r['n_rep'] != 1: return False, 'not one Democrat against one Republican'
    generic = lambda s: bool(re.match(r'^\s*(generic|a |the |someone|unnamed)', s.lower())) or 'generic' in s.lower()
    if generic(r['dem']) or generic(r['rep']): return False, 'no named candidates (a generic ballot)'
    for who in (r['dem'], r['rep']):
        if who.lower() in TERM_LIMITED: return False, f'{who} cannot be elected again'
    if r['partisan'] or r['internal']: return False, 'paid for by a party or a campaign'
    if not (0 < r['dem_pct'] < 100 and 0 < r['rep_pct'] < 100 and r['dem_pct'] + r['rep_pct'] <= 100.5): return False, 'the percentages do not add up'
    if r['dem_pct'] + r['rep_pct'] < 50: return False, 'under half of those asked chose either candidate'
    if nominees:
        if (r['dem'].lower(), r['rep'].lower()) != (nominees[0].lower(), nominees[1].lower()): return False, 'not the two nominees'
    elif r['place'] != 'US':
        for who in (r['dem'], r['rep']):
            if home.get(who.lower()) == r['place'][:2]: return False, f"{who}'s own state, while the nominees are not known"
    return True, ''


def collapse(rows):
    """One line for each poll in each place: the usable pairings averaged, among the likeliest voters it reported."""
    by = {}
    for r in rows:
        by.setdefault((r['source'], r['poll_id'], r['place']), []).append(r)
    out = []
    for (source, pid, where), rs in by.items():
        best = min(POP_RANK.get(r['population'], 3) for r in rs); rs = [r for r in rs if POP_RANK.get(r['population'], 3) == best]
        dem = sum(r['dem_pct'] for r in rs) / len(rs); rep = sum(r['rep_pct'] for r in rs) / len(rs)
        shares = [100 * r['dem_pct'] / (r['dem_pct'] + r['rep_pct']) for r in rs]
        ns = [r['n'] for r in rs if r['n']]
        out.append({'place': where, 'pollster': rs[0]['pollster'], 'start': rs[0]['start'], 'end': rs[0]['end'], 'added': rs[0]['added'], 'population': rs[0]['population'],
                    'n': round(sum(ns) / len(ns)) if ns else None, 'dem': round(dem, 2), 'rep': round(rep, 2), 'dem2': round(100 * dem / (dem + rep), 2),
                    'pairings': [f"{r['dem']} v {r['rep']}" for r in rs], 'pairing_spread': round(max(shares) - min(shares), 2) if len(shares) > 1 else None,
                    'source': source, 'poll_id': pid, 'url': rs[0]['url']})
    return sorted(out, key=lambda p: (p['end'], p['place'], p['pollster']))


# -------------------------------------------------------------------------------------------------------------------- build
def build(records, registry, people=(), nominees=None, sources=None, today=None):
    rows, dropped = dedupe(rows_from_pollresults(records)); home = homes(registry, people)
    for r in rows:
        r['usable'], r['why_not'] = usable(r, home, nominees)
    st = [r for r in rows if r['place'] != 'US']
    why = {}
    for r in st:
        if not r['usable']: why[r['why_not']] = why.get(r['why_not'], 0) + 1
    polls = collapse([r for r in rows if r['usable'] and r['place'] not in ('US', None)])
    count = lambda rs: len({(r['source'], r['poll_id']) for r in rs})
    return {'fetched': today or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 'sources': sources or {},
            'found': {'general_election_questions': len(rows), 'duplicates_removed': dropped, 'national_polls': count([r for r in rows if r['place'] == 'US']),
                      'state_polls': count([r for r in st if r['place']]), 'state_questions': len([r for r in st if r['place']]), 'unplaced_questions': len([r for r in rows if r['place'] is None]),
                      'states_polled': sorted({r['place'] for r in st if r['place']}), 'usable_state_polls': len(polls), 'not_usable': why},
            'polls': polls,
            'state_questions': [{k: r[k] for k in ('place', 'pollster', 'sponsors', 'partisan', 'start', 'end', 'population', 'n', 'dem', 'dem_pct', 'rep', 'rep_pct', 'usable', 'why_not', 'url', 'place_read_from')}
                                for r in sorted(st, key=lambda r: (r['end'], str(r['place'])), reverse=True)]}


def main(argv):
    cache = os.path.join(D, 'cache'); os.makedirs(cache, exist_ok=True)
    feed = os.path.join(cache, 'pollresults_general.json'); reg = os.path.join(cache, 'candidates.json')
    save = lambda recs: json.dump({'results': slim(recs)}, open(feed, 'w'), separators=(',', ':'))
    sources = {}
    if '--offline' not in argv:
        try:
            recs, info = fetch_pollresults(); assert recs, 'the feed returned no polls'
            save(recs); sources['PollResults.org'] = dict(info, answered=True, polls=len(recs))
        except Exception as e:                                                 # noqa: BLE001  fall back on Tipping Point's saved copy, then on our own
            sources['PollResults.org'] = {'answered': False, 'error': f'{type(e).__name__}: {e}'[:200]}
            try:
                recs = json.loads(get(PR_FALLBACK))['results']; assert recs, 'the saved copy holds no polls'
                save(recs); sources["Tipping Point's saved copy"] = {'answered': True, 'polls': len(recs)}
            except Exception as e2:                                            # noqa: BLE001
                sources["Tipping Point's saved copy"] = {'answered': False, 'error': f'{type(e2).__name__}: {e2}'[:200]}
        try:
            types = json.loads(get(VH_TYPES)); types = types if isinstance(types, list) else types.get('poll_types') or types.get('types') or []
            names = [t if isinstance(t, str) else str(t.get('name') or t.get('poll_type') or t) for t in types]
            general = [t for t in names if 'president' in t.lower() and 'primary' not in t.lower()]
            sources['VoteHub'] = {'answered': True, 'poll_types': sorted(names), 'presidential_general_types': general,
                                  'note': 'a presidential general-election type has appeared: it needs wiring in' if general else 'lists no presidential general-election polls'}
        except Exception as e:                                                 # noqa: BLE001
            sources['VoteHub'] = {'answered': False, 'error': f'{type(e).__name__}: {e}'[:200]}
        try:
            json.dump(json.loads(get(CANDIDATES_URL)), open(reg, 'w'), indent=1)
        except Exception as e:                                                 # noqa: BLE001  keep the copy in hand
            sources['candidate list'] = {'answered': False, 'error': f'{type(e).__name__}: {e}'[:200]}
    records = json.load(open(feed))['results'] if os.path.exists(feed) else []
    registry = json.load(open(reg))['candidates'] if os.path.exists(reg) else []
    people, nominees = [], None
    try:
        import run_2028
        nc = run_2028.nowcast(); people = nc.get('h2h', {}).get('people') or []; nominees = run_2028.nominees(nc)
    except Exception:                                                          # noqa: BLE001
        pass
    path = os.path.join(D, 'state_polls.json')
    old = json.load(open(path)) if os.path.exists(path) else {}
    if '--offline' in argv: sources = old.get('sources') or {}                 # nothing was asked, so what is known of the sources stands
    out = build(records, registry, people, nominees, sources)
    out['nominees'] = list(nominees) if nominees else None
    answered = lambda src: {k: (v.get('answered'), v.get('polls'), v.get('stopped_at'), v.get('presidential_general_types')) for k, v in (src or {}).items()}
    if not (all(old.get(k) == out[k] for k in ('found', 'polls', 'state_questions', 'nominees')) and answered(old.get('sources')) == answered(out['sources'])):
        json.dump(out, open(path, 'w'), indent=1)                              # the time of the fetch alone is not a change
    f = out['found']
    print(f"sources: {json.dumps({k: {x: y for x, y in v.items() if x != 'poll_types'} for k, v in out['sources'].items()})}")
    print(f"general-election questions {f['general_election_questions']}; national polls {f['national_polls']}; state polls {f['state_polls']} in {f['states_polled']}; usable {f['usable_state_polls']}; not usable: {f['not_usable']}")
    if out['sources'].get('VoteHub', {}).get('presidential_general_types'): print('::warning::VoteHub now lists a presidential general-election poll type; it is not read yet.')
    return 0 if records else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
