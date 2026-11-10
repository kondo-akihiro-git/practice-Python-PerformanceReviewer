# 人事評価システム（PerformanceReviewer）
 
## 概要
このアプリは、**Googleフォームで行っていた人事評価をWeb上で完結できる**社内向けWebアプリです。  
自己評価の入力から、面談担当者の取りまとめ、マネージャー・社長の評価、本人への結果公開までを1つのシステムで管理します。   
 
<br>
主な機能
- 評価項目ごとの自己評価入力（1〜5の評価点と補足コメント）
- 面談担当者による取りまとめ
- マネージャー・社長による評価（評価点とコメント）
- 本人への評価結果の公開
- 画面内の「あなたの番です」案内による、次にやることの表示
---
 
## 評価の流れ
1. `メンバー` : 自己評価を入力して提出
2. `面談担当者` : 自己評価を確認し、項目ごとに取りまとめて確定
3. `マネージャー` : 評価点とコメントを記入して確定
4. `社長` : マネージャーの評価を踏まえて評価を記入して確定
5. `面談担当者` : 評価内容を確認し、本人に公開
6. `メンバー` : ログインして最終結果を確認
 
---
 
## 主な画面
- `ログイン画面` : メールアドレスとパスワードでログインする画面
<kbd><img width="943" height="668" alt="Screenshot from 2026-11-10 10-34-14" src="https://github.com/user-attachments/assets/4b1ceb89-cd96-4c2c-bd3a-407e8617af42" /></kbd>
</br></br>



- `評価一覧画面` : 自分に関わる評価と、次にやることを確認する画面
<kbd><img width="942" height="552" alt="Screenshot from 2026-11-10 10-18-18" src="https://github.com/user-attachments/assets/bb1ff5c4-6a85-4d21-b551-1a6b33adb9ff" /></kbd>
</br></br>


- `自己評価入力画面` : メンバーが各項目の評価点とコメントを入力する画面
<kbd>
<img width="917" height="528" alt="Screenshot from 2026-11-10 10-39-05" src="https://github.com/user-attachments/assets/7355f8a5-a893-4e0a-a318-a96bc145371f" />
</kbd>
</br></br>


- `面談担当者の取りまとめ画面` : 自己評価の内容を確認し、所見を記入する画面
<kbd>
<img width="913" height="695" alt="Screenshot from 2026-11-10 10-42-45" src="https://github.com/user-attachments/assets/7248c3ce-5e03-46d7-bc19-a49e136f1dc0" />
</kbd>
</br></br>


- `マネージャーの評価画面` : 自己評価と取りまとめを確認し、評価を記入する画面
<kbd>
<img width="717" height="854" alt="Screenshot from 2026-11-10 10-45-01" src="https://github.com/user-attachments/assets/caf980c0-9a6c-407c-8f6b-c92d7aebf173" />
</kbd>
</br></br>

- `社長の評価画面` : 自己評価と取りまとめを確認し、評価を記入する画面
<kbd>
<img width="734" height="851" alt="Screenshot from 2026-11-10 10-50-47" src="https://github.com/user-attachments/assets/e1e71300-75dc-49c2-9cb4-d24b5492d7c2" />
</kbd>
</br></br>

- `評価結果の閲覧画面(数値評価)` : 公開された評価結果を確認する画面
<kbd>
<img width="752" height="877" alt="Screenshot from 2026-11-10 10-55-24" src="https://github.com/user-attachments/assets/fb7732d8-eb73-442d-a740-68f826d7d9eb" />
</kbd>
</br></br>

- `評価結果の閲覧画面(総括)` : 面談担当者、マネージャー、社長からの総括を確認する画面
<kbd>
<img width="729" height="832" alt="Screenshot from 2026-11-10 10-55-34" src="https://github.com/user-attachments/assets/e0341687-6dd1-42e6-ae70-cb116850aceb" />
</kbd>
</br></br>


- `管理画面` : 評価の作成とユーザー追加を行う画面
<kbd>
<img width="713" height="870" alt="Screenshot from 2026-11-10 10-56-29" src="https://github.com/user-attachments/assets/0381114f-9118-466b-9a78-968dfd1b1e0f" />
</kbd>
</br></br>

 
---
 
## フォルダ構成
- `backend/`
  - `api/`
    - `main.py` : FastAPIエントリポイント（API・静的ファイル配信）
  - `logic/`
    - `security.py` : パスワードハッシュ・ログイントークン
    - `workflow.py` : 役割・状態に応じた閲覧／編集の制御
    - `seed.py` : 評価項目・デモデータ
  - `model/`
    - `models.py` : データモデル定義
  - `tests/` : ワークフロー・権限のテスト
  - `requirements.txt` : 依存ライブラリ定義
- `frontend/`
  - `index.html` : 画面の土台
  - `app.js` : 画面ロジック
  - `style.css` : デザイン
- `docs/`
  - `requirements.md` : 要件
  - `setup.md` : 起動・運用手順
---
 
## 主な技術要件

### ローカル開発時
- Python : バックエンド実装
- FastAPI : APIフレームワーク
- SQLite / SQLAlchemy : データ保存
- HTML / CSS / JavaScript : フロントエンド実装（ビルド不要）
---
 
## 起動方法
起動手順・デモアカウント・テスト方法は [docs/setup.md](docs/setup.md) を参照してください。
