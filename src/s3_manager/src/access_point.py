#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This script performs 2 operations:
PUT operation by creating access points on the bucket.
GET operation to retrieve objects based on access-point.
"""

import os
from http import HTTPStatus

import botocore

import constants
import helper

ACCOUNT_ID = os.environ["AWS_ACCOUNT_ID"]
ACCESSPOINT_BASE_ARN = "arn:aws:s3:{0}:{1}:accesspoint".format(
    os.environ["AWS_REGION"],
    os.environ["AWS_ACCOUNT_ID"],
)


def put_object(sts_creds, req_header):
    """
    Uploads objects into s3 bucket/prefix with {tenant_id/user_id}
    along with access point per tenant {tenant_id}
        :param sts_creds:
        :param req_header:
        :return: 201 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        s3_client = helper.get_boto3_client("s3", sts_creds)
        helper.check_create_bucket(s3_client, req_header["bucket_name"])

        s3_ctl_client = helper.get_boto3_client("s3control", sts_creds)
        helper.check_create_access_point(s3_ctl_client, req_header["bucket_name"],
                                         ACCOUNT_ID, req_header["access_point_name"])

        api_put_resp = s3_client.put_object(Bucket=req_header["bucket_name"],
                                            Key='{0}/{1}'.format(req_header["prefix"],
                                                                 req_header["object_key"]),
                                            Body=req_header["object_value"])

        if api_put_resp and \
                api_put_resp['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK:
            return helper.success_response(api_put_resp)
        else:
            return helper.failure_response("Operation failed. Please retry.",
                                           HTTPStatus.SERVICE_UNAVAILABLE)

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def get_object(sts_creds, req_header):
    """
    Retrieve objects based on access points per tenant
        :param sts_creds:
        :param req_header:
        :return: 200 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        s3_client = helper.get_boto3_client("s3", sts_creds)
        s3_ctl_client = helper.get_boto3_client("s3control", sts_creds)
        s3_ctl_client.get_access_point(AccountId=ACCOUNT_ID,
                                       Name=req_header["access_point_name"])

        api_list_resp = s3_client.list_objects_v2(Bucket=req_header["access_point_arn"],
                                                  Prefix=req_header["prefix"])

        if api_list_resp and api_list_resp['KeyCount'] > 0:
            user_objects = [obj['Key'].rsplit('/', 1)[-1]
                            for obj in api_list_resp['Contents']]
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

    bucket_name = "{0}-{1}".format(constants.BUCKET_NAME_AP,
                                   os.environ["AWS_ACCOUNT_ID"])

    access_point_name = sanitize_ap_name(req_header['tenant_id'])

    req_header.update({
        "bucket_name": bucket_name,
        "bucket_arn": "arn:aws:s3:::{0}".format(bucket_name),
        "prefix": "{0}/{1}".format(req_header["tenant_id"],
                                   req_header["user_id"]),
        "access_point_name": access_point_name,
        "access_point_arn": "{0}/{1}".format(ACCESSPOINT_BASE_ARN,
                                             access_point_name)
    })
    return req_header


def sanitize_ap_name(input_name):
    """
    Returns access_point name that begins with a number or lowercase letter,
    3 to 50 chars long, no dash at begin or end, no underscores, uppercase
    letters, or periods
        :param input_name:
    """
    output_name = input_name.translate(
        str.maketrans({'_': '', '.': ''})
    )
    if output_name.startswith('-'):
        output_name = output_name[1:]
    if output_name.endswith('-'):
        output_name = output_name[0:-1]

    return output_name[0:50].lower()
