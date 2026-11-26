"""The Margin from November 2027 to Election Day 2028, on simulated dates.

Tipping Point fixes its academic forecast for good on August 6, 2028. The Margin must go on reading polls after that,
keep the fixed forecasts as its structural inputs, take an author's own forecast whenever it arrives, and go on running
its own simulated elections. The fixtures in tests/fixtures/freeze/ are what Tipping Point's own code writes on each of
these days (its pipeline/tests/test_freeze.py, run with --export): the Nowcast file and the live feed, cut down to the
parts read here. Nothing in this file says what will happen in 2028; it shows what the code does on those days.
"""
import copy, json, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import run_2028 as R, update as U, model as M, fundamentals as F, polls as P       # noqa: E402

FX = os.path.join(HERE, 'fixtures', 'freeze')
stage = lambda name: json.load(open(os.path.join(FX, name + '.json')))
RES = pd.read_csv('data/results.csv'); ERRS = pd.read_csv('data/average_errors.csv'); T = F.table()
NO_STATE_POLLS = {'polls': [], 'state_questions': [], 'nominees': None}


def inputs(nc):
    """The day's inputs as update.py would write them from what it read."""
    return dict(R.inputs(), net_approval=round(float(nc['approval']['approve']) - float(nc['approval']['disapprove']), 1))


def run(nc, day, sp=NO_STATE_POLLS):
    out, info, meta = R.official(inputs(nc), nc, nc, sp, RES, ERRS, T, day)
    return out, info, meta


def changed(a, b, day, sp_a=NO_STATE_POLLS, sp_b=NO_STATE_POLLS):
    """Which parts of the forecast's fingerprint differ between two readings: what update.py would call new."""
    fa, fb = U.fingerprint(day, a, inputs(a), sp_a), U.fingerprint(day, b, inputs(b), sp_b)
    return sorted(k for k in fa if fa[k] != fb[k])


def test_the_live_feed_is_laid_over_the_nowcast_and_only_when_it_is_current():
    s = stage('5-a-national-poll-in-september'); nowcast, live = s['nowcast'], s['live']
    nc = R.with_live(nowcast, live)
    # the frozen file's polls stop in July; the feed's run to the day it was written
    assert R.poll_table(nowcast).end.max() <= pd.Timestamp('2028-07-30') and R.poll_table(nc).end.max() == pd.Timestamp('2028-09-12')
    assert nc['models'] == nowcast['models'] and nc['states'] == nowcast['states'] and nc['summary'] == nowcast['summary'], 'the academic forecast is read from the Nowcast, untouched'
    assert R.nominees(nowcast) is None and R.nominees(nc) is not None, 'the nominees come from the feed'
    assert nc['live']['academic']['fixed'] is True and nc['live']['as_of'] == '2028-09-15'
    old = dict(live, as_of='2028-08-01')                                               # a feed that could not be read since before the Nowcast in hand
    assert R.with_live(nowcast, old) is nowcast and R.with_live(nowcast, None) is nowcast
    # today the two files hold the same polls and the same approval: reading the feed changes nothing
    first = stage('1-before-desart')
    assert changed(first['nowcast'], R.with_live(first['nowcast'], first['live']), '2027-11-10') == []


def test_june_is_read_from_every_day_of_the_month():
    s = stage('3-after-enns'); nc = R.with_live(s['nowcast'], s['live'])
    days = nc['approval']['june']; mean = round(sum(x['a'] - x['dis'] for x in days) / len(days), 1)
    assert len(days) == 30 and R.june_approval(nc, '2028-07-07') is None and R.june_approval(nc, '2028-07-08') == mean
    # the Nowcast's own trend is one figure a week: four or five in June, too few to be the month's reading by the rule
    weekly = [x for x in s['nowcast']['approval']['trend'] if x['d'].startswith('2028-06')]
    assert 0 < len(weekly) < 10 and R.june_approval(s['nowcast'], '2028-08-01') is None
    # a feed with no day in June (nobody polled, the source was down) is not a reading, whatever the date
    assert R.june_approval(dict(nc, approval=dict(nc['approval'], june=[], trend=[])), '2028-09-01') is None


def test_an_authors_forecast_replaces_the_site_run_in_the_margin():
    one, two, three = (stage(n) for n in ('1-before-desart', '2-after-desart', '3-after-enns'))
    nc1, nc2, nc3 = (R.with_live(s['nowcast'], s['live']) for s in (one, two, three))
    _, _, m1 = run(nc1, '2027-11-10'); _, _, m2 = run(nc2, '2027-11-20'); o3, i3, m3 = run(nc3, '2028-08-01')
    # 1. before DeSart's forecast: the site's own run of his model, in the national number at its weight
    assert m1['long_range'] == one['nowcast']['models']['desart']['demPopular'] and m1['long_range_weight'] > 0 and 'published' not in one['nowcast']
    # 2. after it: his own figure, and the national starting point moves with it
    assert m2['long_range'] == two['nowcast']['models']['desart']['demPopular'] and two['nowcast']['model_sources']['desart'] == "authors' forecast"
    assert abs(m2['long_range'] - m1['long_range']) > 0.3 and (m2['prior'] - m1['prior']) * (m2['long_range'] - m1['long_range']) > 0
    assert 'state forecasts' in changed(nc1, dict(nc1, models=nc2['models'], states=nc2['states'], summary=nc2['summary']), '2027-11-20'), 'which is news to the hourly check'
    # 3. after Enns and colleagues': both structural models are the authors' own; June's approval is a fact and the allowance is closed
    assert m3['approval_and_economy'] == three['nowcast']['models']['enns']['demPopular'] and three['nowcast']['model_sources'] == {'enns': "authors' forecast", 'desart': "authors' forecast"}
    assert m3['june_approval'] is not None and m3['net_approval'] == m3['june_approval'] and m3['approval_open'] == 0.0
    # the national starting point is the existing mix: the two authors' figures and the approval equation, each one part
    assert abs(m3['prior'] - F.mix([m3['approval_and_economy'], m3['approval_equation'], m3['long_range']], [1, 1, m3['long_range_weight']])) < 1e-9
    assert M.SET['sims'] == 40000 and abs(o3['p_dem'] + o3['p_rep'] + o3['p_tie'] - 1) < 1e-9 and o3['p_dem'] != three['nowcast']['summary']['pDemWin'], "its own simulated elections, not Tipping Point's chance"


def test_after_the_freeze_the_polls_still_move_the_forecast_and_the_models_do_not():
    four, five, six, eight = (stage(n) for n in ('4-after-the-freeze', '5-a-national-poll-in-september', '6-a-state-poll-in-october', '8-election-day'))
    nc4, nc5, nc6, nc8 = (R.with_live(s['nowcast'], s['live']) for s in (four, five, six, eight))
    fixed = lambda nc: (nc['models'], nc['states'], nc['summary'], nc.get('published'))
    assert fixed(nc4) == fixed(nc5) == fixed(nc6) == fixed(nc8), 'the academic forecast is the same file to Election Day'

    # 5. a national poll in September: it is news, it moves the polling average and the forecast, and nothing structural
    without = copy.deepcopy(nc5); without['h2h']['polls'] = [p for p in without['h2h']['polls'] if p['pollster'] != 'A September Pollster']
    assert changed(without, nc5, '2028-09-15') == ['national polls']
    o_a, i_a, m_a = run(without, '2028-09-15'); o_b, i_b, m_b = run(nc5, '2028-09-15')
    assert i_b['national_polls'] != i_a['national_polls'] and o_b['national'] != o_a['national'] and o_b['p_dem'] != o_a['p_dem']
    assert (m_b['prior'], m_b['approval_and_economy'], m_b['long_range'], m_b['approval_equation']) == (m_a['prior'], m_a['approval_and_economy'], m_a['long_range'], m_a['approval_equation'])
    assert m_b['approval_and_economy'] == four['nowcast']['models']['enns']['demPopular'] and m_b['long_range'] == four['nowcast']['models']['desart']['demPopular']
    assert R.nominees(nc5) == (nc5['tickets']['dem']['president']['name'], nc5['tickets']['rep']['president']['name']) and R.pairing_spread(nc5) is None
    assert m_b['june_approval'] is not None and m_b['approval_open'] == 0.0, 'June is still a fact after the freeze'

    # 6. a state poll in October: read by The Margin itself from the poll feed, judged against the nominees in the live feed
    dem, rep = R.nominees(nc6)
    rec = lambda d, r, dp, rp, pollster: {'pollster': pollster, 'state': 'PA', 'startDate': '10/6/28', 'endDate': '10/8/28', 'createdAt': '10/9/28 12:00', 'url': 'https://example.org/poll',
                                          'questions': [{'sampleSize': 800, 'population': 'lv', 'stage': 'general', 'answers': [{'party': 'DEM', 'pct': dp, 'candidateName': d}, {'party': 'REP', 'pct': rp, 'candidateName': r}]}]}
    built = P.build([rec(dem, rep, 44, 50, 'An October Pollster'), rec('Somebody Else', rep, 55, 40, 'Another Pollster')], [], nc6['h2h'].get('people') or [], (dem, rep), {}, today='2028-10-10')
    assert [(p['pollster'], p['place']) for p in built['polls']] == [('An October Pollster', 'PA')], 'only the poll of the two nominees counts'
    sp = dict(NO_STATE_POLLS, polls=built['polls'], nominees=[dem, rep])
    assert changed(nc6, nc6, '2028-10-10', NO_STATE_POLLS, sp) == ['state polls']
    o_c, i_c, m_c = run(nc6, '2028-10-10'); o_d, i_d, m_d = run(nc6, '2028-10-10', sp)
    pa = lambda o: float(o['states'].set_index('state').loc['PA', 'mean']) if hasattr(o['states'], 'set_index') else next(s['mean'] for s in o['states'] if s['state'] == 'PA')
    assert pa(o_d) < pa(o_c) - 0.2, 'a poll with the Republican ahead in Pennsylvania pulls Pennsylvania that way'
    assert i_d['national_polls'] == i_c['national_polls'] and m_d['prior'] == m_c['prior']

    # 8. Election Day: it runs, and the polls count for more than they did in September
    o_e, i_e, m_e = run(nc8, '2028-11-07')
    assert i_e['poll_share'] > i_b['poll_share'] > 0 and 0 < o_e['p_dem'] < 1 and m_e['prior'] == m_b['prior']
    assert (m_e['approval_and_economy'], m_e['long_range']) == (m_b['approval_and_economy'], m_b['long_range'])


def test_an_authors_forecast_that_arrives_after_the_freeze_replaces_the_stand_in():
    a, b = stage('7a-frozen-with-a-stand-in'), stage('7b-enns-arrives-late')
    nca, ncb = R.with_live(a['nowcast'], a['live']), R.with_live(b['nowcast'], b['live'])
    assert nca['live']['academic']['sources'] == {'enns': 'site run', 'desart': "authors' forecast"} and ncb['live']['academic']['sources']['enns'] == "authors' forecast"
    assert ncb['live']['academic'] == dict(nca['live']['academic'], updated='2028-08-20', sources=ncb['live']['academic']['sources']) and ncb['live']['academic']['fixed'] is True
    news = changed(dict(nca, live=None), dict(ncb, live=None, h2h=nca['h2h'], approval=nca['approval']), '2028-08-20')
    assert news == ['state forecasts'], 'the redone forecast is news to the hourly check, and the only news'
    _, _, ma = run(nca, '2028-08-20'); _, _, mb = run(ncb, '2028-08-20')
    assert ma['approval_and_economy'] == a['nowcast']['models']['enns']['demPopular'] != mb['approval_and_economy'] == b['nowcast']['models']['enns']['demPopular']
    assert ma['long_range'] == mb['long_range'] and ma['prior'] != mb['prior']
    v = U.nowcast_version(json.dumps(b['nowcast']), ncb)
    assert v['fixed'] is True and v['fixed_since'] == '2028-08-06' and v['redone'] == '2028-08-20' and v['sources']['enns'] == "authors' forecast"


def test_a_forecast_fixed_on_purpose_is_not_a_stale_source_and_a_feed_that_stops_is():
    # the Nowcast was fetched today (it is fetched every hour, changed or not), the feed carries today's date: nothing is stale
    read = {'nowcast': '2028-10-10', 'state_polls': '2028-10-10', 'live': '2028-10-10'}
    assert U.stale({'read': read}, '2028-10-10') == [] and U.stale({'read': dict(read, live='2028-10-09')}, '2028-10-10') == []
    # the feed's own date two days old: Tipping Point has stopped writing it, and that is reported
    assert U.stale({'read': dict(read, live='2028-10-08')}, '2028-10-10') == ['the live feed of national polls (last written 2028-10-08)']
    # before the feed existed nothing is reported about it
    assert U.stale({'read': {'nowcast': '2026-11-26', 'state_polls': '2026-11-26'}}, '2026-11-26') == []
    # an empty table of state polls (every earlier poll is of another pairing on the day the nominees are known) still has dates for dates
    empty = R.state_poll_table(NO_STATE_POLLS)
    nc = R.with_live(stage('5-a-national-poll-in-september')['nowcast'], stage('5-a-national-poll-in-september')['live'])
    both = pd.concat([R.poll_table(nc), empty], ignore_index=True)
    assert len(empty) == 0 and str(both.end.dtype).startswith('datetime64')
