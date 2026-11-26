"""What the Census Bureau's housing starts workbook and the Federal Reserve's industrial production tables hold, beside
FRED's copies, so that a second source can be read against the real layouts. Run by the "Source samples" workflow; it
changes nothing.

    python tools/probe_official.py out_folder
"""
import html, io, json, os, re, subprocess, sys, urllib.request

subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'openpyxl'], check=False)
UA = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)', 'Accept': '*/*'}
LOG = {}


def get(url, binary=False, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        b = r.read(); return b if binary else b.decode('utf-8', 'replace')


def text(page):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', page, flags=re.S | re.I); t = re.sub(r'<[^>]+>', ' | ', t)
    return re.sub(r'(\s*\|\s*)+', ' | ', re.sub(r'\s+', ' ', html.unescape(t)))


def around(t, words, span=1200, most=4):
    out = []
    for w in words:
        for m in list(re.finditer(w, t, flags=re.I))[:most]: out.append(f'--- {w} @{m.start()}\n' + t[max(0, m.start() - 200):m.start() + span])
    return '\n'.join(out)


def main(out):
    try:
        import openpyxl
        data = get('https://www.census.gov/construction/nrc/xls/starts_cust.xlsx', binary=True); wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True); lines = [str(wb.sheetnames)]
        for ws in wb.worksheets:
            rows = [['' if c is None else repr(c) for c in r] for r in ws.iter_rows(values_only=True)]; rows = [r for r in rows if any(r)]
            lines.append(f'##### {ws.title!r}: {len(rows)} rows'); lines += [' | '.join(r)[:400] for r in rows[:10] + [['...']] + rows[-16:]]
        open(os.path.join(out, 'census_starts.txt'), 'w').write('\n'.join(lines)); LOG['census'] = len(data)
    except Exception as err:                            # noqa: BLE001
        LOG['census'] = f'{type(err).__name__}: {str(err)[:120]}'
    pages = {'fred_indpro_txt': 'https://fred.stlouisfed.org/data/INDPRO.txt', 'fred_indpro_csv': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDPRO&cosd=2024-01-01', 'fred_ipb50001n': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPB50001N&cosd=2025-06-01',
             'fred_ipman': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPMAN&cosd=2025-06-01', 'fred_series_page': 'https://fred.stlouisfed.org/series/INDPRO',
             'fed_ip_sa': 'https://www.federalreserve.gov/releases/g17/ipdisk/ip_sa.txt', 'fed_ip_nsa': 'https://www.federalreserve.gov/releases/g17/ipdisk/ip_nsa.txt', 'fed_current': 'https://www.federalreserve.gov/releases/g17/current/default.htm',
             'fed_table1': 'https://www.federalreserve.gov/releases/g17/current/table1.htm', 'fed_g17_txt': 'https://www.federalreserve.gov/releases/g17/current/g17.txt', 'fed_download': 'https://www.federalreserve.gov/releases/g17/download.htm',
             'fed_revision': 'https://www.federalreserve.gov/releases/g17/revisions/Current/DefaultRev.htm', 'fed_about': 'https://www.federalreserve.gov/releases/g17/About.htm', 'fed_release_dates': 'https://www.federalreserve.gov/releases/g17/release_dates.htm',
             'fed_ddp_ip': 'https://www.federalreserve.gov/datadownload/Output.aspx?rel=G17&series=d5b24b2f19a7c6ed1b08d2b0c8d5b9a4&lastobs=24&filetype=csv&label=include&layout=seriescolumn',
             'fed_ddp_build': 'https://www.federalreserve.gov/datadownload/Build.aspx?rel=G17', 'fed_ddp_preformatted': 'https://www.federalreserve.gov/datadownload/Choose.aspx?rel=G17'}
    for name, url in pages.items():
        try:
            t = get(url); LOG[name] = len(t)
            if name in ('fed_ip_sa', 'fed_ip_nsa'):
                ls = t.split('\n'); t = '\n'.join(ls[:4]) + '\n...\n' + '\n'.join(l for l in ls if re.match(r'"?B50001"?\s+20(23|24|25|26)', l))
            elif name == 'fred_indpro_txt':
                ls = t.split('\n'); t = '\n'.join(ls[:40]) + '\n...\n' + '\n'.join(ls[-28:])
            elif name == 'fed_download' or name.startswith('fed_ddp'):
                t = '\n'.join(sorted(set(re.findall(r'href="([^"]+)"', t)))[:400]) + '\n\n' + text(t)[-3000:]
            elif not name.startswith('fred_') or name == 'fred_series_page':
                tt = text(t); t = around(tt, ['Total index', 'Total IP', 'Release Date', 'Updated:', 'annual revision', 'Industrial production (rose|fell|increased|decreased|was|moved|edged)', 'Notes:'], most=3)[:14000]
            open(os.path.join(out, name + '.txt'), 'w').write(t[:40000])
        except Exception as err:                        # noqa: BLE001
            LOG[name] = f'{type(err).__name__}: {str(err)[:100]}'
    json.dump(LOG, open(os.path.join(out, '_log.json'), 'w'), indent=1); print(json.dumps(LOG, indent=1))


if __name__ == '__main__':
    os.makedirs(sys.argv[1], exist_ok=True); main(sys.argv[1])
