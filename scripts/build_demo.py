#!/usr/bin/env python3
"""Generate an entirely standalone demo HTML (no local server needed)."""
from pathlib import Path
import json, base64
from import_csv import parse_csv
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text(encoding='utf-8')
css=(ROOT/'styles.css').read_text(encoding='utf-8')
js=(ROOT/'app.js').read_text(encoding='utf-8')
data={'items': parse_csv(ROOT/'examples'/'demo_contents.csv')}
# Preview always labels content as a demo; this build is not intended for deployment.
data['demo']=True
base64_image=base64.b64encode((ROOT/'assets'/'hero-scene.webp').read_bytes()).decode('ascii')
css=css.replace("url('./assets/hero-scene.webp')",f"url('data:image/webp;base64,{base64_image}')")
html=html.replace('<link rel="stylesheet" href="./styles.css">',f'<style>\n{css}\n</style>')
html=html.replace('<link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">','')
html=html.replace('<script defer src="./app.js"></script>','')
# Prevent HTML parser termination if data ever includes markup-looking source text.
data_json=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
inline='''<script>
/* Single-file preview. Not a deployed production app. */
const PREVIEW_DATA = '''+data_json+''';
window.fetch = async () => ({ok:true,json:async()=>PREVIEW_DATA});
</script>
<script>\n'''+js.replace('</script','<\\/script')+'''\n</script>'''
html=html.replace('</body>',inline+'\n</body>')
html=html.replace('<title>BNSC | コンテンツライブラリ</title>', '<title>BNSC | コンテンツライブラリ（操作デモ）</title>')
dest=ROOT/'demo_preview.html'
dest.write_text(html,encoding='utf-8')
print(f'デモHTMLを作成しました: {dest} ({dest.stat().st_size/1024:.0f} KB)')
