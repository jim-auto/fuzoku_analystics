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
| ランキング | 口コミ件数トップ、コスパ指標（口コミ÷料金） |

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

ローカルプレビュー:

```bash
python -m http.server 8080 --directory docs
# http://localhost:8080
```

## GitHub Pages 公開

1. リポジトリを GitHub に push
2. **Settings → Pages → Build and deployment → GitHub Actions**
3. `main` に push すると `.github/workflows/pages.yml` が実行されます

## 免責

- 本プロジェクトは City Heaven **非公式**です
- 画像・文章・口コミ本文は**転載しません**（数値集計のみ）
- 1 req/sec 以下の礼儀正しいアクセス間隔で取得します
- 18歳未満の閲覧禁止

## ライセンス

MIT（データの著作権は各権利者に帰属）
