"""The hourly update: it runs when something the forecast reads has changed and not otherwise, small moves in the odds are
not news, and a forecast once kept is never written over.

    python tests/test_update.py
"""
import copy, json, os, sys, tempfile

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, HERE)
os.chdir(HERE)
import update as U                                                          # noqa: E402
U.COLLECT = lambda cache=None, aggregate=None: {'read': '2026-11-26T00:00Z', 'counts': {}, 'failed': {}, 'combined': {}, 'contracts': []}      # no test reads a market provider


def nowcast():
    return U.parse(open('data/nowcast.js').read())


def inputs():
    i = json.load(open('data/inputs.json')); i.setdefault('keys_mean', i['keys']); return i


SP = {'polls': [], 'state_questions': [], 'nominees': None}


def test_fingerprint_changes_only_with_what_the_forecast_reads():
    nc, inp = nowcast(), inputs(); base = U.fingerprint('2026-11-25', nc, inp, SP)
    same = copy.deepcopy(nc); same['generated_at'] = '2031-01-01T00:00:00Z'; same['approval']['trend'] = []
    assert U.fingerprint('2026-11-25', same, dict(inp, market_note='read again', keys_note='read again', read={'odds': 'x'}), SP) == base       # times of reading are not news
    def moved(nc2=None, inp2=None, sp2=None, day='2026-11-25'):
        new = U.fingerprint(day, nc2 or nc, inp2 or inp, sp2 or SP)
        return [k for k in new if new[k] != base[k]]
    a = copy.deepcopy(nc); a['h2h']['polls'].append(dict(a['h2h']['polls'][0], pollster='A new pollster'))
    assert moved(a) == ['national polls']
    a = copy.deepcopy(nc); a['h2h']['polls'][0]['share'] += 0.5
    assert moved(a) == ['national polls']                                                                   # a poll that was corrected
    a = copy.deepcopy(nc); a['states'][3]['demShare'] += 0.2
    assert moved(a) == ['state forecasts']
    a = copy.deepcopy(nc); a['models']['enns']['demPopular'] += 0.2
    assert moved(a) == ['state forecasts']
    assert moved(inp2=dict(inp, net_approval=inp['net_approval'] - 0.3)) == ['approval']
    # the Fifty-Two Keys count and the betting odds are shown for comparison and are not in the forecast: neither starts a run
    assert moved(inp2=dict(inp, keys=inp['keys'] + 0.02)) == [] and moved(inp2=dict(inp, keys_mean=inp['keys_mean'] + 0.005)) == [] and moved(inp2=dict(inp, market_dem=inp['market_dem'] + 0.01)) == []
    assert moved(sp2=dict(SP, polls=[{'place': 'PA', 'dem2': 51.0}])) == ['state polls']
    assert moved(sp2=dict(SP, state_questions=[{'place': 'PA', 'usable': False}])) == ['state polls']        # a poll that is listed and not used still changes the page
    assert moved(day='2026-11-26') == ['day']


def test_small_moves_in_the_odds_are_not_news():
    held = inputs(); page = lambda d, r: f'<img src="DEM.png"> {d:.1f}% <img src="REP.png"> {r:.1f}%'
    feed = {}
    real = U.get
    def fake(url, tries=3):
        if url == U.ODDS_URL: return feed['odds']
        raise OSError('not in this test')
    U.get = fake
    try:
        import polls; real_polls = polls.main; polls.main = lambda argv: 0
        d0 = round(100 * held['market_dem'], 1)
        feed['odds'] = page(d0 + 0.4, 100 - d0 - 0.4)
        _, inp, _, failed = U.read(held, held['as_of'], False, False)
        assert inp['market_dem'] == held['market_dem'] and inp['market_note'] == held['market_note']         # under a point: the price in use stays
        assert any('Nowcast' in f for f in failed) and not any('Keys' in f or 'odds' in f for f in failed)   # the Nowcast is needed and is reported; the Keys count is for show and is not
        assert inp['keys'] == held['keys']                                                                    # and keep their last values
        feed['odds'] = page(d0 + 2.0, 100 - d0 - 2.0)
        _, inp, _, _ = U.read(held, held['as_of'], False, False)
        assert abs(inp['market_dem'] - (d0 + 2.0) / 100) < 1e-6                                               # a point or more: taken
        feed['odds'] = page(d0 + 0.4, 100 - d0 - 0.4)
        _, inp, _, _ = U.read(held, held['as_of'], True, False)
        assert abs(inp['market_dem'] - (d0 + 0.4) / 100) < 1e-6                                               # the first run of a day takes the price as it stands
        for bad in ('<img src="DEM.png"> 140.0% <img src="REP.png"> 2.0%', 'no odds here', page(30.0, 20.0)):
            feed['odds'] = bad
            _, inp, _, failed = U.read(held, held['as_of'], True, False)
            assert inp['market_dem'] == held['market_dem'], bad                                              # a page that does not look right changes nothing
    finally:
        U.get = real; polls.main = real_polls


def forecast(p=0.62, nat=51.5, ev=284, pa=51.0):
    return {'as_of': '2026-11-25', 'days_out': 713, 'p_dem': p, 'p_model': p - 0.01, 'market': 0.67, 'p_popular': 0.73, 'national': nat, 'national_sd': 2.9, 'ev_median': ev, 'ev_lo': 214, 'ev_hi': 364,
            'tipping_point': 'PA', 'inputs': {'national_polls': 48.8, 'polls_n': 28}, 'states': [{'state': 'PA', 'mean': pa, 'p_dem': 0.58}, {'state': 'WY', 'mean': 28.0, 'p_dem': 0.0}], 'candidate': {'p_dem': 0.63, 'national': 51.4, 'ev_median': 287}}


def test_archive_keeps_each_different_forecast_once():
    with tempfile.TemporaryDirectory() as root:
        assert U.archive(forecast(), ['national polls'], root, '2026-11-25T14:37Z') == '2026-11-25T1437Z.json'
        assert U.archive(forecast(), ['day'], root, '2026-11-25T15:37Z') is None                             # the same forecast is not kept twice
        assert U.archive(forecast(p=0.6204, nat=51.52, pa=51.03), ['approval'], root, '2026-11-25T16:37Z') is None      # nor one that differs by less than can be read
        assert U.archive(forecast(p=0.6212), ['approval'], root, '2026-11-25T17:37Z')                        # a tenth of a point in the chance
        assert U.archive(forecast(p=0.6212, pa=51.2), ['state polls'], root, '2026-11-25T18:37Z')             # one state moving is enough
        assert U.archive(forecast(p=0.6212, pa=51.2, ev=285), ['approval'], root, '2026-11-25T19:37Z')
        index = json.load(open(os.path.join(root, 'index.json')))
        assert [e['file'] for e in index] == ['2026-11-25T1437Z.json', '2026-11-25T1737Z.json', '2026-11-25T1837Z.json', '2026-11-25T1937Z.json']
        first = open(os.path.join(root, index[0]['file'])).read()
        try:
            U.archive(forecast(p=0.9), ['national polls'], root, '2026-11-25T14:37Z'); raise AssertionError('a kept forecast was written over')
        except FileExistsError:
            pass
        assert open(os.path.join(root, index[0]['file'])).read() == first and len(json.load(open(os.path.join(root, 'index.json')))) == 4
        kept = json.loads(first); assert kept['states']['PA'] == [51.0, 0.58] and kept['why'] == ['national polls'] and kept['under_review']['p_dem'] == 0.63


def test_stale_inputs_are_reported():
    inp = {'read': {'nowcast': '2026-11-25', 'keys': '2026-11-24', 'odds': '2026-11-25', 'state_polls': '2026-11-22'}}
    assert U.stale(inp, '2026-11-25') == ['state polls (last read 2026-11-22)']
    got = U.stale(inp, '2026-11-26'); assert len(got) == 2 and got[0].startswith('nowcast') and not any('odds' in g or 'keys' in g for g in got)      # only what the forecast needs can go stale
    assert U.stale({}, '2026-11-26') == []


def test_feeds_are_checked_before_use():
    k = {'as_of': 'November 25, 2026', 'party_in_office': 'R', 'keys': 52, 'likely': {'in_favor': 27, 'index': 0.42}, 'mean': 0.394, 'sd': 0.132}
    assert U.keys(json.dumps(k))[:3] == (0.42, 0.132, 0.394)
    for bad in (dict(k, sd=0.9), dict(k, party_in_office='D'), dict(k, mean=1.4), dict(k, likely={'in_favor': 80, 'index': 0.42})):
        try:
            U.keys(json.dumps(bad)); raise RuntimeError('a keys feed that is not in shape was accepted')
        except AssertionError:
            pass
    try:
        U.parse('window.NOWCAST = {"states": [], "approval": {}, "h2h": {"polls": []}};'); raise RuntimeError('an empty Nowcast was accepted')
    except AssertionError:
        pass


def test_a_kept_forecast_says_what_it_was_made_from():
    """The other sites' versions go into every kept forecast, the Nowcast file itself is kept once for each version of it,
    and the files for other programs describe the forecast they hold."""
    import gzip, hashlib
    text = open('data/nowcast.js').read(); nc = U.parse(text)
    v = U.nowcast_version(text, nc)
    assert v['hash'] == hashlib.sha256(text.encode()).hexdigest()[:16] and v['as_of'] == nc['as_of'] and set(v['models']) >= {'enns', 'desart'} and v['frozen'] is False
    assert U.nowcast_version(text + ' ', nc)['hash'] != v['hash']
    feed = {'as_of': 'November 25, 2026', 'date': '2026-11-25', 'party_in_office': 'R', 'keys': 52, 'engine': '2026.11b', 'format': 2, 'likely': {'in_favor': 27, 'index': 0.42}, 'mean': 0.394, 'sd': 0.132,
            'count': {'settled': 8, 'unresolved': 44, 'provisional': 0, 'held': 0, 'closed': False}, 'calls': {'D01': {'status': 'settled', 'value': False, 'final': True}},
            'index_dist': [[0.3, 0.25], [0.4, 0.5], [0.5, 0.25]]}
    kv, dist = U.keys_version(json.dumps(feed))
    assert kv['engine'] == '2026.11b' and kv['settled'] == 8 and kv['unresolved'] == 44 and dist == [[0.3, 0.25], [0.4, 0.5], [0.5, 0.25]]
    called = copy.deepcopy(feed); called['calls']['D01']['value'] = True
    assert U.keys_version(json.dumps(called))[0]['hash'] != kv['hash'], 'a call that changes is another version'
    assert U.keys_version(json.dumps(dict(feed, index_dist=[[0.3, 0.9], [1.4, 0.5]])))[1] == [], 'a spread that is not a spread is not used'
    root = tempfile.mkdtemp(); J = dict(forecast(), upstream={'tipping_point': v, 'fifty_two_keys': kv}, model={'settings': 'abc', 'sims': 40000, 'seed': 538})
    name = U.archive(J, ['a poll'], root=root, made='2027-02-01T10:00Z')
    kept = json.load(open(os.path.join(root, name)))
    assert kept['upstream']['fifty_two_keys']['hash'] == kv['hash'] and kept['model']['seed'] == 538
    path = os.path.join(root, kept['upstream']['tipping_point']['file'])
    assert gzip.decompress(open(path, 'rb').read()).decode() == text, 'the Nowcast file kept is the one the forecast was made from'
    stamp = os.path.getmtime(path)
    U.archive(dict(J, p_dem=0.7), ['the odds'], root=root, made='2027-02-01T11:00Z')
    assert os.path.getmtime(path) == stamp and len(os.listdir(os.path.join(root, 'upstream'))) == 1, 'one copy for one version, never rewritten'
    other = copy.deepcopy(J); other['upstream']['tipping_point']['hash'] = '0' * 16; other['p_dem'] = 0.4
    U.archive(other, ['x'], root=root, made='2027-02-01T12:00Z')
    assert len(os.listdir(os.path.join(root, 'upstream'))) == 1, 'a file that is not the one the forecast used is not kept under its name'
    api = tempfile.mkdtemp(); full = dict(J, as_of='2027-02-01', candidate={'p_dem': 0.9}, settings={}, states=[{'state': 'PA', 'mean': 51.0, 'lo': 45.0, 'hi': 57.0, 'p_dem': 0.6}])
    man = U.export(full, root=api); body = json.load(open(os.path.join(api, 'forecast.json')))
    assert 'candidate' not in body and body['states'][0]['state'] == 'PA' and man['upstream']['fifty_two_keys']['engine'] == '2026.11b'
    assert man['forecast']['hash'] == hashlib.sha256(open(os.path.join(api, 'forecast.json')).read().encode()).hexdigest()[:16] and not [f for f in os.listdir(api) if f.endswith('.tmp')]


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print('ok', name)
