"""The raw sources of the House forecast's training data, fetched on GitHub's servers through the samples workflow
(samples.yml, script tools/fetch_house.py), since they cannot be reached from everywhere the code is worked on:

    python tools/fetch_house.py <folder> [states]

Into <folder>/house_raw/:
    house.tab                  the MIT Election Data and Science Lab's House results by district, 1976-2024 (CC0,
                               doi:10.7910/DVN/IG0UN2)
    wiki/<year>.wiki           Wikipedia's page of each House election, 2012-2028 (CC BY-SA): each district's lean as
                               Cook published it, the member, the party and what became of the seat
    wiki/<year> <state>.wiki   with "states": each state's page of each election as well
    weball<yy>.txt             the FEC's summary of every candidate's money, each cycle 2012-2026 (public domain)
"""
import io, json, os, sys, time, urllib.error, urllib.parse, urllib.request, zipfile

UA = {'User-Agent': 'election-research (github.com/KA82205/the-margin)'}
YEARS = list(range(2012, 2030, 2))
STATES = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
          'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
          'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
          'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming']


def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404) or i == 3: raise
            print('retry', url[:80], e.code); time.sleep(5 * (i + 1))
        except Exception as e:                                     # noqa: BLE001 - retried, then raised
            if i == 3: raise
            print('retry', url[:80], type(e).__name__); time.sleep(5 * (i + 1))


def wiki(titles):
    """{title: text} for up to 20 titles at a time, following redirects; a page that does not exist is left out."""
    out = {}
    for i in range(0, len(titles), 20):
        chunk = titles[i:i + 20]
        q = urllib.parse.urlencode({'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main', 'format': 'json', 'formatversion': 2, 'redirects': 1, 'titles': '|'.join(chunk)})
        j = json.loads(get('https://en.wikipedia.org/w/api.php?' + q))['query']
        back = {r['to']: r['from'] for r in j.get('redirects', [])}
        for p in j['pages']:
            if p.get('missing') or 'revisions' not in p: continue
            out[back.get(p['title'], p['title'])] = p['revisions'][0]['slots']['main']['content']
        time.sleep(1)
    return out


def main(out, states=False):
    d = os.path.join(out, 'house_raw'); w = os.path.join(d, 'wiki'); os.makedirs(w, exist_ok=True)
    meta = json.loads(get('https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/IG0UN2'))['data']['latestVersion']
    for f in meta['files']:
        df = f['dataFile']
        for url in (f'https://dataverse.harvard.edu/api/access/datafile/{df["id"]}?gbrecs=true', f'https://dataverse.harvard.edu/api/access/datafile/{df["id"]}?format=original&gbrecs=true',
                    f'https://dataverse.harvard.edu/api/access/datafile/:persistentId?persistentId={df.get("persistentId", "")}'):
            try:
                body = get(url)
            except urllib.error.HTTPError as e:
                print('MIT', url[-60:], e.code, e.read()[:300]); continue
            open(os.path.join(d, 'house.tab'), 'wb').write(body); print('MIT', df['filename'], len(body), 'bytes, license', (meta.get('license') or {}).get('name')); break
    # FiveThirtyEight's results by candidate (CC BY 4.0), a second source of the same results
    for name in ('election_results_house.csv',):
        try:
            body = get('https://raw.githubusercontent.com/fivethirtyeight/election-results/main/' + name); open(os.path.join(d, name), 'wb').write(body); print('538', name, len(body))
        except Exception as e:                                     # noqa: BLE001
            print('538', name, 'could not be read:', type(e).__name__, e)
    pages = wiki([f'{y} United States House of Representatives elections' for y in YEARS])
    for t, text in pages.items():
        open(os.path.join(w, t[:4] + '.wiki'), 'w').write(text); print('Wikipedia', t, len(text))
    if states:
        titles = [f'{y} United States House of Representatives elections in {s}' for y in YEARS for s in STATES]
        got = wiki(titles)
        for t, text in got.items():
            open(os.path.join(w, t[:4] + ' ' + t.split(' in ', 1)[1] + '.wiki'), 'w').write(text)
        print('Wikipedia state pages:', len(got), 'of', len(titles))
    for y in YEARS[:-1]:
        try:
            z = zipfile.ZipFile(io.BytesIO(get(f'https://www.fec.gov/files/bulk-downloads/{y}/weball{str(y)[2:]}.zip')))
            open(os.path.join(d, f'weball{str(y)[2:]}.txt'), 'wb').write(z.read(z.namelist()[0])); print('FEC', y)
        except Exception as e:                                     # noqa: BLE001
            print('FEC', y, 'could not be read:', type(e).__name__, e)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0] if a else 'samples', 'states' in a[1:])
