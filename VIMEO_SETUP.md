# Vimeo同期・GitHub Pages 設定手順

## 現在の構成

Cloudflare・ログイン・パスワード・会員確認・退会者管理は使用しません。
GitHub Actionsで毎時17分にVimeo公式APIへ接続し、所有アカウントの正確な `BNSC` タグ付き動画を取得します。全ページの検証成功後、検索情報と埋め込み再生URLを生成し、`dist/` だけをGitHub Pagesへ配信します。APIエラー・途中失敗・再生URL不備では配信せず、前回のサイトを維持します。正常な同期でBNSCタグが0件になった場合は、0件として反映します。

**今回はコード準備のみ。GitHubへのpush・Pagesの有効化・公開フラグの変更・配信は実施していません。`BNSC_PUBLISH_ENABLED=false` のまま、所有者の公開確認を待ちます。**

## 公開範囲

- アプリURLをCAMPFIREの会員限定投稿で案内しますが、アプリ自体は公開サイトです。URLを知っている非会員も検索・動画視聴できます。
- タイトル・説明・タグ・サムネイル・再生用URLは公開データになります。Vimeo限定公開動画の再生に必要な `h`（プライバシーハッシュ）も閲覧者が取得できます。これを秘密のまま静的サイトで再生することはできません。
- APIトークンはGitHub Actions Secretsに保存し、JSON・HTML・ログへ出力しません。会員メール一覧や会員データは不要です。
- 再生URLの共有や取得済みデータ・動画の複製を完全には防げません。BNSCタグ削除はアプリから除外する操作であり、既に取得されたURLを無効化するものではありません。
- Vimeoの埋め込みドメイン制限を利用する場合は、公開先の `safeandsocialsystems-glitch.github.io` を許可してください。これは会員認証の代わりにはなりません。Vimeo上で「自分のみ」やパスワード必須の動画はこの方式ではそのまま再生できません。
- CSVコンテンツのpublished/draft/demo管理は維持します。CAMPFIRE記事は従来どおり投稿先の会員制限に従います。

## 所有者が行う操作（公開承認後）

1. 変更したコードを既存の `safeandsocialsystems-glitch/BNSC_Content_Library` のデフォルトブランチへ反映します。APIトークンをファイルに書かないでください。
2. GitHubの **Settings → Secrets and variables → Actions → Secrets** で `VIMEO_ACCESS_TOKEN` を設定・確認します。Vimeo公式APIの自分のアカウント用トークンで、読み取り用 `public` と `private` が必要です。不要な書き込み・削除権限は付けません。
3. **Variables** の `VIMEO_USER_ID` に動画所有者の数値IDを設定します。`BNSC_PUBLISH_ENABLED` はまだ `false` にします。
4. Vimeoで対象動画に正確な `BNSC` タグを付け、埋め込み再生を許可します。公開サイトから再生できる公開範囲とドメイン設定を確認します。
5. **Actions → Test Vimeo connection (no publishing) → Run workflow** を実行します。所有者、権限、ページ送り、タグ件数、再生URLを検証します。ファイルや再生URLは保存・表示せず、公開もしません。
6. 公開することを最終確認してから **Settings → Pages → Source: GitHub Actions** を選び、`BNSC_PUBLISH_ENABLED` を `true` に変更します。ここから毎時ジョブも公開可能になります。確認前には行わないでください。
7. **Actions → Sync Vimeo and publish GitHub Pages (approval required) → Run workflow** を実行します。成功するとPagesのURLが表示されます。予定URLは `https://safeandsocialsystems-glitch.github.io/BNSC_Content_Library/` です。
8. URLを開き、実動画の再生・検索・絞り込み・あとで見るを確認します。問題がなければ、そのURLをCAMPFIREの会員限定投稿へ掲載します。

以降はタグの追加・削除とタイトル・説明の変更が次の正常同期で反映されます。GitHubの定期実行は遅延する場合があり、厳密な毎時実行の保証ではありません。公開リポジトリでは長期間更新がないと定期実行が停止する場合があるため、Actionsの状態を定期的に確認してください。

`BNSC_PUBLISH_ENABLED=false` は今後の配信を止めるフラグです。公開済みサイトを取り下げる場合はPages側で別途非公開化（Unpublish）します。フラグだけで過去の公開物は消えません。

旧 `MEMBER_SYNC_ENABLED`、Cloudflare/D1の変数・Secretsは新構成で使用しません。今回これらの外部設定は変更していません。

## ローカル確認・検証範囲

- `python3 -m unittest discover -s tests -v`
- `node --check app.js` と `node --test tests/static-player.test.mjs`
- `python3 scripts/build_demo.py` は架空データと明示した操作デモのみ生成します。本番データにはしません。
- `python3 scripts/sync_vimeo.py --check --include-playback --diagnose` はSecrets等を安全に設定した環境でのみ実行します。書き込みなし。
- `python3 scripts/sync_vimeo.py --include-playback` は視聴情報を含む公開用JSONを生成します。APIトークンをログに表示しないでください。生成された実データはGitにコミットする必要はありません。
- `python3 scripts/build_release.py --synced` はdistの生成だけで、公開しません。配信対象はdistのみです。
- `--include-playback` を省略した同期・診断は従来どおり検索メタデータだけを扱います。ローカル保存版等との互換性を維持します。

今回の実API接続・実動画再生・GitHub Actions/Pages配信は未実施です。合成データを使う自動テストとローカル画面確認は、実動画の再生成功を保証するものではありません。

## 公式資料

今回のローカル検証: Python 38件・JavaScript 3件の自動テストが成功。内蔵ブラウザで日本語検索2件、カテゴリー絞り込み2件、保存済み絞り込み1件を操作デモで確認し、JavaScriptエラーログはありませんでした。Chrome/Safariの個別実機確認と実動画再生は未実施です。

- [Vimeo: 限定公開埋め込みに必要なhパラメーター](https://help.vimeo.com/hc/en-us/articles/12426470858001-Embedded-player-displays-This-video-does-not-exist-message)
- [GitHub Pages: カスタムワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
