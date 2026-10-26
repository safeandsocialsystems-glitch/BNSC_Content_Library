#!/usr/bin/env python3
"""Validate and assemble only public files. Does not deploy anything."""
import argparse
import json
import shutil
import sys
from import_csv import ROOT, parse_csv, public_payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synced', action='store_true', help='今回のVimeo同期成功後のJSONを使用（0件への更新も可能）')
    args = parser.parse_args()
    from sync_vimeo import merged_payload
    previous = json.loads((ROOT / 'data' / 'contents.json').read_text(encoding='utf-8'))
    vimeo = [it for it in previous['items'] if it.get('source') == 'vimeo']
    payload = merged_payload(ROOT / 'contents.csv', vimeo)
    if args.synced and previous.get('vimeo_sync', {}).get('complete') is not True:
        raise ValueError('Vimeoの正常な同期結果がありません。先に同期してください。')
    if 'vimeo_sync' in previous:
        payload['vimeo_sync'] = previous['vimeo_sync']
    else:
        payload.pop('vimeo_sync', None)
    if not payload['items'] and not args.synced:
        raise ValueError('公開可能な実コンテンツが0件です。投稿と公開可能なメタデータを確認し、status を published にしてください。')
    output = ROOT / 'dist'
    if output.exists():
        raise ValueError('dist が既に存在します。以前の公開物を確認して別名に移動してから再実行してください。')
    output.mkdir()
    for name in ('index.html', 'app.js', 'styles.css'):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / 'assets', output / 'assets')
    (output / 'data').mkdir()
    (output / 'data' / 'contents.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'公開用ファイルを作成しました: {output} / {len(payload["items"])}件（未デプロイ）')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f'エラー: {exc}', file=sys.stderr)
        sys.exit(1)
