"""The Senate forecast for the coming election, made by the hourly job, and the data of the site's Senate tab.

Each run:
  1. works out which election is next (from the day after an election, the one two years on; the finished cycle's last
     forecast stays in its own folder) and who is president (written down through January 2029, then read from Wikipedia);
  2. reads Wikipedia (CC BY-SA 4.0): the year's overview page (the seats up, regular and special, who holds each,
     whether they are running, the declared candidates, and the chamber as it stands), each race's own page and its
     polling pages (the nominees, once chosen, and every general-election poll), the approval polls and, once there is
     one, the generic-ballot page;
  3. builds each race's inputs as the back-test did: the state's lean, the national environment (half the generic ballot,
     half the approval-and-midterm House forecast), incumbency, the candidates' records, and the race's polling average;
  4. applies the fitted pieces in model.json (live_fit.py: the working version fitted on 2018-2026), at the nearest
     distance tested at or beyond today's (a year out is the furthest; further out, the year-out fit);
  5. pulls the expected seats a quarter of the way to the national seat-change model;
  6. simulates the races 40,000 times: in a presidential year inside The Margin's own presidential simulations
     (docs/api/forecast.json, drawn again from its published states with its own seed), each state's Senate race moving
     half a point with each point its presidential vote moves (step 16), a 50-50 Senate going to the party that wins
     the vice presidency; in a midterm, a 50-50 Senate goes to the sitting vice president's party;
  7. checks what it read and made (the seat count, the chamber, every race's inputs) and stops, keeping the last good
     forecast, if anything is out of line.

Every case it meets on its own:
  - A seat falling vacant adds a special election when Wikipedia adds it; until an appointee is named the seat is open.
  - A senator announcing a retirement, a run for another office or a resignation turns the seat open; one who has not
    said runs in each simulated election with the share of incumbents who ran again in 2018-2026 (79%).
  - Once a party chooses its nominee, the senator runs only if they are that nominee (a primary loss turns the seat open)
    and the nominee's own record counts; once both are chosen, the race's polls of that matchup count, in the
    presidential model's weights, partisan polls left out, as in training.
  - No Democrat on the ballot: an independent running against the Republican stands as the Democratic side (as Dan
    Osborn did in Nebraska). Two nominees of one party (a top-two primary) or, from September, one side with no
    candidate at all: the seat is that party's, outside the simulation.
  - Money raised (senate/fec_live.py, run daily) is shown and not used: tested twice, it made the forecast worse.

    python senate/live.py                      fetches the pages and writes data/senate/<year>/ and docs/api/senate.json
    python senate/live.py --pages FILE.json    reads pages saved before (tools/fetch_wiki_polls.py's shape), for testing
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import backtest as B, build_data as BD, poll_list as PL, wiki_2028 as W28, wiki_candidates as WC, wiki_national as WN, wiki_polls as WP

# who is president, and the page of their approval polls; after the last line here, the job reads the office's
# Wikipedia page (president_from_wikipedia)
PRESIDENTS = [{'from': '2025-01-20', 'name': 'Donald Trump', 'party': 'R', 'approval': 'Opinion polling on the second Trump presidency'}]
SIMS_SEED = 2028
UA = {'User-Agent': 'election-research (github.com/KA82205)'}
API = 'https://en.wikipedia.org/w/api.php?'
# set for the cycle by setup()
YEAR = ELECTION = OUT = OVERVIEW = GENERIC = API_DIR = None
PRES = {}


def election_day(y):
    """The first Tuesday after the first Monday in November."""
    d = pd.Timestamp(f'{y}-11-01'); return d + pd.Timedelta(days=(7 - d.weekday()) % 7 + 1)


def setup(today):
    """The election the forecast is for: the next one still to come (from the day after an election, the one two years on)."""
    global YEAR, ELECTION, OUT, OVERVIEW, GENERIC, API_DIR
    YEAR = today.year + today.year % 2
    if election_day(YEAR) < today: YEAR += 2
    ELECTION = election_day(YEAR); OUT = os.path.join(ROOT, 'data', 'senate', str(YEAR)); API_DIR = os.path.join(ROOT, 'docs', 'api')
    if os.environ.get('SENATE_TEST_DIR'): OUT = API_DIR = os.environ['SENATE_TEST_DIR']        # tests write here, never to the real files
    OVERVIEW = f'{YEAR} United States Senate elections'
    GENERIC = (f'Opinion polling for the {YEAR} United States House of Representatives elections', f'{YEAR} United States House of Representatives elections')


# ------------------------------------------------------------------------------------------------------------- fetching
def _get(params, tries=5):
    url = API + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': '2'})
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:                                     # noqa: BLE001 - retried, then reported
            err = repr(e); time.sleep(5 * (i + 1))
    raise RuntimeError(f'Wikipedia could not be read: {err}')


def fetch(titles):
    """{requested title: {'title': page it resolved to, 'timestamp', 'text'}}; a title with no page is left out."""
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        j = _get({'action': 'query', 'prop': 'revisions', 'rvprop': 'content|timestamp', 'rvslots': 'main', 'titles': '|'.join(chunk), 'redirects': '1'})
        q = j.get('query', {}); to = {r['from']: r['to'] for r in q.get('redirects', [])}
        for n in q.get('normalized', []): to.setdefault(n['from'], n['to'])
        got = {p['title']: {'title': p['title'], 'timestamp': p['revisions'][0]['timestamp'], 'text': p['revisions'][0]['slots']['main']['content']}
               for p in q.get('pages', []) if not p.get('missing') and 'revisions' in p}
        for t in chunk:
            final = to.get(to.get(t, t), to.get(t, t))
            if final in got: out[t] = got[final]
        time.sleep(1.0)
    return out


def search(q):
    j = _get({'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': '5'})
    return [h['title'] for h in j.get('query', {}).get('search', [])]


def race_title(state, special):
    return f'{YEAR} United States Senate {"special election" if special else "election"} in {W28.NAMES[state]}'


def polling_links(text):
    return sorted(set(t.strip() for t in re.findall(r'\[\[\s*(Opinion polling for the [^\]|#]+)', text or '') +
                      re.findall(r'\{\{\s*(?:main|see also|further)\s*\|\s*(Opinion polling for the [^}|#]+)', text or '', flags=re.I)))


def infobox_any(text):
    """The first infobox of any kind, matched brace for brace."""
    m = re.search(r'\{\{\s*Infobox', text or '', flags=re.I)
    if not m: return ''
    depth, i = 0, m.start()
    while i < len(text):
        if text.startswith('{{', i): depth += 1; i += 2; continue
        if text.startswith('}}', i):
            depth -= 1; i += 2
            if depth == 0: return text[m.start():i]
            continue
        i += 1
    return text[m.start():]


def president_from_wikipedia(get):
    """The sitting president, their party and their approval page, from Wikipedia: the office's page names the incumbent,
    their own page their party, and a search finds the page of approval polls of their presidency."""
    office = get(['President of the United States']).get('President of the United States')
    v = WC.field(infobox_any(office['text'] if office else ''), 'incumbent') or ''
    name = WP.clean(re.sub(r'\{\{[^}]*\}\}', '', v)).strip()
    if not name: raise RuntimeError('The sitting president could not be read from Wikipedia')
    person = get([name]).get(name)
    party = W28.party_code(WC.field(infobox_any(person['text'] if person else ''), 'party') or '')
    if party not in ('D', 'R'): raise RuntimeError(f'The party of the president ({name}) could not be read')
    last = name.split()[-1]
    hits = [t for t in search(f'Opinion polling on the {last} presidency') if t.startswith('Opinion polling') and last in t]
    if not hits: raise RuntimeError(f'No page of approval polls of the {last} presidency was found')
    return {'from': None, 'name': name, 'party': party, 'approval': hits[0]}


def president(today, get, saved):
    known = [p for p in PRESIDENTS if pd.Timestamp(p['from']) <= today]
    if today < pd.Timestamp('2029-01-20') or saved: return known[-1]
    return president_from_wikipedia(get)


def gather(today, saved=None):
    """Every page the forecast reads, fetched now (or taken from a saved file), and the seats up."""
    global PRES
    if saved:
        S = json.load(open(saved)); flat = {}
        for v in S.values() if all(isinstance(v, dict) and 'text' not in v for v in S.values()) else [S]:
            flat.update(v)
        get = lambda ts: {t: flat[t] for t in ts if t in flat}
    else:
        get = fetch
    PRES = president(today, get, saved)
    pages = get([OVERVIEW, PRES['approval'], *GENERIC])
    if OVERVIEW not in pages: raise RuntimeError(f'The page "{OVERVIEW}" could not be read')
    seats = W28.seats(pages[OVERVIEW]['text'])
    races = get([race_title(s['state'], s['special']) for s in seats])
    pages.update(races)
    links = sorted(set(l for p in races.values() for l in polling_links(p['text']) if str(YEAR) in l))
    pages.update(get(links))
    return pages, seats


# ------------------------------------------------------------------------------------------------------------- inputs
def chamber(text):
    """The Democratic caucus and the Republicans as the chamber stands, from the overview's box: Democrats plus the
    independents (all of whom sit with the Democrats now), and the seats each side has up."""
    box = WC.infobox(text); num = lambda k: WC.number(WC.field(box, k)) or 0
    parties = {i: WC.field(box, f'party{i}') or '' for i in range(1, 6)}
    dem = sum(num(f'seats_before{i}') for i, p in parties.items() if 'Democratic' in p or 'Independent' in p)
    rep = sum(num(f'seats_before{i}') for i, p in parties.items() if 'Republican' in p)
    return int(dem), int(rep)


def approval_now(pages, today):
    p = pages.get(PRES['approval'])
    if not p: return None
    m = re.search(WN.SECTIONS_APPROVAL, p['text'])
    if not m: return None
    t = WN.approval({f'{PRES["approval"]}|{today.date()}': {'section': p['text'][m.start():m.start() + 12000]}})
    return None if t.empty else {'median': float(t.approve_median.iloc[-1]), 'aggregators': int(t.aggregators.iloc[-1]), 'revision': p['timestamp']}


def generic_now(pages, today):
    for title in GENERIC:
        p = pages.get(title)
        if not p: continue
        m = re.search(r'==+\s*(?:Generic[^=\n]*|Opinion polling|Polls and ratings|Polling aggregat[^=\n]*)\s*==+', p['text'])
        if not m: continue
        t = WN.generic({f'House|{today.date()}': {'section': p['text'][m.start():m.start() + 12000]}})
        if not t.empty: return {'dem2_median': float(t.dem2_median.iloc[-1]), 'aggregators': int(t.aggregators.iloc[-1]), 'page': p['title'], 'revision': p['timestamp']}
    return None


def ballot(text, state, seat, today):
    """(Democratic side, Republican side, fixed) as the race page's box names its nominees: each side's name or None, and
    fixed 'D' or 'R' when the seat is one party's whatever the voters do (two nominees of one party, or from September
    a side with no candidate at all)."""
    c = WC.race(text) if text else {'nominees': [], 'incumbent': None, 'incumbent_party': None}
    noms = [x for x in c['nominees'] if x.get('name')]
    dem, rep, _ = WC.sides(c, state)
    ind = [x for x in noms if x['party'] in ('I', 'O')]
    if dem is None and rep is not None and ind: dem = ind[0]      # no Democrat on the ballot: the independent against the Republican
    fixed = None
    n_d, n_r = sum(x['party'] == 'D' for x in noms), sum(x['party'] == 'R' for x in noms)
    if rep is None and n_d >= 2 and not ind: fixed = 'D'
    if dem is None and n_r >= 2: fixed = 'R'
    if fixed is None and today >= pd.Timestamp(f'{YEAR}-09-01'):
        dd = [x for x in seat['declared'] if x['party'] in ('D', 'I')]; rd = [x for x in seat['declared'] if x['party'] == 'R']
        if (dem or dd) and not (rep or rd): fixed = 'D'
        elif (rep or rd) and not (dem or dd): fixed = 'R'
    name = lambda x: x['name'] if x and x.get('name') else None
    return name(dem), name(rep), fixed


def surname(n):
    return BD.surname(WP.plain(n or '')) if n else ''


def same_person(a, b):
    """Two names for one person: the same surname and, when both give one, the same first initial."""
    if not a or not b or surname(a) != surname(b): return False
    fa, fb = WP.plain(a).split()[0][:1].upper(), WP.plain(b).split()[0][:1].upper()
    return fa == fb or len(WP.plain(a).split()) == 1 or len(WP.plain(b).split()) == 1


def build_races(pages, seats, model, today, days):
    lean = BD.leans(); past = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'past_races.csv'))
    ran = model['incumbent_ran_share']; rows, listed = [], []
    for s in seats:
        st, title = s['state'], race_title(s['state'], s['special'])
        page = pages.get(title); own = page is not None and page['title'] != OVERVIEW
        text = (page['text'] + '\n' + '\n'.join(p['text'] for t, p in pages.items() if t.startswith('Opinion polling for') and W28.NAMES[st] in t
                                                 and ('special' in t) == bool(s['special']))) if own else ''
        dem, rep, fixed = ballot(text, st, s, today) if own else (None, None, None)
        if not own and today >= pd.Timestamp(f'{YEAR}-09-01'):
            dem, rep, fixed = ballot('', st, s, today)
        dem_party = 'I' if dem and own and any(x['party'] in ('I', 'O') and same_person(x['name'], dem) for x in WC.race(text)['nominees']) else 'D'
        party = s['incumbent_party'] if s['incumbent'] else None
        side = 'dem' if party in ('D', 'I') else 'rep' if party == 'R' else None      # independents sit with the Democrats now
        nominee = dem if side == 'dem' else rep if side == 'rep' else None
        if side and nominee:                                       # the senator's party has chosen: they run if they are its nominee
            runs = 1.0 if same_person(nominee, s['incumbent']) else 0.0
            short = ('Nominees chosen' if dem and rep else 'Won the nomination') if runs else ('Not running' if s['running'] is False else 'Lost the nomination')
        else:
            runs = {True: 1.0, False: 0.0, None: ran}[s['running']] if side else 0.0
            short = ('Nominees chosen' if dem and rep else 'Running again' if runs == 1 else 'Not running' if runs == 0 and side else
                     'Has not said' if side else 'Appointee not yet named' if not s['incumbent'] else 'Open seat')
        # records: each side's nominee, or before their party chooses, the senator on their own side (counted as likely
        # to run as they are)
        hold = {'dem': dem or (s['incumbent'] if side == 'dem' else None), 'rep': rep or (s['incumbent'] if side == 'rep' else None)}
        placeholder = side if side and not nominee else None
        tr = BD.track_records(pd.DataFrame([{'year': YEAR, 'state': st, 'dem': (hold['dem'] or '').upper(), 'rep': (hold['rep'] or '').upper()}]), P=past).iloc[0]
        dt = float(tr.dem_track) if pd.notna(tr.dem_track) and hold['dem'] else 0.0; rt = float(tr.rep_track) if pd.notna(tr.rep_track) and hold['rep'] else 0.0
        track_full = dt - rt; track_open = (0.0 if placeholder == 'dem' else dt) - (0.0 if placeholder == 'rep' else rt)
        track = track_open + runs * (track_full - track_open) if placeholder else track_full
        # polls: every general-election poll on the race's pages is listed; the nominees' own matchup counts once both are
        # chosen, polls marked as paid for by a party or a campaign left out, as in training
        poll, pw, n_polls, counted = None, 0.0, 0, set()
        if dem and rep and not fixed:
            P = pd.DataFrame(WP.parse(text, dem.upper(), rep.upper(), st, YEAR))
            if len(P):
                P = P[P.partisan.fillna('') == ''] if 'partisan' in P else P
                P = P[pd.to_datetime(P.end) <= today]
                if len(P):
                    counted = {(p.pollster, p.end, round(float(p.dem_pct), 1), round(float(p.rep_pct), 1)) for p in P.itertuples()}
                    P = P.assign(dem2=100 * P.dem_pct / (P.dem_pct + P.rep_pct), population=P.population.astype(str).str.lower())
                    t = B.table(P, {'end': 'end', 'n': 'n', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'})
                    poll, pw = B.average(t, today, max(days, 1)); n_polls = int(len(P))
        for q in PL.matchups(text, st, YEAR) if own else []:
            dq = next((c['pct'] for c in q['cands'] if c['party'] in ('D', 'I') and same_person(c['name'], dem)), None) if dem else None
            rq = next((c['pct'] for c in q['cands'] if c['party'] == 'R' and same_person(c['name'], rep)), None) if rep else None
            key = (q['pollster'], q['end'], round(dq, 1) if dq is not None else None, round(rq, 1) if rq is not None else None)
            if q['partisan']: why = 'Paid for by a party or a campaign'
            elif fixed: why = 'The seat is one party\'s'
            elif not (dem and rep): why = 'The nominees are not chosen yet'
            elif dq is None or rq is None: why = 'Not the nominees\' matchup'
            elif pd.Timestamp(q['end']) > today: why = 'Not finished yet'
            elif key in counted: why = None
            else: why = 'Not read as the nominees\' matchup'
            listed.append({**q, 'special': bool(s['special']), 'counted': why is None, 'why': why})
        rows.append({'state': st, 'special': bool(s['special']), 'incumbent': s['incumbent'], 'incumbent_party': party, 'status': s['status'], 'short': short,
                     'incumbent_runs': round(runs, 4), 'dem': dem, 'dem_party': dem_party, 'rep': rep, 'fixed': fixed, 'declared': s['declared'],
                     'page': page['title'] if own else None, 'revision': page['timestamp'] if own else None,
                     'lean': lean(YEAR, st), 'inc_d': runs if side == 'dem' else 0.0, 'inc_r': runs if side == 'rep' else 0.0,
                     'track': round(float(track), 4), 'poll': poll, 'poll_w': pw, 'polls': n_polls,
                     # a senator whose plans are not known: whether they run is drawn in each simulated election
                     'unknown_intent': bool(placeholder and s['running'] is None), 'side': side,
                     'track_full': round(track_full, 4), 'track_open': round(track_open, 4)})
    return pd.DataFrame(rows), listed


def validate(seats, caucus_dem, caucus_rep, R, nat, appr):
    """What was read must look like a Senate election, or the run stops and the last good forecast stays."""
    bad = []
    if not 30 <= len(seats) <= 40: bad.append(f'{len(seats)} seats up')
    if len({(s['state'], s['special']) for s in seats}) != len(seats): bad.append('a seat listed twice')
    if not 95 <= caucus_dem + caucus_rep <= 100 or not 30 <= caucus_dem <= 70: bad.append(f'a chamber of {caucus_dem} and {caucus_rep}')
    if R.lean.isna().any(): bad.append('no lean for ' + ', '.join(R[R.lean.isna()].state))
    if appr and not 20 <= appr['median'] <= 80: bad.append(f'approval of {appr["median"]}')
    if not 35 <= nat['blend'] <= 65: bad.append(f'a national environment of {nat["blend"]:.1f}')
    if R.m.isna().any(): bad.append('a race without a forecast')
    if bad: raise RuntimeError('What was read does not look right, so the last forecast stays: ' + '; '.join(bad))


# ------------------------------------------------------------------------------------------------------------- the model
def distance(days, model):
    tested = sorted(int(d) for d in model['distances'])
    return next((d for d in tested if d >= days), tested[-1])


def widen(model, days):
    """The fitted pieces at the nearest distance tested; further out than a year, the error the races share keeps growing
    at the rate it grows between the last day and a year out (its variance, per day), and each race's whole error with it."""
    d = distance(days, model); dist = json.loads(json.dumps(model['distances'][str(d)]))
    far = max(int(k) for k in model['distances']); near = min(int(k) for k in model['distances'])
    if days > far:
        a, b = model['distances'][str(far)]['shared_sd'], model['distances'][str(near)]['shared_sd']
        extra = max(a ** 2 - b ** 2, 0.0) / (far - near) * (days - far)
        dist['shared_sd'] = round(math.sqrt(a ** 2 + extra), 4)
        dist['sd_total'] = {k: round(math.sqrt(v ** 2 + extra), 4) for k, v in dist['sd_total'].items()}
    return d, dist


def national(model, appr, gen):
    """The national environment (Democratic two-party House vote): the approval-and-midterm forecast, averaged half and half
    with the generic-ballot median once there is one."""
    N = model['national']; a = appr['median'] + N['gallup_offset'] if appr else None
    fund = None
    if a is not None:
        v = float(np.dot(N['house_vote']['coef'], [1, a, int(YEAR % 4 == 2)])); fund = v if PRES['party'] == 'D' else 100 - v
    g = gen['dem2_median'] if gen else None
    vals = [x for x in (fund, g) if x is not None]
    return {'approval_gallup_equivalent': a, 'fundamentals': fund, 'generic': g, 'blend': float(np.mean(vals)) if vals else None}


def seat_model(model, appr, up_pres_party, caucus_dem):
    """The national seat-change model's Democratic caucus after the election."""
    if not appr: return None
    a = appr['median'] + model['national']['gallup_offset']
    change = float(np.dot(model['national']['senate_seats']['coef'], [1, a, int(YEAR % 4 == 2), up_pres_party]))
    return caucus_dem + (change if PRES['party'] == 'D' else -change)


def president_draws(F):
    """The presidential forecast's simulated elections, drawn again exactly as model.simulate draws them (its seed, its
    order of places, its national, regional and state errors) from the states as published."""
    import model as M
    SET = {**M.SET, **(F.get('settings') or {})}                  # the settings the published run used
    S0 = pd.DataFrame(F['states']); n = int(SET['sims']); R = M.regions()
    rng = np.random.default_rng(int(SET['seed']) + YEAR); df = SET['t_df']
    eN = rng.standard_t(df, n) * F['national_sd'] / np.sqrt(df / (df - 2))
    regs = sorted(set(R[s] for s in S0.state)); eR = {g: rng.standard_normal(n) for g in regs}
    rs, ids = np.sqrt(SET['region_share']), np.sqrt(1 - SET['region_share'])
    sh = np.empty((len(S0), n))
    own = np.sqrt(np.maximum(S0.sd.values ** 2 - F['national_sd'] ** 2, 0))   # published sd is the state's whole spread, national error included
    for i, (st, m, sd) in enumerate(zip(S0.state, S0['mean'], own)):
        sh[i] = m + eN + sd * (rs * eR[R[st]] + ids * rng.standard_normal(n))
    sh = M.bound(sh); evs = S0.ev.values; dem_ev = (evs[:, None] * (sh > 50)).sum(0); total = evs.sum()
    idx = {st: i for i, st in enumerate(S0.state)}
    return {'dev': {st: sh[i] - S0['mean'].values[i] for st, i in idx.items() if len(st) == 2}, 'dem_win': dem_ev > total / 2, 'tie': dem_ev == total / 2,
            'national_sd': float(F['national_sd']), 'p_dem': float((dem_ev > total / 2).mean()), 'published_p_model': float(F.get('p_model', F['p_dem'])),
            'as_of': F.get('as_of'), 'n': n}


def presidential_link():
    """The presidential forecast's draws when it is for this election (its date plus its days to go is this election
    day); None in a midterm or when it cannot be read."""
    if YEAR % 4: return None, 'a midterm: no presidential race'
    try:
        F = json.load(open(os.path.join(ROOT, 'docs', 'api', 'forecast.json')))
        if pd.Timestamp(F['as_of']) + pd.Timedelta(days=int(F['days_out'])) != ELECTION: return None, 'the presidential forecast is for another election'
        return president_draws(F), None
    except Exception as e:                                         # noqa: BLE001 - the Senate forecast goes on without the link
        return None, f'presidential forecast not read: {type(e).__name__}'


def simulate(R, dist, model, pres):
    """The Democratic side's share in each race in each simulated election (sims x races), and the links used. A seat
    that is one party's whatever the voters do is 100 or 0 in every simulated election."""
    sim = model['simulation']; L, tdf = sim['pres_link'], sim['t_df']; sn = dist['shared_sd']
    n = pres['n'] if pres else 40000; rng = np.random.default_rng(SIMS_SEED)
    sd_tot = np.where(R.poll.notna(), dist['sd_total']['polls'], dist['sd_total']['no_polls'])
    if pres:
        rs = math.sqrt(max(sn ** 2 - (L * pres['national_sd']) ** 2, sim['shared_floor'] ** 2))
        dev = np.vstack([pres['dev'][st] for st in R.state]); v = dev.var(axis=1)
        Lj = np.minimum(L, np.sqrt(np.maximum(sd_tot ** 2 - rs ** 2 - sim['own_floor'] ** 2, 0) / v))
    else:
        rs, dev, v, Lj = sn, np.zeros((len(R), n)), np.zeros(len(R)), np.zeros(len(R))
    own = np.sqrt(np.maximum(sd_tot ** 2 - Lj ** 2 * v - rs ** 2, sim['own_floor'] ** 2))
    shared = rng.standard_t(tdf, size=(n, 1)) * rs * math.sqrt((tdf - 2) / tdf)
    X = R.m.values[None, :] + (Lj[:, None] * dev).T + shared + rng.standard_normal((n, len(R))) * own[None, :]
    # a senator whose plans are not known runs in each simulated election with the share of incumbents who ran again; the
    # race's centre is the average of the two, so each draw moves it by the gap between running and an open seat
    gap = R.run_gap.values; p = R.incumbent_runs.values; u = R.unknown_intent.values
    if u.any():
        runs = rng.random((n, len(R))) < p[None, :]
        X = X + np.where(u[None, :], (runs - p[None, :]) * gap[None, :], 0.0)
    fx = R.fixed.values
    X = np.where((fx == 'D')[None, :], 100.0, np.where((fx == 'R')[None, :], 0.0, X))
    return X, {'shared_sd_rest': round(rs, 4), 'link': [round(float(x), 4) for x in Lj], 'own_sd': [round(float(x), 4) for x in own], 'sd_total': [round(float(x), 4) for x in sd_tot]}


def main(saved=None):
    today = pd.Timestamp(os.environ.get('SENATE_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    setup(today)
    days = int((ELECTION - today).days)
    mp = os.path.join(OUT, 'model.json')
    if not os.path.exists(mp):                                     # a new cycle uses the latest fit until live_fit.py is run for it
        mp = sorted(p for p in (os.path.join(ROOT, 'data', 'senate', d, 'model.json') for d in os.listdir(os.path.join(ROOT, 'data', 'senate'))) if os.path.exists(p))[-1]
    model = json.load(open(mp))
    pages, seats = gather(today, saved)
    caucus_dem, caucus_rep = chamber(pages[OVERVIEW]['text'])
    # seats up by the party that holds them, a vacant seat by the party it was held by (as the overview lists it)
    up_dem = sum(1 for s in seats if s['incumbent_party'] in ('D', 'I')); up_rep = sum(1 for s in seats if s['incumbent_party'] == 'R')
    vacant_up = [s['state'] for s in seats if not s['incumbent']]
    holdover = caucus_dem - up_dem
    appr, gen = approval_now(pages, today), generic_now(pages, today)
    nat = national(model, appr, gen)
    if nat['blend'] is None: raise RuntimeError('No national input could be read (approval or generic ballot)')
    d, dist = widen(model, days)
    R, listed = build_races(pages, seats, model, today, days)
    R['blend_approval'] = nat['blend']
    coef = dist['coef']; R['f'] = coef['const'] + sum(coef[c] * R[c].values for c in model['columns'])
    R['m'] = B.blend(R, tuple(dist['blend']))
    validate(seats, caucus_dem, caucus_rep, R, nat, appr)
    # the gap between a senator running and an open seat, for those whose plans are not known (no polls yet: fundamentals only)
    R['run_gap'] = [(coef['inc_d'] if sd == 'dem' else coef['inc_r']) + coef['track'] * (tf - to) if u else 0.0
                    for sd, tf, to, u in zip(R.side, R.track_full, R.track_open, R.unknown_intent)]
    R['sd_total'] = np.where(R.poll.notna(), dist['sd_total']['polls'], dist['sd_total']['no_polls'])
    free = R.fixed.isna().values; fixed_d = int((R.fixed == 'D').sum())
    ns = seat_model(model, appr, up_rep if PRES['party'] == 'R' else up_dem, caucus_dem)
    own_total = holdover + fixed_d + float(sum(0.5 * (1 + math.erf((m - 50) / (s * math.sqrt(2)))) for m, s in zip(R.m[free], R.sd_total[free])))
    shift = 0.0
    if ns is not None and model['national']['combine'] and free.any():
        import simulate as SM
        shift = SM.shift_for(R.m.values[free], R.sd_total.values[free], (1 - model['national']['combine']) * own_total + model['national']['combine'] * ns - holdover - fixed_d)
        R.loc[free, 'm'] = R.m[free] + shift
    pres, pres_note = presidential_link()
    X, links = simulate(R, dist, model, pres)
    wins = X > 50; seats_d = wins.sum(axis=1); total = holdover + seats_d
    if pres: vp_dem = np.where(pres['tie'], 0.5, pres['dem_win'].astype(float))
    elif YEAR % 4 == 2: vp_dem = np.full(len(total), 1.0 if PRES['party'] == 'D' else 0.0)       # a midterm: the sitting vice president
    else: vp_dem = np.full(len(total), 0.5)                       # a presidential year without the presidential forecast: even
    control = np.where(total > 50, 1.0, np.where(total == 50, vp_dem, 0.0))
    lo, hi = np.percentile(total, [10, 90]); dist_tot = np.bincount(total.astype(int), minlength=101)[:101] / len(total)
    summ = {'dem_caucus_mean': round(float(total.mean()), 2), 'dem_caucus_median': int(np.median(total)), 'low80': int(lo), 'high80': int(hi),
            'p_dem_control': round(float(control.mean()), 4), 'p_50_50': round(float((total == 50).mean()), 4)}
    if pres:
        dw = pres['dem_win']
        summ.update({'p_dem_president': round(float(dw.mean()), 4), 'p_dem_control_if_dem_president': round(float(control[dw].mean()), 4) if dw.any() else None,
                     'p_dem_control_if_rep_president': round(float(control[~dw & ~pres['tie']].mean()), 4) if (~dw).any() else None,
                     'p_dem_both': round(float((dw * control).mean()), 4), 'p_rep_both': round(float(((~dw & ~pres['tie']) * (1 - control)).mean()), 4)})
    txt = lambda v: v if isinstance(v, str) and v else None              # a missing name is null, never NaN
    races = []
    for j, r in enumerate(R.itertuples()):
        x = X[:, j]; lo_j, hi_j = np.percentile(x, [10, 90]); fx = txt(r.fixed)
        races.append({'state': r.state, 'special': r.special, 'incumbent': txt(r.incumbent), 'incumbent_party': txt(r.incumbent_party), 'status': r.status, 'short': r.short,
                      'incumbent_runs': r.incumbent_runs, 'dem': txt(r.dem), 'dem_party': r.dem_party, 'rep': txt(r.rep), 'fixed': fx, 'declared': r.declared,
                      'margin': None if fx else round(2 * float(np.mean(x)) - 100, 2), 'low80': None if fx else round(2 * lo_j - 100, 2), 'high80': None if fx else round(2 * hi_j - 100, 2),
                      'p_dem': round(float((x > 50).mean()), 4),
                      'p_dem_if_dem_president': round(float((x[pres['dem_win']] > 50).mean()), 4) if pres and pres['dem_win'].any() else None,
                      'p_dem_if_rep_president': round(float((x[~pres['dem_win']] > 50).mean()), 4) if pres and (~pres['dem_win']).any() else None,
                      'fundamentals_margin': None if fx else round(2 * r.f - 100, 2), 'polls_margin': round(2 * r.poll - 100, 2) if r.poll == r.poll and r.poll is not None else None,
                      'polls': r.polls, 'lean': r.lean, 'track': r.track, 'page': txt(r.page),
                      'pres_link': links['link'][j], 'sd_own': links['own_sd'][j], 'sd_total': links['sd_total'][j],
                      'run_gap_margin': round(2 * float(r.run_gap), 2) if r.unknown_intent else None})
    long_out = days > max(int(k) for k in model['distances'])
    out = {'as_of': str(today.date()), 'year': YEAR, 'election': str(ELECTION.date()), 'days_out': days, 'distance_used': d,
           'president': PRES['name'], 'president_party': PRES['party'],
           'note': (('Further out than the furthest distance tested (a year): the year-out fit is used, and the shared error widened past a year at the rate it grows within the year. ' if long_out else '')
                    + 'Margins are the Democratic side minus the Republican, in points; the caucus counts the independents who sit with the Democrats.'),
           'chamber_now': {'dem_caucus': caucus_dem, 'rep': caucus_rep, 'seats_up': len(seats), 'dem_up': up_dem, 'rep_up': up_rep, 'vacant_up': vacant_up, 'dem_not_up': holdover},
           'national': {**{k: (round(v, 3) if isinstance(v, float) else v) for k, v in nat.items()},
                        'approval': {k: v for k, v in (appr or {}).items() if k != 'revision'} or None, 'generic_ballot': {k: v for k, v in (gen or {}).items() if k != 'revision'} or None,
                        'seat_model_dem_caucus': round(ns, 2) if ns is not None else None, 'races_own_dem_caucus': round(own_total, 2), 'shift_to_seat_model': round(shift, 3)},
           'presidential_forecast': ({'as_of': pres['as_of'], 'p_dem': round(pres['p_dem'], 4), 'published_p_model': round(pres['published_p_model'], 4)} if pres else {'note': pres_note}),
           'simulation': {'sims': int(len(total)), 'shared_sd': dist['shared_sd'], 'sd_total': dist['sd_total'], 'shared_sd_beside_president': links['shared_sd_rest'], 'pres_link': model['simulation']['pres_link']},
           'summary': summ, 'caucus_distribution': {str(i): round(float(p), 5) for i, p in enumerate(dist_tot) if p > 0}, 'races': races, 'polls': listed,
           'licence': 'Read from Wikipedia (CC BY-SA 4.0); the page versions read are in sources.json'}
    # the page versions read, kept apart so that an edit that changes no number does not change the forecast file
    sources = {'read': str(pd.Timestamp.now(tz='UTC')), 'overview': pages[OVERVIEW]['timestamp'], 'approval': (appr or {}).get('revision'), 'generic': (gen or {}).get('revision'),
               'races': {r.state + (' special' if r.special else ''): r.revision for r in R.itertuples() if isinstance(r.revision, str)}}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'forecast.json'), 'w') as f: json.dump(out, f, indent=1, allow_nan=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    with open(os.path.join(OUT, 'sources.json'), 'w') as f: json.dump(sources, f, indent=1)
    hp = os.path.join(OUT, 'history.csv')
    H = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    row = {'date': str(today.date()), 'days_out': days, 'p_dem_control': summ['p_dem_control'], 'dem_caucus_mean': summ['dem_caucus_mean'],
           'low80': summ['low80'], 'high80': summ['high80'], 'p_dem_president': summ.get('p_dem_president'), 'national': round(nat['blend'], 3)}
    H = pd.concat([H[H.date != row['date']] if len(H) else H, pd.DataFrame([row])], ignore_index=True).sort_values('date')
    H.to_csv(hp, index=False)
    page(out, H, model)
    print(json.dumps({k: out[k] for k in ('as_of', 'days_out', 'distance_used', 'chamber_now', 'national', 'presidential_forecast', 'summary')}, indent=1, default=str))
    return out


def page(out, H, model):
    """The site's Senate data (docs/api/senate.json): the Senate tab, the Senate polls, the Senate model and its back-tests."""
    t26 = json.load(open(os.path.join(ROOT, 'data', 'senate', '2026', 'test_2026.json')))
    last = next(d for d in t26['by_distance'] if d['days'] == 1); br = [r for r in t26['by_race'] if r['days'] == 1]
    check = {'called': last['called'], 'races': last['races'], 'dem_caucus_expected': round(last['dem_seats_mean'] + 34, 1), 'dem_caucus_actual': last['actual'] + 34,
             'avg_miss': round(float(np.mean([abs(r['forecast_margin'] - r['result_margin']) for r in br])), 1),
             'missed': sorted(W28.NAMES[r['state']] for r in br if (r['forecast_margin'] > 0) != (r['result_margin'] > 0))}
    mp = os.path.join(OUT, 'money.json')
    if not os.path.exists(mp): mp = os.path.join(ROOT, 'data', 'senate', str(YEAR), 'money.json')
    money = json.load(open(mp)) if os.path.exists(mp) else {}
    M = money.get('candidates', {})
    def cash(st, nm, pt):
        m = M.get(f'{st}|{nm}')
        return {'name': nm, 'party': pt, 'raised': m.get('raised'), 'cash': m.get('cash'), 'through': m.get('through')} if m else None
    races = []
    for r in out['races']:
        people = ([(r['incumbent'], r['incumbent_party'])] if r['incumbent'] else []) + [(x['name'], x['party']) for x in r['declared']] + [(r['dem'], 'D'), (r['rep'], 'R')]
        seen, money_rows = set(), []
        for nm, pt in people:
            if nm and surname(nm) not in seen:
                seen.add(surname(nm)); c = cash(r['state'], nm, pt)
                if c: money_rows.append(c)
        races.append({'state': r['state'], 'name': W28.NAMES[r['state']], 'special': r['special'], 'incumbent': r['incumbent'], 'party': r['incumbent_party'],
                      'status': r['short'], 'dem': r['dem'], 'dem_party': r['dem_party'], 'rep': r['rep'], 'fixed': r['fixed'],
                      'declared': [{'name': x['name'], 'party': x['party']} for x in r['declared'] if not same_person(x['name'], r['incumbent'])],
                      'p_dem': r['p_dem'], 'margin': r['margin'], 'low80': r['low80'], 'high80': r['high80'],
                      'p_dem_if_dem_president': r['p_dem_if_dem_president'], 'p_dem_if_rep_president': r['p_dem_if_rep_president'],
                      'polls': r['polls'], 'money': money_rows})
    polls = [{**{k: p[k] for k in ('state', 'special', 'pollster', 'end', 'n', 'pop', 'cands', 'counted', 'why')}, 'name': W28.NAMES[p['state']]} for p in out['polls']]
    keep = [k for k in ('365', '120', '60', '14', '1') if k in model['distances']]
    mdl = {'years': model['years'], 'columns': model['columns'], 'ran_share': model['incumbent_ran_share'], 'pres_link': model['simulation']['pres_link'],
           'combine': model['national']['combine'], 'gallup_offset': model['national']['gallup_offset'], 'house_vote': model['national']['house_vote']['coef'],
           'senate_seats': model['national']['senate_seats']['coef'], 't_df': model['simulation']['t_df'],
           'distances': {k: {'coef': model['distances'][k]['coef'], 'blend': model['distances'][k]['blend'], 'sd_total': model['distances'][k]['sd_total'],
                             'shared_sd': model['distances'][k]['shared_sd'], 'races': model['distances'][k]['races']} for k in keep}}
    bp = os.path.join(ROOT, 'data', 'senate', 'site_backtests.json')
    P = {'as_of': out['as_of'], 'year': out['year'], 'days_out': out['days_out'], 'election': out['election'], 'president': out['president'], 'president_party': out['president_party'],
         'chamber_now': out['chamber_now'], 'summary': out['summary'], 'distribution': out['caucus_distribution'], 'races': races, 'polls': polls,
         'national': {'approval': (out['national']['approval'] or {}).get('median'), 'environment': out['national']['blend'], 'generic': out['national']['generic'],
                      'fundamentals': out['national']['fundamentals'], 'seat_model': out['national']['seat_model_dem_caucus'], 'races_own': out['national']['races_own_dem_caucus']},
         'presidential_forecast': out['presidential_forecast'], 'check_2026': check, 'money_as_of': money.get('as_of'),
         'model': mdl, 'backtests': json.load(open(bp)) if os.path.exists(bp) else None,
         'history': [{'date': r.date, 'p': r.p_dem_control, 'mean': r.dem_caucus_mean} for r in H.itertuples()]}
    os.makedirs(API_DIR, exist_ok=True)
    with open(os.path.join(API_DIR, 'senate.json'), 'w') as f: json.dump(P, f, separators=(',', ':'), allow_nan=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[a.index('--pages') + 1] if '--pages' in a else None)
