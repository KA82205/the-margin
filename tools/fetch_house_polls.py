"""FiveThirtyEight's House polls of 2018-2024 (CC BY 4.0), from the archived copy in github.com/jcervas/data at a fixed
commit, into data/house/raw/538_house_polls_historical.csv (kept out of the repository), for house/polls.py. Run by the
samples workflow (script tools/fetch_house_polls.py) or anywhere GitHub can be reached.

    python tools/fetch_house_polls.py [folder]
"""
import os, sys, urllib.request

COMMIT = '27d7b352bcf0361498f249a556656bb1535c0e32'
URL = f'https://raw.githubusercontent.com/jcervas/data/{COMMIT}/fivethirtyeight/projects.fivethirtyeight.com/polls-page/data/house_polls_historical.csv'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(out=None):
    d = out or os.path.join(ROOT, 'data', 'house', 'raw'); os.makedirs(d, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'election-research'}), timeout=120) as r:
        body = r.read()
    p = os.path.join(d, '538_house_polls_historical.csv')
    with open(p, 'wb') as f: f.write(body)
    print(p, len(body), 'bytes')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
