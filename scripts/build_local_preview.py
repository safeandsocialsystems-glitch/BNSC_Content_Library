#!/usr/bin/env python3
"""Build a self-contained, file://-compatible private preview. Never deploy."""
import argparse
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(data_path, output):
    data = json.loads(data_path.read_text(encoding='utf-8'))
    if not isinstance(data.get('items'), list) or not data['items']:
        raise ValueError('実データが0件です。保存版を作成しません。')
    for item in data['items']:
        if item.get('source') == 'vimeo' and item.get('url'):
            raise ValueError('Vimeo視聴リンクは保存版に含められません。')
        if set(item) & {'link', 'player_embed_url', 'access_token', 'files', 'download', 'embed', 'privacy'}:
            raise ValueError('非公開フィールドを検出しました。')
    data['local_preview'] = {'expected_items': len(data['items'])}
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    html = (ROOT / 'index.html').read_text()
    css = (ROOT / 'styles.css').read_text()
    hero = base64.b64encode((ROOT / 'assets/hero-scene.webp').read_bytes()).decode()
    css = css.replace("url('./assets/hero-scene.webp')", "url('data:image/webp;base64," + hero + "')")
    js = (ROOT / 'app.js').read_text().replace('</script', '<\\/script')
    html = html.replace('<link rel="stylesheet" href="./styles.css">', '<style>' + css + '</style>')
    html = html.replace('<script defer src="./app.js"></script>', '')
    html = html.replace('<link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">', '')
    html = html.replace('href="./" aria-label="BNSC', 'href="#" aria-label="BNSC')
    html = html.replace('<title>BNSC | コンテンツライブラリ</title>', '<title>BNSC | 実データ確認・ローカル限定</title>')
    html = html.replace('<div class="wrap page-content">', '<div class="wrap page-content"><p class="demo-notice">ローカル確認用・未公開 ／ 取得済みの動画 ' + str(len(data['items'])) + '件</p>')
    html = html.replace('</body>', '<script id="bnsc-embedded-data" type="application/json">' + encoded + '</script><script>' + js + '</script></body>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    return len(data['items'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print('ローカル保存版を作成:', build(args.data, args.output), '件')
