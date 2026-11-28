"""Each district's lean worked out from The Downballot's presidential results by congressional district, for the House
back-tests, on the lines where Cook's published lean (the PVI on Wikipedia) was worked out a different way or for other
lines. Run on GitHub's servers by the samples workflow (script tools/house_leans.py), since the spreadsheets cannot be read
from everywhere the code is worked on. The Downballot asks that its spreadsheets not be reproduced whole, so only the
lean, one number a district, is written (credited on the site with a link):

    python tools/house_leans.py <folder>   ->  <folder>/house_leans/leans.csv: lines, state, district, lean, how

The lean, as Cook has worked it out since 2022: the district's Democratic share of the two-party presidential vote less
the nation's, three parts the last election and one part the one before. On the 2018 and 2020 lines (Cook's leans of
the time weighted the two halves equally) from 2016 and 2012; on the 2024 lines from 2020 alone (the only election before
2024 counted on those lines), for the districts whose published lean predates the map.
"""
import csv, io, os, re, sys, urllib.request

UA = {'User-Agent': 'election-research (github.com/KA82205/the-margin)'}
NATION = {2012: 51.964, 2016: 51.112, 2020: 52.267, 2024: 49.25}       # the Democratic share of the two-party vote
SHEETS = {2018: ('1zLNAuRqPauss00HDz4XbTH2HqsCzMe0pR8QmD1K8jk8', None), 2020: ('1XbUXnI9OyfAuhP5P3vWtMuGc5UJlrhXbzZo3AwMuHtk', None),
          2024: ('1ng1i_Dm_RMDnEvauH44pgE6JCUsapcuu8F2pCfeLWFo', '620838163')}


def get(sid, gid):
    url = f'https://docs.google.com/spreadsheets/d/{sid}/export?format=csv' + (f'&gid={gid}' if gid else '')
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return list(csv.reader(io.StringIO(r.read().decode('utf-8', 'replace'))))


def num(x):
    try: return float(str(x).replace('%', '').strip())
    except ValueError: return None


def main(out):
    d = os.path.join(out, 'house_leans'); os.makedirs(d, exist_ok=True); rows = []
    for lines, (sid, gid) in SHEETS.items():
        t = get(sid, gid)
        # the header rows: one names the years over pairs of columns, the next the candidates
        yrow = next(i for i, r in enumerate(t) if sum(bool(re.fullmatch(r'(19|20)\d\d', c.strip())) for c in r) >= 1)
        years, cur = {}, None
        for j, c in enumerate(t[yrow]):
            if re.fullmatch(r'(19|20)\d\d', c.strip()): cur = int(c.strip()); years[cur] = j
        print(lines, 'years and their first column:', years, '| header:', t[yrow + 1][:10])
        for r in t[yrow + 2:]:
            m = re.match(r'^([A-Z]{2})-(\d+|AL)$', (r[0] if r else '').strip())
            if not m: continue
            share = {}
            for y, j in years.items():
                dv, rv = num(r[j]) if j < len(r) else None, num(r[j + 1]) if j + 1 < len(r) else None
                if dv is not None and rv is not None and dv + rv > 0: share[y] = 100 * dv / (dv + rv) - NATION[y]
            if lines in (2018, 2020) and 2016 in share and 2012 in share:
                lean, how = 0.75 * share[2016] + 0.25 * share[2012], '2016 and 2012, three to one'
            elif lines == 2024 and 2020 in share:
                lean, how = share[2020], '2020'
            else:
                continue
            rows.append({'lines': lines, 'state': m.group(1), 'district': 0 if m.group(2) == 'AL' else int(m.group(2)), 'lean': round(lean, 2), 'how': how})
    with open(os.path.join(d, 'leans.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['lines', 'state', 'district', 'lean', 'how']); w.writeheader(); w.writerows(rows)
    print(len(rows), 'districts:', {k: sum(r['lines'] == k for r in rows) for k in SHEETS})


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'samples')
