"""What prediction markets said about each state in 2024, at the distances the back-test uses. Run by the "Source samples"
workflow; writes market_history_2024.csv and a log into the folder given. It reads public market data and changes nothing.

Polymarket (real money): each state's "Presidential Election Winner" event, the daily price history of its Democratic and
Republican contracts. Manifold (play money): the state markets of its politics account, the last trade before each date.

    python tools/market_history.py out_folder
"""
import csv, datetime, json, os, sys, time, urllib.parse, urllib.request

UA = 'the-margin/1.0 (election forecast; github.com/KA82205/the-margin)'
STATES = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'Washington DC', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
          'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
          'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
          'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
          'WI': 'Wisconsin', 'WY': 'Wyoming'}
ELECTION = datetime.date(2024, 11, 5)
DAYS = [250, 200, 150, 120, 90, 60, 30, 14, 7, 1]
LOG = {}


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'}), timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as err:                        # noqa: BLE001
            if k == tries - 1: raise
            time.sleep(2 + 3 * k)


def polymarket(rows):
    for ab, name in list(STATES.items()) + [('US', None)]:
        slug = 'presidential-election-winner-2024' if ab == 'US' else name.lower().replace(' ', '-') + '-presidential-election-winner'
        try:
            ev = get('https://gamma-api.polymarket.com/events?slug=' + slug); ev = ev[0] if isinstance(ev, list) and ev else ev
            if not ev or not ev.get('markets'): LOG[f'polymarket {ab}'] = 'no event'; continue
            want = {}
            for m in ev['markets']:
                q = (m.get('question') or '').lower(); who = (m.get('groupItemTitle') or '').lower()
                side = ('d' if ('democrat' in q or 'harris' in who or 'harris' in q) else 'r' if ('republican' in q or 'trump' in who or 'trump' in q) else 'biden' if 'biden' in (who + q) else None)
                if side and side not in want and m.get('clobTokenIds'): want[side] = (json.loads(m['clobTokenIds'])[0], float(m.get('volumeNum') or 0))
            series = {}
            for side, (token, vol) in want.items():
                h = get(f'https://clob.polymarket.com/prices-history?market={token}&interval=max&fidelity=1440').get('history') or []
                series[side] = sorted((int(p['t']), float(p['p'])) for p in h); time.sleep(0.15)
            LOG[f'polymarket {ab}'] = {s: len(v) for s, v in series.items()}
            for d in DAYS:
                cut = int(datetime.datetime.combine(ELECTION - datetime.timedelta(days=d), datetime.time(23, 59), datetime.timezone.utc).timestamp())
                last = lambda s: next((p for t, p in reversed(series.get(s) or []) if t <= cut), None)
                pd_, pr, pb = last('d'), last('r'), last('biden')
                if ab == 'US' and ELECTION - datetime.timedelta(days=d) < datetime.date(2024, 7, 21): pb = None
                if ab == 'US' and pd_ is not None and pb is not None: pd_ = max(pd_, pb)
                elif ab == 'US' and pd_ is None: pd_ = pb
                if pd_ is not None or pr is not None:
                    rows.append({'provider': 'Polymarket', 'place': ab, 'days': d, 'dem': pd_, 'rep': pr, 'volume': round(sum(v for _, v in want.values())), 'traders': ''})
        except Exception as err:                        # noqa: BLE001
            LOG[f'polymarket {ab}'] = f'{type(err).__name__}: {str(err)[:120]}'


def manifold(rows):
    found = {}
    for term in ('Which party will win the US Presidency in', 'Which party will win the 2024 presidential election in', '2024 presidential election winner state'):
        for offset in (0, 100):
            try:
                got = get('https://api.manifold.markets/v0/search-markets?limit=100&filter=resolved&offset=%d&term=%s' % (offset, urllib.parse.quote(term)))
            except Exception as err:                    # noqa: BLE001
                LOG[f'manifold search {term[:20]} {offset}'] = str(err)[:100]; break
            for m in got:
                q = m.get('question') or ''
                if '2024' not in q and 'US Presidency' not in q: continue
                for ab, name in STATES.items():
                    nm = name if ab != 'DC' else 'Washington, D'
                    if (' in ' + nm) in q and not any((' in ' + other) in q for a2, other in STATES.items() if a2 != ab and len(other) > len(nm) and other.startswith(nm)):
                        if ab not in found or (m.get('uniqueBettorCount') or 0) > (found[ab].get('uniqueBettorCount') or 0): found[ab] = m
            if len(got) < 100: break
            time.sleep(0.3)
    LOG['manifold found'] = {ab: [m['question'][:70], m.get('uniqueBettorCount'), m.get('outcomeType'), m.get('creatorUsername')] for ab, m in found.items()}
    for ab, m in found.items():
        try:
            full = get('https://api.manifold.markets/v0/market/' + m['id']); dem = rep = None
            for a in full.get('answers') or []:
                t = (a.get('text') or '').lower()
                if 'democrat' in t: dem = a['id']
                if 'republican' in t: rep = a['id']
            for d in DAYS:
                cut = int(datetime.datetime.combine(ELECTION - datetime.timedelta(days=d), datetime.time(23, 59), datetime.timezone.utc).timestamp() * 1000)
                if cut < (full.get('createdTime') or 0): continue
                bets = get(f"https://api.manifold.markets/v0/bets?contractId={m['id']}&beforeTime={cut}&limit=200&order=desc")
                if full.get('outcomeType') == 'BINARY':
                    p = bets[0].get('probAfter') if bets else None; rows.append({'provider': 'Manifold', 'place': ab, 'days': d, 'dem': p, 'rep': None if p is None else 1 - p, 'volume': round(full.get('volume') or 0), 'traders': full.get('uniqueBettorCount')}) if p is not None else None
                else:
                    pick = lambda aid: next((b.get('probAfter') for b in bets if b.get('answerId') == aid), None)
                    pd_, pr = pick(dem), pick(rep)
                    if pd_ is not None or pr is not None: rows.append({'provider': 'Manifold', 'place': ab, 'days': d, 'dem': pd_, 'rep': pr, 'volume': round(full.get('volume') or 0), 'traders': full.get('uniqueBettorCount')})
                time.sleep(0.12)
        except Exception as err:                        # noqa: BLE001
            LOG[f'manifold {ab}'] = f'{type(err).__name__}: {str(err)[:120]}'


def main(out):
    os.makedirs(out, exist_ok=True); rows = []
    polymarket(rows); manifold(rows)
    with open(os.path.join(out, 'market_history_2024.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, ['provider', 'place', 'days', 'dem', 'rep', 'volume', 'traders'], lineterminator='\n'); w.writeheader(); w.writerows(rows)
    json.dump(LOG, open(os.path.join(out, 'market_history_log.json'), 'w'), indent=1)
    print(len(rows), 'rows;', sum(1 for r in rows if r['provider'] == 'Polymarket'), 'from Polymarket,', sum(1 for r in rows if r['provider'] == 'Manifold'), 'from Manifold')


if __name__ == '__main__':
    main(sys.argv[1])
