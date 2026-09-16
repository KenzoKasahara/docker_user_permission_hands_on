# docker_user_permission_handson

DockerでWebアプリを動かすときに登場する「ユーザー」と「権限」を、3つの層に分けて整理した入門ガイドです。本編ではDjango + PostgreSQLの最小構成を実際に動かして確認します。本番を想定してNginxを前段に置いた構成は、図と解説で紹介しています（サンプルアプリには含まれません）。

## ドキュメント

| ファイル | 内容 |
| --- | --- |
| [docs/README.md](docs/README.md) | 本編の目次 |

## サンプルアプリの起動

Docker ComposeとDockerがあれば、リポジトリのルートで次を実行して起動できます。手順の意味と期待結果は[02. コンテナの実行ユーザーと安全性](docs/02_container_execution_and_security.md)で説明しています。

```bash
cp .env.sample .env   # <...> の部分を自分の値に置き換える
docker compose up -d --build
curl http://localhost:8000/
# {"linux_user": "appuser", "uid": 10001, "gid": 10001, "db_user": "appdb_user"}
docker compose down -v
```

## 扱う内容

- Dockerfileの `USER` によるコンテナの非root化
- Bind MountでのUID/GID不一致と `Permission denied` の切り分け
- PostgreSQLの接続ユーザーをアプリと分けて設計する考え方
- `docker` グループとデプロイ権限の扱い

## License

[LICENSE](LICENSE) を参照してください。
