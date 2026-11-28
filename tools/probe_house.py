"""What the House forecast could be built from: checks each candidate source and writes a short report of what it holds
(sizes, columns, a few rows, terms of use), not the data itself. Started through the samples workflow
(samples.yml, script tools/probe_house.py):

    python tools/probe_house.py <folder>

The report goes to <folder>/house/report.txt. The Downballot asks that its spreadsheets not be reproduced whole, so only
their shape and first rows are noted here; the CC0 and public-domain sources are saved in full for a closer look.
"""
import csv, io, json, os, sys, urllib.request, zipfile

UA = {'User-Agent': 'election-research (github.com/KA82205/the-margin)'}
OUT = []


def get(url, limit=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(limit) if limit else r.read()


def note(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.append(s)


def sheet(name, sid, gid=None):
    url = f'https://docs.google.com/spreadsheets/d/{sid}/export?format=csv' + (f'&gid={gid}' if gid else '')
    try:
        rows = list(csv.reader(io.StringIO(get(url).decode('utf-8', 'replace'))))
        note(f'[Downballot] {name}: {len(rows)} rows'); [note('   ', r[:14]) for r in rows[:6]]
    except Exception as e:                                         # noqa: BLE001 - noted, then the next source
        note(f'[Downballot] {name}: could not be read ({type(e).__name__} {e})')


def dataverse(name, doi, folder, save_max=40_000_000):
    try:
        meta = json.loads(get(f'https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId={doi}'))['data']['latestVersion']
        note(f'[Dataverse] {name} {doi}: license {meta.get("license")}, version {meta.get("versionNumber")}.{meta.get("versionMinorNumber")}, released {meta.get("releaseTime")}')
        for f in meta['files']:
            df = f['dataFile']; note('    file', df.get('originalFileName') or df['filename'], df.get('filesize'))
            if (df.get('filesize') or 0) < save_max and (df['filename'].endswith(('.tab', '.csv')) or (df.get('originalFileName') or '').endswith('.csv')):
                body = get(f'https://dataverse.harvard.edu/api/access/datafile/{df["id"]}?format=original')
                p = os.path.join(folder, df.get('originalFileName') or df['filename']); open(p, 'wb').write(body)
                head = body[:3000].decode('utf-8', 'replace').splitlines()[:4]; [note('     ', h[:300]) for h in head]
    except Exception as e:                                         # noqa: BLE001
        note(f'[Dataverse] {name}: could not be read ({type(e).__name__} {e})')


def main(out):
    folder = os.path.join(out, 'house'); os.makedirs(folder, exist_ok=True)
    # 1 House results by district: the MIT Election Data and Science Lab (CC0)
    dataverse('MIT House 1976-', 'doi:10.7910/DVN/IG0UN2', folder)
    # 2 presidential results by district on each map: The Downballot (free; cite and link; not to be reproduced whole)
    for name, sid in [('2008-2020 on the 2020 districts', '1XbUXnI9OyfAuhP5P3vWtMuGc5UJlrhXbzZo3AwMuHtk'), ('2008-2016 on the 2018 districts', '1zLNAuRqPauss00HDz4XbTH2HqsCzMe0pR8QmD1K8jk8'),
                      ('2008-2016 on the 2016 districts', '1VfkHtzBTP5gf4jAu8tcVQgsBJ1IDvXEHjuMqYlOgYbA'), ('2008-2012 on the 2012-2014 districts', '1xn6nCNM97oFDZ4M-HQgoUT3X4paOiSDsRMSuxbaOBdg'),
                      ('2008 on the 2006-2010 districts', '1l7W130tPRF6dQ4JoqlQJSJexnEg4rZct-7kwDXqgoLE'), ('2020 on the 2022 districts', '1CKngqOp8fzU22JOlypoxNsxL6KSAH920Whc-rd7ebuM'),
                      ('2024 calculations', '17eg8P7li3D2aDP7uKDXjj0bQ5jOPoooF'), ('open seats 2006-2026', '12RhR9oZZpyKKceyLO3C5am84abKzu2XqLWjP2LnQDgI')]:
        sheet(name, sid)
    # 3 FEC candidate totals by cycle (public domain): all candidates, one file a cycle
    for y in (2008, 2016, 2024, 2026):
        try:
            z = zipfile.ZipFile(io.BytesIO(get(f'https://www.fec.gov/files/bulk-downloads/{y}/weball{str(y)[2:]}.zip')))
            n = z.namelist()[0]; lines = z.read(n).decode('latin-1').splitlines()
            house = [l for l in lines if l.split('|')[0][:1] == 'H']
            note(f'[FEC] weball{str(y)[2:]}: {len(lines)} candidates, {len(house)} House; first House row:', house[0][:200] if house else '')
            open(os.path.join(folder, f'weball{str(y)[2:]}.txt'), 'w').write('\n'.join(lines))
        except Exception as e:                                     # noqa: BLE001
            note(f'[FEC] {y}: could not be read ({type(e).__name__} {e})')
    # 4 Wikipedia: the 2028 page, and what a district's page and a state's 2026 page hold
    api = 'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&rvslots=main&format=json&formatversion=2&redirects=1&titles='
    for t in ['2028 United States House of Representatives elections', "Texas's 28th congressional district", '2026 United States House of Representatives elections in Texas',
              '2028 United States House of Representatives elections in Texas', 'Cook Partisan Voting Index']:
        try:
            p = json.loads(get(api + urllib.parse.quote(t)))['query']['pages'][0]
            if p.get('missing'): note(f'[Wikipedia] {t}: no page'); continue
            text = p['revisions'][0]['slots']['main']['content']
            note(f'[Wikipedia] {t}: {len(text)} characters')
            open(os.path.join(folder, t.replace('/', '_').replace("'", '') + '.wiki'), 'w').write(text)
        except Exception as e:                                     # noqa: BLE001
            note(f'[Wikipedia] {t}: could not be read ({type(e).__name__} {e})')
    open(os.path.join(folder, 'report.txt'), 'w').write('\n'.join(OUT) + '\n')


if __name__ == '__main__':
    import urllib.parse
    main(sys.argv[1] if len(sys.argv) > 1 else 'samples')
