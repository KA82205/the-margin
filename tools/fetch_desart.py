"""Jay DeSart's replication data for his long-range state-level forecasts of the 2020 election (doi:10.7910/DVN/6GWHQB)
and the 2024 election (doi:10.7910/DVN/HZGLY9), from the Harvard Dataverse, for the Research tab's study of long-range
forecasts. Started through the samples workflow (samples.yml, script tools/fetch_desart.py):

    python tools/fetch_desart.py <folder>

Each dataset's files go to <folder>/desart/<year>/, beside dataset.json, the dataset's description and terms of use.
"""
import json, os, sys, urllib.request

API = 'https://dataverse.harvard.edu/api'
SETS = {'2020': 'doi:10.7910/DVN/6GWHQB', '2024': 'doi:10.7910/DVN/HZGLY9'}


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'election-research'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main(out):
    for year, doi in SETS.items():
        d = os.path.join(out, 'desart', year); os.makedirs(d, exist_ok=True)
        meta = json.loads(get(f'{API}/datasets/:persistentId/?persistentId={doi}'))
        with open(os.path.join(d, 'dataset.json'), 'w') as f: json.dump(meta, f, indent=1)
        for item in meta['data']['latestVersion']['files']:
            df = item['dataFile']; fid = df['id']
            for name, url in ((df.get('originalFileName') or df['filename'], f'{API}/access/datafile/{fid}?format=original'), (df['filename'], f'{API}/access/datafile/{fid}')):
                try:
                    body = get(url)
                except Exception as e:                             # noqa: BLE001 - reported, and the next form tried
                    print(year, name, 'could not be read:', type(e).__name__, e); continue
                with open(os.path.join(d, name), 'wb') as f: f.write(body)
                print(year, name, len(body), 'bytes')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'samples')
