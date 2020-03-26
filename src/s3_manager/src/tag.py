#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This script performs 2 operations:
PUT operation on objects and tags them.
GET operation to retrieve objects based on tags.
"""

import os
from http import HTTPStatus

import botocore

import constants
import helper


def put_object(sts_creds, req_header):
    """
    Uploads objects into s3 bucket/prefix with {tenant_id/user_id}
    and tags with tenant_id and user_id
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
                                            Key='{0}/{1}'.format(req_header["prefix"],
                                                                 req_header["object_key"]),
                                            Body=req_header["object_value"])

        if api_put_resp and \
                api_put_resp['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK.value:
            api_tag_resp = s3_client.put_object_tagging(Bucket=req_header["bucket_name"],
                                                        Key='{0}/{1}'.format(req_header["prefix"],
                                                                             req_header["object_key"]),
                                                        Tagging=req_header["tag_set"])
            return helper.success_response(api_tag_resp)
        else:
            return helper.failure_response("Operation failed. Please retry.",
                                           HTTPStatus.SERVICE_UNAVAILABLE)

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def get_object(sts_creds, req_header):
    """
    Retrieve objects based on tags
        :param sts_creds:
        :param req_header:
        :return: 200 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        s3_client = helper.get_boto3_client("s3", sts_creds)
        helper.check_create_bucket(s3_client, req_header["bucket_name"])
        api_list_resp = s3_client.list_objects_v2(
            Bucket=req_header["bucket_name"],
            Prefix=req_header["prefix"],
        )

        if api_list_resp and api_list_resp['KeyCount'] > 0:
            user_objects = []
            for obj in api_list_resp['Contents']:
                try:
                    api_tag_resp = s3_client.get_object_tagging(Bucket=req_header["bucket_name"],
                                                                Key=obj['Key'])
                    if api_tag_resp and \
                            api_tag_resp["ResponseMetadata"]["HTTPStatusCode"] == HTTPStatus.OK.value:
                        user_objects.append(obj['Key'].rsplit('/', 1)[-1])

                except botocore.exceptions.ClientError as ex:
                    if ex.response["Error"]["Code"] == "AccessDenied":
                        # boto3 throws an exception, so do nothing
                        pass
                    else:
                        raise ex

            return helper.success_response(user_objects,
                                           HTTPStatus.OK)
        else:
            return helper.failure_response("Operation failed. Please retry.",
                                           HTTPStatus.SERVICE_UNAVAILABLE)

    except botocore.exceptions.ClientError as ex:
        return helper.failure_response_message(helper.format_exception(ex),
                                               ex.response["Error"]["Code"])

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def populate_context(event):
    """
    Adds derived fields to support operations
        :param req_header:
    """
    req_header = helper.get_tenant_context(event)
    if "missing_fields" in req_header:
        return req_header

    bucket_name = "{0}-{1}".format(constants.BUCKET_NAME_TAG,
                                   os.environ["AWS_ACCOUNT_ID"])

    req_header.update({
        "bucket_name": bucket_name,
        "bucket_arn": "arn:aws:s3:::{0}".format(bucket_name),
        "prefix": "{0}/{1}".format(req_header["tenant_id"],
                                   req_header["user_id"]),
        "tag_set": {
            'TagSet': [
                {'Key': 'tenant_id', 'Value': req_header["tenant_id"]},
                {'Key': 'user_id', 'Value': req_header["user_id"]}]
            }
    })
    return req_header
