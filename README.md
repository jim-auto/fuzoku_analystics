# fuzoku_analystics

City Heaven（シティヘブンネット）の公開情報を**客目線**で再整理し、GitHub Pages で公開する分析サイトです。

## 対象エリア

- **東京** (`tokyo`)
- **名古屋（愛知）** (`aichi`)
- **大阪** (`osaka`)

## 提供情報

| カテゴリ | 内容 |
|---------|------|
| エリア比較 | 店舗数・在籍数・在籍/店舗比 |
| 業種分布 | ヘルス / ソープ / ホテヘル / デリヘル / エステ |
| 相場 | 最低コース料金の中央値・四分位 |
| ランキング | 口コミ TOP20 順位表、コスパ指標（口コミ÷料金） |
| 相場マップ | エリア×業種の最低コース中央値ヒートマップ |
| 爆サイ指数 | スレメタデータ、CH 突合、レス増加・ギャップ分析 |

## ローカル実行

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python run.py
```

生成物:

- `data/public/summary.json`
- `docs/data/summary.json`（GitHub Pages 用）
- `docs/data/trends.json`（時系列チャート用）
- `data/history/index.json`（週次スナップショット、差分計算用）

**差分・トレンド**: `run.py` を実行するたびに当日分を履歴に追加します。2回目以降で「前回比」や時系列グラフが表示されます。City Heaven の 403 回避のため、更新はローカル実行 → push を推奨します。

## 週次更新（推奨手順）

City Heaven は GitHub Actions の IP から 403 になることが多いため、**ローカルで取得 → push** が確実です。

1. 仮想環境を有効化し依存関係を最新化（初回のみ `pip install -r requirements.txt`）
2. `python run.py` を実行（3都市 × 業種の取得に **30〜60 分** 程度。1 req/sec 制限あり）
3. 生成物を確認
   - `docs/data/summary.json` — サイト表示用
   - `docs/data/trends.json` — 時系列チャート
   - `data/history/index.json` — CH スナップショット
   - `data/history/bakusai.json` — 爆サイスレ履歴（レス増加差分用）
4. `git add docs/data data/history` → commit → push
5. GitHub Pages（`pages.yml`）が `docs/` を自動デプロイ

**爆サイ**: スレ一覧メタデータのみ取得（最大5ページ/都市）。2回目以降で「レス増加トップ」が表示されます。

**CH×爆サイ突合**: `pipeline/shop_aliases.json` で表記ゆれを補正。上位50店をマッチプールに使用。

**Actions 週次ジョブ**: `.github/workflows/update-data.yml` が月曜 03:00 JST に試行します。403 時は `data-update` ラベルの Issue を自動作成します。

ローカルプレビュー:

```bash
python -m http.server 8080 --directory docs
# http://localhost:8080
```

## GitHub Pages 公開

1. リポジトリを GitHub に push
2. **Settings → Pages → Build and deployment → GitHub Actions**
3. `main` に push すると `.github/workflows/pages.yml` が `docs/` をデプロイします

**データ更新**: City Heaven は GitHub Actions の IP から 403 になることがあります。その場合はローカルで `python run.py` を実行して push してください。週次の自動更新は `.github/workflows/update-data.yml` が試行します（成功時のみ commit）。

## 免責

- 本プロジェクトは City Heaven **非公式**です
- 画像・文章・口コミ本文は**転載しません**（数値集計のみ）
- 1 req/sec 以下の礼儀正しいアクセス間隔で取得します
- 18歳未満の閲覧禁止

## ライセンス

MIT（データの著作権は各権利者に帰属）
