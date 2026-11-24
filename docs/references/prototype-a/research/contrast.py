from pathlib import Path
import re

def luminance(hex_color):
    values = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    channels = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return sum(value * weight for value, weight in zip(channels, (0.2126, 0.7152, 0.0722)))

def contrast(first, second):
    low, high = sorted((luminance(first), luminance(second)))
    return (high + 0.05) / (low + 0.05)

css = Path(__file__).resolve().parents[1].joinpath('prototype.css').read_text()
for start in ('body{','body.b{'):
    rules = css.split(start, 1)[1].split('}', 1)[0]
    tokens = dict(re.findall(r'--([\w-]+):(#\w+)', rules))
    print('A' if start == 'body{' else 'B')
    pairs = [('text', 'page'), ('muted', 'page'), ('text', 'surface'),
             ('muted', 'secondary'), ('text', 'selected'), ('muted', 'selected'), ('action', 'secondary'),
             ('action', 'selected'), ('on-action', 'action'), ('control', 'page'),
             ('control', 'surface'), ('focus', 'secondary'), ('focus', 'selected'),
             ('positive', 'page'), ('warning', 'page'), ('error', 'secondary'), ('divider', 'page')]
    for first, second in pairs:
        print(f'{first} / {second}: {contrast(tokens[first], tokens[second]):.2f}:1')
