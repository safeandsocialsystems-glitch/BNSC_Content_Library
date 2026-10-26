#!/usr/bin/env python3
"""BNSC CSV -> JSON converter. Python 3 stdlib only.
Usage: python3 scripts/import_csv.py [contents.csv]
"""
import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ['id','title','type','category','summary','tags','keywords','duration_minutes','published_at','url']
TYPES = {'動画', '研究解説'}
CATEGORIES = {'トレーニング', 'リハビリ', '療育・発達支援', '脳機能・神経科学'}
HOSTS = {'community.camp-fire.jp','camp-fire.jp','www.camp-fire.jp'}

def fail(message):
    raise ValueError(message)

def is_allowed_url(url):
    try:
        result = urlparse(url)
        return result.scheme == 'https' and result.hostname in HOSTS and not result.username and not result.password and result.port is None and not result.query and not result.fragment
    except ValueError:
        return False

def parse_csv(path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames not in (HEADERS, HEADERS + ['status']):
            fail(f'ヘッダー列が異なります。正しい列: {", ".join(HEADERS)}')
        items = []
        ids = set()
        for rowno, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue
            if None in row:
                fail(f'{rowno}行目: CSVの列が多すぎます。カンマを含む値はダブルクォートで囲んでください。')
            if any(v is None for v in row.values()):
                fail(f'{rowno}行目: CSVの列が不足しています。空欄もカンマで区切ってください。')
            row = {k: (v or '').strip() for k, v in row.items()}
            if not row['id'] or not re.fullmatch(r'[\w-]{1,80}', row['id'], flags=re.ASCII):
                fail(f'{rowno}行目: id は半角英数字・ハイフン・アンダーバー、1〜80文字にしてください。')
            if row['id'] in ids: fail(f'{rowno}行目: id が重複しています: {row["id"]}')
            ids.add(row['id'])
            if not row['title']: fail(f'{rowno}行目: title が空です。')
            if row['type'] not in TYPES: fail(f'{rowno}行目: type は「動画」または「研究解説」です。')
            if row['category'] not in CATEGORIES: fail(f'{rowno}行目: category が不正です: {row["category"]}')
            try: duration = int(row['duration_minutes']) if row['duration_minutes'] else 0
            except ValueError: fail(f'{rowno}行目: duration_minutes は数値にしてください。')
            if duration < 0 or duration > 3000: fail(f'{rowno}行目: duration_minutes は0〜3000です。')
            status = row.get('status', '') or 'draft'
            if status not in {'draft', 'published', 'demo'}:
                fail(f'{rowno}行目: status は draft / published / demo です。')
            if status == 'published' and (not row['url'] or row['id'].upper().startswith('DEMO-')):
                fail(f'{rowno}行目: published は投稿URL確認済みの実コンテンツのみ指定できます。')
            if row['published_at']:
                try:
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['published_at']): raise ValueError()
                    date.fromisoformat(row['published_at'])
                except ValueError: fail(f'{rowno}行目: published_at は YYYY-MM-DD 形式です。')
            if row['url'] and not is_allowed_url(row['url']):
                fail(f'{rowno}行目: url はCAMPFIRE投稿への https URLのみ登録できます。')
            items.append({
                'status':status,'id':row['id'],'title':row['title'],'type':row['type'],'category':row['category'],
                'summary':row['summary'],'tags':[x.strip() for x in row['tags'].split('|') if x.strip()],
                'keywords':[x.strip() for x in row['keywords'].split('|') if x.strip()],
                'duration_minutes':duration,'published_at':row['published_at'],'url':row['url']
            })
    return items

def public_payload(items):
    # Only explicitly reviewed entries enter the publicly downloadable index.
    return {'demo': False, 'items': [
        {k: v for k, v in item.items() if k != 'status'}
        for item in items if item['status'] == 'published'
    ]}

def main():
    parser = argparse.ArgumentParser(description='確認済みの実コンテンツだけを検索JSONへ反映します。')
    parser.add_argument('csv_file', nargs='?', type=Path, default=ROOT / 'contents.csv')
    args = parser.parse_args()
    if not args.csv_file.exists(): fail(f'CSVが見つかりません: {args.csv_file}')
    items = parse_csv(args.csv_file)
    payload = public_payload(items)
    output = ROOT / 'data' / 'contents.json'
    # A CSV-only import must not erase the last successful Vimeo snapshot.
    if output.exists():
        previous = json.loads(output.read_text(encoding='utf-8'))
        vimeo = [it for it in previous['items'] if it.get('source') == 'vimeo']
        if any(it['id'].startswith('vimeo-') for it in payload['items']):
            fail('CSVのidに予約接頭辞 vimeo- は使用できません。')
        payload['items'].extend(vimeo)
        if 'vimeo_sync' in previous:
            payload['vimeo_sync'] = previous['vimeo_sync']
    output.parent.mkdir(exist_ok=True, parents=True)
    temporary = output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(output)
    print(f'変換完了: 管理用 {len(items)}件 / 検索掲載 {len(payload["items"])}件 / 下書き・デモは非掲載')
    print(f'出力先: {output}')

if __name__ == '__main__':
    try: main()
    except ValueError as exc:
        print('エラー:', exc, file=sys.stderr)
        sys.exit(1)
