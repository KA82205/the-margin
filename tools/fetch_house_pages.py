"""Wikipedia's pages of House elections, saved for the House forecast's after-election step and the live forecast's
tests: each year's overview and its states' pages. Run on GitHub's servers by the samples workflow (script
tools/fetch_house_pages.py, names: the years, such as "2026 2028"; add "overview" to read the overviews alone), since
Wikipedia cannot be reached from everywhere the code is worked on.

    python tools/fetch_house_pages.py <folder> <years> [overview]   ->   <folder>/house_pages/<year>.json
                                                                          {title: {title, timestamp, text}}
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, 'house'))
import wiki_house as WH


def main(out, years, states=True):
    d = os.path.join(out, 'house_pages'); os.makedirs(d, exist_ok=True)
    for y in years:
        pages = WH.fetch([WH.overview(y)])
        one = WH.one_seat(pages[WH.overview(y)]['text'], y) if WH.overview(y) in pages else None
        want = WH.titles(y, states, one)
        pages.update(WH.fetch([t for t in want if t not in pages]))
        # the district pages the states' pages point to, where polls and results of the closest races often are
        import polls as PO
        links = sorted({t for p in list(pages.values()) for t in PO.main_links(p['text'], y)})
        if states and links: pages.update(WH.fetch(links)); want += links
        with open(os.path.join(d, f'{y}.json'), 'w') as f: json.dump(pages, f)
        print(y, len(pages), 'of', len(want), 'pages,', sum(len(p['text']) for p in pages.values()), 'characters; missing:', [t for t in want if t not in pages])


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0] if a else 'samples', [int(x) for x in a[1:] if x.isdigit()] or [2026], 'overview' not in a[1:])
