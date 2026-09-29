# 開発

Python 3.14、uv 0.12.19、Node.js 24、packageManagerで固定したpnpmを使用。

```sh
uv sync --locked --group dev
pnpm install --frozen-lockfile --ignore-scripts
uv run ruff format .
uv run ruff check .
uv run pytest
pnpm format
pnpm lint
pnpm format:check
```

PythonはRuff、その他の対応ファイルはoxfmtで整形。
JavaScriptはESLint。依存の更新時はロックファイルも更新して上記チェックを通します。
pnpmのminimumReleaseAgeは7日。自動依存更新botは使用しません。
Actionsは確認したリリースの完全なコミットSHAで固定します。
