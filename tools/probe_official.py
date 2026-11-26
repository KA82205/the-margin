"""Where the Federal Reserve keeps industrial production after an annual revision, beside FRED's copy. Run by the
"Source samples" workflow; it changes nothing.

    python tools/probe_official.py out_folder
"""
import json, os, re, sys, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)', 'Accept': '*/*'}
LOG = {}


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def main(out):
    base = 'https://www.federalreserve.gov/releases/g17/'
    pages = {'fred': 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=INDPRO&cosd=2023-01-01', 'monthly': base + 'ipdisk/ip_sa.txt', 'rev_current': base + 'Revisions/Current/ipdisk/ip_sa.txt', 'rev_dated': base + 'Revisions/20261124/ipdisk/ip_sa.txt',
             'rev_lower': base + 'revisions/Current/ipdisk/ip_sa.txt', 'rev_alltables': base + 'Revisions/Current/ipdisk/alltables.htm', 'rev_index': base + 'Revisions/Current/DefaultRev.htm', 'rev_series': base + 'g17_revision_series.htm',
             'current_alltables': base + 'Current/ipdisk/alltables.htm', 'rev_table1': base + 'Revisions/Current/table1_rev.htm', 'rev_ip': base + 'Revisions/Current/ipdisk/ip_sa.txt?x=1'}
    for name, url in pages.items():
        try:
            t = get(url); LOG[name] = len(t)
            if name in ('monthly', 'rev_current', 'rev_dated', 'rev_lower', 'rev_ip'):
                ls = t.split('\n'); t = '\n'.join(ls[:3]) + '\n...\n' + '\n'.join(l for l in ls if re.match(r'"?B50001"?\s+20(22|23|24|25|26)', l))
            elif name != 'fred':
                t = '\n'.join(sorted(set(re.findall(r'href="([^"]+)"', t)))[:300])
            open(os.path.join(out, name + '.txt'), 'w').write(t[:30000])
        except Exception as err:                        # noqa: BLE001
            LOG[name] = f'{type(err).__name__}: {str(err)[:100]}'
    json.dump(LOG, open(os.path.join(out, '_log.json'), 'w'), indent=1); print(json.dumps(LOG, indent=1))


if __name__ == '__main__':
    os.makedirs(sys.argv[1], exist_ok=True); main(sys.argv[1])
