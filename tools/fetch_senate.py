"""Download the raw files the Senate back-test is built from, as published, into a folder. Run by the "Source samples"
workflow; it changes nothing in the repository.

    python tools/fetch_senate.py out_folder
"""
import json, os, sys, urllib.request
UA = {'User-Agent': 'Mozilla/5.0 (compatible; the-margin/1.0; +https://github.com/KA82205/the-margin)'}
FILES = {
    'mit_senate_1976_2024.tab': 'https://dataverse.harvard.edu/api/access/datafile/13887039',     # MIT Election Data and Science Lab, U.S. Senate 1976-2024, doi:10.7910/DVN/PEJ5QU
    'mit_senate_codebook.md': 'https://dataverse.harvard.edu/api/access/datafile/6708560',
    'fec_weball_header.csv': 'https://www.fec.gov/files/bulk-downloads/data_dictionaries/weball_header_file.csv',
    **{f'fec_weball{y}.zip': f'https://www.fec.gov/files/bulk-downloads/20{y}/weball{y}.zip' for y in ('18', '20', '22', '24', '26')},
}
if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True); log = {}
    for name, url in FILES.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                b = r.read(); open(os.path.join(out, name), 'wb').write(b); log[name] = {'status': r.status, 'bytes': len(b), 'url': url}
        except Exception as e:                              # noqa: BLE001
            log[name] = f'{type(e).__name__}: {str(e)[:150]}'
    json.dump(log, open(os.path.join(out, '_log.json'), 'w'), indent=1); print(json.dumps(log, indent=1))
