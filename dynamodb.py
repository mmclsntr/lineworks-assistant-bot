import boto3
import botocore.exceptions
from boto3.dynamodb.conditions import Key
from typing import List, Optional
import json
from decimal import Decimal

def decimal_default_proc(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

####################################
# DynamoDB #
####################################
def get_item(table_name: str, key: dict) -> Optional[dict]:
    """
    Get item from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.get_item(
        Key=key
    )

    if "Item" in response:
        item = response['Item']
        item = json.loads(json.dumps(item, default=decimal_default_proc))
        return response['Item']
    else:
        return None


def get_items(table_name: str) -> list:
    """
    Get items from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.scan()

    if "Items" in response:
        data = response['Items']
        # レスポンスに LastEvaluatedKey が含まれなくなるまでループ処理を実行する
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            if "Items" in response:
                data.extend(response['Items'])
        return data
    else:
        return []



def query(table_name: str, key: dict, index_name: Optional[str] = None) -> list:
    """
    Query items from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    key_conditions = None
    for k, v in key.items():
        kc = Key(k).eq(v)
        if key_conditions is None:
            key_conditions = kc
        else:
            key_conditions &= kc

    _params = dict()
    _params["KeyConditionExpression"] = key_conditions
    if index_name is not None:
        _params["IndexName"] = index_name

    response = table.query(**_params)

    if "Items" in response:
        return response['Items']
    else:
        return []


def put_items(table_name: str, items: List[dict]):
    """
    Put items from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)

    with table.batch_writer() as writer:
        try:
            for item in items:
                _params = dict()
                _params["Item"] = json.loads(json.dumps(item), parse_float=Decimal)

                table.put_item(**_params)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # 条件NG
                pass
            else:
                raise


def put_item(table_name: str, item: dict, condition_expression: Optional[str] = None, expression_attribute_values: Optional[dict] = None):
    """
    Put item from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    _params = dict()
    _params["Item"] = json.loads(json.dumps(item), parse_float=Decimal)
    if condition_expression is not None:
        _params["ConditionExpression"] = condition_expression

    if expression_attribute_values is not None:
        _params["ExpressionAttributeValues"] = expression_attribute_values

    try:
        table.put_item(**_params)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # 条件NG
            pass
        else:
            raise


def delete_items(table_name: str, keys: List[dict]):
    """
    Delete items from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)

    with table.batch_writer() as writer:
        try:
            for key in keys:
                _params = dict()
                _params["Key"] = key
                table.delete_item(**_params)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # 条件NG
                pass
            else:
                raise


def delete_item(table_name: str, key: dict, condition_expression: Optional[str] = None, expression_attribute_values: Optional[dict] = None):
    """
    Delete item from DynamoDB table
    """
    table = boto3.resource("dynamodb").Table(table_name)
    _params = dict()
    _params["Key"] = key
    if condition_expression is not None:
        _params["ConditionExpression"] = condition_expression

    if expression_attribute_values is not None:
        _params["ExpressionAttributeValues"] = expression_attribute_values

    try:
        table.delete_item(**_params)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # 条件NG
            pass
        else:
            raise
