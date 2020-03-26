#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from enum import Enum


class PartitionApproach(Enum):
    """
    Enums for supported approach types for data partitioning
      :param Enum:
    """
    bucket = 'bucket'
    prefix = 'prefix'
    tag = 'tag'
    access_point = 'access_point'
    db_nosql = 'db_nosql'
