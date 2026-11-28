"""The raw sources of the governor forecast's training data, kept out of the repository (data/governor/raw/):
FiveThirtyEight's governor results by candidate (CC BY 4.0, github.com/fivethirtyeight/election-results) and its governor
polls of 2018-2024 (CC BY 4.0, from the archived copy in github.com/jcervas/data at a fixed commit). Run by the samples
workflow (script tools/fetch_governor_data.py) or anywhere GitHub can be reached.

    python tools/fetch_governor_data.py [folder]
"""
import os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = '27d7b352bcf0361498f249a556656bb1535c0e32'
FILES = {'election_results_gubernatorial.csv': 'https://raw.githubusercontent.com/fivethirtyeight/election-results/main/election_results_gubernatorial.csv',
         '538_governor_polls_historical.csv': f'https://raw.githubusercontent.com/jcervas/data/{ARCHIVE}/fivethirtyeight/projects.fivethirtyeight.com/polls-page/data/governor_polls_historical.csv'}


def main(out=None):
    d = out or os.path.join(ROOT, 'data', 'governor', 'raw'); os.makedirs(d, exist_ok=True)
    for name, url in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'election-research'}), timeout=120) as r:
            body = r.read()
        with open(os.path.join(d, name), 'wb') as f: f.write(body)
        print(name, len(body), 'bytes')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
