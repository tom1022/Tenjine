---
name: project-overview
description: Tenjine Flask研究データベースアプリの概要と技術スタック
metadata:
  type: project
---

Flask製の研究データベースWebアプリ。研究グループ・ファイル・タグ・ニュースの管理機能を持つ。

**Why:** 3年前から止まっていたプロジェクトを最新ライブラリに移行（2026-05-19実施）

**技術スタック（移行後）:**
- パッケージ管理: uv (pyproject.toml)
- Flask 3.1, SQLAlchemy 2.0, Flask-SQLAlchemy 3.1
- DB: SQLite (開発) / MySQL+PyMySQL (本番)
- セッション: Flask-Session 0.8 + Redis
- 認証: Flask-Login (LDAP3でAD認証も対応)
- HTMLサニタイズ: nh3 (bleachから移行)
- ULID: python-ulid (ulid-pyから移行)
- Flask-Principal は削除 → `admin_required` デコレータで代替

**設定ファイル:** `config/config.yml` (config/config.default.yml をコピーして使用)

**主な破壊的変更対応:**
- `@app.before_first_request` → `with app.app_context(): _init_db()`
- `declarative_base()` の import パス変更 (`sqlalchemy.ext.declarative` → `sqlalchemy.orm`)
- `sqlalchemy.case([(cond, val)])` → `case((cond, val), ...)` (リスト構文廃止)
- `USERS.query.get()` → `db.session.get(USERS, id)`
- `werkzeug.urls.url_parse` → `urllib.parse.urlsplit`
- `SESSION_USE_SIGNER`・`SQLALCHEMY_TRACK_MODIFICATIONS` 設定削除
- `JSON_AS_ASCII` → `app.json.ensure_ascii = False`

**How to apply:** パッケージ追加時は `uv add <package>` を使う。pip は使わない。
