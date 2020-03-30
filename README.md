# Storing Multi-Tenant Data on Amazon S3
This repository describes approaches and hands-on exercises for storing Multi-tenant data using [Amazon Simple Storage Service](https://aws.amazon.com/s3/) (Amazon S3)

## Table of Contents
  - [Introduction](#introduction)
  - [Approaches](#approaches)
  - [High Level Architecture](#high-level-architecture)
  - [Example Flow](#example-flow)
  - [APIs](#list-of-apis)
  - [Tech Stack](#tech-stack)
  - [Prerequisites](#prerequisites-for-mac)
    - [mac](#mac)
    - [Windows](#windows)
  - [Installing](#installing)
  - [Hands-on](#hands-on)
    - [JWT Token](#jwt-token-pre-generated)
    - [JWT Token (Optional)](#jwt-token-generation-optional)
    - [Bucket](#put)
    - [Prefix](#put-1)
    - [Tag](#put-2)
    - [Access Point](#put-3)
    - [Database (NoSQL)](#put-4)
  - [Uninstalling](#uninstalling)
  - [Built With](#built-with)
  - [Versioning](#versioning)
  - [Authors](#authors)
  - [Code of Conduct](#code-of-conduct)
  - [Contributing](#contributing)
  - [License](#license)


## Introduction
Amazon S3 is storage for the internet. You can use Amazon S3 to store and retrieve any amount of data at any time, from anywhere on the web. Amazon S3 provides multiple approaches to manage data based on design needs for scalability, security, cost-efficiency and performance. Five approaches are illustrated below. Some of these approaches can be combined to suit requirements.
1. Bucket
2. Prefix
3. Tag
4. [Access Points](https://aws.amazon.com/s3/features/access-points/) (announced at re:Invent 2019)
5. Database metadata (NoSQL - DynamoDB)

## Approaches
- [Bucket](#bucket)
- [Prefix](#prefix)
- [Tag](#tag)
- [Access Point](#access-point)
- [Database (NoSQL)](#database-nosql)

 For the rest of hands-on, assume that `tenanta` tracks entertainment events and `tenantb` tracks sports events.

#### [Bucket](#bucket)
* Bucket per Tenant
* Prefix/folder per User
* User objects can have multiple prefix levels
![Bucket](images/bucket.gif)

#### [Prefix](#prefix)
* Common bucket for all tenants
* One folder/prefix per tenant
* One sub-folder/prefix for each user
* User objects can have multiple prefix levels

![Prefix](images/prefix.gif)

#### [Tag](#tag)
* Common bucket for all tenants
* Tag per Tenant and per User object
* Prefix/folder per User
* User objects can have multiple prefix levels
![Tag](images/tag.gif)

#### [Access Point](#access-point)
* Common bucket for all tenants
* Access point per Tenant
* Prefix/folder per User
* User objects can have multiple prefix levels
![Access Point](images/access_point.gif)

#### [Database (NoSQL)](#database-nosql)
* Common bucket for all tenants to store objects
* Database to store metadata.
* Prefix/folder per User
* User objects can have multiple prefix levels

![Database](images/db.gif)

## High Level Architecture

Multi-tenant data can be stored on S3 in multiple ways. In this hands-on, user's identity is used to manage the ownership of the objects. The identity is a JWT (JSON Web Token) comprised of user's identity/name and tenant's identity/user to which the user belongs. The JWT token is signed using a random text. In reality, [AWS Key Management Service](https://docs.aws.amazon.com/kms/index.html) can be used for stronger security. Another option for the JWT Token is using [Amazon Cognito](https://aws.amazon.com/cognito/) which yields a JWT Token (ID, Access and Refresh) signed by Amazon Cognito. REST APIs designed using OpenAPI (3.0) and developed in Python (3.7) are hosted in [Amazon API Gateway](https://aws.amazon.com/api-gateway/). User issues curl statements to the APIs that invoke Lambda functions. These functions internally invoke Lambda Layers that inspect the token and generate Identity-based user policies based on context embedded in JWT to create short-term security credentials (AWS Security Token Service (STS)). Subsequently, AssumeRole is issued to access AWS services to perform PUT and GET based operations using AWS SDK to manage data using Amazon S3 Buckets, Prefix, Tag, Access Points and DB-based metadata.

![HighLevelFlow](images/high_level_flow.png)

## Example Flow
![UML](images/uml.png)

## List of APIs
Here is a list of APIs implemented.
![APIs](images/openapi_spec.png)

## Tech Stack
- Python3.7 for REST APIs
- [AWS SDK for Python (Boto3)](https://aws.amazon.com/sdk-for-python/)
- AWS Services (API Gateway, Lambda functions, Lambda Layers, S3, DynamoDB)
- AWS CLI (for deployment)

## Prerequisites
### mac
- [x] [AWS CLI (Command Line Interface)](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html)
- [x] [AWS Credentials](https://docs.aws.amazon.com/sdk-for-php/v3/developer-guide/guide_credentials_profiles.html)
  - [ ] Ensure the user has "Administrator Access" policy attached
- [x] [curl](https://brewinstall.org/install-curl-on-mac-with-brew/)
- [x] [jq](https://brewinstall.org/install-jq-on-mac-with-brew/)
- [x] Install Git (Using Homebrew) `brew install git`

### Windows
- [x] [AWS CLI (Command Line Interface)](https://docs.aws.amazon.com/cli/latest/userguide/install-windows.html)
- [x] [AWS Credentials](https://docs.aws.amazon.com/powershell/latest/userguide/specifying-your-aws-credentials.html)
  - [ ] Ensure the user has "Administrator Access" policy attached
- [x] [curl](https://curl.haxx.se/windows/)
  - [ ] Download to folder "*[Program Files location]*\curl"
  - [ ] Add curl.exe to Windows PATH (Current Session)
      ```set PATH="%PATH%;<Program Files>\curl\bin\"```
- [x] [jq](https://github.com/stedolan/jq/releases/download/jq-1.6/jq-win64.exe)
  - [ ] Download to folder "*[Program Files location]*\jq"
  - [ ] Rename executable to *jq.exe*
  - [ ] Add jq.exe to Windows PATH (Current Session)
      ```set PATH="%PATH%;<Program Files>\jq"```
- [x] Install [Git](https://git-scm.com/download/win)
  - [ ] Note: On the "Select Components" screen, make sure to select "Windows Explorer Integration/Git Bash Here"

## Installing
For mac, open *Terminal*. <br/>
For Windows, open *Start -> Git -> Git Bash*
```
git clone https://github.com/aws-samples/aws-saas-factory-s3-multitenancy.git
cd aws-saas-factory-s3-multitenancy/src
bash setup.sh
```
This would take 1 to 2 minutes for setup.
![deploy](images/deploy.png)

Open the `output.txt` and copy the value of APIGTW_BASE_URL. On the terminal
```bash
APIGTW_BASE_URL=<copied value from above>
```

## Hands-on
### JWT Token Pre-generated
4 JWT Tokens for 2 Users each for 2 Tenants are pre-generated for the hands-on.  For the rest of hands-on, assume that `tenanta` tracks entertainment events and `tenantb` tracks sports events. <br/>

On the existing Terminal, set 4 JWT Tokens for each tenant user.
`tenanta/user1`
```bash
TNTAUSR1=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0ZW5hbnRfaWQiOiJ0ZW5hbnRhIiwidXNlcl9pZCI6InVzZXIxIn0.jAqNXRPDPR1U4VrLb6yubV8022JfzKoRpStriQhJRXA
```
`tenanta/user2`
```bash
TNTAUSR2=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0ZW5hbnRfaWQiOiJ0ZW5hbnRhIiwidXNlcl9pZCI6InVzZXIyIn0.E38IhJBzBodP3qDbTbITy8QKJrksBvMVDJqIgc2ttsE
```
`tenantb/user1`
```bash
TNTBUSR1=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0ZW5hbnRfaWQiOiJ0ZW5hbnRiIiwidXNlcl9pZCI6InVzZXIxIn0.4LtIpnzICGlxf8QrQxIyMAVHzzfNb4RnBldxVnFIBZY
```
`tenantb/user2`
```bash
TNTBUSR2=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0ZW5hbnRfaWQiOiJ0ZW5hbnRiIiwidXNlcl9pZCI6InVzZXIyIn0.1Z12kKN5sRTWfQF2iab0-DNEonjC5y4ziFrPIusaU7g
```
You can skip the Optional step.

### JWT Token generation (Optional)
If you want to generate new tokens, create 2 Tenants with 2 Users each. Create JWT tokens for TenantA users using `/get_token` endpoint. <br/>
`tenanta/user1`
```bash
TNTAUSR1=$(curl -X GET ${APIGTW_BASE_URL}/token \
        -H "Content-Type: application/json" \
        -H "x-tenant-id: tenanta" \
        -H "x-user-id: user1" \
        | jq -r '.result.token') && \
        echo $TNTAUSR1 && \
        echo "tenanta/user1: $TNTAUSR1" >> output.txt
```
`tenanta/user2`
```bash
TNTAUSR2=$(curl -X GET ${APIGTW_BASE_URL}/token \
        -H "Content-Type: application/json" \
        -H "x-tenant-id: tenanta" \
        -H "x-user-id: user2" \
        | jq -r '.result.token') && \
        echo $TNTAUSR2 && \
        echo "tenanta/user2: $TNTAUSR2" >> output.txt

```
Similar steps for TenantB users
`tenantb/user1`
```bash
TNTBUSR1=$(curl -X GET ${APIGTW_BASE_URL}/token \
        -H "Content-Type: application/json" \
        -H "x-tenant-id: tenantb" \
        -H "x-user-id: user1" \
        | jq -r '.result.token') && \
        echo $TNTBUSR1 && \
        echo "tenantb/user1: $TNTBUSR1" >> output.txt
```
`tenantb/user2`
```bash
TNTBUSR2=$(curl -X GET ${APIGTW_BASE_URL}/token \
        -H "Content-Type: application/json" \
        -H "x-tenant-id: tenantb" \
        -H "x-user-id: user2" \
        | jq -r '.result.token') && \
        echo $TNTBUSR2 && \
        echo "tenantb/user2: $TNTBUSR2" >> output.txt
```

These tokens are also copied into the [output.txt](./src/output.txt) file
***

### Bucket

- [PUT](#put)
- [GET](#get)

#### PUT
tenanta/user1 stores a text file `movies.txt` in a bucket `aws-saas-s3-tenanta-<account-id>` under a folder/prefix `user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
      -d '{"key": "movies.txt", "value": "Oscar, Golden Globe"}' \
| jq -r '.status'
```
You should receive a response with `Created` status.
> Created

Similarly tenanta/user2 stores a text file `music.txt` in a bucket `aws-saas-s3-tenanta-<account-id>` under a folder/prefix `user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
      -d '{"key": "music.txt", "value": "Grammys, MTV Music awards"}' \
| jq -r '.status'
```

tenantb/user1 stores a text file `basketball.txt` in a bucket `aws-saas-s3-tenantb-<account-id>` under a folder/prefix `user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
      -d '{"key": "basketball.txt", "value": "Larry O\" Brien NBA Championship Trophy"}' \
| jq -r '.status'
```
You should receive `Created` status.
> Created

Similarly user2 stores a text file `golf.txt` in a bucket `aws-saas-s3-tenantb-<account-id>` under a folder/prefix `user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
      -d '{"key": "golf.txt", "value": "The Wanamaker Trophy"}' \
| jq -r '.status'
```

#### GET
tenanta/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["movies.txt"]

tenanta/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["music.txt"]

tenantb/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["basketball.txt"]

tenantb/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=bucket \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["golf.txt"]

***
#### [Prefix](#handson-prefix)
- [PUT](#put-1)
- [GET](#get-1)

#### PUT
tenanta/user1 stores a text file `movies.txt` in a bucket `aws-saas-s3-prefix-<account-id>` under a folder/prefix `tenanta/user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
      -d '{"key": "movies.txt", "value": "Oscar, Golden Globe"}' \
| jq -r '.status'
```
You should receive a response with `Created` status.
> Created

Similarly tenanta/user2 stores a text file `music.txt` in a bucket `aws-saas-s3-prefix-<account-id>` under a folder/prefix `tenanta/user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
      -d '{"key": "music.txt", "value": "Grammys, MTV Music awards"}' \
| jq -r '.status'
```

tenantb/user1 stores a text file `basketball.txt` in a bucket `aws-saas-s3-prefix-<account-id>` under a folder/prefix `user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
      -d '{"key": "basketball.txt", "value": "Larry O\" Brien NBA Championship Trophy"}' \
| jq -r '.status'
```
You should receive `Created` status.
> Created

Similarly user2 stores a text file `golf.txt` in a bucket `aws-saas-s3-prefix-<account-id>` under a folder/prefix `user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
      -d '{"key": "golf.txt", "value": "The Wanamaker Trophy"}' \
| jq -r '.status'
```

#### GET
tenanta/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["movies.txt"]

tenanta/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["music.txt"]

tenantb/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["basketball.txt"]

tenantb/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=prefix \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["golf.txt"]

***

### [Tag](#handson-tag)
- [PUT](#put-2)
- [GET](#get-2)

#### PUT
tenanta/user1 stores a text file `movies.txt` in a bucket `aws-saas-s3-tag-<account-id>` under a folder/prefix `tenanta/user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
      -d '{"key": "movies.txt", "value": "Oscar, Golden Globe"}' \
| jq -r '.status'
```
You should receive a response with `Created` status.
> Created

Similarly tenanta/user2 stores a text file `music.txt` in a bucket `aws-saas-s3-tag-<account-id>` under a folder/prefix `tenanta/user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
      -d '{"key": "music.txt", "value": "Grammys, MTV Music awards"}' \
| jq -r '.status'
```

tenantb/user1 stores a text file `basketball.txt` in a bucket `aws-saas-s3-tag-<account-id>` under a folder/prefix `user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
      -d '{"key": "basketball.txt", "value": "Larry O\" Brien NBA Championship Trophy"}' \
| jq -r '.status'
```
You should receive `Created` status.
> Created

Similarly user2 stores a text file `golf.txt` in a bucket `aws-saas-s3-tag-<account-id>` under a folder/prefix `user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
      -d '{"key": "golf.txt", "value": "The Wanamaker Trophy"}' \
| jq -r '.status'
```

#### GET
tenanta/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["movies.txt"]

tenanta/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["music.txt"]

tenantb/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["basketball.txt"]

tenantb/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=tag \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["golf.txt"]

***

### [Access Point](#handson-accesspoint)
- [PUT](#put-3)
- [GET](#get-3)

#### PUT
tenanta/user1 stores a text file `movies.txt` in a bucket `aws-saas-s3-ap-<account-id>` under a folder/prefix `tenanta/user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
      -d '{"key": "movies.txt", "value": "Oscar, Golden Globe"}' \
| jq -r '.status'
```
You should receive a response with `Created` status.
> Created

Similarly tenanta/user2 stores a text file `music.txt` in a bucket `aws-saas-s3-ap-<account-id>` under a folder/prefix `tenanta/user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
      -d '{"key": "music.txt", "value": "Grammys, MTV Music awards"}' \
| jq -r '.status'
```

tenantb/user1 stores a text file `basketball.txt` in a bucket `aws-saas-s3-ap-<account-id>` under a folder/prefix `user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
      -d '{"key": "basketball.txt", "value": "Larry O\" Brien NBA Championship Trophy"}' \
| jq -r '.status'
```
You should receive `Created` status.
> Created

Similarly user2 stores a text file `golf.txt` in a bucket `aws-saas-s3-ap-<account-id>` under a folder/prefix `user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
      -d '{"key": "golf.txt", "value": "The Wanamaker Trophy"}' \
| jq -r '.status'
```

#### GET
tenanta/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["movies.txt"]

tenanta/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["music.txt"]

tenantb/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["basketball.txt"]

tenantb/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=access_point \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["golf.txt"]

***

### [Database (NoSQL)](#handson-databasenosql)
- [PUT](#put-4)
- [GET](#get-4)

#### PUT
tenanta/user1 stores a text file `movies.txt` in a bucket `aws-saas-s3-dbns-<account-id>` under a folder/prefix `tenanta/user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
      -d '{"key": "movies.txt", "value": "Oscar, Golden Globe"}' \
| jq -r '.status'
```
You should receive a response with `Created` status.
> Created

Similarly tenanta/user2 stores a text file `music.txt` in a bucket `aws-saas-s3-dbns-<account-id>` under a folder/prefix `tenanta/user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
      -d '{"key": "music.txt", "value": "Grammys, MTV Music awards"}' \
| jq -r '.status'
```

tenantb/user1 stores a text file `basketball.txt` in a bucket `aws-saas-s3-dbns-<account-id>` under a folder/prefix `user1`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
      -d '{"key": "basketball.txt", "value": "Larry O\" Brien NBA Championship Trophy"}' \
| jq -r '.status'
```
You should receive `Created` status.
> Created

Similarly user2 stores a text file `golf.txt` in a bucket `aws-saas-s3-dbns-<account-id>` under a folder/prefix `user2`.
```bash
curl  -X PUT ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
      -d '{"key": "golf.txt", "value": "The Wanamaker Trophy"}' \
| jq -r '.status'
```

#### GET
tenanta/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["movies.txt"]

tenanta/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTAUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["music.txt"]

tenantb/user1 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR1}" \
| jq -r '.result'
```
You should receive `OK` status with file names.
> ["basketball.txt"]

tenantb/user2 retrieves data stored using its token.
```bash
curl  -X GET ${APIGTW_BASE_URL}/object?partition=db_nosql \
      -H "Content-Type: application/json" \
      -H "x-token: ${TNTBUSR2}" \
| jq -r '.result'
```
You should receive `OK` status with array of file names.
> ["golf.txt"]

***

## Uninstalling
On a mac, open Terminal
```bash
bash teardown.sh
```
This would take about 1 to 2 minutes for cleanup.

### Manual Cleanup
Delete buckets starting with `aws-saas-*`

## Built With
* API Spec designed using [OpenAPI 3.0](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.0.md)

## Versioning
Initial Version (3/26/2020)

## Authors
Developed by [Sujit Khasnis](sujitkh@amazon.com)

## Code of Conduct
[View](CODE_OF_CONDUCT.md)

## Contributing
[View](./CONTRIBUTING.md)

## License
This library is licensed under the MIT-0 License. See the [LICENSE](./LICENSE) file.

