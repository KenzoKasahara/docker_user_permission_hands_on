# Docker ユーザー・権限設計 入門ガイド

DockerでWebアプリを動かすときに登場する「ユーザー」と「権限」を、3つの層に分けて整理する資料です。

## Overview

- **目的**: アプリ利用者・コンテナ内のLinuxユーザー・ホストOSのユーザーを混同せずに設計できるようになる
- **扱う内容**: 3層の切り分け、コンテナの非root化、Bind MountのUID/GID問題、DBユーザーの分離、デプロイ権限
- **想定読者**: DockerでWebアプリを動かし始めた人。権限エラーの原因を自分で切り分けられるようになりたい人
- **前提知識**: Docker Composeでコンテナを起動した経験、Linuxのファイル権限（所有者・グループ・その他）の基本
- **例に使う構成**: Django + PostgreSQL + Nginx（Docker Compose）。リポジトリの`source/`と`docker-compose.yml`に、Nginxを除いた最小構成のサンプルアプリがあります
- **必要環境**: Docker Engine（またはDocker Desktop）とDocker Compose v2以降。検証環境のバージョンは[02](02_container_execution_and_security.md#サンプルアプリの構成)を参照
- **所要時間**: 通読で約30分

## 全体の流れ

```text
01. 基本概念とユーザーの3層
      │  3層のうち「コンテナ内」を掘り下げる
      ▼
02. コンテナの実行ユーザーと安全性
      │  コンテナが読み書きするデータの権限へ
      ▼
03. DBと永続データの権限設計
      │  コンテナを操作する人の権限へ
      ▼
04. 運用者権限とデプロイ設計
```

## Chapters

| 章 | 達成すること |
| --- | --- |
| [01. 基本概念とユーザーの3層](01_overview_and_roles.md) | 3種類のユーザーを区別し、ログインから権限判定までの流れを説明できる |
| [02. コンテナの実行ユーザーと安全性](02_container_execution_and_security.md) | サンプルアプリを起動し、Djangoが`appuser`で動いていることを確認できる |
| [03. DBと永続データの権限設計](03_data_and_permission_design.md) | Bind Mountの権限エラーを切り分け、DBユーザーを分離して設計できる |
| [04. 運用者権限とデプロイ設計](04_deployment_and_operations.md) | Docker操作を許可する相手を判断し、実装を順序立てて進められる |

## 目的別の入口

| 知りたいこと | 読む章 |
| --- | --- |
| そもそも「ユーザー」が何種類あるのか整理したい | [01](01_overview_and_roles.md) |
| コンテナを非rootで動かす方法を知りたい | [02](02_container_execution_and_security.md) |
| `Permission denied` の原因を切り分けたい | [03](03_data_and_permission_design.md) |
| 誰にDockerの操作を許可すべきか決めたい | [04](04_deployment_and_operations.md) |

各トピックの説明は1つの章にまとめてあります。他章から参照する場合はリンクのみを置いているため、同じ説明を読み返す必要はありません。
