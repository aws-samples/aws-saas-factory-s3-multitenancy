#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module to return a IAM user policy by injecting tenant context into
the IAM Policy template
"""


def get_policy(policy_template, req_header):
    """
    Returns a IAM policy by populating the policy_template with token
    values and its resources
    """
    def inject_tenant_context(policy_template):
        if not isinstance(policy_template, (dict, list)):
            return policy_template.format_map(req_header)
        return {
            key:inject_tenant_context(val)
                if isinstance(val, dict)
                else list(map(inject_tenant_context, val))
                if isinstance(val, list)
                else val.format_map(req_header)
            for key, val in policy_template.items()
        }

    return inject_tenant_context(policy_template)
