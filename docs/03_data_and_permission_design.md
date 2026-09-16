# 03. DBと永続データの権限設計

## この章の目的

Bind Mountで`Permission denied`が起きる仕組みをUID/GIDの観点から理解し、原因を切り分けられるようにします。あわせて、PostgreSQLの接続ユーザーをLinuxユーザーと分けて設計する考え方を整理します。

## 現在地

```text
01. 基本概念 → 02. コンテナ実行 → 【03. データ・権限】 → 04. 運用・デプロイ
```

---

## 1. Volumeで権限エラーが起きる仕組み

[02](02_container_execution_and_security.md)でDjangoを`appuser`（UID 10001）へ切り替えました。その結果として最も多く発生するのが、ホストのディレクトリをコンテナへマウントしたときの権限エラーです。

### 1.1 問題が起きない例: 名前付きVolume

```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```

これはDockerが管理する名前付きVolumeです。PostgreSQL公式イメージ側の設定に沿って使用しやすいため、DBデータの保存にはこちらが基本です。

### 1.2 問題が起きやすい例: Bind Mount

```yaml
services:
  web:
    volumes:
      - ./uploads:/app/uploads
```

この設定では、ホストの`./uploads`とコンテナの`/app/uploads`が同じ保存場所として扱われます。

Linuxはユーザー名ではなく、実際にはUID/GIDという数値で所有者を判定します。

```text
ホスト側のuploads
  所有者UID: 1000

コンテナ側のappuser
  UID: 10001
```

この状態で`appuser`がファイルを書こうとすると、書き込み権限がなく、次のエラーになる場合があります。

```text
Permission denied
```

### 1.3 UID/GIDの基礎

| 項目 | 意味 | 重要ポイント |
| --- | --- | --- |
| UID | User ID の略。Linuxがユーザーを識別するための数値 | `root`は通常0、一般ユーザーは1000以上が多い |
| GID | Group ID の略。Linuxがグループを識別するための数値 | ファイルのアクセス権は「所有者」「グループ」「その他」で決まる |

- `appuser`が`uid=10001`のように見えるのは、Linuxがその数値で所有者を判定しているからです。
- ホストとコンテナで同じユーザー名でも、UID/GIDが違えば「別人」として扱われます。
- たとえば、`appuser`が`appgroup`に所属している場合、グループ権限でファイルにアクセスできることがあります。
- Bind Mountでは、ホスト側のUID/GIDとコンテナ側のUID/GIDが一致していないと、`Permission denied`になりやすくなります。

### 1.4 解決の考え方

主な選択肢は次のとおりです。

| 方法 | 向いている場面 | 注意点 |
| --- | --- | --- |
| 名前付きVolumeを使う | DBやDocker管理でよい永続データ | ホストから直接扱いにくい |
| UID/GIDを合わせる | 開発環境のソース・ファイル共有 | 環境ごとの差を管理する必要がある |
| 保存先の所有者・権限を調整する | 本番サーバーの固定構成 | 広すぎる権限を与えない |
| S3等へ保存する | 本番のアップロードファイル | 外部サービスの設定が必要 |

`chmod 777`で無理やり解決すると、そのファイルへ全ユーザーの読み書き・実行を許可することになります。原因を理解せずに使うべきではありません。

#### 実務でのポイント

- まずは「ユーザー名」ではなく「UID/GID」の値を確認する
- ホストとコンテナの所有者が合っていないと、Bind Mountで権限エラーが起きやすい
- 本番では設定を固定し、`chmod 777`よりも所有者と権限を整える方が安全

---

## 2. DBユーザーも別の権限である

PostgreSQLの`appdb_user`も、LinuxユーザーやDjangoユーザーとは別物です。

```text
Djangoのappuser
  ↓ Djangoプロセスを実行するLinuxユーザー
Djangoアプリ
  ↓ appdb_userとしてDBへ接続
PostgreSQL
```

| ユーザー | 管理対象 | 例 |
| --- | --- | --- |
| `appuser` | コンテナ内のファイル・プロセス | `/app`の読み取り、アプリの実行 |
| `appdb_user` | PostgreSQL内のデータ | テーブルのSELECT、INSERT、UPDATE |
| Djangoの管理者 | アプリ内の機能 | 管理画面、ユーザー管理 |

本番アプリをPostgreSQLの強力な管理ユーザーで接続させるのではなく、アプリに必要な範囲のDB権限だけを持つユーザーを用意します。

---

## まとめ

- ルート権限とアプリ利用者権限は別物である
- ストレージの権限はUID/GIDとファイル所有者の組み合わせで変わる
- PostgreSQLのDBユーザーもLinuxユーザーと別管理で設計する
- 最初は名前付きVolumeとDjangoの権限管理を優先するのが安全で簡単

---

**次に読む**: [04. 運用者権限とデプロイ設計](04_deployment_and_operations.md)

**関連**: 実際にBind Mountを設定する順序は、[04の「初心者向けの実装手順」Phase 4](04_deployment_and_operations.md#2-初心者向けの実装手順)にまとめています。
