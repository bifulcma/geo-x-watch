# Geo-X-Watch

Report OSINT sulle 8 crisi (A/B/O/C) da X, pubblicato su Vercel: Iran-USA-Israele, India-Pakistan, Europa-Russia, Ucraina, Stretto di Taiwan, USA-Europa, Coree, USA-Cina.

- Live: https://geo-x-watch-bifulcmas-projects.vercel.app/
- Aggiornamento: ogni giorno, raccolta alle 03:00 e pubblicazione entro le 04:15 (Europe/Monaco), routine Chief of Staff (Grok Bot)
- `data/latest.json` è il feed del War Index (unico file letto da Hermes); `data/prova.json` è solo per prove, non è letto dal War Index.

## Deploy
Static `index.html`. Linked to Vercel project `geo-x-watch`.

## data/latest.json (percorso FISSO — non spostare mai)

Ogni edizione `rebuild_site.py` esegue `export_latest.py`, che genera `data/latest.json` dallo stesso `REPORT.md` della pagina.
Letto da Hermes/Capo: `https://raw.githubusercontent.com/bifulcma/geo-x-watch/main/data/latest.json` e `https://geo-x-watch.vercel.app/data/latest.json`.
Se `giro_date` non è la data di oggi, il giro è mancato.

Schema (schema_version 1):
```
{schema_version, giro_date "AAAA-MM-GG", published_at ISO Europe/Monaco, edition_stamp, edition_id, timezone, site_url, tiers,
 crises: [{id: iran|ucraina|taiwan|usa-cina|india-pakistan|usa-europa|europa-russia|coree,
           name, riassunto, sentiment, mood, lettura,
           posts: [{account "@x", tier A|B|O|C, date, text, translation_it?, unverified, url "https://x.com/.../status/..."}]}]}
```
