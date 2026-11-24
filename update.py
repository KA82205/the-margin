"""The daily update. Fetches today's polls, state forecasts and approval from the Tipping Point Nowcast and the party odds
from electionbettingodds.com, reruns the 2028 forecast, adds the day to data/history.csv and rebuilds the page.

    python update.py            # fetch, then run
    python update.py --offline  # run on the copies already in data/

The Fifty-Two Keys figures in data/inputs.json are entered by hand. If a fetch fails, yesterday's value is kept and the
forecast is still rerun for today. A failed Nowcast fetch ends the script with an error so that it shows up; failed odds
only print a warning, and the page goes on showing the date the odds were last read.
"""
import datetime, json, re, shutil, sys, urllib.request, zoneinfo

NOWCAST_URL = 'https://ka82205.github.io/tipping-point/nowcast.js'
ODDS_URL = 'https://electionbettingodds.com/PresidentialParty2028.html'
ET = zoneinfo.ZoneInfo('America/New_York')

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (the-margin daily update)'})
    return urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')

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

def parse(text):
    d = json.loads(re.search(r'=\s*(\{[\s\S]*\});?\s*$', text).group(1))
    assert len(d['states']) >= 51 and 'approve' in d['approval'] and len(d['h2h']['polls']) > 0, 'the Nowcast file is not in the shape expected'
    return d

def main():
    failed = None
    today = datetime.datetime.now(ET).date().isoformat()
    if json.load(open('data/inputs.json'))['as_of'] < today:          # a new day: keep yesterday's inputs, to show what moved
        shutil.copy('data/inputs.json', 'data/prev_inputs.json'); shutil.copy('data/nowcast.js', 'data/prev_nowcast.js')
    if '--offline' not in sys.argv:
        try:
            text = get(NOWCAST_URL); parse(text)
            open('data/nowcast.js', 'w').write(text)
        except Exception as e:                       # keep yesterday's copy
            failed = e; print('Could not refresh the Nowcast:', e)
    nc = parse(open('data/nowcast.js').read())
    inp = json.load(open('data/inputs.json'))
    now = datetime.datetime.now(ET)
    inp['as_of'] = now.date().isoformat()
    if '--offline' not in sys.argv:
        try:
            d, r = odds(get(ODDS_URL))
            inp['market_dem'] = round(d / (d + r), 4)
            inp['market_note'] = f"electionbettingodds.com, party to win the presidency, {now.strftime('%B')} {now.day}, {now.year}: Democrats {d}%, Republicans {r}%"
        except Exception as e:                       # keep the last price and its date
            print('::warning::Could not refresh the betting odds:', e)
    inp['net_approval'] = round(float(nc['approval']['approve']) - float(nc['approval']['disapprove']), 1)
    json.dump(inp, open('data/inputs.json', 'w'), indent=1)
    import run_2028, make_page
    run_2028.main(); make_page.main()
    if failed: sys.exit(1)

if __name__ == '__main__':
    main()
