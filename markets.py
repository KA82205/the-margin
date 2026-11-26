"""Prediction markets: found, read, weighed and kept. Nothing in this file moves the official forecast.

What it does on every check
    finds    every open market on the 2028 presidential election it can recognise at each provider: the national winner by
             party, the winner of each state, the District and the five districts of Maine and Nebraska, the national popular
             vote, and the markets on the margin, the electoral votes and the nominations (kept and shown, not turned into a
             chance of winning). Nothing is listed by hand: markets are found by searching each provider and by the pattern
             of their names, so a state market that opens next year is picked up the day it opens
    reads    a Democratic and a Republican price for each, as a chance between the two
    weighs   each market by how much it can be trusted today (quality(), below)
    combines for each place, one market from each provider (its best), averaged by quality
    keeps    every price in docs/markets/prices-YYYY-MM.csv whenever it has moved, and what each market is in
             docs/markets/registry.json. The record starts on November 25, 2026 and is never rewritten

Providers
    Polymarket   real money. gamma-api.polymarket.com: an event for each state, named by pattern
    Kalshi       real money. api.elections.kalshi.com: its list of election series is read once a day and searched
    Manifold     play money. api.manifold.markets: searched by words
    Election Betting Odds   an average of other exchanges' prices for the national winner. Because it is made from the same
                 markets, it is shown on its own line and joins the national figure only when no exchange is read directly

Quality, from 0 to 1. A market is worth more the more is staked on it, the more recently it traded and the tighter its
prices. Play money is not real money: a play-money market is scored on how many people have traded it, not on its volume,
and counts for half. These sizes are stated judgments. They are not fitted to anything, because there is no record of
such markets to fit them to (market_study.py says what little can be checked).

    real money   depth = log10(1 + dollars traded) / 6, at most 1        (a million dollars is full depth)
    play money   depth = log10(1 + people who traded) / 3, at most 1, then halved   (a thousand traders is full depth)
    freshness    1 if it traded in the last 7 days, falling to 0 at 60 days; 1 if the provider gives no time of last trade
    spread       1 at 2 cents or less between bid and ask, falling to 0 at 20 cents; 1 if the provider gives none
    quality      depth x freshness x spread

    python markets.py            read every provider and print what was found, changing nothing
"""
import csv, datetime, json, math, os, re, sys, time, urllib.parse, urllib.request

AGENT = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)', 'Accept': 'application/json'}
STATES = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
          'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
          'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
          'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
          'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'}
DC = ('district of columbia', 'washington, d.c.', 'washington dc', 'washington d.c.', 'washington, dc')
DISTRICTS = {'ME1': ('ME', 1), 'ME2': ('ME', 2), 'NE1': ('NE', 1), 'NE2': ('NE', 2), 'NE3': ('NE', 3)}
ORD = {1: ('1st', 'first'), 2: ('2nd', 'second'), 3: ('3rd', 'third')}
YEAR = 2028
PLAY_MONEY = 0.5


def get(url, timeout=30, tries=2):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT), timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception:                               # noqa: BLE001
            if k == tries - 1: raise
            time.sleep(1.5)


def place_of(text):
    """The state, district or 'US' a market's title is about, or None. A district is looked for before its state, and a
    longer name before a shorter one inside it (West Virginia, Washington, D.C.)."""
    t = ' ' + re.sub(r'[’`]', "'", text or '').lower() + ' '
    for code, (st, n) in DISTRICTS.items():
        name = next(k for k, v in STATES.items() if v == st).lower()
        if re.search(rf"\b{st.lower()}-0?{n}\b", t) or any(re.search(rf"{name}(?:'s)? {o} (?:congressional )?district", t) or re.search(rf"{name} cd-?{n}\b", t) for o in ORD[n]): return code
    if any(d in t for d in DC) or re.search(r'\bd\.c\.', t): return 'DC'
    for name in sorted(STATES, key=len, reverse=True):
        if re.search(rf"\b{name.lower()}\b", t): return STATES[name]
    return None


def kind_of(title):
    """What a market is about: 'winner' (which party wins the presidency, or a state), 'popular' (the national popular vote),
    'margin', 'electoral_votes', 'nomination', or None. With the place it is about, or 'US'."""
    t = (title or '').lower()
    if str(YEAR) not in t or re.search(r'senate|house|governor|congress|mayor|speaker|vice pres|\bvp\b|running mate|balance of power|convention|debate|primary\b|caucus|\bif\b|before|by 20|tipping', t): return None, None
    place = place_of(title)
    if re.search(r'popular vote margin|margin of victory|margin be', t) and place is None: return 'margin', 'US'
    if re.search(r'how many electoral|electoral votes will|electoral college (margin|votes)', t) and place is None: return 'electoral_votes', 'US'
    if re.search(r'nominee|nomination|nominated', t):   # one market for each party's nomination: who, not which party
        return ('nomination', 'D' if 'democrat' in t else 'R') if re.search(r'democrat|republican|gop', t) and place is None and re.match(r'\s*(who|\d{4} (democratic|republican) nominee)', t) else (None, None)
    if not re.search(r'president|electoral|popular vote|white house', t): return None, None
    if re.match(r'\s*who\b', t) or re.search(r'winning ticket|which candidate|\bwinner\?', t) and 'party' not in t and place is None: return None, None      # a market on people, not on parties
    if re.search(r'popular vote', t) and place is None: return 'popular', 'US'
    if re.search(r'\bwin\b|\bwins\b|winner|\bwon\b|carry|carries|stay red|stay blue|elected', t): return 'winner', place or 'US'
    return None, None


def two_party(d, r):
    """The Democratic chance out of the two parties, from a Democratic and a Republican price (either may be missing)."""
    if d is None and r is None: return None
    if d is None: d = 1 - r
    if r is None: r = 1 - d
    return None if d + r <= 0 else max(0.001, min(0.999, d / (d + r)))


def quality(c, now):
    if c['real_money']: depth = min(1.0, math.log10(1 + max(c.get('volume') or 0, 0)) / 6)
    else: depth = PLAY_MONEY * min(1.0, math.log10(1 + max(c.get('traders') or 0, 0)) / 3)
    fresh = 1.0
    if c.get('last_trade'):
        try: age = (now - datetime.datetime.fromisoformat(c['last_trade'].replace('Z', '+00:00'))).total_seconds() / 86400; fresh = max(0.0, min(1.0, 1 - (age - 7) / 53))
        except ValueError: pass
    spread = 1.0 if c.get('spread') is None else max(0.0, min(1.0, 1 - (c['spread'] - 0.02) / 0.18))
    return round(depth * fresh * spread, 4)


iso = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if ms else None


# -------------------------------------------------------------------------------------------------------------- providers
def manifold(read=get, cache=None):
    """Manifold: searched by words; a market's prices are asked for only when it has traded since it was last read."""
    found = {}; cache = cache if cache is not None else {}
    for term in (f'{YEAR} presidential election', f'Which party will win {YEAR} presidential election', f'{YEAR} presidential election popular vote electoral'):
        for offset in (0, 100, 200):
            got = read('https://api.manifold.markets/v0/search-markets?filter=open&limit=100&offset=%d&term=%s' % (offset, urllib.parse.quote(term)))
            for m in got:
                kind, place = kind_of(m.get('question'))
                if kind and not m.get('isResolved') and m.get('outcomeType') in ('BINARY', 'MULTIPLE_CHOICE'): found[m['id']] = (kind, place, m)
            if len(got) < 100: break
    # one market for each thing: the one most people have traded
    best = {}
    for kind, place, m in found.values():
        k = (kind, place)
        if k not in best or (m.get('uniqueBettorCount') or 0) > (best[k][2].get('uniqueBettorCount') or 0): best[k] = (kind, place, m)
    out = []
    for kind, place, m in best.values():
        was = cache.get(m['id']) or {}
        if was.get('last') == m.get('lastBetTime') and was.get('row'): row = dict(was['row'])
        else:
            full = read('https://api.manifold.markets/v0/market/' + m['id']); d = r = None; top = []
            if full.get('outcomeType') == 'BINARY':
                p = full.get('probability'); q = (full.get('question') or '').lower()
                if kind in ('winner', 'popular') and p is not None:
                    if re.search(r'democrat|blue', q) and not re.search(r'stay red', q): d = p
                    elif re.search(r'republican|gop|stay red', q): r = p
            else:
                for a in full.get('answers') or []:
                    t = (a.get('text') or '').lower(); p = a.get('probability', a.get('prob'))
                    if p is None: continue
                    if t.startswith('democrat'): d = p
                    elif t.startswith('republican'): r = p
                    top.append((a.get('text'), round(p, 4)))
            row = {'provider': 'Manifold', 'id': m['id'], 'title': full.get('question'), 'url': full.get('url'), 'real_money': False, 'dem': d, 'rep': r, 'volume': round(full.get('volume') or 0), 'liquidity': round(full.get('totalLiquidity') or 0),
                   'traders': full.get('uniqueBettorCount'), 'last_trade': iso(full.get('lastBetTime')), 'closes': iso(full.get('closeTime')), 'spread': None, 'rules': (full.get('textDescription') or '')[:300],
                   'answers': sorted(top, key=lambda x: -x[1])[:8] if kind in ('nomination', 'margin', 'electoral_votes') else None}
            cache[m['id']] = {'last': m.get('lastBetTime'), 'row': row}; time.sleep(0.05)
        out.append(dict(row, kind=kind, place=place))
    return out


def polymarket(read=get):
    """Polymarket: one event for each state, named by pattern, asked for a few at a time; and the national event."""
    slug = lambda name: f"{YEAR}-presidential-election-{name.lower().replace(' ', '-')}-winner"
    want = {slug(name): code for name, code in STATES.items()}; want[slug('washington dc')] = 'DC'; want[f'{YEAR}-presidential-election'] = 'US'; want[f'which-party-wins-{YEAR}-us-presidential-election'] = 'US'
    for code, (st, n) in DISTRICTS.items():
        name = next(k for k, v in STATES.items() if v == st)
        want[slug(f'{name} {ORD[n][0]} district')] = code; want[slug(f'{name}-{n}')] = code
    out = []; slugs = list(want)
    for i in range(0, len(slugs), 12):
        got = read('https://gamma-api.polymarket.com/events?closed=false&limit=50&' + '&'.join('slug=' + s for s in slugs[i:i + 12]))
        for e in got if isinstance(got, list) else []:
            place = want.get(e.get('slug'))
            if place is None or e.get('closed'): continue
            side = {}
            for m in e.get('markets') or []:
                who = (m.get('groupItemTitle') or m.get('question') or '').lower()
                s = 'dem' if 'democrat' in who else 'rep' if 'republican' in who else None
                if s and not m.get('closed') and s not in side: side[s] = m
            if not side: continue
            def price(m):
                if not m: return None, None
                b, a = m.get('bestBid'), m.get('bestAsk')
                if b and a and 0 < b < a < 1 and a - b <= 0.2: return (a + b) / 2, a - b
                try: return float(json.loads(m.get('outcomePrices') or '[]')[0]), (a - b) if (a and b and a > b) else None
                except (ValueError, IndexError, TypeError): return (m.get('lastTradePrice') or None), None
            (d, sd), (r, sr) = price(side.get('dem')), price(side.get('rep')); ms = [m for m in side.values()]
            out.append({'provider': 'Polymarket', 'id': e.get('slug'), 'title': e.get('title'), 'url': 'https://polymarket.com/event/' + e.get('slug'), 'real_money': True, 'dem': d, 'rep': r,
                        'volume': round(sum(float(m.get('volumeNum') or 0) for m in ms)), 'liquidity': round(sum(float(m.get('liquidityNum') or 0) for m in ms)), 'traders': None,
                        'last_trade': max((m.get('updatedAt') or '' for m in ms), default=None) or None, 'closes': e.get('endDate'), 'spread': max([s for s in (sd, sr) if s is not None], default=None),
                        'rules': re.sub(r'\s+', ' ', e.get('description') or '')[:300], 'answers': None, 'kind': 'winner', 'place': place})
        time.sleep(0.1)
    return out


def kalshi(read=get, cache=None, today=None):
    """Kalshi: its election series are listed once a day and searched for presidential ones; their open events are read."""
    cache = cache if cache is not None else {}; today = today or str(datetime.date.today()); base = 'https://api.elections.kalshi.com/trade-api/v2/'
    if cache.get('series_day') != today or not cache.get('series'):
        series = []
        for s in read(base + 'series?category=Elections', timeout=60).get('series') or []:
            title = s.get('title') or ''; t = title.lower()
            if re.search(r'president|electoral college|popular vote', t) and not re.search(r'run\b|announce|debate|primary|nominee|nomination|prior office|french|brazil|colombia|chile|portugal|korea|turk|poland|ireland|kenya|peru|mongolia|tanzania|bosnia|bulgaria', t):
                series.append([s.get('ticker'), title])
        cache['series'] = series; cache['series_day'] = today
    out = []
    for ticker, title in cache['series']:
        t = title.lower(); place = place_of(title) or 'US'
        kind = 'popular' if 'popular vote' in t and 'margin' not in t else 'margin' if 'margin' in t else 'electoral_votes' if 'electoral' in t else 'winner'
        try: events = read(base + f'events?limit=50&status=open&with_nested_markets=true&series_ticker={ticker}').get('events') or []
        except Exception: continue                      # noqa: BLE001  one series that does not answer does not stop the rest
        for e in events:
            if str(YEAR) not in (e.get('event_ticker') or '') + ' ' + (e.get('title') or '') and str(YEAR)[2:] not in (e.get('event_ticker') or '').split('-')[-1]: continue
            side = {}
            for m in e.get('markets') or []:
                who = ((m.get('yes_sub_title') or '') + ' ' + (m.get('title') or '')).lower()
                s = 'dem' if 'democrat' in who else 'rep' if 'republican' in who else None
                if s and m.get('status') in ('active', 'open', None) and s not in side: side[s] = m
            if not side and kind in ('winner', 'popular'): continue
            f = lambda m, k: float(m.get(k) or 0) if m else 0.0
            def price(m):
                if not m: return None, None
                b, a, last = f(m, 'yes_bid_dollars'), f(m, 'yes_ask_dollars'), f(m, 'last_price_dollars')
                return ((a + b) / 2, a - b) if 0 < b < a < 1 and a - b <= 0.2 else ((last or None), (a - b) if a > b > 0 else None)
            (d, sd), (r, sr) = price(side.get('dem')), price(side.get('rep')); ms = list(side.values())
            out.append({'provider': 'Kalshi', 'id': e.get('event_ticker'), 'title': e.get('title') or title, 'url': 'https://kalshi.com/markets/' + str(ticker).lower(), 'real_money': True, 'dem': d, 'rep': r,
                        'volume': round(sum(f(m, 'volume_fp') for m in ms)), 'liquidity': round(sum(f(m, 'open_interest_fp') for m in ms)), 'traders': None, 'last_trade': max((m.get('updated_time') or '' for m in ms), default=None) or None,
                        'closes': (ms[0].get('close_time') if ms else None), 'spread': max([s for s in (sd, sr) if s is not None], default=None), 'rules': (ms[0].get('rules_primary') or '')[:300] if ms else '', 'answers': None, 'kind': kind, 'place': place})
        time.sleep(0.05)
    return out


def wq(v, w, qs):
    """Points of a weighted sample: the value below which each share q of the weight lies."""
    import numpy as np
    o = np.argsort(v); c = np.cumsum(w[o]); c = c / c[-1]
    return [float(v[o][min(len(v) - 1, int(np.searchsorted(c, q)))]) for q in qs]


def tilt(sims, targets, strength=0.5, floor=0.25, ridge=0.02):
    """The simulated elections, weighted so that market-priced events happen a little more or less often.

    sims: {'states': [codes], 'dem': a places-by-elections table of who won each place, 'ev': Democratic electoral votes,
    'total': all electoral votes, 'vote': the national vote} from the official simulation, untouched.
    targets: {'winner:TX': {'p': the markets' chance, 'quality': 0 to 1}, ...}.

    Each priced event's chance is moved from the simulation's toward the markets' by `strength` x quality of the way, on the
    log-odds scale: at most half way, and a thin market hardly at all. All of them are moved at once by giving every
    simulated election a weight (the least change to equal weights that does it, with a small pull back to equal weights so
    that markets which contradict each other cannot tear the sample apart). Nothing else is touched: the weighted elections
    are still whole elections, so the chance of winning, the electoral votes, each state and the national vote stay
    consistent with one another. If fewer than `floor` of the elections would effectively remain, every move is halved until
    enough do. Returns the weights and what was done."""
    import numpy as np
    n = len(sims['ev']); X = []; m = []; names = []
    logit = lambda p: math.log(p / (1 - p))
    for key, t in targets.items():
        if t.get('p') is None or not t.get('quality'): continue
        kind, place = key.split(':')
        if kind == 'winner' and place == 'US': x = sims['ev'] > sims['total'] / 2
        elif kind == 'popular' and place == 'US': x = sims['vote'] > 50
        elif kind == 'winner' and place in sims['states']: x = sims['dem'][sims['states'].index(place)]
        else: continue
        p0 = float(np.mean(x))
        if p0 < 0.002 or p0 > 0.998: continue                # the simulation has next to no elections on one side: nothing to weight
        X.append(np.asarray(x, float)); m.append((p0, min(0.995, max(0.005, t['p'])), min(1.0, t['quality']))); names.append(key)
    if not X: return np.full(n, 1 / n), {'events': 0, 'effective': 1.0, 'strength': strength, 'moved': []}
    X = np.array(X).T; s = strength
    for _ in range(8):
        goal = np.array([1 / (1 + math.exp(-((1 - s * q) * logit(p0) + s * q * logit(pm)))) for p0, pm, q in m]); th = np.zeros(X.shape[1])
        for _ in range(60):                                  # Newton steps on a smooth, bowl-shaped problem: they settle
            z = X @ th; w = np.exp(z - z.max()); w /= w.sum(); mu = w @ X; g = mu - goal + ridge * th
            if np.abs(g).max() < 1e-6: break
            H = (X * w[:, None]).T @ X - np.outer(mu, mu) + ridge * np.eye(len(th)); th -= np.clip(np.linalg.solve(H, g), -2, 2)
        z = X @ th; w = np.exp(z - z.max()); w /= w.sum(); ess = float(1 / (n * (w ** 2).sum()))
        if ess >= floor: break
        s /= 2
    got = w @ X
    return w, {'events': len(names), 'effective': round(ess, 3), 'strength': s,
               'moved': [{'event': k, 'simulation': round(m[i][0], 4), 'markets': round(m[i][1], 4), 'quality': round(m[i][2], 3), 'aimed_at': round(float(goal[i]), 4), 'reached': round(float(got[i]), 4)} for i, k in enumerate(names)]}


def informed(sims, targets, **kw):
    """What the weighted elections say: the same figures the official forecast gives, from the same simulated elections."""
    import numpy as np
    w, did = tilt(sims, targets, **kw); ev = sims['ev']; half = sims['total'] / 2
    evq = wq(ev, w, [0.1, 0.5, 0.9]); vq = wq(sims['vote'], w, [0.1, 0.9])
    return dict(did, p_dem=float(w[ev > half].sum()), p_rep=float(w[ev < half].sum()), p_tie=float(w[ev == half].sum()), ev_median=evq[1], ev_lo=evq[0], ev_hi=evq[2], ev_mean=float(w @ ev),
                national=float(w @ sims['vote']), national_lo=vq[0], national_hi=vq[1], p_popular=float(w[sims['vote'] > 50].sum()), states={st: round(float(w @ sims['dem'][i]), 4) for i, st in enumerate(sims['states'])})


PROVIDERS = {'Polymarket': polymarket, 'Kalshi': kalshi, 'Manifold': manifold}


# ------------------------------------------------------------------------------------------------------------ the reading
def combine(contracts, now, aggregate=None):
    """For each kind and place: the best market of each provider, and their average by quality. `aggregate`: Election
    Betting Odds' national figure, used for the national winner only when no exchange was read directly."""
    for c in contracts:
        c['p'] = two_party(c.get('dem'), c.get('rep')) if c['kind'] in ('winner', 'popular') else None; c['quality'] = quality(c, now) if c['p'] is not None else 0.0
    out = {}
    for c in contracts:
        if c['p'] is None: continue
        k = f"{c['kind']}:{c['place']}"; best = out.setdefault(k, {})
        if c['provider'] not in best or c['quality'] > best[c['provider']]['quality']: best[c['provider']] = c
    res = {}
    for k, best in out.items():
        use = [c for c in best.values() if c['quality'] > 0]
        if not use:
            res[k] = {'p': None, 'quality': 0.0, 'providers': [], 'thin': [dict(provider=c['provider'], p=round(c['p'], 4), id=c['id']) for c in best.values()]}; continue
        w = sum(c['quality'] for c in use); z = sum(c['quality'] * math.log(c['p'] / (1 - c['p'])) for c in use) / w
        # several exchanges trade on the same news and against each other: together they count for the best of them and a
        # part of the rest, never for the sum
        qs = sorted((c['quality'] for c in use), reverse=True); together = min(1.0, qs[0] + 0.25 * sum(qs[1:]))
        res[k] = {'p': round(1 / (1 + math.exp(-z)), 4), 'quality': round(together, 4), 'real_money': any(c['real_money'] for c in use),
                  'providers': [{'provider': c['provider'], 'p': round(c['p'], 4), 'quality': c['quality'], 'real_money': c['real_money'], 'volume': c.get('volume'), 'traders': c.get('traders'), 'spread': c.get('spread'),
                                 'last_trade': c.get('last_trade'), 'url': c.get('url'), 'id': c['id']} for c in sorted(use, key=lambda c: -c['quality'])]}
    if aggregate is not None:
        k = 'winner:US'
        if k not in res or res[k]['p'] is None: res[k] = {'p': round(aggregate, 4), 'quality': 0.25, 'real_money': True, 'providers': [{'provider': 'Election Betting Odds', 'p': round(aggregate, 4), 'quality': 0.25, 'real_money': True, 'url': 'https://electionbettingodds.com/'}]}
        res[k]['election_betting_odds'] = round(aggregate, 4)
    return res


def collect(read=get, cache=None, now=None, aggregate=None, providers=None):
    """Every provider, each on its own: one that fails is named and the rest go on. Returns the reading."""
    now = now or datetime.datetime.now(datetime.timezone.utc); cache = cache if cache is not None else {}; contracts = []; failed = {}; counts = {}
    for name, fn in (providers or PROVIDERS).items():
        try:
            got = fn(read, cache.setdefault(name, {})) if name != 'Polymarket' else fn(read)
            contracts += got; counts[name] = len(got)
        except Exception as err:                        # noqa: BLE001
            failed[name] = f'{type(err).__name__}: {str(err)[:100]}'
    combined = combine(contracts, now, aggregate)
    return {'read': now.strftime('%Y-%m-%dT%H:%MZ'), 'counts': counts, 'failed': failed, 'combined': combined,
            'contracts': [{k: c.get(k) for k in ('provider', 'id', 'kind', 'place', 'title', 'url', 'real_money', 'dem', 'rep', 'p', 'quality', 'volume', 'liquidity', 'traders', 'spread', 'last_trade', 'closes', 'rules', 'answers')} for c in contracts]}


def moved(a, b):
    """Is reading b news against reading a? A new or vanished market, a national figure a point away, a state three."""
    A, B = (a or {}).get('combined') or {}, (b or {}).get('combined') or {}
    if set(A) != set(B): return True
    for k in B:
        pa, pb = A[k].get('p'), B[k].get('p')
        if (pa is None) != (pb is None): return True
        if pa is not None and abs(pa - pb) >= (0.01 if k.endswith(':US') else 0.03): return True
    return False


def keep(reading, root='docs/markets'):
    """Add what has changed to the record. prices-YYYY-MM.csv gains a line for every market whose price or volume differs from
    its last line; registry.json says what each market is and when it was first and last seen; latest.json is the reading."""
    os.makedirs(root, exist_ok=True); reg_path = os.path.join(root, 'registry.json'); reg = json.load(open(reg_path)) if os.path.exists(reg_path) else {}
    month = reading['read'][:7]; path = os.path.join(root, f'prices-{month}.csv'); cols = ['time', 'provider', 'id', 'kind', 'place', 'dem', 'rep', 'p', 'quality', 'volume', 'liquidity', 'traders', 'spread']
    rows = []
    for c in reading['contracts']:
        key = c['provider'] + ':' + str(c['id']); r = reg.get(key) or {'first_seen': reading['read']}
        last = r.get('last')
        now_ = [None if c.get(k) is None else round(c[k], 4) if isinstance(c[k], float) else c[k] for k in ('dem', 'rep', 'volume')]
        if last != now_:
            rows.append([reading['read'], c['provider'], c['id'], c['kind'], c['place']] + [('' if c.get(k) is None else round(c[k], 4) if isinstance(c[k], float) else c[k]) for k in cols[5:]])
        r.update(provider=c['provider'], id=c['id'], kind=c['kind'], place=c['place'], title=c['title'], url=c['url'], real_money=c['real_money'], rules=c.get('rules'), closes=c.get('closes'), last_seen=reading['read'], last=now_)
        reg[key] = r
    if rows:
        new = not os.path.exists(path)
        with open(path, 'a', newline='') as f:
            w = csv.writer(f, lineterminator='\n')
            if new: w.writerow(cols)
            w.writerows(rows)
    json.dump(reg, open(reg_path, 'w'), indent=0, sort_keys=True)
    json.dump({k: reading[k] for k in ('read', 'counts', 'failed', 'combined')}, open(os.path.join(root, 'latest.json'), 'w'), indent=0)
    return len(rows)


if __name__ == '__main__':
    R = collect(); print(R['read'], R['counts'], R['failed'])
    for k, v in sorted(R['combined'].items()): print(f"{k:14s}", v['p'], v['quality'], [(p['provider'], p['p'], p['quality']) for p in v['providers']])
    print([(c['provider'], c['kind'], c['title'][:60]) for c in R['contracts'] if c['kind'] not in ('winner', 'popular')])
