#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Helper module used by different partition approaches
"""
from __future__ import print_function

import json
import os
import sys
import traceback
from http import HTTPStatus
from os.path import dirname, join

import boto3
import botocore

import token_manager as tkmgr

X_TOKEN = "x-token"
X_TENANT_ID = "x-tenant-id"
X_USER_ID = "x-user-id"


def get_tenant_context(event):
    """
    Returns a JSON object with tenant context
        :param event:
    """""
    req_header = tkmgr.get_header(check_null_field(event, "headers", {}))

    if "token" not in req_header:
        return {
            "missing_fields": [X_TOKEN]
        }

    req_header = {
        "tenant_id": req_header["tenant_id"],
        "user_id": req_header["user_id"],
        "token": req_header["token"],
    }

    if event.get("body"):
        body_json = json.loads(event.get("body").replace("'", "\""))
        req_header["object_key"] = body_json.get("key", "")
        req_header["object_value"] = body_json.get("value", "")

    return req_header


def get_policy_template(file_name):
    """
    Returns AssumeRole policy template in JSON format
        :param file_name:
    """
    iam_policy_path = join(dirname(__file__),
                           "policies",
                           file_name + ".json")

    return json.loads(open(iam_policy_path).read())


def get_assumed_role_creds(service_name, assume_role_policy):
    """
    Returns a new assume role object with AccessID, SecretKey and SessionToken
        :param service_name:
        :param assume_role_policy:
    """

    sts_client = boto3.client("sts", region_name=os.environ["AWS_REGION"])
    assumed_role = sts_client.assume_role(
        RoleArn=os.environ["IAMROLE_LMDEXEC_ARN"],
        RoleSessionName="aws-saasfactory-s3",
        Policy=json.dumps(assume_role_policy),
    )
    credentials = assumed_role["Credentials"]

    return credentials


def get_boto3_client(service_name, sts_creds):
    """
    Returns a new client based on STS credentials
        :param service_name:
        :param sts_creds:
    """
    return boto3.client(
        service_name=service_name,
        aws_access_key_id=sts_creds["AccessKeyId"],
        aws_secret_access_key=sts_creds["SecretAccessKey"],
        aws_session_token=sts_creds["SessionToken"],
    )


def get_token(event, context):
    """
    Gets token based on tenant_id and event_id
        :param event:
        :param context:
    """
    try:
        header = check_null_field(event, "headers", [])
        missing_fields = [key for key in (X_TENANT_ID, X_USER_ID)
                          if key not in header]

        if len(missing_fields) > 0:
            return failure_response({"missing_fields": missing_fields},
                                    HTTPStatus.UNAUTHORIZED)

        req_header = tkmgr.get_header(header)
        return success_response({"token": req_header["token"]},
                                HTTPStatus.OK)

    except Exception as ex:
        return failure_response(str(format_exception(ex)))


def check_create_bucket(s3_client, bucket_name):
    """
    Check and create if the bucket does not exist
        :param s3_client:
        :param bucket_name:
    """
    try:
        s3_client.head_bucket(Bucket=bucket_name)

    except botocore.exceptions.ClientError as ex:
        err_code = int(ex.response["Error"]["Code"])
        if err_code == 404:
            current_region = s3_client.meta.region_name
            if current_region == "us-east-1":
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(Bucket=bucket_name,
                                        CreateBucketConfiguration={
                                            "LocationConstraint": current_region
                                        })

            s3_client.get_bucket_location(Bucket=bucket_name)
            s3_client.put_public_access_block(Bucket=bucket_name,
                                              PublicAccessBlockConfiguration={
                                                  "BlockPublicAcls": True,
                                                  "IgnorePublicAcls": True,
                                                  "BlockPublicPolicy": True,
                                                  "RestrictPublicBuckets": True
                                                })


def check_create_access_point(s3_ctl_client, bucket_name, account_id, acpt_name):
    """
    Check and create if the access_point does not exist
        :param s3_ctl_client:
        :param bucket_name:
        :param account_id:
        :param acpt_name:
    """
    try:
        s3_ctl_client.get_access_point(AccountId=account_id,
                                       Name=acpt_name)

    except botocore.exceptions.ClientError as ex:
        if ex.response["Error"]["Code"] == "NoSuchAccessPoint":
            s3_ctl_client.create_access_point(Bucket=bucket_name,
                                              AccountId=account_id,
                                              Name=acpt_name)


def check_null_field(event, field, default):
    """
    Check for field in event and assign a default value
        :param event:
        :param field:
        :param default:
    """
    return event.get(field) \
        if event.get(field) is not None and event[field] is not None \
        else default


def format_exception(ex):
    """
    Format exception using traceback
        :param ex:
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return repr(traceback.format_exception(exc_type,
                                           exc_value,
                                           exc_traceback))


def create_response(api_resp, http_status, message=None):
    """
    Creates a response with operation result and status code
        :param response:
        :param http_status:
        :param message=None:
    """
    response = {
        "statusCode": http_status.value,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Credentials": True
        },
        "body": json.dumps({
            "status": http_status.phrase,
            "result": api_resp
        })
    }

    if message:
        response["body"] = json.dumps({
            "message": message
        })

    return response


def success_response(api_resp, http_status=HTTPStatus.CREATED):
    """
    Returns a success response with CORS headers
        :param api_resp:
        :param http_status=HTTPStatus.CREATED.value:
    """
    return create_response(api_resp, http_status)


def failure_response(api_ex, http_status=HTTPStatus.INTERNAL_SERVER_ERROR):
    """
    Returns a failure response with CORS headers
        :param api_ex:
        :param http_status=HTTPStatus.INTERNAL_SERVER_ERROR.value:
    """
    return create_response(api_ex, http_status)


def failure_response_message(api_ex, message, http_status=HTTPStatus.INTERNAL_SERVER_ERROR):
    """
    Returns a failure response with message with CORS headers
        :param api_ex:
        :param http_status=HTTPStatus.INTERNAL_SERVER_ERROR.value:
    """
    return create_response(api_ex, http_status, message)
