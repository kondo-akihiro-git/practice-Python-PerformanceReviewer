# 人事評価システム（PerformanceReviewer）

## 概要
Googleフォームで行っている人事評価を、Webシステム上で行えるようにするアプリです。
自己評価 → 面談担当者の取りまとめ → 評価決定側（マネージャー・社長）の評価 → 面談担当者の確認・公開 → 本人が結果を閲覧、という現在の業務フローを維持します。
要件は [docs/requirements.md](docs/requirements.md) を参照してください。

## 評価の流れ
| 状態 | 担当 | 操作 |
|---|---|---|
| 自己評価 入力中 | メンバー | 8項目の評価点（1〜5）とコメントを入力して提出 |
| 面談担当者 取りまとめ待ち | 面談担当者 | 項目ごとの所見と総括を記入して確定 |
| マネージャー 評価待ち | マネージャー | 項目ごとの評価点とコメント、総括を記入して確定 |
| 社長 評価待ち | 社長 | マネージャーの評価を見たうえで、同様に記入して確定 |
| 面談担当者 確認・公開待ち | 面談担当者 | 両者の評価を確認して本人に公開 |
| 公開済み | メンバー | ログインして最終結果をいつでも確認 |

## 権限
- 役割は役職ではなく「評価ごと」に割り当てます（メンバー / 面談担当者 / マネージャー / 社長）。評価決定側はマネージャーと社長の2人で、別々にログインして順に評価します。
- 各段階の情報は、その段階に達するまで他の役割には見えません。社長はマネージャーの評価を見られますが、マネージャーは社長の評価を公開前には見られません。本人には公開されるまで所見・管理職の評価は見えません。
- 管理者は評価の作成とユーザー追加のみ行え、評価の中身は閲覧できません。

## 起動方法
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn api.main:app --port 8000
```
http://localhost:8000 を開きます（初回起動時にSQLiteのDBとデモデータが自動作成されます）。

### デモアカウント（ローカル確認専用・パスワードはすべて `password`）
| メール | 役割 |
|---|---|
| member1@example.com | メンバー（デモ評価の被評価者） |
| interviewer@example.com | 面談担当者 |
| manager@example.com | マネージャー |
| president@example.com | 社長 |
| admin@example.com | 管理者 |
| member2@example.com | メンバー（評価なし） |

本番では `SEED_DEMO=0` を設定し、`SECRET_KEY`（ログイントークンの署名鍵）を必ず環境変数で指定してください。

### テスト
```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q tests
```

## フォルダ構成
- `backend/`
  - `api/main.py` : FastAPIエントリポイント（API・静的ファイル配信）
  - `logic/security.py` : パスワードハッシュ・ログイントークン
  - `logic/workflow.py` : 役割・状態に応じた閲覧／編集の制御
  - `logic/seed.py` : 評価項目（Googleフォームと同一）・デモデータ
  - `model/models.py` : DBモデル（SQLite）
  - `tests/` : ワークフロー・権限のテスト
- `frontend/` : 画面（HTML/CSS/JavaScript、ビルド不要）
- `docs/requirements.md` : 要件
