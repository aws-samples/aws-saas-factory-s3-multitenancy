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


def verify_bucket_owner(s3_client, bucket_name):
    """
    Confirm that bucket_name is owned by this AWS account.

    S3 bucket names are globally unique across all AWS accounts, and the names this
    sample derives are predictable -- a static prefix plus the account id, and for the
    bucket-per-tenant approach the tenant id too. An attacker who can guess one can
    create it in their own account first and attach a bucket policy that lets this
    account read and write it. The application then stores tenant data in, or serves
    tenant data from, a bucket it does not own. This is the "shadow resource" class of
    attack, and nothing in a bucket name or in a successful API call distinguishes the
    two cases on its own -- ownership has to be asserted explicitly.

    ExpectedBucketOwner is that assertion. S3 compares it server-side against the
    bucket's real owner and fails the request with 403 when they differ, so it cannot
    be defeated by any policy the squatter attaches to their own bucket.

    get_bucket_location is used as the probe rather than head_bucket, which may look
    like the more natural choice. head_bucket requires s3:ListBucket, and every
    per-approach session policy under policies/ grants s3:ListBucket only with an
    s3:prefix condition, to keep a tenant's session confined to its own prefix.
    HeadBucket sends no prefix, so that condition can never match and the call is
    denied under tenant credentials. s3:GetBucketLocation is granted unconditionally
    in all five of those policies and in the Lambda execution role, so this probe
    works under either credential set without widening a single grant -- which
    matters, because widening s3:ListBucket is exactly the isolation boundary these
    policies exist to demonstrate.

        :param s3_client:
        :param bucket_name:
        :return: True if the bucket exists and this account owns it; False if the
            bucket does not exist at all.
        :raises RuntimeError: if the bucket exists but is owned by another account, or
            if ownership cannot be established for any other reason. Callers must not
            read from or write to the bucket in that case.
    """
    expected_owner = os.environ["AWS_ACCOUNT_ID"]

    try:
        s3_client.get_bucket_location(Bucket=bucket_name,
                                      ExpectedBucketOwner=expected_owner)
        return True

    except botocore.exceptions.ClientError as ex:
        err = ex.response.get("Error", {})
        err_code = str(err.get("Code", ""))
        status = ex.response.get("ResponseMetadata", {}).get("HTTPStatusCode")

        if status == 404 or err_code in ("404", "NoSuchBucket"):
            return False

        # Anything else -- a 403 because the bucket belongs to someone else, a
        # throttle, a permissions gap -- must deny. The previous version of this
        # check read int(ex.response["Error"]["Code"]) and acted only when it
        # equalled 404, so a 403 (precisely "this bucket exists and is not yours")
        # matched no branch, the exception was swallowed, and the caller carried on.
        # That int() was also a latent crash: a non-numeric code such as
        # AccessDenied raised ValueError from inside the handler.
        raise RuntimeError(
            "Refusing to use bucket '{0}': could not confirm it is owned by account "
            "{1} (S3 returned {2} {3}). If this bucket exists in another account the "
            "name has been taken, and this deployment must not read from or write to "
            "it.".format(bucket_name, expected_owner, status, err_code)) from ex


def check_create_bucket(s3_client, bucket_name):
    """
    Check the bucket exists AND is owned by this account, creating it if absent.

        :param s3_client:
        :param bucket_name:
        :raises RuntimeError: if the bucket exists but is not owned by this account, or
            if ownership cannot be established. Callers must not continue in that case.
    """
    expected_owner = os.environ["AWS_ACCOUNT_ID"]

    if verify_bucket_owner(s3_client, bucket_name):
        return

    # Only reached when the bucket genuinely does not exist.
    current_region = s3_client.meta.region_name
    try:
        if current_region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(Bucket=bucket_name,
                                    CreateBucketConfiguration={
                                        "LocationConstraint": current_region
                                    })
    except botocore.exceptions.ClientError as ex:
        err_code = str(ex.response.get("Error", {}).get("Code", ""))
        if err_code == "BucketAlreadyOwnedByYou":
            # A concurrent request in this account won the race. Harmless. Note that
            # in us-east-1 CreateBucket is idempotent for a bucket you already own
            # and returns 200 instead, so this branch is region-dependent.
            pass
        else:
            # BucketAlreadyExists means the globally unique name is held by another
            # account -- the shadow resource case, caught here if the name was taken
            # between the ownership check above and this call.
            raise RuntimeError(
                "Refusing to use bucket '{0}': create failed with {1}. If the name is "
                "held by another account this deployment must not write to "
                "it.".format(bucket_name, err_code)) from ex

    # ExpectedBucketOwner here too, so that losing the race above cannot result in
    # this account altering the public access configuration of a bucket it does not own.
    s3_client.put_public_access_block(Bucket=bucket_name,
                                      ExpectedBucketOwner=expected_owner,
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
        err_code = str(ex.response.get("Error", {}).get("Code", ""))
        if err_code != "NoSuchAccessPoint":
            # Anything other than a clean "it does not exist" must deny rather than
            # fall through. Previously any other error -- an access denial, a
            # throttle -- was swallowed and the caller carried on as though the
            # access point were present and ours.
            #
            # Unlike bucket names, access point names are NOT globally unique: an
            # access point is addressed by an ARN that contains the account id, so
            # another account cannot pre-create one here and cannot be reached by
            # this call. This is defence against a silent failure, not against the
            # cross-account name squatting that check_create_bucket guards.
            raise RuntimeError(
                "Refusing to use access point '{0}' on bucket '{1}': could not confirm "
                "it exists in account {2} (S3 returned {3}).".format(
                    acpt_name, bucket_name, account_id, err_code)) from ex

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
