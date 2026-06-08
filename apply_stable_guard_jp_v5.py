# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys


DEV_NOTES = """# Word Territory 日本語版 安定版ルール

この文書は React #130 再発防止のための開発メモです。

## 絶対ルール

frontend/pages/index.js は単一ファイル構成を維持する。

許可する default export は次の形だけ。

export default function Home() {

禁止する形。

export default Home;
export default SomeVariable;
export default __WordTerritoryPageComponent;

## 禁止事項

- index.js を next/dynamic ラッパーに変換しない
- frontend/components/WordTerritoryPageSource.js に分離しない
- ページコンポーネントを自動推定しない
- スコア方式でコンポーネント名を推定しない
- export default <変数> にしない
- repair / flatten / wrapper 系スクリプトで default export を書き換えない

## コミット前・デプロイ前の確認

py -3 verify_stable.py

期待される結果。

結果: 安定

結果: 不安定 が出た場合は、コミット・デプロイしない。

## 手動確認

PowerShell で確認する。

Select-String -Path frontend\\pages\\index.js -Pattern "export default"

期待される出力は次の1行のみ。

export default function Home() {

次も確認する。

Select-String -Path frontend\\pages\\index.js -Pattern "__WordTerritoryPageComponent|__WordTerritoryResolvedComponent|next/dynamic|WordTerritoryPageSource|Default export is not a React component"

期待される結果は、何も表示されないこと。

## Render デプロイ後の確認

PC とスマホの両方で確認する。

- React #130 が出ない
- トップ画面が表示される
- 5x5 が開始できる
- 7x7 が開始できる
- Bot戦が開始できる
- 奪字ボタンが動く
- 回転侵略ボタンが動く

## 掃除対象

デプロイ前に以下を残さない。

- frontend/pages/index.js.*.bak
- frontend/components/WordTerritoryPageSource.js
- frontend/_disabled_next_pages*
- frontend/pages/repair_*
- frontend/pages/apply_*
- frontend/pages/fix_*
- frontend/.next
- frontend/node_modules
"""


VERIFY_STABLE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


fails = []
warns = []
oks = []


def ok(msg: str) -> None:
    oks.append(msg)
    print("  [成功] " + msg)


def warn(msg: str) -> None:
    warns.append(msg)
    print("  [警告] " + msg)


def fail(msg: str) -> None:
    fails.append(msg)
    print("  [失敗] " + msg)


def find_project(start: Path) -> Path:
    p = start.resolve()

    for cand in (p, p / "word-territory-ja"):
        if (cand / "frontend" / "pages" / "index.js").exists():
            return cand

    for parent in (p, *p.parents):
        if (parent / "frontend" / "pages" / "index.js").exists():
            return parent

        nested = parent / "word-territory-ja"
        if (nested / "frontend" / "pages" / "index.js").exists():
            return nested

    print("ERROR: frontend/pages/index.js が見つかりません")
    sys.exit(2)


def check_index(project: Path) -> None:
    index = project / "frontend" / "pages" / "index.js"

    if not index.exists():
        fail("frontend/pages/index.js が存在する")
        return

    ok("frontend/pages/index.js が存在する")

    text = index.read_text(encoding="utf-8", errors="replace")
    export_lines = re.findall(r"^export\s+default\b.*$", text, re.M)

    if len(export_lines) == 1 and re.search(r"^export\s+default\s+function\s+Home\s*\(", text, re.M):
        ok("default export が export default function Home() の1つだけ")
    else:
        shown = ", ".join(x.strip() for x in export_lines[:5]) or "なし"
        fail("default export は export default function Home() の1つだけである必要があります。検出数: " + str(len(export_lines)) + " / 内容: " + shown)

    banned = [
        "WordTerritoryPageSource",
        "__WordTerritoryPageComponent",
        "__WordTerritoryResolvedComponent",
        "Default export is not a React component",
        "next/dynamic",
        "dynamic(() => import",
    ]

    hits = [word for word in banned if word in text]

    if hits:
        fail("wrapper / flatten / 自動推定の残骸があります: " + ", ".join(hits))
    else:
        ok("wrapper / flatten / 自動推定の残骸がない")

    if re.search(r"export\s+default\s+(true|false)\s*;?", text):
        fail("boolean を default export している")
    else:
        ok("boolean を default export していない")


def show_features(project: Path) -> None:
    index = project / "frontend" / "pages" / "index.js"

    if not index.exists():
        return

    text = index.read_text(encoding="utf-8", errors="replace")

    features = {
        "奪字ボタン / daziMode": ("bdazi", "daziMode"),
        "回転侵略ボタン": ("brot",),
        "2段モバイル操作": ("brow-special",),
        "ドラッグ入力": ("extendPath",),
        "奪取リング表示": ("cap-ring",),
        "候補語チップ": ("best-word-chip",),
        "共有画像": ("shareResultImage",),
        "3ステップチュートリアル": ("intro-stepcards",),
    }

    print("  機能検出一覧（情報表示のみ）:")
    for name, tokens in features.items():
        present = any(token in text for token in tokens)
        print("      " + ("あり  " if present else "なし  ") + name)


def check_strays(project: Path) -> None:
    pages = project / "frontend" / "pages"
    components = project / "frontend" / "components"
    frontend = project / "frontend"

    allowed = {
        "index.js",
        "index.jsx",
        "_app.js",
        "_app.jsx",
        "_document.js",
        "_document.jsx",
        "404.js",
        "404.jsx",
    }

    stray = []

    if pages.exists():
        for p in pages.iterdir():
            if p.is_dir():
                if p.name != "api":
                    stray.append("frontend/pages/" + p.name + "/")
                continue

            if p.name in allowed:
                continue

            low = p.name.lower()

            if (
                ".bak" in low
                or "backup" in low
                or "wrapper" in low
                or "repair" in low
                or low.startswith("apply_")
                or low.startswith("fix_")
                or low.endswith(".txt")
                or low.endswith(".csv")
                or low.endswith(".json")
                or low.endswith(".md")
            ):
                stray.append("frontend/pages/" + p.name)
                continue

            if p.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
                stray.append("frontend/pages/" + p.name)
                continue

            other_text = p.read_text(encoding="utf-8", errors="replace")
            if "export default" not in other_text:
                stray.append("frontend/pages/" + p.name + " default export なし")

    split = components / "WordTerritoryPageSource.js"
    if split.exists():
        stray.append("frontend/components/WordTerritoryPageSource.js")

    for d in frontend.glob("_disabled_next_pages*"):
        if d.is_dir():
            stray.append("frontend/" + d.name + "/")

    if stray:
        fail("余計な backup / wrapper / repair ファイルがあります: " + ", ".join(stray))
    else:
        ok("余計な backup / wrapper / repair ファイルがない")


def check_backend(project: Path) -> None:
    backend = project / "backend"

    if not backend.exists():
        warn("backend ディレクトリが見つかりません")
        return

    result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(backend)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode == 0:
        ok("backend が compile できる")
    else:
        fail("backend compile に失敗")
        print(result.stderr[:800])


def finish() -> int:
    print("")
    print("=" * 60)

    if fails:
        print("結果: 不安定 — " + str(len(fails)) + " 件の問題")
        for item in fails:
            print("   - " + item)

        if warns:
            print("警告: " + str(len(warns)) + " 件")
            for item in warns:
                print("   note: " + item)

        return 1

    msg = "結果: 安定 — " + str(len(oks)) + " 件の確認に成功"
    if warns:
        msg += "、警告 " + str(len(warns)) + " 件"
    print(msg)

    for item in warns:
        print("   note: " + item)

    return 0


def main() -> int:
    project = find_project(Path.cwd())
    print("プロジェクト: " + str(project))
    print("")

    check_index(project)
    show_features(project)
    check_strays(project)
    check_backend(project)

    return finish()


if __name__ == "__main__":
    raise SystemExit(main())
'''


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    print("$ " + " ".join(str(x) for x in cmd))
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    print(result.stdout)
    return result.returncode, result.stdout


def remove_artifacts(project: Path) -> None:
    frontend = project / "frontend"
    pages = frontend / "pages"

    split = frontend / "components" / "WordTerritoryPageSource.js"
    if split.exists():
        split.unlink()
        print("削除: frontend/components/WordTerritoryPageSource.js")

    for d in frontend.glob("_disabled_next_pages*"):
        if d.is_dir():
            shutil.rmtree(d)
            print("削除: " + str(d.relative_to(project)))

    if pages.exists():
        for p in list(pages.rglob("*")):
            if not p.is_file():
                continue

            low = p.name.lower()

            if (
                ".bak" in low
                or "backup" in low
                or "wrapper" in low
                or low.startswith("repair_")
                or low.startswith("apply_")
                or low.startswith("fix_")
                or low.endswith(".txt")
                or low.endswith(".csv")
                or low.endswith(".json")
                or low.endswith(".md")
            ):
                p.unlink()
                print("削除: " + str(p.relative_to(project)))


def clean_outputs(project: Path) -> None:
    frontend = project / "frontend"

    for p in [frontend / ".next", frontend / "node_modules"]:
        if p.exists():
            shutil.rmtree(p)
            print("削除: " + str(p.relative_to(project)))

    self_script = project / "apply_stable_guard_jp_v5.py"
    if self_script.exists():
        self_script.unlink()


def main() -> int:
    project = Path(__file__).resolve().parent
    repo = project.parent

    print("プロジェクト: " + str(project))
    print("リポジトリ: " + str(repo))

    (project / "DEV_NOTES.md").write_text(DEV_NOTES, encoding="utf-8", newline="\n")
    (project / "verify_stable.py").write_text(VERIFY_STABLE, encoding="utf-8", newline="\n")

    print("作成: DEV_NOTES.md")
    print("作成: verify_stable.py")

    remove_artifacts(project)

    code, _ = run([sys.executable, "verify_stable.py"], project, timeout=180)
    if code != 0:
        raise SystemExit("verify_stable.py が失敗しました")

    frontend = project / "frontend"

    code, _ = run(["npm.cmd", "install"], frontend, timeout=300)
    if code != 0:
        raise SystemExit("npm install が失敗しました")

    code, build_output = run(["npm.cmd", "run", "build"], frontend, timeout=300)
    if code != 0:
        raise SystemExit("npm run build が失敗しました")

    if "Compiled successfully" not in build_output:
        raise SystemExit("Next build の成功表示を確認できませんでした")

    clean_outputs(project)

    code, status = run(["git", "status", "--short"], repo, timeout=60)
    if code != 0:
        raise SystemExit("git status が失敗しました")

    if not status.strip():
        print("コミット対象の変更はありません")
        return 0

    code, _ = run(["git", "add", "."], repo, timeout=60)
    if code != 0:
        raise SystemExit("git add が失敗しました")

    code, _ = run(["git", "commit", "-m", "Add Japanese stable frontend guard"], repo, timeout=120)
    if code != 0:
        raise SystemExit("git commit が失敗しました")

    code, _ = run(["git", "push", "origin", "main"], repo, timeout=180)
    if code != 0:
        raise SystemExit("git push が失敗しました")

    print("完了: 日本語版 stable guard を commit / push しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
