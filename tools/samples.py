"""Fetch a sample from each outside source into a folder, so that readers can be written and tested against what the
sources really send. It changes nothing in the repository. Run by the "Source samples" workflow, which keeps the folder as
a download.

    python tools/samples.py out_folder [name ...]
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)'
W = 'https://en.wikipedia.org/w/api.php?format=json&formatversion=2&'
wiki = lambda title, section=None: W + urllib.parse.urlencode(dict({'action': 'parse', 'page': title, 'prop': 'wikitext|revid|sections', 'redirects': 1}, **({'section': section} if section is not None else {})))
M = 'https://api.manifold.markets/v0/'
K = 'https://api.elections.kalshi.com/trade-api/v2/'
P = 'https://gamma-api.polymarket.com/'
q = urllib.parse.quote

SOURCES = {
    # ---- markets
    'manifold_search_2028_pres': M + 'search-markets?limit=100&term=' + q('2028 presidential election'),
    'manifold_search_2028_state': M + 'search-markets?limit=100&term=' + q('2028 presidential election Texas'),
    'manifold_search_2028_win': M + 'search-markets?limit=100&term=' + q('which party will win 2028'),
    'manifold_search_2028_popular': M + 'search-markets?limit=50&term=' + q('2028 popular vote'),
    'manifold_search_2028_electoral': M + 'search-markets?limit=50&term=' + q('2028 electoral college'),
    'manifold_search_2028_nomination': M + 'search-markets?limit=50&term=' + q('2028 nomination'),
    'manifold_election_page': 'https://manifold.markets/election',
    'manifold_search_2024_state': M + 'search-markets?limit=100&filter=resolved&term=' + q('2024 presidential election state win'),
    'manifold_search_2024_which_party': M + 'search-markets?limit=100&filter=resolved&term=' + q('Which party will win the 2024 US Presidential Election in'),
    'kalshi_series_elections': K + 'series?category=Elections',
    'kalshi_series_politics': K + 'series?category=Politics',
    'kalshi_events_open': K + 'events?limit=200&status=open',
    'kalshi_markets_sample': K + 'markets?limit=5&status=open',
    'kalshi_events_pres': K + 'events?limit=200&status=open&with_nested_markets=true&series_ticker=KXPRESPARTY',
    'polymarket_search_2028': P + 'public-search?limit_per_type=50&q=' + q('2028 presidential election'),
    'polymarket_search_2028_state': P + 'public-search?limit_per_type=50&q=' + q('2028 presidential election winner Texas'),
    'polymarket_events_tag': P + 'events?closed=false&limit=100&tag_slug=us-presidential-election',
    'polymarket_events_2028': P + 'events?closed=false&limit=100&tag_slug=2028-presidential-election',
    'polymarket_2024_texas': P + 'events?slug=texas-presidential-election-winner',
    'polymarket_2024_search': P + 'public-search?limit_per_type=100&events_status=closed&q=' + q('Presidential Election Winner 2024'),
    'polymarket_2024_national': P + 'events?slug=presidential-election-winner-2024',
    'ebo_party': 'https://electionbettingodds.com/PresidentialParty2028.html',
    'iem_home': 'https://iemweb.biz.uiowa.edu/markets/',
    'iem_closed': 'https://iemweb.biz.uiowa.edu/closed/',
    'iem_pres24': 'https://iemweb.biz.uiowa.edu/markets/pres24.html',
    'iem_history_24': 'https://iemweb.biz.uiowa.edu/pricehistory/pricehistory_SelectContract.cfm?market_ID=390',
    # ---- primaries and nominees: every Wikipedia page in one request, as the readers will ask
    'wiki_batch_a': W + 'action=query&prop=revisions&rvprop=content|ids|timestamp&rvslots=main&redirects=1&titles=' + q('|'.join(
        [f'{y} New Hampshire {p} presidential primary' for y in (2016, 2020, 2024, 2028) for p in ('Republican', 'Democratic')] + [f'{y} United States presidential election' for y in (2016, 2020, 2024, 2028)])),
    'wiki_batch_b': W + 'action=query&prop=revisions&rvprop=content|ids|timestamp&rvslots=main&redirects=1&titles=' + q('|'.join(
        [f'{y} {p} Party presidential primaries' for y in (2016, 2020, 2024, 2028) for p in ('Republican', 'Democratic')] + [f'Results of the {y} {p} Party presidential primaries' for y in (2016, 2020, 2024, 2028) for p in ('Republican', 'Democratic')])),
    **{f'green_{y}_nh_{p}': f'https://www.thegreenpapers.com/P{y % 100}/NH-{p}' for y in (2016, 2020, 2024) for p in 'RD'},
    **{f'green_{y}_{p}': f'https://www.thegreenpapers.com/P{y % 100}/{p}' for y in (2016, 2020, 2024) for p in 'RD'},
    'green_robots': 'https://www.thegreenpapers.com/robots.txt',
    'nh_robots': 'https://www.sos.nh.gov/robots.txt',
    'nh_results_index': 'https://www.sos.nh.gov/elections/election-results',
    'nh_2024_r': 'https://www.sos.nh.gov/2024-republican-presidential-primary-election-results',
    'iem_history': 'https://iemweb.biz.uiowa.edu/markets/historical-data/',
    'iem_recent': 'https://iemweb.biz.uiowa.edu/markets/recent-markets/',
    'manifold_market_detail': M + 'slug/which-party-will-win-the-2028-us-pr-nhSncsUR0n',
    'manifold_search_states': M + 'search-markets?limit=100&creatorId=vuI5upWB8yU00rP7yxj95J2zd952&term=' + q('2028 presidential election'),
    'polymarket_2028_texas': P + 'events?slug=2028-presidential-election-texas-winner',
    'polymarket_search_2028_winner': P + 'public-search?limit_per_type=100&events_status=active&q=' + q('2028 Presidential Election Winner'),
    'kalshi_events_2028_states': K + 'events?limit=200&status=open&series_ticker=PRESPARTYTX&with_nested_markets=true',
    'desart_site': 'https://research.uvu.edu/DeSart/forecasting/',
    # ---- second sources for the economic series
    'fed_g17': 'https://www.federalreserve.gov/releases/g17/ipdisk/ip_sa.txt',
    'census_starts': 'https://api.census.gov/data/timeseries/eits/resconst?get=cell_value,data_type_code,time_slot_id,category_code,seasonally_adj&time=from+2025-01&for=us:*',
    'umich': 'https://www.sca.isr.umich.edu/files/tbmics.csv',
    'eia_wti_month': 'https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RWTC&f=M',
    'eia_wti_day': 'https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RWTC&f=D',
    'stooq_spx': 'https://stooq.com/q/d/l/?s=%5Espx&i=d&d1=20260801&d2=20261231',
    'dol_claims': ('https://oui.doleta.gov/unemploy/claims.asp', 'level=us&final_yr=2026&strtdate=2025&enddate=2026&filetype=xml&submit=Submit'),
    'bea_q': ('FILTER', 'https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt', ('A191RL,', 'A067RL,', 'B230RC,', 'A939RX,', 'A229RX,')),
    'bea_m': ('FILTER', 'https://apps.bea.gov/national/Release/TXT/NipaDataM.txt', ('DPCERA,',)),
    'bea_series': ('FILTER', 'https://apps.bea.gov/national/Release/TXT/SeriesRegister.txt', ('A191RL,', 'A067RL,', 'B230RC,', 'A939RX,', 'A229RX,', 'DPCERA,')),
    'civiqs_robots': 'https://civiqs.com/robots.txt',
}


def fetch(spec, keep=3_000_000):
    if isinstance(spec, tuple) and spec[0] == 'FILTER':
        req = urllib.request.Request(spec[1], headers={'User-Agent': UA}); out, n, head = [], 0, []
        with urllib.request.urlopen(req, timeout=120) as r:
            for raw in r:
                line = raw.decode('utf-8', 'replace'); n += 1
                if n <= 3: head.append(line)
                if line.startswith(spec[2]) and (len(out) < 4000): out.append(line)
        return 200, {}, ''.join(head) + f'... {n} lines ...\n' + ''.join(out[-600:])
    url, body = (spec, None) if isinstance(spec, str) else spec
    req = urllib.request.Request(url, data=body.encode() if body else None, headers={'User-Agent': UA, 'Accept': '*/*', **({'Content-Type': 'application/x-www-form-urlencoded'} if body else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, dict(r.headers), r.read(keep).decode('utf-8', 'replace')


def main(out, names):
    os.makedirs(out, exist_ok=True); log = {}
    for name, spec in SOURCES.items():
        if names and not any(name.startswith(n) for n in names): continue
        try:
            status, headers, text = fetch(spec)
            open(os.path.join(out, name + '.txt'), 'w').write(text); log[name] = {'status': status, 'bytes': len(text), 'type': headers.get('Content-Type')}
        except Exception as err:                        # noqa: BLE001
            log[name] = {'error': f'{type(err).__name__}: {str(err)[:200]}', 'code': getattr(err, 'code', None)}
        print(name, log[name], flush=True); time.sleep(0.4)
    json.dump(log, open(os.path.join(out, '_log.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
