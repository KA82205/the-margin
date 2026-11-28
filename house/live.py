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
    page still gives the old lines' leans after a new map adds the spread a redraw moves a district's lean by (about ten
    points), until the leans are updated. A redraw still pending changes nothing until it is enacted.
  - A district with one party's candidates only is left to its lean, as the safe seat it is.
  - Money raised is not used: tested on 2018-2024, it did not improve the forecast.

    python house/live.py                      fetches the overview and writes data/house/<year>/ and docs/api/house.json
    python house/live.py --pages FILE.json    reads pages saved before (tools/fetch_house_pages.py), for testing
"""
import json, math, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import wiki_house as WH

SEED = 2028
D = os.path.join(ROOT, 'data', 'house')
# what a redraw moves a district's lean by, where the page still gives the old lines' leans (house/fit.py measures the
# spread of leans noted as not Cook's; this one is the spread between a district's lean before and after the redraws of
# 2016-2024, by district number: 149 districts)
REDRAW_MOVE_SD = 9.7
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
    title = WH.overview(YEAR)
    if saved:
        S = json.load(open(saved)); page = S.get(title)
    else:
        page = WH.fetch([title]).get(title)
    if not page: raise RuntimeError(f'The page "{title}" could not be read')
    return page


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


SHORT = {'out': 'Not running', 'renominated': 'Renominated', 'running': 'Running', 'unknown': 'Has not said', 'open': 'Vacant'}


def districts(text, model, latest):
    """One row a district, with each party's member and their chance of being on the November ballot."""
    W = pd.DataFrame(WH.rows(text, YEAR))
    if W.empty: raise RuntimeError('No district could be read from the overview')
    W['score'] = W.pvi.notna() * 2 + W.members.map(len)
    W = W.sort_values('score', ascending=False).groupby(['state', 'district'], as_index=False).first().sort_values(['state', 'district']).reset_index(drop=True)
    W['plan'] = W.status.map(plan)
    changes = WH.map_changes(text)
    # the members' chances of running: the past rate of members on the ballot, less those who have said they run
    mem = [(i, n, p) for i, ms in enumerate(W.members) for n, p in ms]
    pl, run_share = model['members']['primary_loss'], model['members']['run_share']
    seats_m = int((W.members.map(len) > 0).sum())
    known = sum(1 - pl if W.plan[i] == 'running' else 1.0 if W.plan[i] == 'renominated' else 0.0 for i, _, _ in mem if W.plan[i] != 'unknown')
    n_unknown = int(sum(1 for i, _, _ in mem if W.plan[i] == 'unknown'))
    p_unknown = float(np.clip((run_share * seats_m - known) / n_unknown, 0.5, 0.97)) if n_unknown else None
    pr = {'out': 0.0, 'renominated': 1.0, 'running': 1 - pl, 'unknown': p_unknown}
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
    W.loc[W.pvi.isna(), 'extra_sd'] = REDRAW_MOVE_SD
    for st, kind in changes.items():
        if kind != 'enacted' or st not in set(W.state): continue
        same = latest[latest.state == st].set_index('district').pvi if latest is not None else pd.Series(dtype=float)
        rows = W.index[W.state == st]
        if len(same) and all(W.at[i, 'district'] in same.index and same[W.at[i, 'district']] == W.at[i, 'pvi'] for i in rows):
            W.loc[rows, 'extra_sd'] = REDRAW_MOVE_SD; W.loc[rows, 'lean_note'] = 'new map: leans still those of the old lines'
    W['map'] = W.state.map(changes).fillna('in place')
    return W, changes, p_unknown, n_unknown


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


def simulate(W, model, level, sn, pres):
    """Each district's Democratic share in each simulated election (sims x districts), float32."""
    c = model['coef']; sim = model['simulation']; L, tdf = sim['pres_link'], sim['t_df']
    n = pres['n'] if pres else 40000; rng = np.random.default_rng(SEED)
    own0 = np.sqrt(model['district_sd'] ** 2 + W.extra_sd.values ** 2)
    sd_tot = np.sqrt(sn ** 2 + own0 ** 2)
    W['m'] = level + c['lean'] * W.lean.values + c['inc_d'] * W.p_inc_d.values + c['inc_r'] * W.p_inc_r.values
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
APPORTIONED = {'AL': 7, 'AK': 1, 'AZ': 9, 'AR': 4, 'CA': 52, 'CO': 8, 'CT': 5, 'DE': 1, 'FL': 28, 'GA': 14, 'HI': 2, 'ID': 2, 'IL': 17, 'IN': 9, 'IA': 4, 'KS': 4, 'KY': 6,
               'LA': 6, 'ME': 2, 'MD': 8, 'MA': 9, 'MI': 13, 'MN': 8, 'MS': 4, 'MO': 8, 'MT': 2, 'NE': 3, 'NV': 4, 'NH': 2, 'NJ': 12, 'NM': 3, 'NY': 26, 'NC': 14, 'ND': 1,
               'OH': 15, 'OK': 5, 'OR': 6, 'PA': 17, 'RI': 2, 'SC': 7, 'SD': 1, 'TN': 9, 'TX': 38, 'UT': 4, 'VT': 1, 'VA': 11, 'WA': 10, 'WV': 2, 'WI': 8, 'WY': 1}   # the 2020 census


def validate(W, nat, seats_mean):
    bad = []
    if len(W) != 435: bad.append(f'{len(W)} districts')
    per = W.groupby('state').size().to_dict()
    if YEAR <= 2030 and per != APPORTIONED: bad.append('districts by state: ' + ', '.join(f'{s} {per.get(s, 0)} (not {k})' for s, k in APPORTIONED.items() if per.get(s, 0) != k)[:300])
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
    page = gather(saved)
    W, changes, p_unknown, n_unknown = districts(page['text'], model, latest)
    nat = mood(today)
    d, sn = shared_sd(model, days)
    level = nat['blend'] + model['gap']
    pres, pres_note = presidential_link()
    X, parts = simulate(W, model, level, sn, pres)
    wins = X > 50; seats = wins.sum(axis=1)
    validate(W, nat, float(seats.mean()))
    lo, hi = np.percentile(seats, [10, 90]); maj = seats >= 218
    summ = {'dem_seats_mean': round(float(seats.mean()), 2), 'dem_seats_median': int(np.median(seats)), 'low80': int(lo), 'high80': int(hi),
            'p_dem_majority': round(float(maj.mean()), 4), 'p_tie': 0.0}
    if pres:
        dw = pres['dem_win']; rw = ~dw & ~pres['tie']
        summ.update({'p_dem_president': round(float(dw.mean()), 4), 'p_dem_majority_if_dem_president': round(float(maj[dw].mean()), 4) if dw.any() else None,
                     'p_dem_majority_if_rep_president': round(float(maj[rw].mean()), 4) if rw.any() else None,
                     'p_dem_both': round(float((dw & maj).mean()), 4), 'p_rep_both': round(float((rw & ~maj).mean()), 4)})
    dist = np.bincount(seats, minlength=436)[:436] / len(seats)
    txt = lambda v: v if isinstance(v, str) and v else None
    rows = []
    for j, r in enumerate(W.itertuples()):
        x = X[:, j]; l80, h80 = np.percentile(x, [10, 90]); mem = list(r.members)
        row = {'state': r.state, 'district': int(r.district), 'lean': round(float(r.lean), 1), 'lean_note': txt(r.lean_note), 'map': r.map,
               'members': [{'name': n, 'party': p} for n, p in mem], 'plan': SHORT['open'] if not mem else SHORT[r.plan], 'status': clean_status(r.status) or None,
               'p_member_runs': round(float(max(r.p_inc_d, r.p_inc_r)), 3) if mem else None,
               'p_dem': round(float(wins[:, j].mean()), 4), 'margin': round(2 * float(x.mean()) - 100, 2), 'low80': round(2 * float(l80) - 100, 2), 'high80': round(2 * float(h80) - 100, 2)}
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
           'members': {'p_unknown_runs': round(p_unknown, 4) if p_unknown is not None else None, 'unknown': n_unknown,
                       'not_running': int(sum(1 for r in rows if r['plan'] == SHORT['out'])), 'running': int(sum(1 for r in rows if r['plan'] in (SHORT['running'], SHORT['renominated'])))},
           'maps': changes,
           'presidential_forecast': ({'as_of': pres['as_of'], 'p_dem': round(pres['p_dem'], 4)} if pres else {'note': pres_note}),
           'simulation': {'sims': int(len(seats)), 'shared_sd': round(sn, 4), 'shared_sd_beside_president': round(parts['shared_rest'], 4), 'district_sd': model['district_sd'], 'pres_link': model['simulation']['pres_link']},
           'summary': summ, 'seat_distribution': {str(i): round(float(p), 5) for i, p in enumerate(dist) if p > 0}, 'districts': rows,
           'licence': 'Read from Wikipedia (CC BY-SA 4.0); the page version read is in sources.json'}
    os.makedirs(OUT, exist_ok=True)
    dump = lambda o, p: json.dump(o, open(p, 'w'), indent=1, allow_nan=False, default=lambda v: v.item() if hasattr(v, 'item') else str(v))
    dump(out, os.path.join(OUT, 'forecast.json'))
    json.dump({'read': str(pd.Timestamp.now(tz='UTC')), 'overview': page['timestamp']}, open(os.path.join(OUT, 'sources.json'), 'w'), indent=1)
    hp = os.path.join(OUT, 'history.csv'); H = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    row = {'date': str(today.date()), 'days_out': days, 'p_dem_majority': summ['p_dem_majority'], 'dem_seats_mean': summ['dem_seats_mean'], 'low80': summ['low80'], 'high80': summ['high80'],
           'mood': round(nat['blend'], 3), 'p_dem_president': summ.get('p_dem_president')}
    H = pd.concat([H[H.date != row['date']] if len(H) else H, pd.DataFrame([row])], ignore_index=True).sort_values('date'); H.to_csv(hp, index=False)
    page_data(out, H, model)
    print(json.dumps({k: out[k] for k in ('as_of', 'days_out', 'distance_used', 'house_now', 'national', 'members', 'maps', 'presidential_forecast', 'simulation', 'summary')}, indent=1, default=str))
    return out


def page_data(out, H, model):
    """The site's House data (docs/api/house.json): the House tab, the House model and its back-tests."""
    bp = os.path.join(D, 'backtest.json')
    B = json.load(open(bp)) if os.path.exists(bp) else None
    keep = [k for k in ('365', '120', '60', '14', '1') if k in model['distances']]
    mdl = {'years': model['years'], 'coef': model['coef'], 'district_sd': model['district_sd'], 'gap': model['gap'], 'gap_sd': model['gap_sd'],
           'members': model['members'], 'redraw_sd': model['redraw_sd'], 'redraw_move_sd': REDRAW_MOVE_SD, 't_df': model['simulation']['t_df'], 'pres_link': model['simulation']['pres_link'],
           'distances': {k: {'shared_sd': model['distances'][k]['shared_sd'], 'mood_rmse': model['distances'][k]['mood_rmse'], 'mood_bias': model['distances'][k]['mood_bias'],
                             'mood_years': model['distances'][k]['mood_years']} for k in keep}}
    P = {k: out[k] for k in ('as_of', 'year', 'election', 'days_out', 'distance_used', 'house_now', 'national', 'members', 'maps', 'presidential_forecast', 'summary', 'seat_distribution', 'districts')}
    P.update({'sims': out['simulation']['sims'], 'shared_sd': out['simulation']['shared_sd'], 'model': mdl, 'backtests': B,
              'history': [{'date': r.date, 'p': r.p_dem_majority, 'mean': r.dem_seats_mean} for r in H.itertuples()]})
    os.makedirs(API_DIR, exist_ok=True)
    with open(os.path.join(API_DIR, 'house.json'), 'w') as f: json.dump(P, f, separators=(',', ':'), allow_nan=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[a.index('--pages') + 1] if '--pages' in a else None)
