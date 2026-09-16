# 03. DBと永続データの権限設計

## この章の目的

Bind Mountで `Permission denied` が起きる仕組みをUID/GIDの観点から理解し、原因を切り分けられるようにします。後半では、PostgreSQLの接続ユーザーをLinuxユーザーと分けて設計する考え方を整理します。

## 現在地

```text
01. 基本概念 → 02. コンテナ実行 → 【03. データ・権限】 → 04. 運用・デプロイ
```

---

## 1. Volumeで権限エラーが起きる仕組み

[02](02_container_execution_and_security.md)でDjangoを `appuser`（UID 10001）へ切り替えました。非root化した後によく起きるのが、ホストのディレクトリをコンテナへマウントしたときの権限エラーです。

### 1.1 名前付きVolumeでは問題が起きにくい

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

これはDockerが管理する名前付きVolumeです。空のVolumeを初めてマウントすると、Dockerはイメージ内の同じパスにあるファイルと所有者をVolumeへコピーします。PostgreSQL公式イメージのエントリポイントも、rootのままデータディレクトリの所有者を `postgres` へ揃えてから、`postgres` ユーザーに切り替えて起動します。ホスト側のUID/GIDが関わらないため、DBデータの保存にはこちらが基本です。

### 1.2 Bind Mountでは問題が起きやすい

```yaml
services:
  web:
    volumes:
      - ./uploads:/app/uploads
```

この設定では、Dockerがホストの `./uploads` をコンテナの `/app/uploads` へそのままつなぎます。どちらから書き込んでも同じディレクトリに反映され、ファイルの所有者もホスト側の値がそのまま見えます。

Linuxはユーザー名ではなく、実際にはUID/GIDという数値で所有者を判定します。

```text
ホスト側のuploads
  所有者UID: 1000

コンテナ側のappuser
  UID: 10001
```

この状態で `appuser` がファイルを書こうとすると、書き込み権限がなく、次のエラーになる場合があります。

```text
Permission denied
```

> Windows の Docker Desktop で、Windows 側のフォルダ（`C:\...`）をマウントした場合、このエラーは再現しません。
> Windows のファイルシステムにはLinuxの所有者・パーミッションがないため、コンテナからは所有者UID 0・`drwxrwxrwx` に見えます。「その他」に書き込み権限があるので、`appuser` でもファイルを作れてしまいます。
> 実際の権限エラーを確かめたい場合は、LinuxサーバーかWSLのLinux側のディレクトリ（`~/` 配下など）でリポジトリを動かしてください。

### 1.3 UID/GIDの基礎

| 項目 | 意味 | 重要ポイント |
| --- | --- | --- |
| UID | User ID の略。Linuxがユーザーを識別するための数値 | `root` は通常0、一般ユーザーは1000以上が多い |
| GID | Group ID の略。Linuxがグループを識別するための数値 | ファイルのアクセス権は「所有者」「グループ」「その他」で決まる |

`id` コマンドで `uid=10001(appuser)` のように数値が併記されるのは、Linuxがその数値で所有者を判定しているからです。ホストとコンテナで同じユーザー名でも、UID/GIDが違えば別人として扱われます。

Bind Mountでホスト側の所有者とコンテナ側のUIDが一致しないと、`Permission denied` になります。ただし、グループやその他の権限で書き込みが許可されていれば、UIDが違っても書き込めます。

### 1.4 解決の考え方

主な選択肢は次のとおりです。

| 方法 | 向いている場面 | 注意点 |
| --- | --- | --- |
| 名前付きVolumeを使う | DBやDocker管理でよい永続データ | ホストから直接扱いにくい |
| UID/GIDを合わせる | 開発環境のソース・ファイル共有 | 環境ごとの差を管理する必要がある |
| 保存先の所有者・権限を調整する | 本番サーバーの固定構成 | 広すぎる権限を与えない |
| S3等へ保存する | 本番のアップロードファイル | 外部サービスの設定が必要 |

`chmod 777` で無理やり解決すると、そのファイルへ全ユーザーの読み書き・実行を許可することになります。原因を理解せずに使うべきではありません。

---

## 2. DBユーザーも別の権限である

PostgreSQLの `appdb_user` も、LinuxユーザーやDjangoユーザーとは別物です。

```text
Djangoのappuser
  ↓ Djangoプロセスを実行するLinuxユーザー
Djangoアプリ
  ↓ appdb_userとしてDBへ接続
PostgreSQL
```

| ユーザー | 管理対象 | 例 |
| --- | --- | --- |
| `appuser` | コンテナ内のファイル・プロセス | `/app` の読み取り、アプリの実行 |
| `appdb_user` | PostgreSQL内のデータ | テーブルのSELECT、INSERT、UPDATE |
| Djangoの管理者 | アプリ内の機能 | 管理画面、ユーザー管理 |

本番アプリをPostgreSQLの強力な管理ユーザーで接続させるのではなく、アプリに必要な範囲のDB権限だけを持つユーザーを用意します。

---

**次に読む**: [04. 運用者権限とデプロイ設計](04_deployment_and_operations.md)

**関連**: 実際にBind Mountを設定する順序は、[04の「初級者向けの実装手順」Phase 4](04_deployment_and_operations.md#2-初級者向けの実装手順)にまとめています。
