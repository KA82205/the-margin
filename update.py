"""The update. It is run every hour and does nothing unless something the forecast reads has changed.

Each run reads four things:
    the Tipping Point Nowcast     the national polls, the state forecasts and presidential approval (nowcast.js)
    Fifty-Two Keys                the count of keys and the spread of that site's run ahead (keys.json)
    electionbettingodds.com       the party odds
    PollResults.org               polls of single states (polls.py)

What it read is then compared with what the last forecast was made from (data/fingerprint.json). The forecast is run again
when any of these is true, and otherwise the run ends with nothing saved:
    - a poll has been added, changed or dropped, national or of a state
    - the Nowcast's forecasts or its approval average have moved
    - the Fifty-Two Keys count, or the spread around it, has moved
    - the betting odds stand a point or more from the price in use
    - the day has changed: the first run of each day is always made, so the day-by-day record has every day

Every forecast that differs from the last one kept is written to docs/archive/ and never changed afterwards
(docs/archive/index.json lists them). data/history.csv keeps one row a day, the day's latest.

A source that cannot be read keeps its last value and the run goes on. That is a warning on an ordinary run. On the day's
first run, and on a run started by hand, an input that has gone stale ends the run with an error after the forecast has
been made, so it shows up once a day and not once an hour.

    python update.py             read, compare, and run if anything is new
    python update.py --force     run even if nothing is new
    python update.py --offline   run on the copies already in data/
    python update.py --wait 240  for a run started by another site's update: look again for up to 240 seconds, since the
                                 other site's page can take a minute or two to show what it has just saved
"""
import datetime, hashlib, json, os, re, shutil, sys, time, urllib.request, zoneinfo

NOWCAST_URL = 'https://ka82205.github.io/tipping-point/nowcast.js'
ODDS_URL = 'https://electionbettingodds.com/PresidentialParty2028.html'
KEYS_URL = 'https://ka82205.github.io/fifty-two-keys/keys.json'
ET = zoneinfo.ZoneInfo('America/New_York')
ODDS_STEP = 0.01                                    # the odds count as new once they stand this far from the price in use
STALE = {'nowcast': 1, 'keys': 2, 'odds': 2, 'state_polls': 2}        # days since the last good read at which the day's first run reports it
ARCHIVE = 'docs/archive'


def get(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (the-margin update)', 'Cache-Control': 'no-cache'})
            return urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
        except Exception:                            # noqa: BLE001  a second and third try before giving up
            if attempt == tries - 1: raise
            time.sleep(5 * (attempt + 1))


def odds(html):
    """Democratic and Republican chances from the odds page: the first plain percentage after each party's logo.
    Changes over the last hours carry a sign and are skipped."""
    def first(after, before=None):
        a = html.index(after); b = html.index(before, a) if before else len(html)
        m = re.search(r'(?<![-+\d.])(\d{1,3}\.\d)%', html[a:b])
        return float(m.group(1))
    d, r = first('DEM.png', 'REP.png'), first('REP.png')
    assert 0 < d < 100 and 0 < r < 100 and 85 <= d + r <= 100.5, f'odds do not look right: {d}, {r}'
    return d, r


def keys(text):
    """The count from the Fifty-Two Keys feed: the share of keys in the party's favor if every open key lands the way it
    leans, the middle of that site's run ahead, and its spread."""
    k = json.loads(text); index, sd, mean = float(k['likely']['index']), float(k['sd']), float(k.get('mean', k['likely']['index']))
    assert k['party_in_office'] == 'R' and 0 < index < 1 and 0 < mean < 1 and 0.02 <= sd <= 0.3 and 0 <= int(k['likely']['in_favor']) <= int(k['keys']), 'the keys feed is not in the shape expected'
    return round(index, 3), round(sd, 3), round(mean, 3), f"Fifty-Two Keys, {k['as_of']}: {k['likely']['in_favor']} of {k['keys']} keys in the Republicans' favor if each open key lands the way it leans"


def parse(text):
    d = json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', text).group(1))
    assert len(d['states']) >= 51 and 'approve' in d['approval'] and len(d['h2h']['polls']) > 0, 'the Nowcast file is not in the shape expected'
    return d


# ------------------------------------------------------------------------------------------- has anything changed?
def fingerprint(day, nc, inp, sp):
    """One short hash for each thing the forecast reads. Times of reading and of the other sites' own runs are left out:
    only what would move the forecast, or what the page lists, is in."""
    h = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]
    m = nc.get('models') or {}; f = nc.get('desart_final') or {}
    return {'day': day,
            'national polls': h(sorted([p.get('pollster'), p.get('date'), p.get('d'), p.get('r'), round(float(p['share']), 2)] for p in nc['h2h']['polls'])),
            'state forecasts': h([[(m.get(k) or {}).get('demPopular') and round(float(m[k]['demPopular']), 2) for k in ('enns', 'desart')], round(float(nc['summary']['demPopular']), 2),
                                  sorted([s['abbr'], round(float(s['demShare']), 2)] for s in nc['states']), nc.get('tickets'), bool(f.get('frozen'))]),
            'approval': h([inp['net_approval']]),
            'Fifty-Two Keys': h([inp['keys'], inp['keys_sd'], inp.get('keys_mean')]),
            'betting odds': h([inp['market_dem']]),
            'state polls': h([sp.get('polls'), sp.get('state_questions'), sp.get('nominees')])}


def read(inp, today, new_day, offline):
    """Everything from the four sources. Returns (the Nowcast, the inputs as they would now stand, the state polls, the
    sources that could not be read)."""
    import polls, run_2028
    failed = []; inp = dict(inp); seen = dict(inp.get('read') or {}); now = datetime.datetime.now(ET)
    if not offline:
        try:
            text = get(NOWCAST_URL); parse(text)
            open('data/nowcast.js', 'w').write(text); seen['nowcast'] = today
        except Exception as e:                       # noqa: BLE001  keep the copy in hand
            failed.append(f'the Nowcast ({type(e).__name__}: {e})')
    nc = parse(open('data/nowcast.js').read())
    inp['as_of'] = today
    if not offline:
        try:
            d, r = odds(get(ODDS_URL)); price = round(d / (d + r), 4); seen['odds'] = today
            if new_day or abs(price - inp['market_dem']) >= ODDS_STEP:        # small hourly wobbles are not news
                inp['market_dem'] = price
                inp['market_note'] = f"electionbettingodds.com, party to win the presidency, {now.strftime('%B')} {now.day}, {now.year}: Democrats {d}%, Republicans {r}%"
        except Exception as e:                       # noqa: BLE001  keep the last price and its date
            failed.append(f'the betting odds ({type(e).__name__}: {e})')
        try:
            inp['keys'], inp['keys_sd'], inp['keys_mean'], inp['keys_note'] = keys(get(KEYS_URL)); seen['keys'] = today
        except Exception as e:                       # noqa: BLE001  keep the last count
            failed.append(f'the Fifty-Two Keys count ({type(e).__name__}: {e})')
        try:
            if polls.main([]) != 0: raise RuntimeError('no polls in hand')
            if any(v.get('answered') for k, v in (run_2028.state_poll_file().get('sources') or {}).items() if k in ('PollResults.org', "Tipping Point's saved copy")): seen['state_polls'] = today
            else: failed.append('the state polls (no source answered)')
        except Exception as e:                       # noqa: BLE001  keep the list in hand
            failed.append(f'the state polls ({type(e).__name__}: {e})')
    inp['net_approval'] = round(float(nc['approval']['approve']) - float(nc['approval']['disapprove']), 1)
    inp['read'] = seen
    return nc, inp, run_2028.state_poll_file(), failed


# ------------------------------------------------------------------------------------------------------ the archive
def snapshot(J, made, why):
    c = J.get('candidate') or {}
    return {'made': made, 'as_of': J['as_of'], 'days_out': J['days_out'], 'why': why,
            'p_dem': round(J['p_dem'], 4), 'p_model': round(J['p_model'], 4), 'market': round(J['market'], 4), 'p_popular': round(J['p_popular'], 4),
            'national': round(J['national'], 3), 'national_sd': round(J['national_sd'], 3), 'ev_median': int(J['ev_median']), 'ev_lo': int(J['ev_lo']), 'ev_hi': int(J['ev_hi']),
            'tipping_point': J['tipping_point'],
            'inputs': {k: (round(v, 3) if isinstance(v, float) else v) for k, v in J['inputs'].items() if k in ('national_polls', 'polls_n', 'poll_share', 'fundamentals', 'net_approval', 'keys', 'nowcast_national', 'nowcast_as_of')},
            'states': {s['state']: [s['mean'], s['p_dem']] for s in J['states']},
            'under_review': {k: (round(c[k], 4) if isinstance(c[k], float) else c[k]) for k in ('p_dem', 'national', 'ev_median') if k in c}}


def differs(a, b):
    """Is forecast a meaningfully different from b? A tenth of a point in the chance, a twentieth of a point in the national
    share, a different middle count of electoral votes, or the same in any one state."""
    if abs(a['p_dem'] - b['p_dem']) >= 0.001 or abs(a['national'] - b['national']) >= 0.05 or a['ev_median'] != b['ev_median']: return True
    if set(a['states']) != set(b['states']): return True
    return any(abs(a['states'][s][0] - b['states'][s][0]) >= 0.05 or abs(a['states'][s][1] - b['states'][s][1]) >= 0.005 for s in a['states'])


def archive(J, why, root=ARCHIVE, made=None):
    """Keep the forecast if it differs from the last one kept. Files are written once and never opened for writing again.
    Returns the file's name, or None if the forecast is the same as the last one kept."""
    os.makedirs(root, exist_ok=True); index = os.path.join(root, 'index.json')
    made = made or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    snap = snapshot(J, made, why)
    entries = json.load(open(index)) if os.path.exists(index) else []
    if entries:
        last = json.load(open(os.path.join(root, entries[-1]['file'])))
        if not differs(snap, last): return None
    name = made.replace(':', '') + '.json'
    with open(os.path.join(root, name), 'x') as f:                    # 'x': fails rather than replace a forecast already kept
        json.dump(snap, f, separators=(',', ':'))
    entries.append({'made': made, 'as_of': snap['as_of'], 'p_dem': snap['p_dem'], 'national': snap['national'], 'ev_median': snap['ev_median'], 'why': why, 'file': name})
    json.dump(entries, open(index, 'w'), indent=0)
    return name


# --------------------------------------------------------------------------------------------------------- the run
def stale(inp, today):
    """Inputs that have gone without a good read for too long."""
    day = datetime.date.fromisoformat; out = []
    for k, limit in STALE.items():
        last = (inp.get('read') or {}).get(k)
        if last and (day(today) - day(last)).days >= limit: out.append(f'{k.replace("_", " ")} (last read {last})')
    return out


def say(key, value):
    """A result for the workflow that started the run."""
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f: f.write(f'{key}={value}\n')


def main(argv):
    offline, force = '--offline' in argv, '--force' in argv
    wait = int(argv[argv.index('--wait') + 1]) if '--wait' in argv else 0
    today = datetime.datetime.now(ET).date().isoformat()
    held = json.load(open('data/inputs.json')); new_day = held['as_of'] < today
    if new_day:                                      # keep yesterday's inputs, to show what moved
        shutil.copy('data/inputs.json', 'data/prev_inputs.json'); shutil.copy('data/nowcast.js', 'data/prev_nowcast.js')
    old = json.load(open('data/fingerprint.json')) if os.path.exists('data/fingerprint.json') else {}
    started = time.time()
    while True:
        nc, inp, sp, failed = read(held, today, new_day, offline)
        fp = fingerprint(today, nc, inp, sp); what = [k for k in fp if fp[k] != old.get(k)]
        if what or force or time.time() - started >= wait: break
        time.sleep(45)
    for f in failed: print(f'::warning::Could not read {f}; the last copy is used.')
    if not what and not force:
        print(f'Nothing new since the forecast of {held["as_of"]}: no run.'); say('changed', 'false')
        return 0
    print('New:', ', '.join(what) if what else 'nothing (forced)')
    json.dump(inp, open('data/inputs.json', 'w'), indent=1)
    import run_2028, make_page
    run_2028.main()
    if not offline:                                  # a run on the copies in hand is not a new published forecast
        kept = archive(json.load(open('data/forecast_2028.json')), [w for w in what if w != 'day'] or ['the calendar'])
        print('Kept as', kept) if kept else print('The forecast is the same as the last one kept: nothing added to the archive.')
    make_page.main()
    json.dump(fp, open('data/fingerprint.json', 'w'), indent=1)
    say('changed', 'true'); say('what', ', '.join(w for w in what if w != 'day') or 'the calendar')
    old_news = stale(inp, today) if (new_day or force or not os.environ.get('GITHUB_ACTIONS')) else []
    for s in old_news: print(f'::error::Stale input: {s}.')
    if old_news: say('alert', 'true')
    return 1 if old_news else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
