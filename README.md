# LINE WORKS アシスタントボット
OpenAIのGPTをベースとした、LINE WORKS上で動くチャットボット。

## Description
OpenAIのChat APIを用いたGPTベースのチャットボット。

そして、Function Callingによって、予定登録に関連する要求があればカレンダーに自動的に登録してくれる、アシスタント機能を実装。

## Features
- チャット機能 (GPTによって回答を生成)
- カレンダー予定追加機能 (Function Calling利用)

## Architecture
AWSのサーバーレス構成。

- AWS Lambda
- AWS DynamoDB

## Get started
### Prepare
LINE WORKS APIを使うための認証情報を作成。

https://dev.worksmobile.com/jp/reference/authorization-sa?lang=ja

OpenAIのAPI keyを生成 (Azure OpenAI Serviceにも対応)

https://platform.openai.com/account/api-keys

### Workspace with Docker

```sh
docker compose up -d
docker compose exec workspace bash
```

### Set env

```sh
export OPENAI_API_KEY=sk-xxxxxxxxxxx
export OPENAI_ORGANIZATION_ID=org-xxxxxxxx
export OPENAI_MODEL=gpt-4

export LW_API_BOT_ID=1111111
export LW_API_BOT_SECRET=xxxxxxxxxx
export LW_API_CLIENT_ID=xxxxxxxx
export LW_API_CLIENT_SECRET=xxxxxx
export LW_API_SERVICE_ACCOUNT=xxxxx@xxxxxxx
export LW_API_PRIVATEKEY="-----BEGIN PRIVATE KEY-----
xxxxxxxxxxxxxxxxxxxxxxxx
-----END PRIVATE KEY-----"
```

### Deploy

```sh
sls deploy --param="author={author}"  --stage dev --aws-profile {profile}
```
