import os
import urllib.parse
import json
import openai

from datetime import datetime, timedelta, timezone

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver, Response, content_types, CORSConfig
from aws_lambda_powertools.event_handler.exceptions import (
    NotFoundError,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

import lineworks
import dynamodb


logger = Logger()

app = LambdaFunctionUrlResolver()


def get_access_token_from_db(table_name: str, domain_id: str) -> dict:
    _raw = dynamodb.get_item(table_name, {"domain_id": domain_id})
    return _raw


def put_access_token_from_db(table_name: str, domain_id: str, access_token: str, expired_at: int):
    data = {
        "domain_id": domain_id,
        "access_token": access_token,
        "expired_at": expired_at
    }
    dynamodb.put_item(table_name, data)


def delete_access_token_from_db(self, domain_id: str):
    dynamodb.delete_item(self.table_name, {"domain_id": domain_id})


def add_schedule(title, start_time, end_time, user_id, access_token) -> str:
    lineworks.create_event_to_user_default_calendar(title, start_time, end_time, user_id, access_token)
    return "予定をカレンダーへ登録しました。\n\nタイトル: {}\n開始日時: {}\n終了日時: {}".format(title, start_time, end_time)


def chatWithGPT(text: str, api_type: str, model: str, user_id, access_token) -> str:
    dt_now = datetime.now(timezone(timedelta(hours=9)))
    system_script = """現在の時刻は{}です。予定の登録を依頼されたらカレンダーに登録します。
    現在の時刻から依頼された時間が午前なのか午後なのかを判断して過去の時間に予定が入らないよう適切に処理してください。
    その他の返答は2000文字以内にしてください。""".format(dt_now)

    functions = [
        {
            "name": "add_schedule",
            "description": "予定をカレンダーへ登録する。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "予定のタイトル。これは空欄とすることはできない。"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "予定の開始日時。形式は \"YYYY-MM-DDTHH:mm:ss\" とする。これは空欄とすることはできない。既定値は現在の日時から1時間後の正時間とする。"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "予定の終了日時。形式は \"YYYY-MM-DDTHH:mm:ss\" とする。これは空欄とすることはできない。既定値はstart_timeから1時間後の日時とする。"
                    }
                },
                "required": ["title", "start_time", "end_time"]
            },
        }
    ]

    if api_type == "azure":
        response = openai.ChatCompletion.create(
            deployment_id=model,
            messages=[
                {"role": "system", "content": system_script},
                {"role": "user", "content": text},
            ],
            functions=functions,
            function_call="auto"
        )
    else:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_script},
                {"role": "user", "content": text},
            ],
            functions=functions,
            function_call="auto"
        )
    logger.info(response)
    res_msg = response.choices[0]["message"]

    reply_text = ""
    if res_msg.get("function_call"):
        function_name = res_msg["function_call"]["name"]
        function_args = json.loads(res_msg["function_call"]["arguments"])

        if function_name == "add_schedule":
            reply_text = add_schedule(function_args["title"],
                                      function_args["start_time"],
                                      function_args["end_time"],
                                      user_id,
                                      access_token)
    else:
        reply_text = res_msg["content"].strip()

    logger.info(reply_text)
    return reply_text


@app.post("/bot-callback")
def post_bot_callback():
    logger.info(app.current_event.body)
    logger.info(app.current_event.headers)

    body: dict = app.current_event.json_body
    body_raw = app.current_event.body
    headers = app.current_event.headers

    header_botid = headers["x-works-botid"]
    header_sig = headers["x-works-signature"]

    current_time = datetime.now().timestamp()

    access_token_table_name = os.environ.get("TABLE_ACCESS_TOKEN")
    if access_token_table_name is None:
        raise Exception("Please set TABLE_ACCESS_TOKEN env")

    bot_id = os.environ.get("LW_API_BOT_ID", "dummy")
    bot_secret = os.environ.get("LW_API_BOT_SECRET", "dummy")
    client_id = os.environ.get("LW_API_CLIENT_ID", "dummy")
    client_secret = os.environ.get("LW_API_CLIENT_SECRET", "dummy")
    service_account = os.environ.get("LW_API_SERVICE_ACCOUNT", "dummy")
    private_key = os.environ.get("LW_API_PRIVATEKEY", "dummy")

    oa_api_type = os.environ.get("OPENAI_API_TYPE", "dummy")
    oa_api_key = os.environ.get("OPENAI_API_KEY", "dummy")
    oa_model = os.environ.get("OPENAI_MODEL", "dummy")
    if oa_api_type == "azure":
        openai.api_type = oa_api_type
        oa_api_base = os.environ.get("OPENAI_API_BASE", "dummy")
        openai.api_base = oa_api_base
        oa_api_version = os.environ.get("OPENAI_API_VER", "dummy")
        openai.api_version = oa_api_version
    else:
        oa_org = os.environ.get("OPENAI_ORGANIZATION_ID")
        if oa_org is not None:
            openai.organization = oa_org

    openai.api_key = oa_api_key

    # Check bot id
    if header_botid != bot_id:
        raise Exception("Bot id is invalid.")

    # Verify request
    if bot_secret is not None and not lineworks.validate_request(body_raw.encode(), header_sig, bot_secret):
        # invalid request
        logger.warn("Invalid request")
        return

    domain_id = str(body["source"]["domainId"])
    user_id = body["source"]["userId"]

    content = body["content"]
    event_type = body["type"]

    # get text message
    if event_type != "message":
        logger.warn("Not message")
        return
    if content["type"] != "text":
        logger.warn("Not text message")
        return

    msg_text = content["text"]

    # Get access token
    access_token_data = get_access_token_from_db(access_token_table_name, domain_id)
    if access_token_data is None or access_token_data["expired_at"] < current_time:
        # Renew access token
        res = lineworks.get_access_token(client_id,
                                        client_secret,
                                        service_account,
                                        private_key,
                                        "bot.message calendar")
        # Put access token
        put_access_token_from_db(access_token_table_name,
                                 domain_id,
                                 res["access_token"],
                                 int(current_time + int(res["expires_in"])))

        access_token = res["access_token"]
    else:
        access_token = access_token_data["access_token"]

    # create response
    reply_text = chatWithGPT(msg_text, oa_api_type, oa_model, user_id, access_token)

    # create mssage content
    msg_content = {
        "content": {
            "type": "text",
            "text": reply_text
        }
    }

    logger.info(msg_content)
    # send message
    try:
        res = lineworks.send_message_to_user(msg_content,
                                             bot_id,
                                             user_id,
                                             access_token)
        return {}
    except Exception as e:
        logger.exception(e)
        raise


# You can continue to use other utilities just as before
@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info(event)
    return app.resolve(event, context)
