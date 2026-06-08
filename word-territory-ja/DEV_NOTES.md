# Word Territory 日本語版 安定版ルール

この文書は React #130 再発防止のための開発メモです。

1. 絶対ルール

frontend/pages/index.js は単一ファイル構成を維持する。

許可する default export は次の形だけ。

export default function Home() {

禁止する形。

export default Home;
export default SomeVariable;
export default __WordTerritoryPageComponent;

2. 禁止事項

- index.js を next/dynamic ラッパーに変換しない
- frontend/components/WordTerritoryPageSource.js に分離しない
- ページコンポーネントを自動推定しない
- スコア方式でコンポーネント名を推定しない
- export default <変数> にしない
- repair / flatten / wrapper 系スクリプトで default export を書き換えない

3. コミット前・デプロイ前の確認

py -3 verify_stable.py

期待される結果。

結果: 安定

結果: 不安定 が出た場合は、コミット・デプロイしない。

4. 手動確認

PowerShell で確認する。

Select-String -Path frontend\pages\index.js -Pattern "export default"

期待される出力は次の1行のみ。

export default function Home() {

次も確認する。

Select-String -Path frontend\pages\index.js -Pattern "__WordTerritoryPageComponent|__WordTerritoryResolvedComponent|next/dynamic|WordTerritoryPageSource|Default export is not a React component"

期待される結果は、何も表示されないこと。

5. Render デプロイ後の確認

PC とスマホの両方で確認する。

- React #130 が出ない
- トップ画面が表示される
- 5x5 が開始できる
- 7x7 が開始できる
- Bot戦が開始できる
- 奪字ボタンが動く
- 回転侵略ボタンが動く

6. 掃除対象

デプロイ前に以下を残さない。

- frontend/pages/index.js.*.bak
- frontend/components/WordTerritoryPageSource.js
- frontend/_disabled_next_pages*
- frontend/pages/repair_*
- frontend/pages/apply_*
- frontend/pages/fix_*
- frontend/.next
- frontend/node_modules
