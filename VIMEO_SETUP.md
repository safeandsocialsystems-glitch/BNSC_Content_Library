# Vimeo自動同期：初期設定から公開まで

現在は未公開です。このフォルダーにはGitリポジトリ・公開先・APIトークンがありません。GitHub ActionsからVimeo公式APIを読み、正常に全件検証できた場合だけGitHub Pagesへ配信する構成です。トークン設定前のため実Vimeo接続は未検証です。

## 1. 同期・公開ルール

- 自分のアカウントの動画に **BNSC** タグ（この表記、前後空白なし）を付けることを、検索メタデータの一般公開承認として扱います。動画ごとの追加承認は不要です。
- 所有アカウントを `/me` と `VIMEO_USER_ID` で照合します。`/me/videos` を全ページ取得し、ID・所有者・タグだけを確認します。**詳細（タイトル・説明・再生時間・サムネイル）はBNSC付きの動画だけ**取得します。Vimeo全体を検索する公開タグAPIは使いません。
- 毎回BNSC動画の詳細を取得し直すため、タイトル・説明・他のタグの変更も反映します。差分キャッシュは使いません。
- IDは `vimeo-<動画ID>` です。同じ動画を複数登録しません。CSVでは `vimeo-` で始まるIDを使用しないでください。
- BNSCタグがなくなった動画・削除された動画は、正常な同期結果から除外します。最後の1件を外した場合も0件を配信します。
- 全ページ・件数・重複・所有者・権限・必須フィールドを検証し、詳細取得後に一覧とタグを再取得して変化がないことを確認します。不一致、タイムアウト、429、401、403、途中ページ失敗等は同期全体を失敗にします。
- 成功するまでローカルJSONを置換せず、Actionsでも同期失敗後の配信ステップは動きません。公開済みのPagesは前回の正常な状態を維持します。GitHub上に検索JSONをコミットする必要はありません。
- APIにはトランザクション単位のスナップショット機能がないため、同期直後の変更は次回の同期対象です。頻繁な編集中に検証が失敗した場合も次回再試行します。
- Vimeo以外は `contents.csv` の `draft / published / demo` 管理を継続します。CSVだけを変換しても前回のVimeo結果を消しません。

## 2. 公開される情報とされない情報

公開JSONには動画ID、タイトル、説明由来の概要、秒数・分数、作成日、その他のタグ、サムネイル画像URLを収録します。`BNSC` タグ自体は検索タグから外します。

**BNSCを付ける前に、タイトル・説明・他のタグ・サムネイルが一般公開可能か確認してください。** 会員限定本文、研究論文全文、個人情報、パスワードは説明に入れないでください。説明内のリンク・HTMLは取り除き、APIが返した限定公開ハッシュやトークンの混入も除去・検査します。任意の個人情報や秘密情報を自動判定する機能ではありません。

- 再生URL、埋め込みHTML、ダウンロード情報、プライバシーハッシュ、トークンをJSON・CSV・ログ・公開アーティファクトへ保存しません。
- 再生関連の値は同期プロセスのメモリ内で除外検査にだけ使用し、破棄します。視聴用データの永続保存や再生エンドポイントは作っていません。
- 公開データは許可した検索フィールドだけで構成します。サムネイルは `i.vimeocdn.com/video/` の画像URLのみを許可し、クエリを取り除きます。既存デザイン維持のためサムネイル表示は追加しません。
- Vimeoカードのリンク欄は「視聴機能は準備中」。Vimeo由来のレコードはURLが誤って入ってもフロント側でリンクを生成しません。
- カテゴリーは他のタグが既存4領域の名称と一致した場合に使用します。一致しない場合は既存互換の「脳機能・神経科学」です。複数一致の場合はタグ名のソート順で最初を採用します。

## 3. GitHubリポジトリを作る

1. GitHubへログインし、右上の「＋」→ **New repository** を選びます。
2. 例として `bnsc-content-library` という名前を付けます。
3. リポジトリの公開範囲を選びます。**公開リポジトリではCSVの下書きや履歴も閲覧可能**です。公開不可の管理情報を置く場合は非公開リポジトリを使い、非公開リポジトリでPagesを利用できる契約か確認してください。無料プランで公開リポジトリを使う場合は、CSVを含め全ファイルが公開可能である必要があります。
4. 作成したリポジトリへこのプロジェクトを登録します。GitHub Desktopの「Add Local Repository」→必要に応じて「Create a Repository」→「Publish repository」を利用できます。既にWebで作った空リポジトリを使う場合は、GitHub Desktopでそれをクローンし、クローン先へプロジェクトをコピーしてCommit / Pushします。
5. `.github/workflows/` と `.gitignore` を含めてください。トークンや `.env`、`dist/` は登録しません。デフォルトブランチ（通常 `main`）へPushします。
6. この段階では **BNSC_PUBLISH_ENABLED を true にしません**。リポジトリ作成やPushだけではPagesの配信処理は動きません。

## 4. Vimeo APIアプリとトークンを作る

1. **対象動画を所有するVimeoアカウント**でログインします。
2. [VimeoのAPIアプリ管理](https://developer.vimeo.com/apps)を開き、アプリを作成します。自分のアカウント用として設定します。
3. 作成したアプリの **Personal Access Tokens** で **Authenticated** を選びます。
4. 読み取り用の **public** と **private** を選び、トークンを生成します。upload、edit、delete、video_files等は不要です。限定公開メタデータへのアクセスにはprivateが必要です。
5. トークンは次のGitHub Secret欄に直接保存します。チャット、ソースコード、CSV、スクリーンショット、コミットに含めないでください。
6. 自分の**数値ユーザーID**を確認します。カスタムプロフィール名ではなく、Vimeoアカウントの数値IDです。分からない場合はVimeo APIの公式テスト画面で `GET /me` を実行し、`uri` が `/users/12345678` なら `12345678` を使用します。API応答全体やトークンを共有する必要はありません。

## 5. GitHub Secrets / Variables を登録する

リポジトリ → **Settings → Secrets and variables → Actions** を開きます。

1. **Secrets → New repository secret**：名前 `VIMEO_ACCESS_TOKEN`、値は生成したトークン。
2. **Variables → New repository variable**：名前 `VIMEO_USER_ID`、値は自分の数値ユーザーID。
3. 同じVariablesに `BNSC_PUBLISH_ENABLED` を作り、値を **false** にします。
4. Settings → Actions → GeneralでActionsが許可されていることを確認します。必要に応じGitHub公式の `actions/*` を許可します。トークンは同期ステップだけに渡し、Pagesへ送信しません。

## 6. まだ公開せず、実API接続をテストする

1. 公開可能なメタデータを持つ自分の動画1件に、Vimeo上で **BNSC** タグを追加します。
2. GitHubの **Actions → Test Vimeo connection (no publishing)** を開きます。
3. **Run workflow** を押し、デフォルトブランチで実行します。
4. 成功ログの「Vimeo全件検証成功: BNSC …件」を確認します。タイトル・URL・トークンはログへ出しません。このテストは検索JSONを書かず、Pagesへの公開も行いません。
5. 動画のタイトル・説明・他のタグを変更して再実行します。続いてBNSCタグを外して再実行し、BNSC件数が減ることを確認します。他の動画を変更していなければ、1件分減ります。
6. 公開したい動画にはBNSCタグを戻します。失敗した場合はログのHTTPコードや設定を確認します。401はトークン、403は権限、429はAPI利用制限を確認し、後で再実行してください。通信・応答不備の際も配信しません。
7. 実際のタイトル・説明の更新表示までの最終確認は、下記公開後、または安全なローカル同期後に実施します。件数だけのログでは文面が更新されたことまでは検証できません。

## 7. 公開内容を確認してから配信を有効にする

**ここからは一般公開される操作です。ユーザーが公開すると判断してから実施してください。**

1. 対象動画のタイトル・説明・タグ・サムネイルと、CSVのpublished行が一般公開可能か最終確認します。
2. リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。
3. 毎回の追加承認なしで運用する場合、`github-pages` Environmentに実行ごとの必須レビューを設定しないでください。最初の公開承認は、次の有効化操作で行います。
4. Variablesの **BNSC_PUBLISH_ENABLED を true に変更**します。**この時点から次の定期実行でも公開されます。** まだ公開したくない場合はfalseのままにします。
5. **Actions → Sync Vimeo and publish library → Run workflow** を実行します。
6. buildとdeployが成功したら、deployの **page_url** またはSettings → Pagesに表示されるURLを開きます。
7. 日本語キーワード検索、カテゴリー、あとで見る、スマートフォン幅を確認します。Vimeo動画には直接視聴リンクがないことも確認します。
8. テスト動画の題名・説明・タグを変更し、次の成功した同期後に画面を再読み込みして確認します。BNSCタグの削除も同様に確認します。

## 8. 自動運用と停止

- 毎時17分（UTC指定、JSTでも毎時17分）に同期を要求します。GitHub側の待ち時間により遅延・欠落する場合があり、厳密に60分以内の反映を保証するものではありません。必要時はRun workflowで再実行できます。
- 定期実行はデフォルトブランチ上のworkflowが対象です。公開リポジトリで長期間アクティビティがない場合、スケジュールが無効化されることがあります（GitHubの現行仕様では60日）。Actionsの実行履歴と失敗通知を確認してください。
- 同期失敗時には旧公開サイトを維持します。トークン失効時も既存動画は削除せず、新しいSecretを登録して再実行します。
- 同期を止めるには `BNSC_PUBLISH_ENABLED=false`。**既に公開されているサイトは消えません**。サイト自体を非公開にする場合はGitHub Pagesの公開停止操作が別途必要です。実行中のworkflowは必要に応じキャンセルしてください。
- CSV変更も次の成功した定期実行に含まれます。Vimeo障害中はCSVの変更も含めて配信を保留します。
- コード更新時は自動テスト後にデモの操作を確認してください。公開済みレコードのIDを変えると既存ブックマークと一致しなくなります。

## 9. ローカルで使うコマンド（任意）

GitHub Secretsだけで運用するならローカルトークン設定は不要です。

```sh
python3 -m unittest discover -s tests -v
python3 scripts/import_csv.py
python3 scripts/build_demo.py
```

実APIのローカル検証をする場合は、公開フォルダー外に読み取りを制限したトークンファイルを作り、そのパスを指定します。トークン文字列をコマンドに直接書かないでください。

```sh
VIMEO_USER_ID=自分の数値ID python3 scripts/sync_vimeo.py --token-file /公開フォルダー外の絶対パス/vimeo.token --check
```

`--check` を外すとローカルJSONを更新します。全件成功後にだけ `python3 scripts/build_release.py --synced` で配信用ファイルを生成できます。`dist/` は既存なら上書きしません。`dist/` の中身だけをHTTP配信してください。トークンファイルをプロジェクト内に置くことはスクリプトでも拒否します。

## 検証状況

- 自動テスト：29件成功。合成データでタグ承認、除外、変更反映、ID重複、途中失敗、権限不足、別アカウント、ページ欠落、秘密情報除外、CSV共存、最後の動画削除を検証。
- ブラウザ確認：デモによる日本語検索、カテゴリー絞り込み、保存・解除、390px幅、Vimeo由来カードのリンク非表示を確認。確認中のJavaScriptエラーログは0件。本番JSONは0件のままです。
- 実Vimeo API接続：**未実施**。トークン設定後に上記手順6で実施してください。
- GitHub上の定期実行・Pagesデプロイ：**未実施**。リポジトリ設定とユーザーの公開判断後に有効化します。

公式資料：[Vimeoトークン作成](https://help.vimeo.com/hc/en-us/articles/12427789081745-How-to-generate-a-personal-access-token)、[Vimeo API](https://developer.vimeo.com/api/reference/videos)、[GitHub Pagesワークフロー](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[定期実行の制約](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
