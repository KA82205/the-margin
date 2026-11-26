"""Prediction markets: found by their names, read, weighed and kept, with stand-ins for the providers cut from what each
really sends. And the experimental run, which weights whole simulated elections and never a headline.

    python tests/test_markets.py
"""
import copy, datetime, json, os, sys, tempfile, urllib.parse
import numpy as np

HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, HERE)
import markets as K                        # noqa: E402

FX = json.load(open(os.path.join(HERE, 'tests', 'fixtures', 'markets.json')))
NOW = datetime.datetime(2026, 11, 26, 0, 30, tzinfo=datetime.timezone.utc)


def reader(down=(), asked=None):
    def read(url, timeout=30, tries=2):
        if asked is not None: asked.append(url)
        host = urllib.parse.urlsplit(url).netloc
        if any(d in host for d in down): raise ConnectionError('down')
        if 'manifold' in host:
            if '/search-markets' in url: return FX['manifold_search'] if 'offset=0' in url else []
            m = copy.deepcopy(FX['manifold_market']); mid = url.rsplit('/', 1)[1]; hit = next(x for x in FX['manifold_search'] if x['id'] == mid)
            m.update(id=mid, question=hit['question'], uniqueBettorCount=hit['uniqueBettorCount'], volume=hit['volume'], totalLiquidity=hit['totalLiquidity'], lastBetTime=hit['lastBetTime']); return m
        if 'polymarket' in host: return [FX['polymarket_event']] if 'texas' in url else []
        if 'kalshi' in host:
            if '/series' in url: return {'series': FX['kalshi_series']}
            return {'events': [FX['kalshi_event']] if 'series_ticker=KXPRESPARTY' in url else []}
        raise AssertionError(url)
    return read


def test_names():
    for title, want in (("Which party will win Nebraska's 2nd District (NE-2) in the 2028 presidential election?", ('winner', 'NE2')), ('Which party will win West Virginia in the 2028 presidential election?', ('winner', 'WV')),
                        ('Which party will win Washington in the 2028 presidential election?', ('winner', 'WA')), ('Washington DC presidential winner 2028', ('winner', 'DC')), ('2028 Presidential Election: Texas Winner', ('winner', 'TX')),
                        ('Which party will win the 2028 U.S. presidential election?', ('winner', 'US')), ('Which party will win the popular vote in Illinois in the 2028 presidential election?', ('winner', 'IL')),
                        ('Which party will win the national popular vote in the 2028 presidential election?', ('popular', 'US')), ('What will the national popular vote margin be in the 2028 presidential election?', ('margin', 'US')),
                        ('How many electoral votes will the 2028 Democratic presidential nominee win?', ('electoral_votes', 'US')), ('Who will be the Republican nominee for president in 2028?', ('nomination', 'R')),
                        ('Which party will win the 2028 U.S. Senate election in Ohio?', (None, None)), ('Will a Democrat win Texas for President by 2050?', (None, None)), ('2028 US Presidential Election winner?', (None, None)),
                        ('Who will win the 2028 United States Presidential Election?', (None, None)), ('If a Democrat wins the presidency in 2028, will the S&P 500 close 2029 higher', (None, None)),
                        ('Which party will win the 2032 U.S. presidential election?', (None, None))):
        assert K.kind_of(title) == want, (title, K.kind_of(title))


def test_found_read_and_weighed():
    asked = []; R = K.collect(reader(asked=asked), cache={}, now=NOW, aggregate=0.676); C = R['combined']
    assert R['failed'] == {} and R['counts']['Polymarket'] == 1 and R['counts']['Kalshi'] == 1 and R['counts']['Manifold'] >= 5
    us = C['winner:US']; names = [p['provider'] for p in us['providers']]
    assert names[0] == 'Kalshi' and 'Manifold' in names and 0.6 < us['p'] < 0.7 and us['election_betting_odds'] == 0.676, us          # real money with volume leads; the average of exchanges is kept apart
    assert us['quality'] <= 1.0 and us['quality'] < sum(p['quality'] for p in us['providers']) + 1e-9                                  # providers together never count for their sum
    tx = C['winner:TX']; pm = next(p for p in tx['providers'] if p['provider'] == 'Polymarket'); mf = next(p for p in tx['providers'] if p['provider'] == 'Manifold')
    assert abs(pm['p'] - 0.415 / (0.415 + 0.56)) < 0.01 and pm['real_money'] and not mf['real_money'] and mf['quality'] <= K.PLAY_MONEY       # play money never counts for more than half of a deep real-money market
    assert 'winner:NE2' in C and 'popular:US' in C and 'winner:IL' in C
    assert not any('KXFRPRES' in u or 'KELLYRUN' in u for u in asked), 'only presidential-winner series are asked for'
    # a market nobody has traded for months, or with prices far apart, counts for nothing; and one that is thin is listed as thin
    c = dict(real_money=True, volume=1e6, last_trade='2026-11-25T00:00:00Z', spread=0.01, p=0.5); assert K.quality(c, NOW) > 0.9
    assert K.quality(dict(c, last_trade='2026-08-01T00:00:00Z'), NOW) == 0 and K.quality(dict(c, spread=0.25), NOW) == 0 and K.quality(dict(c, volume=100), NOW) < 0.4
    assert K.quality(dict(real_money=False, traders=1000, last_trade=None, spread=None, p=0.5), NOW) == K.PLAY_MONEY and K.quality(dict(real_money=False, traders=3, last_trade=None, spread=None, p=0.5), NOW) < 0.11
    # the second reading asks Manifold for nothing it has already read and that has not traded since
    cache = {}; K.collect(reader(), cache=cache, now=NOW); asked = []; K.collect(reader(asked=asked), cache=cache, now=NOW)
    assert not any('/v0/market/' in u for u in asked)


def test_a_provider_that_fails_does_not_stop_the_rest():
    R = K.collect(reader(down=('kalshi',)), cache={}, now=NOW); assert list(R['failed']) == ['Kalshi'] and R['combined']['winner:US']['providers'][0]['provider'] == 'Manifold' and 'winner:TX' in R['combined']
    R = K.collect(reader(down=('kalshi', 'manifold', 'polymarket')), cache={}, now=NOW, aggregate=0.66)
    assert len(R['failed']) == 3 and R['combined']['winner:US']['providers'][0]['provider'] == 'Election Betting Odds' and R['contracts'] == []          # with no exchange read, the average of exchanges stands in for the national figure only


def test_the_record_and_what_counts_as_news():
    d = tempfile.mkdtemp(); R = K.collect(reader(), cache={}, now=NOW); n = K.keep(R, d)
    assert n == len(R['contracts']) and K.keep(R, d) == 0, 'a price that has not moved is not written twice'
    R2 = copy.deepcopy(R); R2['read'] = '2026-11-26T01:30Z'; c = next(x for x in R2['contracts'] if x['provider'] == 'Polymarket'); c['dem'] = c['dem'] + 0.04
    assert K.keep(R2, d) == 1 and len(open(os.path.join(d, 'prices-2026-11.csv')).read().strip().split('\n')) == n + 2
    reg = json.load(open(os.path.join(d, 'registry.json'))); k = next(x for x in reg if x.startswith('Polymarket')); assert reg[k]['first_seen'] == R['read'] and reg[k]['last_seen'] == R2['read'] and reg[k]['real_money']
    assert not K.moved(R, R) and not K.moved(R, None) is False
    a = copy.deepcopy(R); a['combined']['winner:US']['p'] += 0.004; assert not K.moved(R, a)
    a['combined']['winner:US']['p'] += 0.01; assert K.moved(R, a)
    b = copy.deepcopy(R); b['combined']['winner:TX']['p'] += 0.02; assert not K.moved(R, b); b['combined']['winner:TX']['p'] += 0.02; assert K.moved(R, b)
    b = copy.deepcopy(R); b['combined']['winner:GA'] = {'p': 0.5, 'quality': 0.2, 'providers': []}; assert K.moved(R, b), 'a market that has just opened is news'


def toy(n=40000):
    rng = np.random.default_rng(1); nat = rng.standard_t(5, n) * 2.5; lean = np.array([-6, -5, 0, 1, 3, 8]); sh = 52 + lean[:, None] + nat + rng.standard_normal((6, n)) * 2.5; evs = np.array([40, 30, 19, 15, 16, 54]); dem = sh > 50
    return {'states': ['TX', 'FL', 'PA', 'MI', 'GA', 'CA'], 'dem': dem, 'ev': (evs[:, None] * dem).sum(0), 'total': float(evs.sum()), 'vote': 52 + nat}


def test_the_experimental_run_weights_whole_elections():
    s = toy(); base = K.informed(s, {}); assert base['events'] == 0 and base['effective'] == 1.0 and abs(base['p_dem'] - float((s['ev'] > s['total'] / 2).mean())) < 1e-12
    r = K.informed(s, {'winner:US': {'p': 0.60, 'quality': 0.9}, 'winner:TX': {'p': 0.41, 'quality': 0.4}, 'winner:FL': {'p': 0.2, 'quality': 0.05}, 'winner:ZZ': {'p': 0.9, 'quality': 1.0}, 'winner:GA': {'p': None, 'quality': 0}})
    assert r['events'] == 3 and abs(r['p_dem'] + r['p_rep'] + r['p_tie'] - 1) < 1e-9
    assert 0.60 < r['p_dem'] < base['p_dem'] and base['states']['TX'] < r['states']['TX'] < 0.41, 'each chance moves toward the market and stops short of it'
    assert abs(r['states']['FL'] - base['states']['FL']) < 0.01, 'a thin market moves next to nothing'
    assert r['ev_lo'] <= r['ev_median'] <= r['ev_hi'] and r['national_lo'] < r['national'] < r['national_hi'] and r['effective'] > 0.9
    for m in r['moved']: assert min(m['simulation'], m['markets']) - 1e-6 <= m['reached'] <= max(m['simulation'], m['markets']) + 1e-6, m
    # the states' chances and the national one come from the same weighted elections: a state the Democrats carry more often
    # with the weights is carried more often in the elections they win
    half = K.informed(s, {'winner:US': {'p': 0.60, 'quality': 0.9}}, strength=0.25); assert abs(half['p_dem'] - base['p_dem']) < abs(K.informed(s, {'winner:US': {'p': 0.60, 'quality': 0.9}})['p_dem'] - base['p_dem'])
    # markets that would leave too few elections are pulled back until a quarter of them effectively remain
    x = K.informed(s, {'winner:US': {'p': 0.02, 'quality': 1.0}, 'winner:CA': {'p': 0.01, 'quality': 1.0}}, strength=1.0); assert x['effective'] >= 0.25 and x['strength'] < 1.0
    # an event the simulation all but never has is left alone: there is nothing to weight
    assert K.informed(s, {'winner:CA': {'p': 0.5, 'quality': 1.0}})['events'] in (0, 1)


if __name__ == '__main__':
    test_names(); test_found_read_and_weighed(); test_a_provider_that_fails_does_not_stop_the_rest(); test_the_record_and_what_counts_as_news(); test_the_experimental_run_weights_whole_elections()
    print('ok (prediction markets: names, providers, quality, the record, and the weighted run)')
