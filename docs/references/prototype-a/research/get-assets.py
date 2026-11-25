import concurrent.futures
import json
import pathlib
import re
import urllib.request

base = pathlib.Path(__file__).resolve().parents[1]
assets = base / 'assets'
files = {}
faces = {
    'Space Grotesk': 'space',
    'Cinzel': 'cinzel',
    'Instrument Sans': 'instrument',
    'Barlow Semi Condensed': 'barlow',
}

for block in (assets / 'font-source.css').read_text().split('/* latin */')[1:]:
    block = block.split('}')[0]
    family = re.search(r"font-family: '(.+?)'", block)[1]
    weight = re.search(r'font-weight: ([^;]+)', block)[1]
    url = re.search(r'url\((.*?)\)', block)[1]
    key = faces[family]
    if key == 'barlow':
        key += '-' + weight
    files[key + '.woff2'] = url

source = {}
for mode in ('solo', 'team'):
    data = json.loads((assets / (mode + '-source.json')).read_text())
    source[mode] = data['data']
    for lane in data['data'].values():
        for champion in lane:
            url = champion['icon_url']
            if url:
                assert url.startswith('https://cdn5.lolalytics.com/champx46/')
                key = url.rsplit('/', 1)[1]
                files[key] = url
                champion['portrait'] = key

def download(task):
    name, url = task
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=12) as response:
        (assets / name).write_bytes(response.read())

with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    list(pool.map(download, files.items()))

(assets / 'data.js').write_text('const snapshot = ' + json.dumps(source, separators=(',', ':')) + ';\n')
print(f'Cached {len(files)} portraits and font files')
