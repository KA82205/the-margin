"""The governor forecast for every race from today through the next even-year election, made by the hourly job after the
Senate forecast, and the data of the site's Governors tab (docs/api/governor.json).

Each run:
  1. works out the races: those of the coming even-year election and of the odd year before it, if that one is still to
     come (Kentucky, Louisiana and Mississippi vote in the year before a presidential election; New Jersey and Virginia
     in the year after one), from Wikipedia's overview of each year (CC BY-SA 4.0): the governor, their party, what they
     have said (term-limited, running, retiring) and the candidates;
  2. reads each race's page and the polling pages it points to for the polls of its two nominees, once the overview
     names one Democrat and one Republican, partisan polls left out (gov_polls.py, house/polls.py);
  3. takes the national mood from the Senate forecast's last run (data/senate/<year>/forecast.json);
  4. places each race with the fitted equation (data/governor/model.json, gov_fit.py): the year's level, 50 + alpha +
     beta x (the national mood - 50), plus weights on the state's lean and on a governor running; a governor who has not
     said runs in each simulated election with the share of governors free to run who did; the race's polls blended in by
     the share fitted for its distance from election day;
  5. simulates the races together 40,000 times: an error every race shares (t with 5 degrees of freedom, as large as the
     fitted one at each race's distance) and each race's own; the even year's races inside The Margin's presidential
     simulations in a presidential year, each moving half a point with each point its state's presidential vote moves;
  6. counts the governorships each party holds after the races: the races' winners and, for the states with no race,
     the party of the governor their last election chose (the overview of the year it was held);
  7. checks what it read and made, and stops, keeping the last good forecast, if anything is out of line.

    python governor/gov_live.py                      fetches the pages and writes data/governor/<year>/ and docs/api/governor.json
    python governor/gov_live.py --pages FILE.json    reads pages saved before ({title: page}), for testing
"""
import glob, json, math, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import gov_data as GD, gov_polls as GP, wiki_governor as WG
from house_mod import load
HL = load('live')                      # house/live.py: the presidential draws and the shared error past a year

D = os.path.join(ROOT, 'data', 'governor')
SEED = 2028
YEAR = ELECTION = OUT = API_DIR = None
PLAN = {'out': 'Not running', 'term': 'Term-limited', 'lost': 'Not the nominee', 'nominee': 'The nominee', 'running': 'Running', 'unknown': 'Has not said', 'open': 'Vacant'}


def election_day(y):
    d = pd.Timestamp(f'{y}-11-01'); return d + pd.Timedelta(days=(7 - d.weekday()) % 7 + 1)


def setup(today):
    global YEAR, ELECTION, OUT, API_DIR
    YEAR = today.year + today.year % 2
    if election_day(YEAR) < today: YEAR += 2
    ELECTION = election_day(YEAR); OUT = os.path.join(D, str(YEAR)); API_DIR = os.path.join(ROOT, 'docs', 'api')
    if os.environ.get('GOVERNOR_TEST_DIR'): OUT = API_DIR = os.environ['GOVERNOR_TEST_DIR']


def plan(status):
    s = (status or '').replace('’', "'").lower()
    if re.search(r'term[- ]limited', s): return 'term'
    if re.search(r"lost (?:re-?)?nomination|lost (?:the |their |a )?primary|retir|not (?:seeking|running)|to run for|running for (?!re-?election)|resign|died|vacan|declin|withdr", s): return 'out'
    if re.search(r'renominated|won (?:re-?)?nomination|won (?:the |their )?primary', s): return 'nominee'
    if re.search(r'running|seeking re-?election|re-?election campaign|filed', s): return 'running'
    return 'unknown'


# ------------------------------------------------------------------------------------------------------------- reading
def gather(today, saved=None):
    """The overviews of the cycle's years and of the four years before (for the states with no race, the governor their
    last election chose), each race's page and its polling pages."""
    if saved:
        P = json.load(open(saved)); get = lambda ts: {t: P[t] for t in ts if t in P}
    else:
        import wiki_house as WH
        get = WH.fetch
    years = list(range(YEAR - 4, YEAR + 1))
    pages = get([WG.overview(y) for y in years])
    cycle = [y for y in (YEAR - 1, YEAR) if election_day(y) >= today]
    for y in cycle:
        if WG.overview(y) not in pages: raise RuntimeError(f'The page "{WG.overview(y)}" could not be read')
    races = {y: WG.races(pages[WG.overview(y)]['text'], y) for y in cycle}
    want = [WG.race_title(y, r['state']) for y in cycle for r in races[y]]
    pages.update(get([t for t in want if t not in pages]))
    links = sorted({l for y in cycle for r in races[y] for l in GP.poll_links(pages.get(WG.race_title(y, r['state']), {}).get('text', ''), y)} - set(pages))
    if links: pages.update(get(links))
    return pages, races, cycle


def holdovers(pages, cycle):
    """{state: party} of the governor each state's last election chose, for the states with no race in the cycle: the
    winner the latest earlier overview marks, else what its status says became of the seat, else the governor it lists."""
    up = set()
    for y in cycle:
        up |= {r['state'] for r in WG.races(pages[WG.overview(y)]['text'], y)}
    out = {}
    for y in sorted({int(t[:4]) for t in pages if t.endswith('United States gubernatorial elections')} - set(cycle), reverse=True):
        for r in WG.races(pages[WG.overview(y)]['text'], y):
            st = r['state']
            if st in up or st in out: continue
            won = [c['party'] for c in r['candidates'] if c['won']]
            m = re.search(r'(Democratic|Republican|Independent)\s+(?:gain|hold)', r['status'])
            out[st] = won[0] if won else (WG.PARTY_WORDS.get(m.group(1)) if m else None) or r['party']
    return out, up


def race_rows(races, pages, model, today, lean):
    out = []
    pr = model['governors_ran']
    for y, R in races.items():
        days = int((election_day(y) - today).days)
        for r in R:
            nm = WG.nominees(r); p = plan(r['status'])
            if nm and r['governor']:
                p = 'nominee' if WG.same_person(r['governor'], nm[0 if r['party'] == 'D' else 1]) and r['party'] in ('D', 'R') else 'lost'
            if not r['governor']: p = 'open'
            runs = {'term': 0.0, 'out': 0.0, 'lost': 0.0, 'open': 0.0, 'nominee': 1.0, 'running': 1.0, 'unknown': pr}[p]
            title = WG.race_title(y, r['state'])
            pg = pages.get(title, {})
            out.append({'year': y, 'state': r['state'], 'special': r['special'], 'days': days, 'governor': r['governor'], 'party': r['party'], 'status': r['status'],
                        'plan': p, 'p_runs': runs, 'nominees': nm, 'lean': lean(y, r['state']), 'page': title if pg else None, 'revision': pg.get('timestamp'),
                        'declared': [{'name': c['name'], 'party': c['party']} for c in r['candidates'] if c['round'] == 'general'],
                        'titles': [title] + GP.poll_links(pg.get('text', ''), y)})
    return pd.DataFrame(out)


def read_polls(pages, R, today):
    R['poll'], R['poll_w'], R['polls'] = np.nan, 0.0, 0
    for y in sorted(R.year.unique()):
        sub = R[(R.year == y) & R.nominees.notna()]
        if sub.empty: continue
        nm = {r.state: tuple(r.nominees) for r in sub.itertuples()}
        P = GP.from_pages(pages, y, nm, {r.state: r.titles for r in sub.itertuples()})
        if P.empty: continue
        Q = GP.HP.prepared(P)
        for st, g in Q.groupby('state'):
            i = R.index[(R.year == y) & (R.state == st)]
            a = GP.HP.average(g, today, max(int(R.loc[i[0], 'days']), 1))
            if a: R.loc[i, 'poll'] = a[0]; R.loc[i, 'poll_w'] = a[1]; R.loc[i, 'polls'] = a[2]


def mood(today):
    p = os.path.join(ROOT, 'data', 'senate', str(YEAR), 'forecast.json')
    if not os.path.exists(p): raise RuntimeError(f'The Senate forecast for {YEAR} (its national mood) could not be read')
    S = json.load(open(p)); n = S['national']; age = (today - pd.Timestamp(S['as_of'])).days
    if S['year'] != YEAR or age > 3: raise RuntimeError(f'The Senate forecast\'s national mood is from {S["as_of"]} ({age} days old) for {S["year"]}')
    return {'blend': float(n['blend']), 'fundamentals': n.get('fundamentals'), 'generic': n.get('generic'), 'as_of': S['as_of']}


# ------------------------------------------------------------------------------------------------------------- the model
def shared_at(model, days):
    """The shared error at the nearest distance tested at or beyond this one; past a year, growing at the rate it grows
    within the year (as the House's and the Senate's do)."""
    d, s = HL.shared_sd(model, days)
    return d, s


def simulate(R, model, level, pres):
    c = model['coef']; sim = model['simulation']; L, tdf = sim['pres_link'], sim['t_df']
    n = pres['n'] if pres else 40000; rng = np.random.default_rng(SEED)
    R['f'] = level + c['lean'] * R.lean.values + np.where(R.party == 'D', c['inc_d'], np.where(R.party == 'R', c['inc_r'], 0.0)) * R.p_runs.values
    dist = [shared_at(model, max(int(x), 1)) for x in R.days]; R['distance'] = [d for d, _ in dist]; sn = np.array([s for _, s in dist])
    pp = [(model['polls'].get(str(d)) or {}) for d in R.distance]
    hp = np.array([pd.notna(p) and q.get('own_sd') is not None for p, q in zip(R.poll, pp)])
    R['poll_share'] = [q['w0'] + (q['w1'] - q['w0']) * w / (w + q['k']) if h else 0.0 for h, q, w in zip(hp, pp, R.poll_w)]
    R['m'] = R.f + R.poll_share * (R.poll.fillna(R.f) - R.f)
    own0 = np.array([q['own_sd'] if h else model['race_sd'] for h, q in zip(hp, pp)])
    sd_tot = np.sqrt(sn ** 2 + own0 ** 2)
    linked = (R.year.values == YEAR) & bool(pres)
    if pres:
        rs = np.sqrt(np.maximum(sn ** 2 - (L * pres['national_sd']) ** 2, sim['shared_floor'] ** 2))
        v = np.array([float(pres['dev'][s].var()) if l else 0.0 for s, l in zip(R.state, linked)])
        Lj = np.where(linked, np.minimum(L, np.sqrt(np.maximum(sd_tot ** 2 - rs ** 2 - sim['own_floor'] ** 2, 0) / np.where(v > 0, v, 1))), 0.0)
        rs = np.where(linked, rs, sn)
    else:
        rs, v, Lj = sn, np.zeros(len(R)), np.zeros(len(R))
    own = np.sqrt(np.maximum(sd_tot ** 2 - Lj ** 2 * v - rs ** 2, sim['own_floor'] ** 2))
    t = rng.standard_t(tdf, size=(n, 1)) * math.sqrt((tdf - 2) / tdf)
    X = R.m.values[None, :] + t * rs[None, :] + rng.standard_normal((n, len(R))) * own[None, :]
    if pres:
        for j, (s, l) in enumerate(zip(R.state, linked)):
            if l: X[:, j] += Lj[j] * pres['dev'][s]
    # a governor who has not said runs in each simulated election with the share who did; each draw moves the race by the
    # governor's weight times (ran - chance)
    u = (R.p_runs > 0) & (R.p_runs < 1)
    for j in np.where(u.values)[0]:
        coef = c['inc_d'] if R.party.iloc[j] == 'D' else c['inc_r'] if R.party.iloc[j] == 'R' else 0.0
        p = R.p_runs.iloc[j]; X[:, j] += coef * ((rng.random(n) < p) - p)
    return X, {'shared': sn, 'link': Lj, 'own': own, 'sd_total': sd_tot}


def validate(R, hold, up, nat):
    bad = []
    if len(R) == 0: bad.append('no race read')
    if not 5 <= len(R) <= 45: bad.append(f'{len(R)} races')
    if R.lean.isna().any(): bad.append('no lean for ' + ', '.join(R.state[R.lean.isna()]))
    if len(set(hold) | set(up)) != 50: bad.append(f'{len(set(hold) | set(up))} states accounted for, not 50')
    if any(v not in ('D', 'R', 'I') for v in hold.values()): bad.append('a governor of no known party among the states with no race')
    if not 35 <= nat['blend'] <= 65: bad.append(f'a national mood of {nat["blend"]:.1f}')
    if bad: raise RuntimeError('What was read does not look right, so the last forecast stays: ' + '; '.join(bad))


# ------------------------------------------------------------------------------------------------------------- main
def main(saved=None):
    today = pd.Timestamp(os.environ.get('GOVERNOR_TODAY') or pd.Timestamp.now(tz='America/New_York').date())
    setup(today)
    model = json.load(open(os.path.join(D, 'model.json')))
    pages, races, cycle = gather(today, saved)
    hold, up = holdovers(pages, cycle)
    R = race_rows(races, pages, model, today, GD.leans())
    read_polls(pages, R, today)
    nat = mood(today)
    validate(R, hold, up, nat)
    level = 50 + model['alpha'] + model['beta'] * (nat['blend'] - 50)
    HL.YEAR, HL.ELECTION = YEAR, ELECTION
    pres, pres_note = HL.presidential_link()
    X, parts = simulate(R, model, level, pres)
    wins = X > 50
    held_d = sum(1 for v in hold.values() if v == 'D'); held_r = sum(1 for v in hold.values() if v == 'R')
    total = held_d + wins.sum(axis=1)
    lo, hi = np.percentile(total, [10, 90]); dist = np.bincount(total, minlength=51)[:51] / len(total)
    summ = {'dem_mean': round(float(total.mean()), 2), 'dem_median': int(np.median(total)), 'low80': int(lo), 'high80': int(hi),
            'p_dem_most': round(float((total >= 26).mean()), 4), 'p_even': round(float((total == 25).mean()), 4),
            'races': int(len(R)), 'dem_favored': int((wins.mean(0) > 0.5).sum()), 'dem_expected': round(float(wins.mean(0).sum()), 2)}
    if pres:
        dw = pres['dem_win']; summ.update({'p_dem_president': round(float(dw.mean()), 4)})
    txt = lambda v: v if isinstance(v, str) and v else None
    rows = []
    for j, r in enumerate(R.itertuples()):
        x = X[:, j]; l80, h80 = np.percentile(x, [10, 90])
        row = {'year': int(r.year), 'election': str(election_day(r.year).date()), 'state': r.state, 'name': WG.WH.NAMES[r.state], 'special': bool(r.special),
               'governor': txt(r.governor), 'party': txt(r.party), 'status': txt(r.status), 'plan': PLAN[r.plan], 'p_runs': round(float(r.p_runs), 3),
               'nominees': list(r.nominees) if isinstance(r.nominees, tuple) else None, 'declared': r.declared, 'lean': round(float(r.lean), 2),
               'p_dem': round(float(wins[:, j].mean()), 4), 'margin': round(2 * float(x.mean()) - 100, 2), 'low80': round(2 * float(l80) - 100, 2), 'high80': round(2 * float(h80) - 100, 2),
               'poll_margin': round(2 * float(r.poll) - 100, 2) if r.poll == r.poll else None, 'polls': int(r.polls), 'poll_share': round(float(r.poll_share), 3),
               'fundamentals_margin': round(2 * float(r.f) - 100, 2), 'distance': int(r.distance), 'page': txt(r.page)}
        if pres and r.year == YEAR:
            row['p_dem_if_dem_president'] = round(float(wins[pres['dem_win'], j].mean()), 4)
            row['p_dem_if_rep_president'] = round(float(wins[~pres['dem_win'] & ~pres['tie'], j].mean()), 4)
        rows.append(row)
    out = {'as_of': str(today.date()), 'year': YEAR, 'cycle': [{'year': y, 'election': str(election_day(y).date()), 'days_out': int((election_day(y) - today).days), 'races': int((R.year == y).sum())} for y in cycle],
           'governors_now': {'dem': held_d + int(sum(1 for r in R.itertuples() if r.party == 'D')), 'rep': held_r + int(sum(1 for r in R.itertuples() if r.party == 'R')),
                             'other': 50 - held_d - held_r - int(sum(1 for r in R.itertuples() if r.party in ('D', 'R')))},
           'not_up': {'dem': held_d, 'rep': held_r, 'states': {k: v for k, v in sorted(hold.items())}},
           'national': {'mood': round(nat['blend'], 3), 'fundamentals': nat['fundamentals'], 'generic': nat['generic'], 'level': round(level, 3), 'senate_as_of': nat['as_of']},
           'presidential_forecast': ({'as_of': pres['as_of'], 'p_dem': round(pres['p_dem'], 4)} if pres else {'note': pres_note}),
           'simulation': {'sims': int(len(total)), 'race_sd': model['race_sd'], 'pres_link': model['simulation']['pres_link']},
           'summary': summ, 'distribution': {str(i): round(float(p), 5) for i, p in enumerate(dist) if p > 0}, 'races': rows,
           'licence': 'Read from Wikipedia (CC BY-SA 4.0); the page versions read are in sources.json'}
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'forecast.json'), 'w'), indent=1, allow_nan=False, default=lambda v: v.item() if hasattr(v, 'item') else str(v))
    json.dump({'read': str(pd.Timestamp.now(tz='UTC')), 'pages': {t: p['timestamp'] for t, p in sorted(pages.items())}}, open(os.path.join(OUT, 'sources.json'), 'w'), indent=1)
    hp = os.path.join(OUT, 'history.csv'); H = pd.read_csv(hp) if os.path.exists(hp) else pd.DataFrame()
    row = {'date': str(today.date()), 'dem_mean': summ['dem_mean'], 'low80': summ['low80'], 'high80': summ['high80'], 'p_dem_most': summ['p_dem_most'], 'mood': round(nat['blend'], 3)}
    H = pd.concat([H[H.date != row['date']] if len(H) else H, pd.DataFrame([row])], ignore_index=True).sort_values('date'); H.to_csv(hp, index=False)
    page_data(out, H, model)
    print(json.dumps({k: out[k] for k in ('as_of', 'cycle', 'governors_now', 'not_up', 'national', 'presidential_forecast', 'summary')}, indent=1, default=str))
    return out


def page_data(out, H, model):
    """The site's governor data (docs/api/governor.json): the Governors tab, its model and its back-tests."""
    bp = os.path.join(D, 'backtest.json'); B = json.load(open(bp)) if os.path.exists(bp) else None
    keep = [k for k in ('365', '120', '60', '14', '1') if k in model['distances']]
    mdl = {k: model[k] for k in ('years', 'coef', 'race_sd', 'alpha', 'beta', 'level_sd', 'governors_ran', 'governors_free')}
    mdl.update({'t_df': model['simulation']['t_df'], 'pres_link': model['simulation']['pres_link'],
                'distances': {k: model['distances'][k] for k in keep}, 'polls': {k: model['polls'][k] for k in keep}})
    P = {k: out[k] for k in ('as_of', 'year', 'cycle', 'governors_now', 'not_up', 'national', 'presidential_forecast', 'summary', 'distribution', 'races')}
    P.update({'sims': out['simulation']['sims'], 'model': mdl, 'backtests': B, 'history': [{'date': r.date, 'mean': r.dem_mean} for r in H.itertuples()]})
    os.makedirs(API_DIR, exist_ok=True)
    with open(os.path.join(API_DIR, 'governor.json'), 'w') as f: json.dump(P, f, separators=(',', ':'), allow_nan=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[a.index('--pages') + 1] if '--pages' in a else None)
