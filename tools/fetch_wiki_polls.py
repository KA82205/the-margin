"""Fetches Wikipedia's pages for polls into samples/, for testing Wikipedia as the Senate forecast's poll feed. Run by
the "Source samples" workflow with script=tools/fetch_wiki_polls.py and names set to one or more of the groups below;
nothing here runs on the site. Wikipedia's text is CC BY-SA 4.0.

    senate2026     each 2026 Senate race's page, and any separate polling page it points to
    senate2018 ... senate2024  the same for earlier years (to compare with the FiveThirtyEight archive)
    national2026   the 2026 generic-ballot polls and the second Trump term's approval polls
"""
import json, os, re, sys, time, urllib.parse, urllib.request

OUT = os.path.join(os.getcwd(), 'samples'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'election-research (github.com/KA82205)'}
API = 'https://en.wikipedia.org/w/api.php?'
STATES = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii',
          'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
          'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
          'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
          'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming']
log = []


def get(params, tries=6):
    url = API + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': '2'})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:                                     # noqa: BLE001 - logged and retried
            err = repr(e); time.sleep(10 * (i + 1))
    log.append({'params': params, 'error': err}); return None


def pages(titles):
    """Up to 50 pages a request (the API's limit for page content)."""
    out = {}
    for i in range(0, len(titles), 40):
        j = get({'action': 'query', 'prop': 'revisions', 'rvprop': 'content|timestamp', 'rvslots': 'main', 'titles': '|'.join(titles[i:i + 40]), 'redirects': '1'})
        time.sleep(1.0)
        for p in (j or {}).get('query', {}).get('pages', []):
            if p.get('missing') or 'revisions' not in p: continue
            out[p['title']] = {'title': p['title'], 'timestamp': p['revisions'][0]['timestamp'], 'text': p['revisions'][0]['slots']['main']['content']}
    return out


def page(title):
    return pages([title]).get(title) or next(iter(pages([title]).values()), None)


def polling_links(text):
    """Separate polling pages a race page points to ({{main|Opinion polling for ...}} and the like)."""
    return sorted(set(t.strip() for t in re.findall(r'\[\[\s*(Opinion polling for the [^\]|#]+)', text) + re.findall(r'\{\{\s*(?:main|see also|further)\s*\|\s*(Opinion polling for the [^}|#]+)', text, flags=re.I)))


def senate(year):
    out = pages([f'{year} United States Senate {kind} in {st}' for st in STATES for kind in ('election', 'special election')])
    links = sorted(set(t for p in list(out.values()) for t in polling_links(p['text'])))
    out.update(pages(links))
    return out


def national2026():
    out = {}
    for q in ('Opinion polling for the 2026 United States House of Representatives elections', 'Opinion polling on the second Trump presidency'):
        p = page(q)
        if p is None:
            s = get({'action': 'query', 'list': 'search', 'srsearch': q, 'srlimit': '3'})
            for hit in (s or {}).get('query', {}).get('search', [])[:2]:
                p2 = page(hit['title'])
                if p2: out[p2['title']] = p2
        else:
            out[p['title']] = p
    return out


if __name__ == '__main__':
    for g in sys.argv[2:] or ['senate2026', 'national2026']:
        data = senate(int(g[-4:])) if g.startswith('senate') else national2026()
        with open(os.path.join(OUT, f'wiki_{g}.json'), 'w') as f: json.dump(data, f)
        log.append({'group': g, 'pages': len(data), 'titles': sorted(data)[:80]})
    with open(os.path.join(OUT, 'fetch_log.json'), 'w') as f: json.dump(log, f, indent=1)
    print(json.dumps(log, indent=1)[:3000])
