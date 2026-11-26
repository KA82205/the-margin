"""Sample the sources a Senate (and later House) forecast would read, and what 2028 congressional prediction markets
exist. Run by the "Source samples" workflow; it changes nothing.

    python tools/probe_senate.py out_folder
"""
import json, os, sys, urllib.parse, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)', 'Accept': '*/*'}
q = urllib.parse.quote
K = 'https://api.elections.kalshi.com/trade-api/v2/'; P = 'https://gamma-api.polymarket.com/'; M = 'https://api.manifold.markets/v0/'
SRC = {
    # ---- markets
    'kalshi_series_elections': K + 'series?category=Elections', 'kalshi_series_politics': K + 'series?category=Politics',
    'poly_search_senate_2028': P + 'public-search?limit_per_type=50&q=' + q('2028 Senate'), 'poly_search_house_2028': P + 'public-search?limit_per_type=50&q=' + q('2028 House'),
    'poly_search_senate_control': P + 'public-search?limit_per_type=50&q=' + q('Senate control 2028'), 'poly_search_senate_race': P + 'public-search?limit_per_type=50&q=' + q('Senate election winner 2028'),
    'poly_search_2026_senate': P + 'public-search?limit_per_type=20&events_status=closed&q=' + q('2026 Senate election winner'),
    'manifold_senate_2028': M + 'search-markets?limit=100&term=' + q('2028 Senate'), 'manifold_house_2028': M + 'search-markets?limit=100&term=' + q('2028 House'),
    'manifold_senate_2022': M + 'search-markets?limit=100&filter=resolved&term=' + q('2022 Senate election'), 'manifold_senate_2024': M + 'search-markets?limit=100&filter=resolved&term=' + q('2024 Senate election'),
    # ---- history for a back-test
    'mit_senate_dataverse': 'https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/PEJ5QU',
    'mit_house_dataverse': 'https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/IG0UN2',
    '538_senate_polls_hist': 'https://projects.fivethirtyeight.com/polls/data/senate_polls_historical.csv',
    '538_generic_hist': 'https://projects.fivethirtyeight.com/polls/data/generic_ballot_polls_historical.csv',
    '538_github_polls_readme': 'https://raw.githubusercontent.com/fivethirtyeight/data/master/polls/README.md',
    '538_github_pollster_ratings': 'https://api.github.com/repos/fivethirtyeight/data/contents/polls',
    '538_github_election_forecasts': 'https://api.github.com/repos/fivethirtyeight/data/contents/election-forecasts-2022',
    'fec_candidates_demo': 'https://api.open.fec.gov/v1/candidates/search/?api_key=DEMO_KEY&office=S&election_year=2024&per_page=5',
    'fec_bulk_index': 'https://www.fec.gov/data/browse-data/?tab=bulk-data',
    'pollresults_senate': 'https://api.pollresults.org/v1.0/politics/results/senate',
    'votehub_poll_types': 'https://api.votehub.com/poll-types',
    'votehub_generic': 'https://api.votehub.com/polls?poll_type=generic-ballot',
    'wiki_2028_senate': 'https://en.wikipedia.org/w/api.php?format=json&formatversion=2&action=parse&page=' + q('2028 United States Senate elections') + '&prop=sections|revid',
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
