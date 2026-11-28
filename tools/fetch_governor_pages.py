"""Wikipedia's pages of governor elections, saved for the governor forecast's training data and its tests: each year's
overview ("<year> United States gubernatorial elections") and, with "races", each state's page of the race ("<year>
<State> gubernatorial election"). Run on GitHub's servers by the samples workflow (script tools/fetch_governor_pages.py,
names: the years and, optionally, "races"), since Wikipedia cannot be reached from everywhere the code is worked on.

    python tools/fetch_governor_pages.py <folder> <years> [races]   ->   <folder>/governor_pages/<year>.json
                                                                          {title: {title, timestamp, text}}
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, 'house'))
import wiki_house as WH


def main(out, years, races=False):
    d = os.path.join(out, 'governor_pages'); os.makedirs(d, exist_ok=True)
    for y in years:
        want = [f'{y} United States gubernatorial elections'] + ([f'{y} {WH.NAMES[st]} gubernatorial election' for st in sorted(WH.NAMES)] if races else [])
        pages = WH.fetch(want)
        with open(os.path.join(d, f'{y}.json'), 'w') as f: json.dump(pages, f)
        print(y, len(pages), 'of', len(want), 'pages,', sum(len(p['text']) for p in pages.values()), 'characters')


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0] if a else 'samples', [int(x) for x in a[1:] if x.isdigit()] or [2026], 'races' in a[1:])
