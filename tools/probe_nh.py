"""Can New Hampshire's Secretary of State be read from here, and what do its result files hold? Changes nothing.

    python tools/probe_nh.py out_folder
"""
import html, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'xlrd', 'openpyxl'], check=False)
NAME = 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)'
WAYS = {'name only': {'User-Agent': NAME}, 'name and accept': {'User-Agent': NAME, 'Accept': '*/*'}, 'name, html': {'User-Agent': NAME, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en'},
        'keys name': {'User-Agent': 'Mozilla/5.0 (compatible; fifty-two-keys/1.0; +https://github.com/KA82205/fifty-two-keys)'}}
LOG = {}


def get(url, head, binary=False, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=head), timeout=timeout) as r:
        b = r.read(); return b if binary else b.decode('utf-8', 'replace')


def sheets(data):
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
        out['ERROR'] = [[f'{type(err).__name__}: {err}', str(data[:80])]]
    return out


def main(out):
    pages = ['https://www.sos.nh.gov/robots.txt', 'https://www.sos.nh.gov/2024-republican-presidential-primary-election-results', 'https://www.sos.nh.gov/2024-democratic-presidential-primary-election-results',
             'https://www.sos.nh.gov/elections/election-results', 'https://www.sos.nh.gov/elections', 'https://www.sos.nh.gov/2020-republican-presidential-primary-election-results',
             'https://www.sos.nh.gov/2020-democratic-presidential-primary-election-results', 'https://www.sos.nh.gov/2016-republican-presidential-primary-election-results', 'https://www.sos.nh.gov/sitemap.xml']
    good = None; texts = {}
    for u in pages[:2]:
        for way, head in WAYS.items():
            for attempt in (1, 2):
                try:
                    t = get(u, head); LOG[f'{u[22:]} | {way} | {attempt}'] = len(t); good = good or head; texts[u] = t; break
                except Exception as err:                # noqa: BLE001
                    LOG[f'{u[22:]} | {way} | {attempt}'] = f'{type(err).__name__}: {str(err)[:60]}'; time.sleep(3)
    head = good or WAYS['name only']
    for u in pages[2:]:
        try:
            texts[u] = get(u, head); LOG[u[22:]] = len(texts[u])
        except Exception as err:                        # noqa: BLE001
            LOG[u[22:]] = f'{type(err).__name__}: {str(err)[:60]}'
        time.sleep(1)
    files = []
    for u, t in texts.items():
        name = re.sub(r'[^a-z0-9]+', '_', u[22:].lower())[:60]
        if u.endswith('robots.txt') or u.endswith('.xml'): open(os.path.join(out, name + '.txt'), 'w').write(t[:20000]); continue
        ls = [(urllib.parse.urljoin(u, html.unescape(m.group(1))), re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2)))).strip()) for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', t, flags=re.S | re.I)]
        keep = [(a, b) for a, b in ls if re.search(r'\.(xlsx?|csv|pdf)(\?|$)|/media/|/document|sites/g/files', a, re.I) or re.search(r'president|primary|result', a + ' ' + b, re.I)]
        title = re.search(r'<title>(.*?)</title>', t, flags=re.S); h = re.findall(r'<h[1-4][^>]*>(.*?)</h[1-4]>', t, flags=re.S)
        open(os.path.join(out, name + '_links.txt'), 'w').write((title.group(1).strip() if title else '') + '\n' + ' / '.join(re.sub(r'<[^>]+>', '', x).strip() for x in h)[:1500] + '\n\n' + '\n'.join(f'{b} -> {a}' for a, b in keep[:500]))
        if '2024' in u or '2020-republican' in u:
            files += [(name, a, b) for a, b in keep if re.search(r'summary', a + ' ' + b, re.I)][:4]
            if '2024-republican' in u: files += [(name, a, b) for a, b in keep if re.search(r'belknap', a + ' ' + b, re.I)][:2]
            i = t.lower().find('summary by counties'); open(os.path.join(out, name + '_around.html'), 'w').write(t[max(0, i - 6000):i + 1500] if i >= 0 else t[:6000])
    for n, (name, a, b) in enumerate(files):
        try:
            data = get(a, head, binary=True); LOG[f'file {n} {a[-70:]}'] = len(data); lines = [f'{b} -> {a}']
            for sheet, rows in sheets(data).items():
                rows = [r for r in rows if any(c.strip() for c in r)]; lines.append(f'##### sheet {sheet!r}: {len(rows)} rows')
                lines += [' | '.join(c.strip() for c in r)[:900] for r in rows[:70]]
            open(os.path.join(out, f'{name}_file{n}.txt'), 'w').write('\n'.join(lines))
        except Exception as err:                        # noqa: BLE001
            LOG[f'file {n} {a[-70:]}'] = f'{type(err).__name__}: {str(err)[:80]}'
        time.sleep(1)
    json.dump(LOG, open(os.path.join(out, '_log.json'), 'w'), indent=1); print(json.dumps(LOG, indent=1))


if __name__ == '__main__':
    os.makedirs(sys.argv[1], exist_ok=True); main(sys.argv[1])
