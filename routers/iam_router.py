from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import boto3
from botocore.exceptions import ClientError
import json

router = APIRouter()

class IAMUserRequest(BaseModel):
    user_name: str

class IAMRoleRequest(BaseModel):
    role_name: str
    assume_role_policy_document: dict

class IAMPolicyRequest(BaseModel):
    policy_name: str
    policy_document: dict

class AssumeRoleRequest(BaseModel):
    role_arn: str
    role_session_name: str

class AccessKeyRequest(BaseModel):
    user_name: str

@router.post("/create-user")
async def create_user(request: IAMUserRequest):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.create_user(UserName=request.user_name)
        return response
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list-users")
async def list_users():
    try:
        iam_client = boto3.client('iam')
        paginator = iam_client.get_paginator('list_users')
        users = []
        for response in paginator.paginate():
            users.extend(response['Users'])
        return users
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-role")
async def create_role(request: IAMRoleRequest):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.create_role(
            RoleName=request.role_name,
            AssumeRolePolicyDocument=json.dumps(request.assume_role_policy_document)
        )
        return response
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/attach-policy-to-role")
async def attach_policy_to_role(role_name: str, policy_arn: str):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        return response
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-policy")
async def create_policy(request: IAMPolicyRequest):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.create_policy(
            PolicyName=request.policy_name,
            PolicyDocument=json.dumps(request.policy_document)
        )
        return response
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assume-role")
async def assume_role(request: AssumeRoleRequest):
    try:
        sts_client = boto3.client('sts')
        response = sts_client.assume_role(
            RoleArn=request.role_arn,
            RoleSessionName=request.role_session_name
        )
        return response
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-access-key")
async def create_access_key(request: AccessKeyRequest):
    try:
        iam_client = boto3.client('iam')
        response = iam_client.create_access_key(UserName=request.user_name)
        return response['AccessKey']
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
