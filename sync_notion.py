"""Read only the 75 Soul habit flags from Notion and publish a minimal dashboard snapshot."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOKEN = os.environ['NOTION_TOKEN']
SOURCE_ID = '3cccc5d0-6ff7-46e8-a77a-ceb10cf762df'
PILLARS = ['Stillness', 'Reflection', 'Nature', 'Gratitude', 'Movement', 'Wisdom', 'Nourishment', 'Transformation']
URL = f'https://api.notion.com/v1/data_sources/{SOURCE_ID}/query'


def request(payload):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={
        'Authorization': f'Bearer {TOKEN}',
        'Notion-Version': '2025-09-03',
        'Content-Type': 'application/json',
    }, method='POST')
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def value(props, name, typ, default=None):
    obj = props.get(name, {})
    return obj.get(typ, default)


rows = []
cursor = None
while True:
    payload = {'page_size': 100}
    if cursor:
        payload['start_cursor'] = cursor
    result = request(payload)
    for page in result.get('results', []):
        props = page.get('properties', {})
        title = ''.join(t.get('plain_text', '') for t in value(props, 'Day', 'title', []))
        date = (value(props, 'Date', 'date') or {}).get('start', '')[:10]
        if not title.startswith('Day ') or not date:
            continue
        status_obj = value(props, 'Status', 'select') or value(props, 'Status', 'status') or {}
        row = {'day': title, 'date': date, 'status': status_obj.get('name', 'Not started')}
        for pillar in PILLARS:
            row[pillar.lower()] = bool(value(props, pillar, 'checkbox', False))
        rows.append(row)
    if not result.get('has_more'):
        break
    cursor = result.get('next_cursor')
    if not cursor:
        raise RuntimeError('Notion reported more rows but did not return a cursor')

if len(rows) != 75 or len({r['date'] for r in rows}) != 75:
    raise RuntimeError(f'Expected 75 unique daily rows; received {len(rows)}. Refusing to replace last good snapshot.')
rows.sort(key=lambda r: r['date'])
snapshot = {'synced_at': datetime.now(timezone.utc).isoformat(), 'days': rows}
Path('progress.json').write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
print(f'Updated public progress snapshot with {len(rows)} days; no notes, photos, or Notion token included.')
