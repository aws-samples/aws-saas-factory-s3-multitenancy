#!/usr/bin/env bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

set -e
start_time="$(date -u +%s)"

# Set environment
AWS_REGION=$(aws configure list | grep region | awk '{print $2}')
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Deploying to AWS Region: $AWS_REGION"

NUM_LMD_LAYERS=2
NUM_LMD_FUNCTIONS=3
NUM_RESTAPI_ENDPOINTS=2

nosql_create_table(){
  aws dynamodb create-table \
  --cli-input-json file://s3_manager/src/config/db/$1 \
  | jq -r '.TableDescription.TableName'
}

lambda_create_layer(){
  aws lambda publish-layer-version \
  --layer-name $1 \
  --zip-file fileb://$2 \
  | jq -r '.LayerVersionArn'
}

iam_create_role(){
  aws iam create-role \
  --role-name $1 \
  --assume-role-policy file://$2 \
  | jq -r '.Role.Arn'
}

iam_create_role_policy(){
  aws iam put-role-policy \
  --role-name $1 \
  --policy-name $1-policy \
  --policy-document file://$2
}

lambda_create_function(){
  aws lambda create-function \
  --function-name $1 \
  --handler $2 \
  --runtime python3.7 \
  --role $3 \
  --environment Variables={$4} \
  --zip-file fileb://s3_manager/s3_manager_lambda.zip \
  | jq -r '.FunctionArn'
  > /dev/null

  aws lambda update-function-configuration \
  --function-name $1 \
  --layers $LMDLYR_TOKMGR_ARN $LMDLYR_PLYMGR_ARN \
  > /dev/null
}

apigtw_create_api(){
  aws apigateway create-rest-api \
  --name $1 \
  | jq -r '.id'
}

apigtw_create_parent_res(){
  aws apigateway get-resources \
  --rest-api-id $1 \
  | jq -r '.items[0].id'
}

apigtw_create_resource() {
  aws apigateway create-resource \
  --rest-api-id $1 \
  --parent-id $2 \
  --path-part $3 | jq -r '.id'
}

apigtw_create_method() {
  aws apigateway put-method \
  --http-method $1 \
  --rest-api-id $2 \
  --resource-id $3 \
  --authorization-type "NONE" \
  > /dev/null

  aws apigateway put-integration \
  --http-method $1 \
  --rest-api-id $2 \
  --resource-id $3 \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$5/invocations \
  --credentials $6 \
  > /dev/null

  aws apigateway put-integration-response \
  --http-method $1 \
  --rest-api-id $2 \
  --resource-id $3 \
  --status-code $4 \
  --response-templates '{}' \
  > /dev/null
}

apigtw_create_deployment(){
  aws apigateway create-deployment \
  --rest-api-id $1 \
  --stage-name $2 \
  > /dev/null
}

NOSQL_DBTABLE_NAME=$(nosql_create_table dynamodb_create_tables.json)
echo "NoSQL Table (DynamoDB) created: $NOSQL_DBTABLE_NAME"

LMDLYR_TOKMGR_ARN=$(lambda_create_layer token_manager layers/token_manager/token_manager.zip)
echo "Deployed Lambda layer (1 of $NUM_LMD_LAYERS): $LMDLYR_TOKMGR_ARN"

LMDLYR_PLYMGR_ARN=$(lambda_create_layer policy_manager layers/policy_manager/policy_manager.zip)
echo "Deployed Lambda layer (2 of $NUM_LMD_LAYERS): $LMDLYR_PLYMGR_ARN"

# Create IAM role and attach policies for Lambda executions
IAMROLE_LMDEXEC_ARN=$(iam_create_role aws-saas-s3-lambdaexec s3_manager/src/config/iam/iam_lambda_role.json)
iam_create_role_policy aws-saas-s3-lambdaexec s3_manager/src/config/iam/iam_lambda_role_policy.json > /dev/null

# Create IAM role and attach policies for API Gateway invocations
IAMROLE_APIGTW_ARN=$(iam_create_role aws-saas-s3-apigtw s3_manager/src/config/iam/iam_apigtw_role.json)
iam_create_role_policy aws-saas-s3-apigtw s3_manager/src/config/iam/iam_apigtw_role_policy.json > /dev/null
echo "Deployed IAM roles for Lambda and API Gateway"

# Deploy Lambda functions
# TODO: Retry using do/while
sleep 10
LMDFUNC_TKNGET_ARN=$(lambda_create_function 'aws_saas_tkn_get' 'helper.get_token' $IAMROLE_LMDEXEC_ARN)
echo "Deployed Lambda function (1 of $NUM_LMD_FUNCTIONS): $LMDFUNC_TKNGET_ARN"

LMDFUNC_S3PUT_ARN=$(lambda_create_function 'aws_saas_s3_put' 'apis.put_object' $IAMROLE_LMDEXEC_ARN IAMROLE_LMDEXEC_ARN=$IAMROLE_LMDEXEC_ARN,AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID,NOSQL_DBTABLE_NAME=$NOSQL_DBTABLE_NAME)
echo "Deployed Lambda function (2 of $NUM_LMD_FUNCTIONS): $LMDFUNC_S3PUT_ARN"

LMDFUNC_S3GET_ARN=$(lambda_create_function 'aws_saas_s3_get' 'apis.get_object' $IAMROLE_LMDEXEC_ARN IAMROLE_LMDEXEC_ARN=$IAMROLE_LMDEXEC_ARN,AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID,NOSQL_DBTABLE_NAME=$NOSQL_DBTABLE_NAME)
echo "Deployed Lambda function (3 of $NUM_LMD_FUNCTIONS): $LMDFUNC_S3GET_ARN"

APIGTW_API_ID=$(apigtw_create_api aws-saas-s3)
APIGTW_PARENTRES_ID=$(apigtw_create_parent_res $APIGTW_API_ID)
APIGTW_BASE_URL=https://${APIGTW_API_ID}.execute-api.${AWS_REGION}.amazonaws.com/dev

APIGTW_TOKENRES_ID=$(apigtw_create_resource $APIGTW_API_ID $APIGTW_PARENTRES_ID 'token')
apigtw_create_method 'GET' $APIGTW_API_ID $APIGTW_TOKENRES_ID '200' $LMDFUNC_TKNGET_ARN $IAMROLE_APIGTW_ARN
echo "Deployed REST Endpoint (1 of $NUM_RESTAPI_ENDPOINTS):  $APIGTW_BASE_URL/token"

APIGTW_OBJRES_ID=$(apigtw_create_resource $APIGTW_API_ID $APIGTW_PARENTRES_ID 'object')
apigtw_create_method 'PUT' $APIGTW_API_ID $APIGTW_OBJRES_ID '201' $LMDFUNC_S3PUT_ARN $IAMROLE_APIGTW_ARN
apigtw_create_method 'GET' $APIGTW_API_ID $APIGTW_OBJRES_ID '200' $LMDFUNC_S3GET_ARN $IAMROLE_APIGTW_ARN
echo "Deployed REST Endpoint (2 of $NUM_RESTAPI_ENDPOINTS):  $APIGTW_BASE_URL/object"

apigtw_create_deployment $APIGTW_API_ID 'dev'
end_time="$(date -u +%s)"
elapsed="$(($end_time-$start_time))"
echo "Deployed dev environment (in $elapsed seconds)"

echo "API Gateway URL (copy the URL): " $APIGTW_BASE_URL
echo "APIGTW_BASE_URL: $APIGTW_BASE_URL" > output.txt
