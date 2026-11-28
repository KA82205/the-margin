"""The House forecast for the coming election, made by the hourly job after the Senate forecast, and the data of the
site's House tab (docs/api/house.json).

Each run:
  1. works out which election is next (from the day after an election, the one two years on), as the Senate forecast does;
  2. reads Wikipedia's overview of the election (CC BY-SA 4.0): each district's lean (Cook's PVI, as the page lists it for
     the lines in use), the member who holds it and what they have said about running, and the states changing maps;
  3. takes the national mood from the Senate forecast's latest run (data/senate/<year>/forecast.json): the
     approval-and-midterm House forecast, averaged half and half with the generic ballot once there is one;
  4. places each district with the fitted equation (data/house/model.json, house/fit.py): the year's level (the mood plus
     the usual gap between a year's level and its national House vote) plus the weights on its lean and on its member;
     once a district's two nominees are known, its polls of the two of them (on its state's page and its own page) are
     averaged as the presidential model averages polls, partisan ones left out, and blended in, with more of the weight
     the more polling there is, up to the cap fitted for that distance (house/polls.py);
  5. simulates the 435 seats together 40,000 times: an error every district shares, drawn from a t distribution with 5
     degrees of freedom and as large as the national mood's misses at the nearest distance tested, and each district's
     own; in a presidential year inside The Margin's presidential simulations (docs/api/forecast.json, drawn again with
     its own seed), each district moving half a point with each point its state's presidential vote moves, as the
     Senate's races do;
  6. checks what it read and made and stops, keeping the last good forecast, if anything is out of line.

Every case it meets on its own:
  - A member who has not said whether they will run is on the November ballot in each simulated election with the chance
    left over: of the members the past rate puts on the ballot (87%, 2018-2026), those not already accounted for by the
    members who have said they are running, spread over those who have not said.
  - A member who has said they are running is on the ballot unless they lose their primary, as 2% of those who ran did
    in 2018-2026, until the primary is held; a member renominated is on it.
  - A member retiring, running for another office, resigning, dying or losing a primary leaves the seat open, as does a
    vacancy; in a district with two members (after a redraw), each runs or not as their own plans say.
  - A state that enacts a new map: the page's leans for the new lines, once Wikipedia has them; a lean the page notes
    was not published by Cook for the lines adds the spread such leans have had (2024's redrawn states); a state whose
    page still gives the old lines' leans after a new map adds the spread a redraw has moved a district's lean by
    (measured on every redraw between censuses in the training table), until the leans are updated. A redraw still
    pending changes nothing until it is enacted.
  - Its checks need no list kept by hand: the number of districts each state has is the last election's, except in the
    first election after a census, when only the total of 435 is checked.
  - A district with one party's candidates only is left to its lean, as the safe seat it is.
  - Money raised is not used: tested on 2018-2024, it did not improve the forecast.

    python house/live.py                      fetches the overview and writes data/house/<year>/ and docs/api/house.json
    python house/live.py --pages FILE.json    reads pages saved before (tools/fetch_house_pages.py), for testing
"""
import json, math, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import polls as PO, wiki_house as WH

SEED = 2028
D = os.path.join(ROOT, 'data', 'house')
YEAR = ELECTION = OUT = API_DIR = None


def election_day(y):
    d = pd.Timestamp(f'{y}-11-01'); return d + pd.Timedelta(days=(7 - d.weekday()) % 7 + 1)


def setup(today):
    global YEAR, ELECTION, OUT, API_DIR
    YEAR = today.year + today.year % 2
    if election_day(YEAR) < today: YEAR += 2
    ELECTION = election_day(YEAR); OUT = os.path.join(D, str(YEAR)); API_DIR = os.path.join(ROOT, 'docs', 'api')
    if os.environ.get('HOUSE_TEST_DIR'): OUT = API_DIR = os.environ['HOUSE_TEST_DIR']          # tests write here, never to the real files


# ------------------------------------------------------------------------------------------------------------- reading
def gather(saved=None):
    """The overview page, and the function that fetches more pages (or takes them from the saved file)."""
    title = WH.overview(YEAR)
    if saved:
        S = json.load(open(saved)); get = lambda ts: {t: S[t] for t in ts if t in S}
    else:
        get = WH.fetch
    pages = get([title])
    if title not in pages: raise RuntimeError(f'The page "{title}" could not be read')
    return pages, get


def clean_status(s):
    """The page's account of the seat without the years a member was first elected, which can sit in the same cell
    ("2020 2024 (lost renomination) 2026 Incumbent's intent unknown")."""
    s = re.sub(r'\b(?:19|20)\d\d\b(?:\s*\([^)]*\))?', ' ', (s or '').replace('’', "'"))
    return re.sub(r'\s+', ' ', s).strip(' .|')


def plan(status):
    """What a member has said: 'out' (retiring, running for another office, resigned, died, lost the primary),
    'renominated', 'running' or 'unknown'."""
    s = clean_status(status).lower()
    if re.search(r"lost (?:re-?)?nomination|lost (?:the |their |a )?primary|retir|not (?:seeking|running)|to run for|running for (?!re-?election)|seeking (?!re-?election)|"
                 r"resign|died|death|vacan|expelled|declin|appointed to|withdr", s): return 'out'
    if re.search(r'renominated|won (?:re-?)?nomination|won (?:the |their )?primary|nominee', s): return 'renominated'
    if re.search(r'running|seeking re-?election|re-?election campaign|filed for|announced re-?election', s): return 'running'
    return 'unknown'


SHORT = {'out': 'Not running', 'lost': 'Not the nominee', 'renominated': 'Renominated', 'running': 'Running', 'unknown': 'Has not said', 'open': 'Vacant'}


def same_person(a, b):
    """The same person, as the training table matches members to candidates: a word of the surname in common and the
    same first two letters of the given name."""
    import build_data as BD
    if not a or not b or not (BD.names(a) & BD.names(b)): return False
    return BD.fold(a).split()[0][:2] == BD.fold(b).split()[0][:2]


def districts(text, model, latest):
    """One row a district, with each party's member and their chance of being on the November ballot."""
    W = pd.DataFrame(WH.rows(text, YEAR))
    if W.empty: raise RuntimeError('No district could be read from the overview')
    W['score'] = W.pvi.notna() * 2 + W.members.map(len)
    W = W.sort_values('score', ascending=False).groupby(['state', 'district'], as_index=False).first().sort_values(['state', 'district']).reset_index(drop=True)
    W['C'] = W.candidates_raw.map(WH.candidates)
    W['plan'] = W.status.map(plan)
    # once the nominees are known, they settle it: a member is on the ballot if they are their party's nominee, and not
    # if someone else is (beaten in the primary, or not running)
    nm = nominees(W)
    for i in W.index:
        k = (W.at[i, 'state'], int(W.at[i, 'district']))
        if k in nm and W.at[i, 'members']:
            won = [p for n, p in W.at[i, 'members'] if same_person(n, nm[k][0 if p == 'D' else 1]) and p in ('D', 'R')]
            W.at[i, 'plan'] = 'renominated' if won else 'lost'
            if len(W.at[i, 'members']) > 1: W.at[i, 'members'] = [m for m in W.at[i, 'members'] if m[1] in won] or W.at[i, 'members']
    changes = WH.map_changes(text)
    # the members' chances of running: the past rate of members on the ballot, less those who have said they run
    mem = [(i, n, p) for i, ms in enumerate(W.members) for n, p in ms]
    pl, run_share = model['members']['primary_loss'], model['members']['run_share']
    seats_m = int((W.members.map(len) > 0).sum())
    known = sum(1 - pl if W.plan[i] == 'running' else 1.0 if W.plan[i] == 'renominated' else 0.0 for i, _, _ in mem if W.plan[i] != 'unknown')
    n_unknown = int(sum(1 for i, _, _ in mem if W.plan[i] == 'unknown'))
    p_unknown = float(np.clip((run_share * seats_m - known) / n_unknown, 0.5, 0.97)) if n_unknown else None
    pr = {'out': 0.0, 'lost': 0.0, 'renominated': 1.0, 'running': 1 - pl, 'unknown': p_unknown}
    pd_, pr_ = [], []
    for i, ms in enumerate(W.members):
        p = pr[W.plan[i]] if ms else 0.0
        dem = [p for _, q in ms if q == 'D']; rep = [p for _, q in ms if q == 'R']
        pd_.append(1 - math.prod(1 - x for x in dem) if dem else 0.0); pr_.append(1 - math.prod(1 - x for x in rep) if rep else 0.0)
    W['p_inc_d'], W['p_inc_r'] = pd_, pr_
    # the lean and how far it can be trusted
    W['lean'] = W.pvi
    W['state_mean'] = W.groupby('state').pvi.transform('mean')
    W['lean_note'] = None
    W.loc[W.lean.isna(), 'lean_note'] = 'no lean listed: the state\'s average'; W['lean'] = W.lean.fillna(W.state_mean).fillna(0.0)
    W['extra_sd'] = 0.0
    W.loc[W.pvi_stale.astype(bool), 'extra_sd'] = model['redraw_sd']; W.loc[W.pvi_stale.astype(bool), 'lean_note'] = 'lean worked out on the new lines, not yet Cook\'s'
    W.loc[W.pvi.isna(), 'extra_sd'] = model['redraw_move_sd']
    for st, kind in changes.items():
        if kind != 'enacted' or st not in set(W.state): continue
        same = latest[latest.state == st].set_index('district').pvi if latest is not None else pd.Series(dtype=float)
        rows = W.index[W.state == st]
        if len(same) and all(W.at[i, 'district'] in same.index and same[W.at[i, 'district']] == W.at[i, 'pvi'] for i in rows):
            W.loc[rows, 'extra_sd'] = model['redraw_move_sd']; W.loc[rows, 'lean_note'] = 'new map: leans still those of the old lines'
    W['map'] = W.state.map(changes).fillna('in place')
    return W, changes, p_unknown, n_unknown


def nominees(W):
    """The districts whose two nominees the overview names: one Democrat and one Republican among its candidates."""
    out = {}
    for r in W.itertuples():
        gen = [c for c in r.C if c['round'] == 'general']
        dm = [c['name'] for c in gen if c['party'] == 'D']; rp = [c['name'] for c in gen if c['party'] == 'R']
        if len(dm) == 1 and len(rp) == 1: out[(r.state, int(r.district))] = (dm[0], rp[0])
    return out


def read_polls(pages, get, W, today, days):
    """Each district's polling average today, once its nominees are known: the polls of the two of them on its state's
    page and on the district's own page, partisan ones left out, in the presidential model's weights."""
    W['poll'], W['poll_w'], W['polls'] = np.nan, 0.0, 0
    nm = nominees(W)
    if not nm: return pd.DataFrame(), nm
    one = set(W.state[W.district == 0]); sts = sorted({s for s, _ in nm})
    want = [WH.state_title(YEAR, st, st in one) for st in sts]
    pages.update(get([t for t in want if t not in pages]))
    links = sorted({t for t in want if t in pages for t in PO.main_links(pages[t]['text'], YEAR)} - set(pages))
    if links: pages.update(get(links))
    P = PO.from_pages(pages, YEAR, nm)
    if len(P):
        Q = PO.prepared(P)
        for (st, d), g in Q.groupby(['state', 'district']):
            a = PO.average(g, today, max(days, 1))
            if a:
                i = W.index[(W.state == st) & (W.district == d)]
                W.loc[i, 'poll'] = a[0]; W.loc[i, 'poll_w'] = a[1]; W.loc[i, 'polls'] = a[2]
    return P, nm


def mood(today):
    """The national mood from the Senate forecast's last run: half the approval-and-midterm House forecast, half the
    generic ballot once there is one."""
    p = os.path.join(ROOT, 'data', 'senate', str(YEAR), 'forecast.json')
    if not os.path.exists(p): raise RuntimeError(f'The Senate forecast for {YEAR} (its national mood) could not be read')
    S = json.load(open(p)); n = S['national']
    age = (today - pd.Timestamp(S['as_of'])).days
    if S['year'] != YEAR or age > 3: raise RuntimeError(f'The Senate forecast\'s national mood is from {S["as_of"]} ({age} days old) for {S["year"]}')
    return {'blend': float(n['blend']), 'fundamentals': n.get('fundamentals'), 'generic': n.get('generic'), 'approval': (n.get('approval') or {}).get('median'),
            'as_of': S['as_of'], 'president': S.get('president'), 'president_party': S.get('president_party')}


# ------------------------------------------------------------------------------------------------------------- the model
def distance(days, model):
    tested = sorted(int(d) for d in model['distances'])
    return next((d for d in tested if d >= days), tested[-1])


def shared_sd(model, days):
    """The shared error at the nearest distance tested; further out than a year, its variance keeps growing at the rate it
    grows between the last day and a year out."""
    d = distance(days, model); s = model['distances'][str(d)]['shared_sd']
    far, near = max(int(k) for k in model['distances']), min(int(k) for k in model['distances'])
    if days > far:
        a, b = model['distances'][str(far)]['shared_sd'], model['distances'][str(near)]['shared_sd']
        s = math.sqrt(a ** 2 + max(a ** 2 - b ** 2, 0.0) / (far - near) * (days - far))
    return d, s


def president_draws(F):
    """The presidential forecast's simulated elections, drawn again exactly as model.simulate draws them (its seed, its
    order of places, its national, regional and state errors) from the states as published: as senate/live.py does."""
    import model as M
    SET = {**M.SET, **(F.get('settings') or {})}
    S0 = pd.DataFrame(F['states']); n = int(SET['sims']); R = M.regions()
    rng = np.random.default_rng(int(SET['seed']) + YEAR); df = SET['t_df']
    eN = rng.standard_t(df, n) * F['national_sd'] / np.sqrt(df / (df - 2))
    regs = sorted(set(R[s] for s in S0.state)); eR = {g: rng.standard_normal(n) for g in regs}
    rs, ids = np.sqrt(SET['region_share']), np.sqrt(1 - SET['region_share'])
    sh = np.empty((len(S0), n))
    own = np.sqrt(np.maximum(S0.sd.values ** 2 - F['national_sd'] ** 2, 0))
    for i, (st, m, sd) in enumerate(zip(S0.state, S0['mean'], own)):
        sh[i] = m + eN + sd * (rs * eR[R[st]] + ids * rng.standard_normal(n))
    sh = M.bound(sh); evs = S0.ev.values; dem_ev = (evs[:, None] * (sh > 50)).sum(0); total = evs.sum()
    return {'dev': {st: (sh[i] - S0['mean'].values[i]).astype(np.float32) for i, st in enumerate(S0.state)}, 'dem_win': dem_ev > total / 2, 'tie': dem_ev == total / 2,
            'national_sd': float(F['national_sd']), 'p_dem': float((dem_ev > total / 2).mean()), 'as_of': F.get('as_of'), 'n': n}


def presidential_link():
    if YEAR % 4: return None, 'a midterm: no presidential race'
    try:
        F = json.load(open(os.path.join(ROOT, 'docs', 'api', 'forecast.json')))
        if pd.Timestamp(F['as_of']) + pd.Timedelta(days=int(F['days_out'])) != ELECTION: return None, 'the presidential forecast is for another election'
        return president_draws(F), None
    except Exception as e:                                         # noqa: BLE001 - the House forecast goes on without the link
        return None, f'presidential forecast not read: {type(e).__name__}'


def simulate(W, model, level, sn, pres, d):
    """Each district's Democratic share in each simulated election (sims x districts), float32. Districts with a polling
    average are blended with it by the share fitted at distance d, and have the own error of polled districts."""
    c = model['coef']; sim = model['simulation']; L, tdf = sim['pres_link'], sim['t_df']
    n = pres['n'] if pres else 40000; rng = np.random.default_rng(SEED)
    W['f'] = level + c['lean'] * W.lean.values + c['inc_d'] * W.p_inc_d.values + c['inc_r'] * W.p_inc_r.values
    pp = (model.get('polls') or {}).get(str(d)) or {}
    hp = W.poll.notna().values & (pp.get('own_sd') is not None)
    W['poll_share'] = np.where(hp, pp.get('w0', 0) + (pp.get('w1', 0) - pp.get('w0', 0)) * W.poll_w.values / (W.poll_w.values + pp.get('k', 1)), 0.0)
    W['m'] = W.f + W.poll_share * (W.poll.fillna(W.f) - W.f)
    own0 = np.sqrt(np.where(hp, pp.get('own_sd') or model['district_sd'], model['district_sd']) ** 2 + W.extra_sd.values ** 2)
    sd_tot = np.sqrt(sn ** 2 + own0 ** 2)
    if pres:
        keys = [f'{s}{d}' if s in ('ME', 'NE') and f'{s}{d}' in pres['dev'] else s for s, d in zip(W.state, W.district)]
        rs = math.sqrt(max(sn ** 2 - (L * pres['national_sd']) ** 2, sim['shared_floor'] ** 2))
        v = np.array([float(pres['dev'][k].var()) for k in keys])
        Lj = np.minimum(L, np.sqrt(np.maximum(sd_tot ** 2 - rs ** 2 - sim['own_floor'] ** 2, 0) / v))
    else:
        keys, rs, v, Lj = None, sn, np.zeros(len(W)), np.zeros(len(W))
    own = np.sqrt(np.maximum(sd_tot ** 2 - Lj ** 2 * v - rs ** 2, sim['own_floor'] ** 2)).astype(np.float32)
    shared = (rng.standard_t(tdf, size=(n, 1)) * rs * math.sqrt((tdf - 2) / tdf)).astype(np.float32)
    X = W.m.values.astype(np.float32)[None, :] + shared + rng.standard_normal((n, len(W)), dtype=np.float32) * own[None, :]
    if pres:
        for j, k in enumerate(keys): X[:, j] += np.float32(Lj[j]) * pres['dev'][k]
    # a member whose running is not certain runs in each simulated election with their chance; the district's centre is
    # the average of the two, so each draw moves it by the member's weight times (ran - chance)
    for col, coef in (('p_inc_d', c['inc_d']), ('p_inc_r', c['inc_r'])):
        p = W[col].values; u = (p > 0) & (p < 1)
        if u.any():
            idx = np.where(u)[0]; runs = rng.random((n, len(idx)), dtype=np.float32) < p[idx][None, :]
            X[:, idx] += np.float32(coef) * (runs - p[idx][None, :].astype(np.float32))
    return X, {'shared_rest': rs, 'link': Lj, 'own': own, 'sd_total': sd_tot}


# ------------------------------------------------------------------------------------------------------------- checks
def validate(W, nat, seats_mean, latest=None):
    """What was read must look like the House, or the run stops and the last good forecast stays. Each state's number of
    districts must be the last election's (the training table's latest year), except in the first election after a
    census, when seats move between states and only the total is checked."""
    bad = []
    if len(W) != 435: bad.append(f'{len(W)} districts')
    per = W.groupby('state').size().to_dict()
    if latest is not None and len(latest) and YEAR % 10 != 2:
        was = latest.groupby('state').size().to_dict()
        if per != was: bad.append('districts by state: ' + ', '.join(f'{s} {per.get(s, 0)} (not {k})' for s, k in sorted(was.items()) if per.get(s, 0) != k)[:300])
    if W.pvi.isna().sum() > 5: bad.append(f'{int(W.pvi.isna().sum())} districts without a lean')
    if (W.members.map(len) > 0).sum() < 400: bad.append(f'only {int((W.members.map(len) > 0).sum())} districts with a member')
    if not 35 <= nat['blend'] <= 65: bad.append(f'a national mood of {nat["blend"]:.1f}')
    if not 100 <= seats_mean <= 335: bad.append(f'{seats_mean:.0f} Democratic seats on average')
    if bad: raise RuntimeError('What was read does not look right, so the last forecast stays: ' + '; '.join(bad))


# ------------------------------------------------------------------------------------------------------------- main
def main(saved=None):
    today = pd.Timestamp(os.environ.get('HOUSE_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    setup(today)
    days = int((ELECTION - today).days)
    model = json.load(open(os.path.join(D, 'model.json')))
    T = pd.read_csv(os.path.join(D, 'training.csv'))
    latest = T[T.year == T.year.max()] if len(T) else None
    pages, get = gather(saved); page = pages[WH.overview(YEAR)]
    W, changes, p_unknown, n_unknown = districts(page['text'], model, latest)
    P, nm = read_polls(pages, get, W, today, days)
    nat = mood(today)
    d, sn = shared_sd(model, days)
    level = nat['blend'] + model['gap']
    pres, pres_note = presidential_link()
    X, parts = simulate(W, model, level, sn, pres, d)
    wins = X > 50; seats = wins.sum(axis=1)
    validate(W, nat, float(seats.mean()), latest)
    majority = len(W) // 2 + 1
    lo, hi = np.percentile(seats, [10, 90]); maj = seats >= majority
    summ = {'dem_seats_mean': round(float(seats.mean()), 2), 'dem_seats_median': int(np.median(seats)), 'low80': int(lo), 'high80': int(hi),
            'p_dem_majority': round(float(maj.mean()), 4), 'p_tie': 0.0}
    if pres:
        dw = pres['dem_win']; rw = ~dw & ~pres['tie']
        summ.update({'p_dem_president': round(float(dw.mean()), 4), 'p_dem_majority_if_dem_president': round(float(maj[dw].mean()), 4) if dw.any() else None,
                     'p_dem_majority_if_rep_president': round(float(maj[rw].mean()), 4) if rw.any() else None,
                     'p_dem_both': round(float((dw & maj).mean()), 4), 'p_rep_both': round(float((rw & ~maj).mean()), 4)})
    dist = np.bincount(seats, minlength=len(W) + 1)[:len(W) + 1] / len(seats)
    txt = lambda v: v if isinstance(v, str) and v else None
    rows = []
    for j, r in enumerate(W.itertuples()):
        x = X[:, j]; l80, h80 = np.percentile(x, [10, 90]); mem = list(r.members)
        row = {'state': r.state, 'district': int(r.district), 'lean': round(float(r.lean), 1), 'lean_note': txt(r.lean_note), 'map': r.map,
               'members': [{'name': n, 'party': p} for n, p in mem], 'plan': SHORT['open'] if not mem else SHORT[r.plan], 'status': clean_status(r.status) or None,
               'p_member_runs': round(float(max(r.p_inc_d, r.p_inc_r)), 3) if mem else None,
               'p_dem': round(float(wins[:, j].mean()), 4), 'margin': round(2 * float(x.mean()) - 100, 2), 'low80': round(2 * float(l80) - 100, 2), 'high80': round(2 * float(h80) - 100, 2),
               'nominees': list(nm.get((r.state, int(r.district)), ())) or None,
               'poll_margin': round(2 * float(r.poll) - 100, 2) if r.poll == r.poll else None, 'polls': int(r.polls), 'poll_share': round(float(r.poll_share), 3)}
        if pres:
            row['p_dem_if_dem_president'] = round(float(wins[pres['dem_win'], j].mean()), 4)
            row['p_dem_if_rep_president'] = round(float(wins[~pres['dem_win'] & ~pres['tie'], j].mean()), 4)
        rows.append(row)
    long_out = days > max(int(k) for k in model['distances'])
    now_d = sum(1 for ms in W.members for _, p in ms[:1] if p == 'D'); now_r = sum(1 for ms in W.members for _, p in ms[:1] if p == 'R')
    out = {'as_of': str(today.date()), 'year': YEAR, 'election': str(ELECTION.date()), 'days_out': days, 'distance_used': d,
           'note': ('Further out than the furthest distance tested (a year): the year-out fit is used, and the shared error widened past a year at the rate it grows within the year. ' if long_out else '')
                   + 'Margins are the Democrats\' share less the Republicans\', in points.',
           'house_now': {'dem': now_d, 'rep': now_r, 'vacant': int(435 - now_d - now_r)},
           'national': {'mood': round(nat['blend'], 3), 'fundamentals': nat['fundamentals'], 'generic': nat['generic'], 'approval': nat['approval'], 'level': round(level, 3), 'gap': model['gap'],
                        'senate_as_of': nat['as_of'], 'president': nat['president'], 'president_party': nat['president_party']},
           'majority': majority,
           'polls': {'districts_with_nominees': len(nm), 'districts_with_polls': int(W.poll.notna().sum()), 'polls_read': int(len(P)),
                     'partisan_left_out': int((P.partisan.fillna('') != '').sum()) if len(P) else 0},
           'members': {'p_unknown_runs': round(p_unknown, 4) if p_unknown is not None else None, 'unknown': n_unknown,
                       'not_running': int(sum(1 for r in rows if r['plan'] in (SHORT['out'], SHORT['lost']))), 'running': int(sum(1 for r in rows if r['plan'] in (SHORT['running'], SHORT['renominated'])))},
           'maps': changes,
           'presidential_forecast': ({'as_of': pres['as_of'], 'p_dem': round(pres['p_dem'], 4)} if pres else {'note': pres_note}),
           'simulation': {'sims': int(len(seats)), 'shared_sd': round(sn, 4), 'shared_sd_beside_president': round(parts['shared_rest'], 4), 'district_sd': model['district_sd'], 'pres_link': model['simulation']['pres_link']},
           'summary': summ, 'seat_distribution': {str(i): round(float(p), 5) for i, p in enumerate(dist) if p > 0}, 'districts': rows,
           'licence': 'Read from Wikipedia (CC BY-SA 4.0); the page version read is in sources.json'}
    os.makedirs(OUT, exist_ok=True)
    dump = lambda o, p: json.dump(o, open(p, 'w'), indent=1, allow_nan=False, default=lambda v: v.item() if hasattr(v, 'item') else str(v))
    dump(out, os.path.join(OUT, 'forecast.json'))
    json.dump({'read': str(pd.Timestamp.now(tz='UTC')), 'overview': page['timestamp'], 'pages': {t: p['timestamp'] for t, p in sorted(pages.items()) if t != WH.overview(YEAR)}},
              open(os.path.join(OUT, 'sources.json'), 'w'), indent=1)
    hp = os.path.join(OUT, 'history.csv'); H = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    row = {'date': str(today.date()), 'days_out': days, 'p_dem_majority': summ['p_dem_majority'], 'dem_seats_mean': summ['dem_seats_mean'], 'low80': summ['low80'], 'high80': summ['high80'],
           'mood': round(nat['blend'], 3), 'p_dem_president': summ.get('p_dem_president')}
    H = pd.concat([H[H.date != row['date']] if len(H) else H, pd.DataFrame([row])], ignore_index=True).sort_values('date'); H.to_csv(hp, index=False)
    page_data(out, H, model)
    print(json.dumps({k: out[k] for k in ('as_of', 'days_out', 'distance_used', 'house_now', 'national', 'polls', 'members', 'maps', 'presidential_forecast', 'simulation', 'summary')}, indent=1, default=str))
    return out


def page_data(out, H, model):
    """The site's House data (docs/api/house.json): the House tab, the House model and its back-tests."""
    bp = os.path.join(D, 'backtest.json')
    B = json.load(open(bp)) if os.path.exists(bp) else None
    keep = [k for k in ('365', '120', '60', '14', '1') if k in model['distances']]
    mdl = {'years': model['years'], 'coef': model['coef'], 'district_sd': model['district_sd'], 'gap': model['gap'], 'gap_sd': model['gap_sd'],
           'members': model['members'], 'redraw_sd': model['redraw_sd'], 'redraw_move_sd': model['redraw_move_sd'], 'redraw_move_districts': model.get('redraw_move_districts'),
           't_df': model['simulation']['t_df'], 'pres_link': model['simulation']['pres_link'],
           'tossup_gap': model.get('tossup_gap'), 'polls': {k: model['polls'][k] for k in keep if k in model.get('polls', {})},
           'distances': {k: {'shared_sd': model['distances'][k]['shared_sd'], 'mood_rmse': model['distances'][k]['mood_rmse'], 'mood_bias': model['distances'][k]['mood_bias'],
                             'mood_years': model['distances'][k]['mood_years'], 'mood_miss': model['distances'][k].get('mood_miss')} for k in keep}}
    P = {k: out[k] for k in ('as_of', 'year', 'election', 'days_out', 'distance_used', 'house_now', 'national', 'majority', 'polls', 'members', 'maps', 'presidential_forecast', 'summary', 'seat_distribution', 'districts')}
    P.update({'sims': out['simulation']['sims'], 'shared_sd': out['simulation']['shared_sd'], 'model': mdl, 'backtests': B,
              'history': [{'date': r.date, 'p': r.p_dem_majority, 'mean': r.dem_seats_mean} for r in H.itertuples()]})
    os.makedirs(API_DIR, exist_ok=True)
    with open(os.path.join(API_DIR, 'house.json'), 'w') as f: json.dump(P, f, separators=(',', ':'), allow_nan=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[a.index('--pages') + 1] if '--pages' in a else None)
