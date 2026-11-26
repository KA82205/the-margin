"""Fetch New Hampshire's official primary result files, the Census Bureau's housing starts workbook and the Federal Reserve's
industrial production tables, and write what is in them as text, so that readers can be written against the real layouts.
Run by the "Source samples" workflow; it changes nothing.

    python tools/probe_official.py out_folder
"""
import html, io, json, os, re, subprocess, sys, urllib.parse, urllib.request

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'xlrd', 'openpyxl'], check=False)
UA = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)', 'Accept': '*/*'}
LOG = {}


def get(url, binary=False, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        b = r.read(); return b if binary else b.decode('utf-8', 'replace')


def sheets(data, name):
    """Every sheet of a workbook as rows of text, .xls or .xlsx."""
    out = {}
    try:
        if data[:2] == b'PK':
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
            for ws in wb.worksheets: out[ws.title] = [['' if c is None else str(c) for c in row] for row in ws.iter_rows(values_only=True)]
        else:
            import xlrd
            wb = xlrd.open_workbook(file_contents=data)
            for ws in wb.sheets(): out[ws.name] = [[str(ws.cell_value(r, c)) for c in range(ws.ncols)] for r in range(ws.nrows)]
    except Exception as err:                            # noqa: BLE001
        out['ERROR'] = [[f'{type(err).__name__}: {err}', name, str(data[:60])]]
    return out


def dump(out, name, book, head=45, tail=12):
    lines = []
    for sheet, rows in book.items():
        rows = [r for r in rows if any(c.strip() for c in r)]
        lines.append(f'##### sheet {sheet!r}: {len(rows)} rows')
        for r in rows[:head] + ([['...']] + rows[-tail:] if len(rows) > head + tail else rows[head:]): lines.append(' | '.join(c.strip() for c in r)[:600])
    open(os.path.join(out, name + '.txt'), 'w').write('\n'.join(lines))


def links(page, base):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S | re.I):
        out.append((urllib.parse.urljoin(base, html.unescape(m.group(1))), re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2)))).strip()))
    return out


def new_hampshire(out):
    pages = {'2024_R': 'https://www.sos.nh.gov/2024-republican-presidential-primary-election-results', '2024_D': 'https://www.sos.nh.gov/2024-democratic-presidential-primary-election-results',
             '2028_R': 'https://www.sos.nh.gov/2028-republican-presidential-primary-election-results', '2020_R': 'https://www.sos.nh.gov/elections/2020-election-results/2020-presidential-primary-election-results/2020-republican',
             '2020_R_b': 'https://www.sos.nh.gov/2020-republican-presidential-primary-election-results', '2016_R_b': 'https://www.sos.nh.gov/2016-republican-presidential-primary-election-results',
             'elections': 'https://www.sos.nh.gov/elections', 'results': 'https://www.sos.nh.gov/elections/election-results-information', 'results_b': 'https://www.sos.nh.gov/election-results'}
    found = {}
    for key, url in pages.items():
        try:
            page = get(url); ls = links(page, url); LOG['nh ' + key] = {'bytes': len(page), 'links': len(ls)}
            keep = [(u, t) for u, t in ls if re.search(r'\.(xlsx?|csv|pdf)(\?|$)', u, re.I) or re.search(r'presidential|primary|election-results|results', u + ' ' + t, re.I)]
            found[key] = keep
            open(os.path.join(out, f'nh_{key}_links.txt'), 'w').write(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', page))[:1500] + '\n\n' + '\n'.join(f'{t} -> {u}' for u, t in keep[:400]))
        except Exception as err:                        # noqa: BLE001
            LOG['nh ' + key] = f'{type(err).__name__}: {str(err)[:100]}'
    for key in ('2024_R', '2024_D'):
        for u, t in found.get(key, []):
            if re.search(r'\.xlsx?(\?|$)', u, re.I) and re.search(r'summary|write', (t + ' ' + u), re.I):
                try:
                    data = get(u, binary=True); name = f"nh_{key}_" + re.sub(r'[^a-z0-9]+', '_', (t or u.rsplit('/', 1)[-1]).lower())[:50]
                    dump(out, name, sheets(data, u)); LOG[name] = {'url': u, 'bytes': len(data)}
                except Exception as err:                # noqa: BLE001
                    LOG['nh file ' + u[-60:]] = f'{type(err).__name__}: {str(err)[:100]}'


def census(out):
    for name, url in (('census_starts', 'https://www.census.gov/construction/nrc/xls/starts_cust.xlsx'), ('census_newresconst', 'https://www.census.gov/construction/nrc/xls/newresconst.xlsx')):
        try:
            data = get(url, binary=True); dump(out, name, sheets(data, url), head=30, tail=30); LOG[name] = {'bytes': len(data)}
        except Exception as err:                        # noqa: BLE001
            LOG[name] = f'{type(err).__name__}: {str(err)[:100]}'


def fed(out):
    for name, url in (('fed_ip_sa', 'https://www.federalreserve.gov/releases/g17/ipdisk/ip_sa.txt'), ('fed_g17_current', 'https://www.federalreserve.gov/releases/g17/current/default.htm'), ('fed_g17_table1', 'https://www.federalreserve.gov/releases/g17/current/table1_sup.htm'),
                      ('fred_indpro', 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDPRO&cosd=2025-01-01'), ('fred_houst', 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=HOUST&cosd=2025-01-01'),
                      ('fed_ddp', 'https://www.federalreserve.gov/datadownload/Output.aspx?rel=G17&series=6ac6dcfcd49eaa1d2a8a7e2c36b2d3a6&lastobs=24&from=&to=&filetype=csv&label=include&layout=seriescolumn'),
                      ('fed_ddp_choose', 'https://www.federalreserve.gov/datadownload/Choose.aspx?rel=G17')):
        try:
            t = get(url)
            if name == 'fed_ip_sa':
                ls = t.split('\n'); t = '\n'.join(ls[:6]) + '\n...\n' + '\n'.join(l for l in ls if re.match(r'"?(B50001|B00004|B5610C)"?\s+20(24|25|26)', l))
            elif name.startswith('fed_g17') or name == 'fed_ddp_choose':
                t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<script.*?</script>|<style.*?</style>', ' ', t, flags=re.S)))
                t = re.sub(r'<[^>]+>', ' | ', t); t = re.sub(r'(\s*\|\s*)+', ' | ', t)[:9000]
            open(os.path.join(out, name + '.txt'), 'w').write(t[:60000]); LOG[name] = {'bytes': len(t)}
        except Exception as err:                        # noqa: BLE001
            LOG[name] = f'{type(err).__name__}: {str(err)[:100]}'


if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    new_hampshire(out); census(out); fed(out)
    json.dump(LOG, open(os.path.join(out, '_log.json'), 'w'), indent=1); print(json.dumps(LOG, indent=1)[:6000])
