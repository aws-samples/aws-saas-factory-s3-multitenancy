#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

set -e

nosql_delete_table(){
  aws dynamodb delete-table \
  --table-name $1 \
  > /dev/null
}

lambda_delete_layer(){
  LAYER_VERSION=$(aws lambda list-layer-versions \
  --layer-name $1 \
  | jq -r '.LayerVersions[0].Version')

  aws lambda delete-layer-version \
  --layer-name $1 \
  --version-number $LAYER_VERSION \
  > /dev/null
}

iam_delete_role_policy(){
  aws iam delete-role-policy \
  --role-name $1 \
  --policy-name $1-policy \
  > /dev/null
}

iam_delete_role(){
  aws iam delete-role \
  --role-name $1 \
  > /dev/null
}

lambda_delete_function(){
  aws lambda delete-function \
  --function-name $1 \
  > /dev/null
}

apigtw_delete_api(){
  aws apigateway delete-rest-api \
  --rest-api-id $APIGTW_RES_ID \
  | jq -r '.id'
}

# Delete DB entities
nosql_delete_table aws-saas-s3-tenantmd
echo "Deleted tables"

# Delete REST API(s)
APIGTW_RES_ID=$(aws apigateway get-rest-apis --query 'items[?starts_with(name,`aws-saas-s3`)].id' | jq -r '.[]')
apigtw_delete_api $APIGTW_RES_ID
echo "Deleted REST API"

# Delete lambda functions
lambda_delete_function aws_saas_tkn_get
lambda_delete_function aws_saas_s3_put
lambda_delete_function aws_saas_s3_get
echo "Deleted Lambda functions"

# Delete lambda layers
lambda_delete_layer policy_manager
lambda_delete_layer token_manager
echo "Deleted Lambda layers"

# Delete IAM policies
iam_delete_role_policy aws-saas-s3-lambdaexec
iam_delete_role_policy aws-saas-s3-apigtw
echo "Deleted IAM role policies"

# Delete IAM roles
iam_delete_role aws-saas-s3-lambdaexec
iam_delete_role aws-saas-s3-apigtw
echo "Deleted IAM roles"

echo "Clean up completed"
