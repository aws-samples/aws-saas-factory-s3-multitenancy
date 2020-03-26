#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Two operations supported:
PUT: Store object in bucket, metadata in NoSQL (DynamoDB)
GET: Retrieve object names from NoSQL (DynamoDB)
"""

import os
from http import HTTPStatus

import botocore

import constants
import helper

ACCOUNT_ID = os.environ["AWS_ACCOUNT_ID"]
IAMROLE_LMDEXEC_ARN = os.environ["IAMROLE_LMDEXEC_ARN"]
NOSQL_DBTABLE_NAME = os.environ["NOSQL_DBTABLE_NAME"]
NOSQL_DBTABLE_ARN = "arn:aws:dynamodb:{0}:{1}:table/{2}".format(os.environ["AWS_REGION"],
                                                                os.environ["AWS_ACCOUNT_ID"],
                                                                NOSQL_DBTABLE_NAME)


def put_object(sts_creds, req_header):
    """
    Store object in bucket, metadata in NoSQL (DynamoDB) with
    {tenant_id, user_id} as partition key
        :param sts_creds:
        :param req_header:
        :return: 201 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        s3_client = helper.get_boto3_client("s3", sts_creds)
        helper.check_create_bucket(s3_client, req_header["bucket_name"])
        api_put_resp = s3_client.put_object(Bucket=req_header["bucket_name"],
                                            Key=req_header["key_name"],
                                            Body=req_header["object_value"])

        if api_put_resp and \
                api_put_resp['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK.value:
            api_obj_md = s3_client.head_object(Bucket=req_header["bucket_name"],
                                               Key=req_header["key_name"])
            ddb_client = helper.get_boto3_client("dynamodb", sts_creds)
            api_put_md = add_metadata_db(ddb_client, req_header, api_obj_md)
            return helper.success_response(api_put_md)
        else:
            return helper.failure_response("Operation failed. Please retry.",
                                           HTTPStatus.SERVICE_UNAVAILABLE)

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def get_object(sts_creds, req_header):
    """
    Retrieve objects from NoSQL (DynamoDB) based on
    {tenant_id, user_id} as partition key
        :param sts_creds:
        :param req_header:
        :return: 200 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        ddb_client = helper.get_boto3_client("dynamodb", sts_creds)
        resp_metadata = read_metadata_db(ddb_client, req_header)
        user_objects = [obj['key_name']['S'].rsplit('/', 1)[-1]
                        for obj in resp_metadata['Items']]
        return helper.success_response(user_objects,
                                       HTTPStatus.OK)

    except botocore.exceptions.ClientError as ex:
        return helper.failure_response_message(helper.format_exception(ex),
                                               ex.response["Error"]["Code"])

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def add_metadata_db(ddb_client, req_header, obj_md):
    """
    Stores metadata in a NoSQL Database (DynamoDB)
    """
    object_url = "https://{0}.s3.amazonaws.com/{1}".format(req_header["bucket_name"],
                                                           req_header["key_name"],)
    item = {
        "id_concat": {"S": req_header["nosql_partition_key"]},
        "key_name": {"S": req_header["key_name"]},
        "tenant_id": {"S": req_header["tenant_id"]},
        "user_id": {"S": req_header["user_id"]},
        "bucket_name": {"S": req_header["bucket_name"]},
        "url": {"S": object_url},
        "last_modified": {"S": obj_md["LastModified"].isoformat()},
        "size": {"N": str(obj_md.get("ContentLength", 0))},
        "etag": {"S": obj_md.get("ETag", "")},
        "contenttype": {"S": obj_md.get("ContentType", "")}
    }

    return ddb_client.put_item(TableName=NOSQL_DBTABLE_NAME,
                               Item=item)


def read_metadata_db(ddb_client, req_header):
    """
    Returns metadata from NoSQL Database (DynamoDB)
    """
    return ddb_client.query(TableName=NOSQL_DBTABLE_NAME,
                            ProjectionExpression='key_name',
                            KeyConditionExpression='id_concat= :id_concat',
                            ExpressionAttributeValues={
                                ':id_concat': {
                                    'S': req_header["nosql_partition_key"]
                                }
                            })


def populate_context(event):
    """
    Adds derived fields to support operations
        :param req_header:
    """
    req_header = helper.get_tenant_context(event)
    if "missing_fields" in req_header:
        return req_header

    bucket_name = "{0}-{1}".format(constants.BUCKET_NAME_NSDB,
                                   os.environ["AWS_ACCOUNT_ID"])

    key_name = '{0}/{1}/{2}'.format(req_header['tenant_id'],
                                    req_header['user_id'],
                                    req_header.get("object_key"))

    req_header.update({
        "bucket_name": bucket_name,
        "bucket_arn": "arn:aws:s3:::{0}".format(bucket_name),
        "key_name": key_name,
        "nosql_table_arn": NOSQL_DBTABLE_ARN,
        "nosql_partition_key": "{0}^{1}".format(req_header['tenant_id'],
                                                req_header['user_id'])
    })
    return req_header
