"""The state polls: where a poll was taken is read, never guessed; a poll is counted once; and the reasons a poll is not
used are the stated ones.

    python tests/test_polls.py
"""
import json, os, sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, HERE)
os.chdir(HERE)
import polls as P                                                          # noqa: E402


def test_place():
    ok = {('US',): 'US', ('National',): 'US', ('PA',): 'PA', ('pa',): 'PA', (' Pennsylvania ',): 'PA', ('north carolina',): 'NC', ('DC',): 'DC', ('District of Columbia',): 'DC',
          ('Maine CD-2',): 'ME2', ('ME-2',): 'ME2', ('ME 02',): 'ME2', ('Nebraska CD-2',): 'NE2', ('NE2',): 'NE2', ('Nebraska 2nd District',): 'NE2', ('Maine',): 'ME', ('NE',): 'NE',
          ('ME', '', '2'): 'ME2', ('NE', 'CD-2'): 'NE2', ('NE', 'District 3'): 'NE3', ('ME', '', '', '1'): 'ME1', ('PA', '', '7'): 'PA', ('US', 'US'): 'US'}
    for args, want in ok.items():
        assert P.place(*args)[0] == want, (args, P.place(*args))
    for args in (('',), (None,), ('Puerto Rico',), ('PR',), ('XX',), ('ME-4',), ('Nebraska CD-5',), ('Midwest',), ('PA', 'US'), ('Guam',)):
        assert P.place(*args)[0] is None, (args, P.place(*args))                    # not a state: listed, never used, never guessed to be national


def q(dem, dp, rep, rp, pop='lv', n=800, qid='q', stage='general', extra=()):
    return {'questionId': qid, 'sampleSize': n, 'population': pop, 'stage': stage, 'seatName': '', 'seatNumber': '',
            'answers': [{'party': 'DEM', 'pct': dp, 'candidateName': dem}, {'party': 'REP', 'pct': rp, 'candidateName': rep}, {'party': 'NONE', 'pct': 100 - dp - rp, 'candidateName': "Don't know"}] + list(extra)}


def rec(pid, state, end, qs, pollster='Some Poll', partisan='', cycle='2028'):
    return {'pollId': pid, 'pollster': pollster, 'state': state, 'startDate': end, 'endDate': end, 'createdAt': end, 'partisan': partisan, 'internal': '', 'cycle': cycle, 'sponsors': '', 'questions': qs, 'url': ''}


REG = [{'name': 'Josh Shapiro', 'party': 'D', 'state': 'PA'}, {'name': 'JD Vance', 'party': 'R', 'state': 'OH', 'aliases': ['J. D. Vance']}, {'name': 'Gavin Newsom', 'party': 'D', 'state': 'CA'}]


def test_rules_and_counting():
    R = [rec('1', 'GA', '6/1/27', [q('Gavin Newsom', 46, 'JD Vance', 47, 'lv', 800, 'a'), q('Gavin Newsom', 44, 'JD Vance', 45, 'rv', 1000, 'b'), q('Pete Buttigieg', 48, 'JD Vance', 46, 'lv', 800, 'c')]),
         rec('1', 'GA', '6/1/27', [q('Gavin Newsom', 46, 'JD Vance', 47, 'lv', 800, 'a')]),                         # the same poll again, as on a second page
         rec('2', 'GA', '6/1/27', [q('Gavin Newsom', 46, 'JD Vance', 47, 'lv', 800, 'z')], pollster='Some Polling'),  # the same poll under another id and spelling
         rec('3', 'PA', '6/2/27', [q('Josh Shapiro', 53, 'JD Vance', 43)]), rec('4', 'OH', '6/2/27', [q('Gavin Newsom', 40, 'J. D. Vance', 52)]),
         rec('5', 'NV', '6/3/27', [q('Gavin Newsom', 43, 'JD Vance', 47)], partisan='REP'), rec('6', 'NC', '6/3/27', [q('Generic Democrat', 43, 'Generic Republican', 44)]),
         rec('7', 'AK', '6/3/27', [q('Gavin Newsom', 40, 'Donald Trump', 43)]), rec('8', 'Guam', '6/3/27', [q('Gavin Newsom', 40, 'JD Vance', 43)]),
         rec('9', 'WI', '6/4/27', [q('Gavin Newsom', 20, 'JD Vance', 21)]), rec('10', 'MI', '6/4/27', [q('Gavin Newsom', 45, 'JD Vance', 44, stage='primary')]),
         rec('11', 'AZ', '6/4/27', [q('Gavin Newsom', 45, 'JD Vance', 44)], cycle='2024'), rec('12', 'US', '6/4/27', [q('Gavin Newsom', 45, 'JD Vance', 44)]),
         rec('13', 'NE', '6/5/27', [dict(q('Gavin Newsom', 50, 'JD Vance', 44), seatNumber='2')])]
    out = P.build(R, REG, today='x')
    f = out['found']
    assert f['duplicates_removed'] == 2 and f['unplaced_questions'] == 1 and f['national_polls'] == 1
    assert f['not_usable'] == {"Josh Shapiro's own state, while the nominees are not known": 1, "J. D. Vance's own state, while the nominees are not known": 1, 'paid for by a party or a campaign': 1,
                               'no named candidates (a generic ballot)': 1, 'Donald Trump cannot be elected again': 1, "its place could not be read: unreadable place: 'Guam'": 1,
                               'under half of those asked chose either candidate': 1}, f['not_usable']
    got = {p['place']: p for p in out['polls']}
    assert sorted(got) == ['GA', 'NE2'], sorted(got)
    ga = got['GA']                                                                  # one line: the two pairings among likely voters, the registered-voter question left aside
    assert ga['population'] == 'lv' and ga['pairings'] == ['Gavin Newsom v JD Vance', 'Pete Buttigieg v JD Vance'] and ga['dem'] == 47.0 and ga['rep'] == 46.5 and ga['pairing_spread'] is not None
    # once the nominees are known only their pairing counts, and a nominee's own state is polled like any other
    out = P.build(R, REG, nominees=('Josh Shapiro', 'JD Vance'), today='x')
    assert [p['place'] for p in out['polls']] == ['PA'] and sum(v for k, v in out['found']['not_usable'].items() if k.startswith('not the two nominees')) >= 3


def test_paging_stops():
    pages = {None: {'results': [{'pollId': 'a'}, {'pollId': 'b'}], 'cursor': 'c1'}, 'c1': {'results': [{'pollId': 'b'}, {'pollId': 'c'}], 'cursor': 'c2'}, 'c2': {'results': [{'pollId': 'd'}]}}
    def fetch(url):
        cur = url.split('cursor=')[1] if 'cursor=' in url else None
        return json.dumps(pages[cur])
    recs, info = P.fetch_pollresults(fetch)
    assert [r['pollId'] for r in recs] == ['a', 'b', 'c', 'd'] and info == {'pages': 3, 'stopped_at': 'the last page'}
    loop = lambda url: json.dumps({'results': [{'pollId': 'a'}], 'cursor': 'same'})
    recs, info = P.fetch_pollresults(loop)
    assert len(recs) == 1 and info['stopped_at'] == 'a page with nothing new'
    n = [0]
    def endless(url):
        n[0] += 1; return json.dumps({'results': [{'pollId': str(n[0])}], 'cursor': str(n[0])})
    recs, info = P.fetch_pollresults(endless, max_pages=5)
    assert len(recs) == 5 and 'limit of 5 pages' in info['stopped_at']


def test_the_feed_as_saved():
    """The copy of the feed in the repository: the counts add up, every poll that is used has a place, and a question whose
    place could not be read is listed and not used."""
    recs = json.load(open('data/cache/pollresults_general.json'))['results']
    out = P.build(recs, json.load(open('data/cache/candidates.json'))['candidates'], today='x')
    f = out['found']
    assert f['state_questions'] + f['unplaced_questions'] == len(out['state_questions']) and f['usable_state_polls'] == len(out['polls'])
    assert sum(f['not_usable'].values()) + sum(1 for q_ in out['state_questions'] if q_['usable']) == len(out['state_questions'])
    places = set(P.NAMES) | {'ME1', 'ME2', 'NE1', 'NE2', 'NE3'}
    assert all(p['place'] in places and 0 < p['dem2'] < 100 for p in out['polls'])
    assert all(not q_['usable'] for q_ in out['state_questions'] if q_['place'] is None)


if __name__ == '__main__':
    test_place(); test_rules_and_counting(); test_paging_stops(); test_the_feed_as_saved()
    print('ok (state polls: places, counting once, reasons)')
