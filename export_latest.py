#!/usr/bin/env python3
"""Export data/latest.json from REPORT.md (stdlib only).
FIXED PATH: data/latest.json — never move it (read by Hermes/Capo from GitHub).
Usage: python3 export_latest.py [REPORT.md] [--published-at ISO]
"""
import json, re, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SITE = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Monaco')
IDS = [('iran', 'iran'), ('ucraina', 'ucraina'), ('taiwan', 'taiwan'), ('usa-cina', 'usa-cina'),
       ('india-pakistan', 'india-pakistan'), ('usa-europa', 'usa-europa'),
       ('europa-russia', 'europa-russia'), ('coree', 'coree')]
MONTHS = {m: i for i, m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'], 1)}

def crisis_id(title):
    t = title.lower().replace('–', '-')
    for key, cid in [('iran', 'iran'), ('ucraina', 'ucraina'), ('taiwan', 'taiwan'), ('usa-cina', 'usa-cina'),
                     ('india', 'india-pakistan'), ('usa-europa', 'usa-europa'), ('europa-russia', 'europa-russia'),
                     ('core', 'coree')]:
        if key in t:
            return cid
    raise ValueError(f'unknown crisis title: {title}')

def tier_of(mode):
    m = re.search(r'\[([ABOC])\]', mode)
    return m.group(1) if m else None

def export(report_path, published_at=None):
    md = Path(report_path).read_text()
    stamp_m = re.search(r'\*\*([^*]+)\*\*(?:\s*\(([^)]+)\))?', md)
    stamp = stamp_m.group(1).strip() if stamp_m else ''
    edition = stamp_m.group(2).strip() if stamp_m and stamp_m.group(2) else ''
    dm = re.search(r'(\d{1,2}) (\w{3})\w* (\d{4})', stamp)
    giro_date = f'{int(dm.group(3)):04d}-{MONTHS[dm.group(2).lower()]:02d}-{int(dm.group(1)):02d}'
    crises, cur, mode, post = [], None, None, None
    for line in md.splitlines():
        if re.match(r'^# [^#]', line) and not line.startswith('# Geo-X-Watch'):
            title = line[2:].strip()
            cur = {'id': crisis_id(title), 'name': title, 'riassunto': '', 'sentiment': '', 'lettura': '', 'posts': []}
            crises.append(cur); mode = None; post = None
        elif cur is None:
            continue
        elif line.startswith('## '):
            h = line[3:].strip(); post = None
            mode = 'R' if h.lower().startswith('riassunto') else 'S' if h.lower().startswith('sentiment') else h
        elif line.startswith('- ') and mode not in ('R', 'S', None):
            # same skip rule as rebuild_site.py
            if re.search(r'404|non trovat|nessun post|sospeso|protetto', line, re.I) and 'status/' not in line:
                post = None; continue
            raw = line[2:].strip()
            m = re.match(r'(@[\w_]+(?:\s+@[\w_]+)*)\s*[—\-]\s*(.*)', raw, re.S)
            account, rest = (m.group(1), m.group(2)) if m else ('', raw)
            urls = re.findall(r'https://x\.com/[A-Za-z0-9_]+/status/\d+', rest)
            d = re.match(r'\((\d{1,2} \w{3})\)\s*', rest)
            text = re.sub(r'\s*\[https?://[^\]]+\]', '', rest[d.end():] if d else rest).strip()
            post = {'account': account, 'tier': tier_of(mode), 'date': d.group(1) if d else None,
                    'text': text, 'unverified': ('NON VERIFICATO' in rest or 'voce di parte' in rest),
                    'url': urls[-1] if urls else None}
            cur['posts'].append(post)
        elif (it := re.match(r'^\s+IT:\s*(.+)$', line)) and post is not None:
            itx = it.group(1).strip()
            urls = re.findall(r'https://x\.com/[A-Za-z0-9_]+/status/\d+', itx)
            if urls and not post['url']:
                post['url'] = urls[-1]
            post['translation_it'] = re.sub(r'\s*\[https?://[^\]]+\]', '', itx).strip()
        elif mode == 'R' and line.strip():
            cur['riassunto'] = (cur['riassunto'] + '\n' + line.strip()).strip()
        elif mode == 'S' and line.strip():
            s = line.strip()
            if s.lower().startswith('lettura'):
                cur['lettura'] = re.sub(r'(?i)^lettura della giornata\s*:\s*', '', s)
            else:
                cur['sentiment'] = (cur['sentiment'] + ' ' + s).strip()
    for c in crises:
        mm = re.search(r'Mood:\s*([^.\n]+)', c['sentiment'])
        c['mood'] = mm.group(1).strip() if mm else None
    data = {'schema_version': 1, 'giro_date': giro_date,
            'published_at': published_at or datetime.now(TZ).isoformat(timespec='seconds'),
            'edition_stamp': f'{stamp} ({edition})' if edition else stamp, 'edition_id': edition,
            'timezone': 'Europe/Monaco', 'site_url': 'https://geo-x-watch.vercel.app/',
            'tiers': {'A': 'Ufficiali', 'B': 'Analisti & stampa', 'O': 'Opinion / wire', 'C': 'Controversi / propaganda (NON VERIFICATO)'},
            'crises': crises}
    validate(data)
    return data

def validate(d):
    ids = [c['id'] for c in d['crises']]
    assert sorted(ids) == sorted(i for i, _ in IDS), f'crisis ids: {ids}'
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', d['giro_date'])
    for c in d['crises']:
        assert c['riassunto'] and c['sentiment'], f'{c["id"]}: missing riassunto/sentiment'
        for p in c['posts']:
            assert p['account'].startswith('@'), (c['id'], p)
            assert p['tier'] in ('A', 'B', 'O', 'C'), (c['id'], p)
            assert p['url'] and re.fullmatch(r'https://x\.com/[A-Za-z0-9_]+/status/\d+', p['url']), (c['id'], p)

if __name__ == '__main__':
    args = sys.argv[1:]
    pub = None
    if '--published-at' in args:
        i = args.index('--published-at'); pub = args[i + 1]; del args[i:i + 2]
    src = args[0] if args else '/workspace/geo-x-watch/REPORT.md'
    data = export(src, pub)
    out = SITE / 'data' / 'latest.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('latest.json', data['giro_date'], {c['id']: len(c['posts']) for c in data['crises']})
