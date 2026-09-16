# 02. コンテナの実行ユーザーと安全性

## この章の目的

Dockerfileでコンテナ内に一般ユーザーを作り、アプリをrootではなく `appuser` で動かせるようにします。後半では、非root化がなぜ必要なのかと、よくある誤解を整理します。

## 現在地

```text
01. 基本概念 → 【02. コンテナ実行】 → 03. データ・権限 → 04. 運用・デプロイ
```

## 完了条件

- [ ] `docker compose ps` で `web` と `db` が起動している
- [ ] `docker compose exec web id` で `uid=10001(appuser)` と表示される
- [ ] `http://localhost:8000/` で、Linuxユーザー `appuser` とDBユーザー `appdb_user` が返る

---

## 1. コンテナ起動時の流れ

[01](01_overview_and_roles.md)ではDjangoが利用者の権限を判定していました。ここでは、そのDjango自体がどのユーザーで動くのかを確認します。

### サンプルアプリの構成

この章の手順は、リポジトリに含まれるサンプルアプリをそのまま起動して確認します。コマンドはすべてリポジトリのルートで実行します。

```text
（リポジトリのルート）
├─ docker-compose.yml   … Step 3 で使うCompose定義
├─ .env.sample          … Step 2 でコピーして .env を作る
└─ source/              … webコンテナのビルドコンテキスト
    ├─ Dockerfile       … Step 1 のDockerfile
    ├─ .dockerignore    … .env をイメージへ入れないための除外設定
    ├─ requirements.txt … Django / gunicorn / psycopg
    ├─ manage.py
    └─ config/          … Djangoプロジェクト（settings, urls, views, wsgi）
```

サンプルアプリは `/` にアクセスすると、Djangoを動かしているLinuxユーザーと、PostgreSQLへ接続しているDBユーザーをJSONで返します。3層のうち「コンテナ内のLinuxユーザー」と、[03](03_data_and_permission_design.md#2-dbユーザーも別の権限である)で扱うDBユーザーを、1回のリクエストで確認するためです。

| 項目 | 検証したバージョン |
| --- | --- |
| Docker | Docker Desktop（Engine 29.7.2）、Compose v5.5.0、Windows 11 |
| webイメージ | `python:3.14-slim`（Python 3.14.7）、Django 5.2.8、gunicorn 23.0.0、psycopg 3.2.12 |
| dbイメージ | `postgres:17`（PostgreSQL 17.11） |

### Step 1: Dockerイメージを作る

#### やること

コンテナ内に一般ユーザーを作り、アプリの実行ユーザーをrootから切り替えます。

#### 実行

[`source/Dockerfile`](../source/Dockerfile)は次の内容です。ビルドはStep 3の `docker compose up --build` でまとめて行うため、ここでは中身を確認するだけで構いません。

```dockerfile
FROM python:3.14-slim

WORKDIR /app

# コンテナ内に一般ユーザーを作成する
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 \
               --gid appgroup \
               --create-home \
               --shell /usr/sbin/nologin \
               appuser

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/
RUN chown -R appuser:appgroup /app

# ここから先の実行ユーザーをappuserにする
USER appuser

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

#### なぜ行うのか

重要なのは次の行です。

```dockerfile
USER appuser
```

これにより、Djangoはrootではなく `appuser` として動きます。`USER` より前の `pip install` や `chown` はrootで実行されるため、インストールと所有者変更を先に済ませてから実行ユーザーを切り替えます。

#### ユーザー作成コマンドの読み方

`USER appuser` で切り替えるには、その前にユーザーが存在している必要があります。それを作るのが次の部分です。

```dockerfile
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 \
               --gid appgroup \
               --create-home \
               --shell /usr/sbin/nologin \
               appuser
```

見た目は複数行ですが、1つのシェルコマンドです。

- 行末の `\` は「次の行に続く」という意味で、改行を打ち消します
- `&&` は「左のコマンドが成功したら右を実行する」という意味です。グループ作成に失敗したらユーザー作成へ進まず、ビルドがそこで止まります

実際に実行されるのは、次の2つのコマンドです。

```bash
groupadd --gid 10001 appgroup
useradd --uid 10001 --gid appgroup --create-home --shell /usr/sbin/nologin appuser
```

| 部分 | 意味 | この指定にする理由 |
| --- | --- | --- |
| `groupadd --gid 10001 appgroup` | GID 10001の `appgroup` グループを作る | 次の `useradd` で所属先に指定するため、先に作る |
| `useradd ... appuser` | `appuser` ユーザーを作る | 最後の引数がユーザー名 |
| `--uid 10001` | UIDを10001に固定する | 番号を自動採番に任せると、ベースイメージによって変わりうる。固定しておけば、ホスト側やVolumeで `chown 10001:10001` のように数値で所有者を合わせられる（[03](03_data_and_permission_design.md)で使う）。1000はホストの一般ユーザーと重なりやすいため、離れた値にしている |
| `--gid appgroup` | 所属する主グループを `appgroup` にする | 上で作ったGID 10001のグループに揃える |
| `--create-home` | `/home/appuser` を作る | Debian系の `useradd` は既定でホームディレクトリを作らない。ライブラリによってはキャッシュや設定を `$HOME` へ書くため、存在しないとエラーになることがある |
| `--shell /usr/sbin/nologin` | ログインシェルを「ログイン不可」にする | 対話的なログインに使わないユーザーであることを明示する |

`--shell /usr/sbin/nologin` は、`docker compose exec web bash` まで禁止するものではありません。`exec` はログインシェルを経由せず、指定したコマンドを直接起動するためです。あくまで「ログイン用のユーザーではない」という表明であり、侵入対策の本体は `USER` による非root化のほうです。

### Step 2: 接続情報を `.env` に用意する

#### やること

DBのパスワードとDjangoの `SECRET_KEY` を、リポジトリのルートの `.env` へ書きます。

#### 実行

```bash
cp .env.sample .env
```

コピーした `.env` を開き、`<...>` の部分を自分で決めた値に置き換えます。

```dotenv
DB_PASSWORD=<任意の強いパスワード>
DJANGO_SECRET_KEY=<ランダムな長い文字列>
# 8000番が使用中の場合だけ変更する
WEB_PORT=8000
```

`DJANGO_SECRET_KEY` には、たとえば `python -c "import secrets; print(secrets.token_urlsafe(50))"` の出力を使います。

#### 期待結果

次のコマンドが何も表示せずに終われば、`.env` を読み込めています。

```bash
docker compose config --quiet
```

`.env` がない、または値が空の場合は、`required variable DB_PASSWORD is missing a value: .envにDB_PASSWORDを設定してください` のようなエラーで止まります。

#### なぜ行うのか

Compose定義は `${DB_PASSWORD}` と `${DJANGO_SECRET_KEY}` を参照します。PostgreSQL公式イメージは `POSTGRES_PASSWORD` について「空または未定義であってはならない」と明記しており、値がないとdbコンテナは初期化に失敗します。そこで `${DB_PASSWORD:?...}` と書き、値がなければ起動前にエラーで止めています。

`.env` の置き場所は、`docker-compose.yml` と同じリポジトリのルートです。Composeが変数の置換に使う `.env` はプロジェクトディレクトリのものだけで、`source/.env` に置いても読まれません。

秘密情報をリポジトリとイメージの両方から外すため、次の2つを設定済みです。

| ファイル | 設定 | 防いでいること |
| --- | --- | --- |
| [`.gitignore`](../.gitignore) | `.env` | パスワードをGitへコミットする |
| [`source/.dockerignore`](../source/.dockerignore) | `.env` | Dockerfileの `COPY . /app/` で、`.env` がイメージへ焼き込まれる |

### Step 3: Docker Composeで起動する

#### やること

DjangoとPostgreSQLのコンテナを起動します。

#### 実行

[`docker-compose.yml`](../docker-compose.yml)は次の内容です。

```yaml
services:
  web:
    build: ./source
    # この例はNginxを含まない最小構成のため、Djangoを直接公開している。
    # Nginxを前段に置く場合は ports をやめて expose に変え、
    # 外部へ公開するポートはNginxだけにする。
    ports:
      # ホスト側のポートは .env の WEB_PORT で変更できる（既定は8000）
      - "${WEB_PORT:-8000}:8000"
    environment:
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?.envにDJANGO_SECRET_KEYを設定してください}
      DB_HOST: db
      DB_NAME: appdb
      DB_USER: appdb_user
      DB_PASSWORD: ${DB_PASSWORD:?.envにDB_PASSWORDを設定してください}
    depends_on:
      db:
        # DBが接続を受け付けるまでwebの起動を待つ
        condition: service_healthy

  db:
    image: postgres:17
    # ports は書かない。DBをホストや外部へ公開しないため
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appdb_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:?.envにDB_PASSWORDを設定してください}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appdb_user -d appdb"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

```bash
docker compose up -d --build
docker compose ps
```

#### 期待結果

`docker compose ps` で、`db` が `(healthy)`、`web` が `Up` になっていれば成功です（検証時の出力。検証環境では8000番が使用中だったため `WEB_PORT=8001` で起動しており、既定の設定なら `PORTS` は `0.0.0.0:8000->8000/tcp` になります。`CREATED` や `STATUS` の時間は環境により異なります）。

```text
NAME                                    IMAGE                                 COMMAND                   SERVICE   CREATED          STATUS                    PORTS
docker_user_permission_hands_on-db-1    postgres:17                           "docker-entrypoint.s…"   db        18 seconds ago   Up 17 seconds (healthy)   5432/tcp
docker_user_permission_hands_on-web-1   docker_user_permission_hands_on-web   "gunicorn config.wsg…"   web       1 second ago     Up Less than a second     0.0.0.0:8001->8000/tcp, [::]:8001->8000/tcp
```

`db` の `PORTS` は `5432/tcp` だけで、`0.0.0.0:` が付いていません。コンテナ間では接続できますが、ホストや外部へは公開されていない状態です。

`docker compose up -d --build` を実行すると、Docker Composeは次の順序でイメージとコンテナを用意します。

```text
1. source/Dockerfile からDjangoイメージを作成
2. PostgreSQLコンテナをpostgresユーザー（UID 999）で起動
3. healthcheck（pg_isready）が成功するまで待つ
4. Djangoコンテナをappuser（UID 10001）で起動
5. gunicornがポート8000でリクエストを待ち受ける
6. 最初のリクエストで、DjangoがPostgreSQLへ接続する
```

Djangoは起動時にはDBへ接続せず、DBを使う処理が初めて呼ばれたときに接続します。そのため、起動しただけではDB接続を確認できません。接続はStep 5で確認します。

<details>
<summary>補足：起動時によくあるエラー</summary>

| エラー | 原因 | 対処 |
| --- | --- | --- |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | ホストの8000番を別のプロセスやコンテナが使っている | `.env` の `WEB_PORT` を `8001` などに変え、`docker compose up -d` を再実行する。以降の手順のURLもそのポートに読み替える |
| `required variable DB_PASSWORD is missing a value` | ルートに `.env` がない、または値が空 | Step 2をやり直す |
| dbが `unhealthy` のまま、ログに `password authentication failed` | 以前に別のパスワードでVolumeを初期化している。`POSTGRES_PASSWORD` はVolumeが空のときだけ使われる | 検証用のデータなら `docker compose down -v` でVolumeごと削除して再起動する |

</details>

#### なぜ行うのか

この例は[01の全体構成図](01_overview_and_roles.md#2-全体構成)からNginxを省いた最小構成です。非root化の確認に集中するためで、本番では図のとおりNginxを前段へ置き、Djangoのポートは外部へ公開しません。

### Step 4: 実行ユーザーを確認する

#### やること

Djangoが実際に `appuser` で動いているかを確認します。

#### 実行

```bash
docker compose exec web id
```

#### 期待結果

次のように表示されれば、`appuser` で動いています。

```text
uid=10001(appuser) gid=10001(appgroup) groups=10001(appgroup)
```

`exec` で起動したコマンドも、Dockerfileの `USER` で指定したユーザーで動きます。

プロセスも確認できます。

```bash
docker compose top web
```

`UID` 列が `10001` であれば、gunicornのmasterプロセス・workerプロセスともに `appuser` で動いています（検証時の出力。`PID` や時刻は環境により異なります）。

```text
SERVICE  #   UID    PID    PPID   C   STIME  TTY  TIME      CMD
web      1   10001  64861  64836  2   11:57  ?    00:00:00  /usr/local/bin/python3.14 /usr/local/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000
web      1   10001  64892  64861  5   11:57  ?    00:00:00  /usr/local/bin/python3.14 /usr/local/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

rootが必要な操作は拒否されます。

```bash
docker compose exec web touch /etc/test
```

```text
touch: cannot touch '/etc/test': Permission denied
```

WindowsのGit Bashでは、`/etc/test` のような `/` で始まる引数がWindowsのパス（例: `C:/Program Files/Git/etc/test`）へ自動変換され、`No such file or directory` になります。先頭に `MSYS_NO_PATHCONV=1` を付けて変換を止めてください。PowerShellやコマンドプロンプトでは、この変換は起きません。

```bash
MSYS_NO_PATHCONV=1 docker compose exec web touch /etc/test
```

### Step 5: アプリとDBの接続を確認する

#### やること

ブラウザまたは `curl` でアプリへアクセスし、LinuxユーザーとDBユーザーを確認します。あわせて、マイグレーションでDBへ書き込めることを確認します。

#### 実行

```bash
curl http://localhost:8000/
docker compose exec web python manage.py migrate
```

Windows PowerShell 5.1では `curl` が `Invoke-WebRequest` の別名になっているため、`curl.exe` と入力するか、ブラウザで開きます。

#### 期待結果

`curl` の結果は次のとおりです。

```json
{"linux_user": "appuser", "uid": 10001, "gid": 10001, "db_user": "appdb_user"}
```

`migrate` は、最後に次のような行を表示して終わります。

```text
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
```

#### なぜ行うのか

`linux_user` と `db_user` が別の値になっていることが、この確認の要点です。Djangoのプロセスは `appuser` というLinuxユーザーで動き、PostgreSQLへは `appdb_user` というDBユーザーで接続しています。同じDjangoでも、ファイルやプロセスの権限とDB内の権限は別々に判定されます（[03](03_data_and_permission_design.md#2-dbユーザーも別の権限である)）。

### Step 6: 後片付け

#### やること

コンテナを停止し、検証用のDBデータを削除します。

#### 実行

```bash
docker compose down -v
```

#### 期待結果

`web` ・ `db` のコンテナ、ネットワーク、`postgres_data` Volumeが `Removed` と表示されます。データを残して止めるだけなら、`-v` を付けずに `docker compose down` を実行します。

---

## 2. なぜrootで動かさないのか

rootは、Linux上でほぼすべての操作を行える強いユーザーです。

Djangoや依存ライブラリの脆弱性を悪用され、コンテナ内で任意のコマンドを実行されたとします。このときプロセスがrootで動いていると、攻撃者もrootとして操作できるため、被害が大きくなります。

```text
脆弱性が悪用される
  ↓
Djangoの実行権限を奪われる
  ↓
rootなら広い操作が可能
appuserなら許可された範囲に限定
```

非root化だけですべて安全になるわけではありませんが、被害範囲を狭める基本対策になります。これは「必要な権限だけを与える」という最小権限の原則です。

---

## 3. よくある誤解

### 誤解1「利用者ごとにコンテナを作る」

通常の業務アプリでは不要です。1つのDjangoアプリに複数のアプリケーションユーザーを登録し、Django側で権限を分けます。

利用者ごとに環境やデータを完全分離するSaaS設計では別の検討が必要ですが、最初からそこまで考える必要はありません。

### 誤解2「Dockerの `USER` でアプリ側の管理者・一般利用者を分ける」

Dockerfileの `USER` は、コンテナ内でプロセスを動かすLinuxユーザーです。画面を利用する管理者・一般利用者は、Django側で分けます。

### 誤解3「非rootにすれば安全である」

非root化は重要ですが、それだけでは不十分です。コンテナの設定としては、少なくとも次の対策を組み合わせます。

- パスワードや秘密情報をイメージへ埋め込まない
- DBを含め、不要なポートを公開しない
- コンテナへ不要なLinux Capabilityを与えない
- 可能ならファイルシステムを読み取り専用にする

コンテナの外側でも、イメージや依存パッケージの脆弱性スキャン、HTTPS、サーバー側での認証・認可の検証が欠かせません。

### 誤解4「コンテナのrootはホストのrootと別物である」

既定のDocker Engineでは、ユーザー名前空間の再マッピング（`userns-remap`）は有効になっていません。そのため、コンテナ内のrootはホストのUID 0と同一のユーザーです。実際に操作を制限しているのは、Capabilityの削減・seccomp・AppArmorといった仕組みであり、ユーザーIDの分離ではありません。

ユーザーIDまで分離するには、`userns-remap` を明示的に有効にするか、Rootlessモードを使います。いずれにしても「コンテナだからrootでも問題ない」とは考えません。

---

**次に読む**: [03. DBと永続データの権限設計](03_data_and_permission_design.md)

**関連**: 非rootにしたことでBind Mountの書き込みが失敗する場合は、[03の「Volumeで権限エラーが起きる仕組み」](03_data_and_permission_design.md#1-volumeで権限エラーが起きる仕組み)を参照してください。
