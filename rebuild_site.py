from pathlib import Path
import re, html as H

md = Path('/workspace/geo-x-watch/REPORT.md').read_text()
sections = []
cur = None
for line in md.splitlines():
    if re.match(r'^# [^#]', line) and not line.startswith('# Geo-X-Watch'):
        cur = {'title': line[2:].strip(), 'blocks': []}
        sections.append(cur)
    elif cur is not None:
        cur['blocks'].append(line)

def esc(s):
    return H.escape(s)

def linkify(text):
    parts = []
    pattern = re.compile(r'\[([^\]]+)\]\((https?://[^)]+)\)|(https://x\.com/[A-Za-z0-9_/\-]+)')
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            parts.append(('t', text[last:m.start()]))
        if m.group(1) and m.group(2):
            parts.append(('a', m.group(2), 'Apri post'))
        elif m.group(3):
            parts.append(('a', m.group(3), 'Apri post'))
        last = m.end()
    if last < len(text):
        parts.append(('t', text[last:]))
    out = []
    for p in parts:
        if p[0] == 't':
            out.append(esc(p[1]))
        else:
            out.append(f'<a class="chip" href="{esc(p[1])}" target="_blank" rel="noopener">{esc(p[2])}</a>')
    return ''.join(out)

def render_item(line):
    raw = line[2:].strip()
    unver = 'NON VERIFICATO' in raw or 'voce di parte' in raw or '⚠' in raw
    cls = 'item warn' if unver else 'item'
    handle = ''
    rest = raw
    m = re.match(r'(@[\w_]+(?:\s+@[\w_]+)*)\s*[—\-]\s*(.*)', raw, re.S)
    if m:
        handle, rest = m.group(1), m.group(2)
    hh = f'<span class="handle">{esc(handle)}</span>' if handle else ''
    return f'<li class="{cls}">{hh}<div class="body">{linkify(rest)}</div></li>'

def tier_class(mode):
    ml = mode.lower()
    if '[a]' in ml or 'ufficial' in ml:
        return 'a'
    if '[o]' in ml or 'opinion' in ml:
        return 'o'
    if '[b]' in ml or 'analist' in ml:
        return 'b'
    if '[c]' in ml or 'controvers' in ml:
        return 'c'
    return 'a'

crisis_html = []
nav = []
for i, sec in enumerate(sections):
    sid = f'c{i}'
    nav.append(f'<a href="#{sid}">{esc(sec["title"])}</a>')
    parts = [f'<section class="crisis" id="{sid}"><header class="crisis-head"><h2>{esc(sec["title"])}</h2></header>']
    mode = None
    buf = []
    riassunto = None
    sentiment = None
    lettura = None
    empty_note = None
    for line in sec['blocks']:
        if line.startswith('## '):
            if mode and buf:
                tc = tier_class(mode)
                parts.append(f'<div class="tier tier-{tc}"><h3><span class="badge">{esc(mode)}</span></h3><ul>{"".join(buf)}</ul></div>')
            mode = line[3:].strip()
            buf = []
            if mode.lower().startswith('riassunto'):
                riassunto = []
                mode = '__RIASSUNTO__'
            elif mode.lower().startswith('sentiment'):
                sentiment = []
                lettura = []
                mode = '__SENTIMENT__'
        elif line.startswith('- '):
            if mode in ('__RIASSUNTO__', '__SENTIMENT__'):
                continue
            if re.search(r'404|non trovat|nessun post|sospeso|protetto', line, re.I) and 'status/' not in line:
                continue
            buf.append(render_item(line))
        elif mode == '__RIASSUNTO__' and line.strip():
            riassunto.append(line.strip())
        elif mode == '__SENTIMENT__' and line.strip():
            s = line.strip()
            if s.startswith('Lettura'):
                lettura.append(s)
            else:
                sentiment.append(s)
        elif line.startswith('Riassunto'):
            if mode and buf and mode not in ('__RIASSUNTO__', '__SENTIMENT__'):
                tc = tier_class(mode)
                parts.append(f'<div class="tier tier-{tc}"><h3><span class="badge">{esc(mode)}</span></h3><ul>{"".join(buf)}</ul></div>')
                mode = None
                buf = []
            riassunto = []
            mode = '__RIASSUNTO__'
        elif line.startswith('Sentiment'):
            if mode and buf and mode not in ('__RIASSUNTO__', '__SENTIMENT__'):
                tc = tier_class(mode)
                parts.append(f'<div class="tier tier-{tc}"><h3><span class="badge">{esc(mode)}</span></h3><ul>{"".join(buf)}</ul></div>')
                mode = None
                buf = []
            sentiment = []
            lettura = []
            mode = '__SENTIMENT__'
        elif 'Nessun segnale' in line or 'Nessun post' in line:
            empty_note = line.strip()
    if mode and buf and mode not in ('__RIASSUNTO__', '__SENTIMENT__'):
        tc = tier_class(mode)
        parts.append(f'<div class="tier tier-{tc}"><h3><span class="badge">{esc(mode)}</span></h3><ul>{"".join(buf)}</ul></div>')

    # Order: Riassunto → tiers (already in parts after header) → empty → Sentiment
    # Currently tiers were appended as we went; need to reorder: insert riassunto after header
    body = parts[1:]  # after header
    parts = [parts[0]]
    if riassunto:
        paras = ''.join(f'<p>{esc(p)}</p>' for p in riassunto)
        parts.append(f'<div class="riassunto"><h3>Riassunto</h3>{paras}</div>')
    if empty_note:
        parts.append(f'<p class="empty">{esc(empty_note)}</p>')
    parts.extend(body)
    if sentiment:
        sent_lines = [s for s in sentiment if s != '__LETTURA__' and not s.startswith('Lettura')]
        if sent_lines:
            parts.append(f'<div class="sentiment"><h3>Sentiment</h3><p>{esc(" ".join(sent_lines))}</p></div>')
    if lettura:
        # Keep full "Lettura della giornata: …" text; strip only a bare "Lettura" header if present
        lett_lines = []
        for s in lettura:
            if s == 'Lettura' or s == 'Lettura della giornata':
                continue
            if s.lower().startswith('lettura della giornata'):
                s = re.sub(r'(?i)^lettura della giornata\s*:\s*', '', s).strip() or s
            if s:
                lett_lines.append(s)
        if lett_lines:
            parts.append(f'<div class="lettura"><h3>Lettura della giornata</h3><p>{esc(" ".join(lett_lines))}</p></div>')
    parts.append('</section>')
    crisis_html.append(''.join(parts))

site = Path('/workspace/geo-x-watch-site')
prev = (site / 'index.html').read_text()
m = re.search(r'<style>(.*?)</style>', prev, re.S)
style = m.group(1) if m else ''
extra = '''
.tier-o .badge{background:#7c3aed;color:#fff}
.riassunto{margin:0.85rem 0 1.1rem;padding:1.05rem 1.15rem;border-radius:12px;border:1px solid rgba(77,163,255,.35);background:rgba(77,163,255,.08)}
.riassunto h3{margin:0 0 .55rem;font-size:.85rem;letter-spacing:.04em;text-transform:uppercase;color:#7cc0ff}
.riassunto p{margin:0 0 .55rem;line-height:1.55}
.riassunto p:last-child{margin-bottom:0}
.sentiment{margin:1rem 0;padding:1rem 1.1rem;border-radius:12px;border:1px solid rgba(124,58,237,.35);background:rgba(124,58,237,.08)}
.sentiment h3{margin:0 0 .4rem;font-size:.85rem;letter-spacing:.04em;text-transform:uppercase;color:#c4b5fd}
.sentiment p{margin:0;line-height:1.5}
.lettura{margin:.75rem 0 0;padding:.9rem 1.1rem;border-radius:12px;border:1px solid rgba(34,197,94,.3);background:rgba(34,197,94,.07)}
.lettura h3{margin:0 0 .4rem;font-size:.85rem;letter-spacing:.04em;text-transform:uppercase;color:#86efac}
.lettura p{margin:0;line-height:1.5}
.empty{opacity:.7;font-style:italic}
'''
for chunk in ['.riassunto{', '.tier-o .badge{', '.sentiment{margin:1rem', '.lettura{']:
    if chunk not in style:
        style += extra
        break
else:
    if '.riassunto{' not in style:
        style += extra

_hm = re.search(r'\*\*([^*]+)\*\*', md)
_stamp_raw = _hm.group(1).strip() if _hm else '18 Sep 2026, ~09:40 Europe/Monaco'
_dm = re.search(r'(\d{1,2} \w+ \d{4}).*?(\d{1,2}:\d{2})', _stamp_raw)
_day = _dm.group(1) if _dm else '18 Sep 2026'
_hhmm = _dm.group(2) if _dm else '09:40'
_n = len(sections)
_preqc = 'bozza pre-QC' if ('bozza' in md[:500].lower() or 'qc-draft' in md[:500].lower()) else 'post-QC'

page = f'''<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Geo-X-Watch — Giro {_n} crisi</title>\n<!-- stamp from REPORT -->
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>{style}</style></head><body><div class="wrap">
<header class="top"><div class="brand"><div class="logo">GX</div><div>
<h1>Geo-X-Watch</h1><p class="sub">Giro {_day} · {_n} crisi · [A][B][O][C] · riassunto + sentiment · {_preqc}</p></div></div><div class="meta"><span class="pill live">{"Draft" if _preqc.startswith("bozza") else "Live"}</span><span class="pill">{_day} · {_hhmm}</span><span class="pill">Europe/Monaco</span><span class="pill">ogni giorno 08:00</span></div></header>
<div class="disclaimer"><strong>⚠️ NON VERIFICATO</strong> — claim [C] = voce di parte. [O] = opinion maker geopolitica (non lifestyle). Il <em>Riassunto</em> apre ogni crisi; <em>Sentiment</em> e <em>Lettura della giornata</em> chiudono. Pesa [A] più di [C].</div>
<nav class="nav">{''.join(nav)}</nav>
{''.join(crisis_html)}
<footer>Geo-X-Watch · lun–dom 08:00 · solo segnali utili</footer>
</div></body></html>'''
(site / 'index.html').write_text(page)
print('page', len(page))
print('sections', _n)
print('has riassunto', page.count('riassunto'))
print('has sentiment', page.count('class="sentiment"'))
print('has lettura', page.count('class="lettura"'))
print('noise', bool(re.search(r'profili 404|nessun post rilevante in finestra', page, re.I)))
