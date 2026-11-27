"""Fetches the public series behind the national fundamentals models (approval, income, seats and the national House
vote) into samples/, for the Senate and House research. Run by the "Source samples" workflow with
script=tools/fetch_fundamentals.py; nothing here runs on the site.

    FRED          real disposable personal income (DPIC96) and real GDP growth (A191RL1Q225SBEA), quarterly
    Presidency    every Gallup presidential job-approval reading, from the American Presidency Project (UC Santa Barbara)
    Wikipedia     each House and Senate election's infobox, 1946-2026 (seats before and after, national House vote)
"""
import json, os, re, sys, time, urllib.parse, urllib.request

OUT = os.path.join(os.getcwd(), 'samples'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'election-research (github.com/KA82205)'}
log = []


def get(url, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except Exception as e:                                     # noqa: BLE001 - logged and retried
            err = repr(e); time.sleep(10 * (i + 1))
    log.append({'url': url, 'error': err}); return None


def save(name, data):
    if data is None: return
    with open(os.path.join(OUT, name), 'wb') as f: f.write(data)
    log.append({'saved': name, 'bytes': len(data)})


def fred():
    for s in ('DPIC96', 'A191RL1Q225SBEA', 'A229RX0Q048SBEA'):
        save(f'fred_{s}.csv', get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}'))


def gallup():
    html = get('https://www.presidency.ucsb.edu/statistics/data/presidential-job-approval-all-data')
    if html is None: return
    t = html.decode('utf-8', 'replace')
    with open(os.path.join(OUT, 'gallup_page.txt'), 'w') as f:          # the page as text, tags stripped, for checking the parse
        f.write(re.sub(r'\s+', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', ' ', t, flags=re.S)))
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, flags=re.S):
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S)]
        cells = [re.sub(r'\s+', ' ', c.replace('&nbsp;', ' ')).strip() for c in cells]
        if cells: rows.append(cells)
    with open(os.path.join(OUT, 'gallup_approval_rows.json'), 'w') as f: json.dump(rows, f)
    log.append({'saved': 'gallup_approval_rows.json', 'rows': len(rows)})


def wiki():
    out = {}
    for y in range(1946, 2027, 2):
        for ch in ('House of Representatives', 'Senate'):
            title = f'{y} United States {ch} elections'
            q = urllib.parse.urlencode({'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main', 'format': 'json',
                                        'formatversion': '2', 'titles': title, 'redirects': '1'})
            raw = get('https://en.wikipedia.org/w/api.php?' + q)
            if raw is None: continue
            try:
                page = json.loads(raw)['query']['pages'][0]; text = page['revisions'][0]['slots']['main']['content']
            except Exception:                                      # noqa: BLE001
                log.append({'title': title, 'error': 'no content'}); continue
            m = re.search(r'\{\{\s*Infobox election(.*?)\n\}\}', text, flags=re.S | re.I)
            out[f'{y} {ch}'] = {'title': page.get('title'), 'infobox': m.group(1)[:20000] if m else None}
            time.sleep(2.0)
    with open(os.path.join(OUT, 'wiki_infoboxes.json'), 'w') as f: json.dump(out, f)
    log.append({'saved': 'wiki_infoboxes.json', 'pages': len(out)})


if __name__ == '__main__':
    fred(); gallup(); wiki()
    with open(os.path.join(OUT, 'fetch_log.json'), 'w') as f: json.dump(log, f, indent=1)
    print(json.dumps(log, indent=1)[:4000])
