"""Sample the sources a Senate (and later House) forecast would read, and what 2028 congressional prediction markets
exist. Run by the "Source samples" workflow; it changes nothing.

    python tools/probe_senate.py out_folder
"""
import json, os, sys, urllib.parse, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)', 'Accept': '*/*'}
q = urllib.parse.quote
K = 'https://api.elections.kalshi.com/trade-api/v2/'; P = 'https://gamma-api.polymarket.com/'; M = 'https://api.manifold.markets/v0/'
SRC = {
    '538_senate_polls_hist': 'https://projects.fivethirtyeight.com/polls-page/data/senate_polls_historical.csv',
    '538_generic_hist': 'https://projects.fivethirtyeight.com/polls-page/data/generic_ballot_polls_historical.csv',
    '538_house_polls_hist': 'https://projects.fivethirtyeight.com/polls-page/data/house_polls_historical.csv',
    'kalshi_events_senate': K + 'events?limit=100&with_nested_markets=true&series_ticker=KXSENATE',
    'kalshi_events_house': K + 'events?limit=100&with_nested_markets=true&series_ticker=KXHOUSE',
    'kalshi_events_dsenate': K + 'events?limit=100&series_ticker=KXDSENATESEATS',
    'kalshi_events_pasen': K + 'events?limit=100&with_nested_markets=true&series_ticker=KXPASENRUN',
    'kalshi_events_senate_states': K + 'events?limit=200&status=open&series_ticker=SENATEPA',
    'poly_senate_2028': P + 'events?slug=which-party-will-win-the-senate-in-2028',
    'poly_house_2028': P + 'events?slug=which-party-will-win-the-house-in-2028',
    'pollresults_senate_p1': 'https://api.pollresults.org/v1.0/politics/results/senate?limit=100',
    'manifold_senate_2022_races': M + 'search-markets?limit=100&filter=resolved&term=' + q('win 2022 Senate race'),
    'manifold_senate_2024_races': M + 'search-markets?limit=100&filter=resolved&term=' + q('win the 2024 US Senate election in'),
}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
        return r.status, r.headers.get('content-type', ''), r.read()
if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True); log = {}
    for k, u in SRC.items():
        try:
            st, ct, b = get(u); open(os.path.join(out, k + ('.csv' if 'csv' in u else '.json' if 'json' in ct else '.txt')), 'wb').write(b[:4_000_000])
            log[k] = {'status': st, 'type': ct[:40], 'bytes': len(b)}
        except Exception as e:                              # noqa: BLE001
            log[k] = f'{type(e).__name__}: {str(e)[:120]}'
    json.dump(log, open(os.path.join(out, '_log.json'), 'w'), indent=1); print(json.dumps(log, indent=1))
