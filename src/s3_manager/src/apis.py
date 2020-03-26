#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This script performs 2 operations:
Invokes a specific data partitioning approach based on a parameter
for either PUT or GET of objects
"""


import importlib
from http import HTTPStatus

import helper
import policy_manager as plcymgr
from partition_approaches import PartitionApproach


def put_object(event, context):
    """
    Uploads objects into s3 based on partition approach
        :param event:
        :param context:
        :return: 201 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        partition_approach = validate_request(event)
        if isinstance(partition_approach, dict) and \
                "invalid" in partition_approach:
            return helper.failure_response(partition_approach,
                                           HTTPStatus.BAD_REQUEST)

        rtm_module = importlib.import_module(partition_approach.value)
        rtm_method_context = getattr(rtm_module, "populate_context")
        req_header = rtm_method_context(event)

        if "missing_fields" in req_header:
            return helper.failure_response(req_header, HTTPStatus.UNAUTHORIZED)

        policy_template = helper.get_policy_template(partition_approach.value)
        assume_role_policy = plcymgr.get_policy(policy_template, req_header)
        sts_creds = helper.get_assumed_role_creds("s3", assume_role_policy)

        rtm_method_put = getattr(rtm_module, "put_object")
        return rtm_method_put(sts_creds, req_header)

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def get_object(event, context):
    """
    Retrieve objects from s3 based on partition approach
        :param event:
        :param context:
        :return: 200 - Success
                 400 - Bad Request, 401 - Unauthorized
                 500 - Error, 503 - Unavailable
    """
    try:
        partition_approach = validate_request(event)
        if isinstance(partition_approach, dict) and \
                "invalid" in partition_approach:
            return helper.failure_response(partition_approach, HTTPStatus.BAD_REQUEST)

        rtm_module = importlib.import_module(partition_approach.value)
        rtm_method_context = getattr(rtm_module, "populate_context")
        req_header = rtm_method_context(event)

        if "missing_fields" in req_header:
            return helper.failure_response(req_header, HTTPStatus.UNAUTHORIZED)

        policy_template = helper.get_policy_template(partition_approach.value)
        assume_role_policy = plcymgr.get_policy(policy_template, req_header)
        sts_creds = helper.get_assumed_role_creds("s3", assume_role_policy)

        rtm_method_get = getattr(rtm_module, "get_object")
        return rtm_method_get(sts_creds, req_header)

    except Exception as ex:
        return helper.failure_response(helper.format_exception(ex))


def validate_request(event):
    """
    Validate input parameter (enum)
        :param event:
    """
    query_string = event.get("queryStringParameters")
    if query_string:
        partition = query_string.get("partition")
        if partition and hasattr(PartitionApproach, partition):
            return PartitionApproach[partition]

    return {
        "invalid": "input for partition approach"
    }
