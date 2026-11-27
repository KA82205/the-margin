"""The Senate forecast for the coming election (2028), made by the hourly job. Backend only: nothing here is on the site.

Each run:
  1. reads Wikipedia (CC BY-SA 4.0): the year's overview page (the seats up, who holds each, whether they are running,
     the declared candidates, and the chamber as it stands), each race's own page (its nominees, once chosen, and its
     polls), the approval polls and, once there is one, the generic-ballot page;
  2. builds each race's inputs as the back-test did: the state's lean, the national environment (half the generic ballot,
     half the approval-and-midterm House forecast), incumbency, the candidates' records, and the race's polling average;
  3. applies the fitted pieces in data/senate/2028/model.json (live_fit.py: the working version fitted on 2018-2026),
     at the nearest distance tested at or beyond today's (a year out is the furthest; further out, the year-out fit);
  4. pulls the expected seats a quarter of the way to the national seat-change model;
  5. simulates the races in the same 40,000 elections as The Margin's presidential forecast (docs/api/forecast.json),
     drawn again from its published states with its own seed: each state's Senate race moves half a point with each
     point its presidential vote moves in that election (step 16), and a 50-50 Senate goes to the party of the
     vice president elected with the president in that election.

Rules for what is not known yet:
  - Polls count once both nominees are on the race's page. Before the primaries the race runs on its fundamentals.
  - A senator whose plans are not known counts as running with the share of incumbents who ran again in 2018-2026
    (model.json, incumbent_ran_share), toward both incumbency and their record; one retiring counts as an open seat.

    python senate/live.py                      fetches the pages and writes data/senate/2028/
    python senate/live.py --pages FILE.json    reads pages saved before (tools/fetch_wiki_polls.py's shape), for testing

Writes data/senate/2028/forecast.json (the forecast, its inputs and each race), history.csv (one line a day) and
sources.json (the versions of the pages read).
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import backtest as B, build_data as BD, wiki_2028 as W28, wiki_candidates as WC, wiki_national as WN, wiki_polls as WP

YEAR = 2028
ELECTION = pd.Timestamp('2028-11-07')
OUT = os.path.join(ROOT, 'data', 'senate', '2028')
OVERVIEW = f'{YEAR} United States Senate elections'
APPROVAL = 'Opinion polling on the second Trump presidency'
GENERIC = (f'Opinion polling for the {YEAR} United States House of Representatives elections', f'{YEAR} United States House of Representatives elections')
PRES_PARTY = 'R'                                     # the party holding the White House going into the election
SIMS_SEED = 2028
UA = {'User-Agent': 'election-research (github.com/KA82205)'}
API = 'https://en.wikipedia.org/w/api.php?'


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


def race_title(state, special):
    return f'{YEAR} United States Senate {"special election" if special else "election"} in {W28.NAMES[state]}'


def polling_links(text):
    return sorted(set(t.strip() for t in re.findall(r'\[\[\s*(Opinion polling for the [^\]|#]+)', text or '') +
                      re.findall(r'\{\{\s*(?:main|see also|further)\s*\|\s*(Opinion polling for the [^}|#]+)', text or '', flags=re.I)))


def gather(saved=None):
    """Every page the forecast reads, fetched now (or taken from a saved file)."""
    if saved:
        S = json.load(open(saved)); flat = {}
        for v in S.values() if all(isinstance(v, dict) and 'text' not in v for v in S.values()) else [S]:
            flat.update(v)
        get = lambda ts: {t: flat[t] for t in ts if t in flat}
    else:
        get = fetch
    pages = get([OVERVIEW, APPROVAL, *GENERIC])
    if OVERVIEW not in pages: raise RuntimeError('The overview page could not be read')
    seats = W28.seats(pages[OVERVIEW]['text'])
    races = get([race_title(s['state'], s['special']) for s in seats])
    pages.update(races)
    links = sorted(set(l for p in races.values() for l in polling_links(p['text']) if str(YEAR) in l))
    pages.update(get(links))
    return pages, seats


# ------------------------------------------------------------------------------------------------------------- inputs
def chamber(text):
    """The Democratic caucus and the Republicans as the chamber stands, from the overview's box: Democrats plus the
    independents (who caucus with them), and the seats each side has up."""
    box = WC.infobox(text); num = lambda k: WC.number(WC.field(box, k)) or 0
    parties = {i: WC.field(box, f'party{i}') or '' for i in range(1, 6)}
    dem = sum(num(f'seats_before{i}') for i, p in parties.items() if 'Democratic' in p or 'Independent' in p)
    rep = sum(num(f'seats_before{i}') for i, p in parties.items() if 'Republican' in p)
    return int(dem), int(rep)


def approval_now(pages, today):
    p = pages.get(APPROVAL)
    if not p: return None
    m = re.search(WN.SECTIONS_APPROVAL, p['text'])
    if not m: return None
    t = WN.approval({f'{APPROVAL}|{today.date()}': {'section': p['text'][m.start():m.start() + 12000]}})
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


def nominees(text, state):
    """(Democratic side, Republican side) once the race page's box names both; else (None, None)."""
    if not text: return None, None
    c = WC.race(text); dem, rep, _ = WC.sides(c, state)
    return (dem['name'] if dem and dem.get('name') else None), (rep['name'] if rep and rep.get('name') else None)


def surname(n):
    return BD.surname(WP.plain(n or '')) if n else ''


def build_races(pages, seats, model, today, days):
    lean = BD.leans(); past = pd.read_csv(os.path.join(ROOT, 'data', 'senate', 'past_races.csv'))
    ran = model['incumbent_ran_share']; rows = []
    for s in seats:
        st, title = s['state'], race_title(s['state'], s['special'])
        page = pages.get(title); own = page is not None and page['title'] != OVERVIEW
        text = page['text'] + '\n' + '\n'.join(p['text'] for t, p in pages.items() if t.startswith('Opinion polling for') and W28.NAMES[st] in t) if own else ''
        dem, rep = nominees(text, st) if own else (None, None)
        party = s['incumbent_party'] if s['incumbent'] else None
        side = 'dem' if party == 'D' or (party == 'I' and (st, surname(s['incumbent'])) in BD.DEM_ALIGNED) else 'rep' if party == 'R' else None
        if dem and rep:                                            # the nominees are known: the incumbent runs if one of them
            nom = dem if side == 'dem' else rep if side == 'rep' else None
            runs = 1.0 if side and surname(nom) == surname(s['incumbent']) else 0.0; status = 'nominees chosen'
        else:
            runs = {True: 1.0, False: 0.0, None: ran}[s['running']] if side else 0.0; status = s['status']
        # records: the nominees', or before then the incumbent's on their own side (as likely to run as they are)
        names = {'dem': dem, 'rep': rep}
        if not (dem and rep) and side: names = {'dem': s['incumbent'] if side == 'dem' else None, 'rep': s['incumbent'] if side == 'rep' else None}
        tr = BD.track_records(pd.DataFrame([{'year': YEAR, 'state': st, 'dem': (names['dem'] or '').upper(), 'rep': (names['rep'] or '').upper()}]), P=past).iloc[0]
        dt = float(tr.dem_track) if pd.notna(tr.dem_track) and names['dem'] else 0.0; rt = float(tr.rep_track) if pd.notna(tr.rep_track) and names['rep'] else 0.0
        track = dt - rt
        if not (dem and rep): track *= runs
        # polls, once both nominees are known; partisan polls left out, as in training
        poll, pw, n_polls = None, 0.0, 0
        if dem and rep:
            P = pd.DataFrame(WP.parse(text, dem.upper(), rep.upper(), st, YEAR))
            if len(P):
                P = P[P.partisan.fillna('') == ''] if 'partisan' in P else P
                P = P.assign(dem2=100 * P.dem_pct / (P.dem_pct + P.rep_pct), population=P.population.astype(str).str.lower())
                t = B.table(P, {'end': 'end', 'n': 'n', 'pop': 'population', 'pollster': 'pollster', 'x': 'dem2'})
                poll, pw = B.average(t, today, max(days, 1)); n_polls = int((t.end <= today).sum())
        rows.append({'state': st, 'special': bool(s['special']), 'incumbent': s['incumbent'], 'incumbent_party': party, 'status': status,
                     'incumbent_runs': round(runs, 4), 'dem': dem, 'rep': rep, 'declared': s['declared'],
                     'page': page['title'] if own else None, 'revision': page['timestamp'] if own else None,
                     'lean': lean(YEAR, st), 'inc_d': runs if side == 'dem' else 0.0, 'inc_r': runs if side == 'rep' else 0.0,
                     'track': round(float(track), 4), 'poll': poll, 'poll_w': pw, 'polls': n_polls})
    return pd.DataFrame(rows)


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
        v = float(np.dot(N['house_vote']['coef'], [1, a, int(YEAR % 4 == 2)])); fund = v if PRES_PARTY == 'D' else 100 - v
    g = gen['dem2_median'] if gen else None
    vals = [x for x in (fund, g) if x is not None]
    return {'approval_gallup_equivalent': a, 'fundamentals': fund, 'generic': g, 'blend': float(np.mean(vals)) if vals else None}


def seat_model(model, appr, up_pres_party, caucus_dem):
    """The national seat-change model's Democratic caucus after the election."""
    if not appr: return None
    a = appr['median'] + model['national']['gallup_offset']
    change = float(np.dot(model['national']['senate_seats']['coef'], [1, a, int(YEAR % 4 == 2), up_pres_party]))
    return caucus_dem + (change if PRES_PARTY == 'D' else -change)


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


def simulate(R, dist, model, pres):
    """The Democratic side's share in each race in each simulated election (sims x races), and the links used."""
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
    return X, {'shared_sd_rest': round(rs, 4), 'link': [round(float(x), 4) for x in Lj], 'own_sd': [round(float(x), 4) for x in own], 'sd_total': [round(float(x), 4) for x in sd_tot]}


def main(saved=None):
    today = pd.Timestamp(os.environ.get('SENATE_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    days = int((ELECTION - today).days)
    model = json.load(open(os.path.join(OUT, 'model.json')))
    pages, seats = gather(saved)
    caucus_dem, caucus_rep = chamber(pages[OVERVIEW]['text'])
    up_dem = sum(1 for s in seats if s['incumbent_party'] in ('D', 'I')); up_rep = sum(1 for s in seats if s['incumbent_party'] == 'R')
    vacant_up = [s['state'] for s in seats if s['incumbent_party'] is None]
    holdover = caucus_dem - up_dem
    appr, gen = approval_now(pages, today), generic_now(pages, today)
    nat = national(model, appr, gen)
    if nat['blend'] is None: raise RuntimeError('No national input could be read (approval or generic ballot)')
    d, dist = widen(model, days)
    R = build_races(pages, seats, model, today, days)
    R['blend_approval'] = nat['blend']
    coef = dist['coef']; R['f'] = coef['const'] + sum(coef[c] * R[c].values for c in model['columns'])
    R['m'] = B.blend(R, tuple(dist['blend']))
    R['sd_total'] = np.where(R.poll.notna(), dist['sd_total']['polls'], dist['sd_total']['no_polls'])
    ns = seat_model(model, appr, up_rep if PRES_PARTY == 'R' else up_dem, caucus_dem)
    own_total = holdover + float(sum(0.5 * (1 + math.erf((m - 50) / (s * math.sqrt(2)))) for m, s in zip(R.m, R.sd_total)))
    shift = 0.0
    if ns is not None and model['national']['combine']:
        import simulate as SM
        shift = SM.shift_for(R.m.values, R.sd_total.values, (1 - model['national']['combine']) * own_total + model['national']['combine'] * ns - holdover)
        R['m'] = R.m + shift
    pres, pres_note = None, None
    fp = os.path.join(ROOT, 'docs', 'api', 'forecast.json')
    try:
        pres = president_draws(json.load(open(fp)))
    except Exception as e:                                         # noqa: BLE001 - the Senate forecast goes on without the link
        pres_note = f'presidential forecast not read: {type(e).__name__}'
    X, links = simulate(R, dist, model, pres)
    wins = X > 50; seats_d = wins.sum(axis=1); total = holdover + seats_d
    if pres:
        vp_dem = np.where(pres['tie'], 0.5, pres['dem_win'].astype(float))
    else:
        vp_dem = np.full(len(total), 0.0)
    control = np.where(total > 50, 1.0, np.where(total == 50, vp_dem, 0.0))
    lo, hi = np.percentile(total, [10, 90]); dist_tot = np.bincount(total.astype(int), minlength=101)[:101] / len(total)
    summ = {'dem_caucus_mean': round(float(total.mean()), 2), 'dem_caucus_median': int(np.median(total)), 'low80': int(lo), 'high80': int(hi),
            'p_dem_control': round(float(control.mean()), 4), 'p_50_50': round(float((total == 50).mean()), 4)}
    if pres:
        dw = pres['dem_win']
        summ.update({'p_dem_president': round(float(dw.mean()), 4), 'p_dem_control_if_dem_president': round(float(control[dw].mean()), 4) if dw.any() else None,
                     'p_dem_control_if_rep_president': round(float(control[~dw & ~pres['tie']].mean()), 4) if (~dw).any() else None,
                     'p_dem_both': round(float((dw * control).mean()), 4), 'p_rep_both': round(float(((~dw & ~pres['tie']) * (1 - control)).mean()), 4)})
    races = []
    for j, r in enumerate(R.itertuples()):
        x = X[:, j]; lo_j, hi_j = np.percentile(x, [10, 90])
        races.append({'state': r.state, 'special': r.special, 'incumbent': r.incumbent, 'incumbent_party': r.incumbent_party, 'status': r.status,
                      'incumbent_runs': r.incumbent_runs, 'dem': r.dem, 'rep': r.rep, 'declared': r.declared,
                      'margin': round(2 * float(np.mean(x)) - 100, 2), 'low80': round(2 * lo_j - 100, 2), 'high80': round(2 * hi_j - 100, 2),
                      'p_dem': round(float((x > 50).mean()), 4),
                      'p_dem_if_dem_president': round(float((x[pres['dem_win']] > 50).mean()), 4) if pres and pres['dem_win'].any() else None,
                      'p_dem_if_rep_president': round(float((x[~pres['dem_win']] > 50).mean()), 4) if pres and (~pres['dem_win']).any() else None,
                      'fundamentals_margin': round(2 * r.f - 100, 2), 'polls_margin': round(2 * r.poll - 100, 2) if r.poll == r.poll and r.poll is not None else None,
                      'polls': r.polls, 'lean': r.lean, 'track': r.track, 'page': r.page,
                      'pres_link': links['link'][j], 'sd_own': links['own_sd'][j], 'sd_total': links['sd_total'][j]})
    out = {'as_of': str(today.date()), 'election': str(ELECTION.date()), 'days_out': days, 'distance_used': d,
           'note': ('Backend only. ' + ('Further out than the furthest distance tested (a year): the year-out fit is used. ' if days > max(int(k) for k in model['distances']) else '')
                    + ('The shared error is widened past a year at the rate it grows within the year. ' if days > max(int(k) for k in model['distances']) else '')
                    + 'Margins are the Democratic side minus the Republican, in points; the caucus counts the independents who sit with the Democrats.'),
           'chamber_now': {'dem_caucus': caucus_dem, 'rep': caucus_rep, 'seats_up': len(seats), 'dem_up': up_dem, 'rep_up': up_rep, 'vacant_up': vacant_up, 'dem_not_up': holdover},
           'national': {**{k: (round(v, 3) if isinstance(v, float) else v) for k, v in nat.items()},
                        'approval': {k: v for k, v in (appr or {}).items() if k != 'revision'} or None, 'generic_ballot': {k: v for k, v in (gen or {}).items() if k != 'revision'} or None,
                        'seat_model_dem_caucus': round(ns, 2) if ns is not None else None, 'races_own_dem_caucus': round(own_total, 2), 'shift_to_seat_model': round(shift, 3)},
           'president': ({'as_of': pres['as_of'], 'p_dem': round(pres['p_dem'], 4), 'published_p_model': round(pres['published_p_model'], 4)} if pres else {'note': pres_note}),
           'simulation': {'sims': int(len(total)), 'shared_sd': dist['shared_sd'], 'sd_total': dist['sd_total'], 'shared_sd_beside_president': links['shared_sd_rest'], 'pres_link': model['simulation']['pres_link']},
           'summary': summ, 'caucus_distribution': {str(i): round(float(p), 5) for i, p in enumerate(dist_tot) if p > 0}, 'races': races,
           'licence': 'Read from Wikipedia (CC BY-SA 4.0); the page versions read are in sources.json'}
    # the page versions read, kept apart so that an edit that changes no number does not change the forecast file
    sources = {'read': str(pd.Timestamp.now(tz='UTC')), 'overview': pages[OVERVIEW]['timestamp'], 'approval': (appr or {}).get('revision'), 'generic': (gen or {}).get('revision'),
               'races': {r.state + (' special' if r.special else ''): r.revision for r in R.itertuples() if isinstance(r.revision, str)}}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'forecast.json'), 'w') as f: json.dump(out, f, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    with open(os.path.join(OUT, 'sources.json'), 'w') as f: json.dump(sources, f, indent=1)
    hp = os.path.join(OUT, 'history.csv')
    H = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    row = {'date': str(today.date()), 'days_out': days, 'p_dem_control': summ['p_dem_control'], 'dem_caucus_mean': summ['dem_caucus_mean'],
           'low80': summ['low80'], 'high80': summ['high80'], 'p_dem_president': summ.get('p_dem_president'), 'national': round(nat['blend'], 3)}
    H = pd.concat([H[H.date != row['date']] if len(H) else H, pd.DataFrame([row])], ignore_index=True).sort_values('date')
    H.to_csv(hp, index=False)
    print(json.dumps({k: out[k] for k in ('as_of', 'days_out', 'distance_used', 'chamber_now', 'national', 'president', 'summary')}, indent=1, default=str))
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[a.index('--pages') + 1] if '--pages' in a else None)
