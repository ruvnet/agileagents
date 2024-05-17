import os
import subprocess
import json
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from services.aws_services import (
    get_aws_client,
    ensure_iam_role,
    create_ecr_repository,
    push_docker_image_to_ecr,
    create_or_update_lambda_function,
)

deploy_router = APIRouter()

class DeployRequest(BaseModel):
    repository_name: str
    image_tag: str
    python_script: str
    requirements: str
    function_name: str
    region: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_ids: Optional[List[str]] = None
    security_group_ids: Optional[List[str]] = None

class AdvancedDeployRequest(BaseModel):
    repository_name: str
    image_tag: str
    base_image: str
    build_commands: List[str]
    function_name: str
    region: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_ids: Optional[List[str]] = None
    security_group_ids: Optional[List[str]] = None

# Function to install AWS CLI
async def install_aws_cli():
    subprocess.run(["curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["unzip", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install"], check=True)
    subprocess.run(["rm", "-rf", "awscliv2.zip", "aws"], check=True)

# Deployment endpoint
@deploy_router.post("/deploy")
async def deploy(request: DeployRequest):
    try:
        # Ensure Docker is running
        docker_running = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if docker_running.returncode != 0:
            raise HTTPException(status_code=500, detail="Docker daemon is not running. Please start Docker daemon.")

        # Ensure AWS CLI is installed
        aws_cli_installed = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        if aws_cli_installed.returncode != 0:
            await install_aws_cli()

        # Create a virtual environment
        subprocess.run(["python3", "-m", "venv", "venv"], check=True)

        # Write the Python script to a file
        with open("app.py", "w") as f:
            f.write(request.python_script)

        # Write the requirements to a file
        with open("requirements.txt", "w") as f:
            f.write(request.requirements)

        # Install dependencies
        subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"], check=True)

        # Create a Dockerfile
        dockerfile_content = f"""
        FROM public.ecr.aws/lambda/python:3.8
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY app.py .
        CMD ["app.lambda_handler"]
        """
        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)

        # Build the Docker image
        image_name = f"{request.repository_name}:{request.image_tag}"
        build_result = subprocess.run(["docker", "build", "-t", image_name, "."], capture_output=True, text=True)
        if build_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Docker build failed: {build_result.stderr}")

        # Push the Docker image to ECR
        region = request.region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        image_uri = push_docker_image_to_ecr(request.repository_name, request.image_tag, region_name=region)

        # Ensure IAM role exists
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        role_arn = ensure_iam_role("lambda-execution-role", account_id)

        # Create or update the Lambda function
        vpc_config = {
            'SubnetIds': request.subnet_ids or [],
            'SecurityGroupIds': request.security_group_ids or []
        } if request.vpc_id else None
        response = create_or_update_lambda_function(
            request.function_name, image_uri, role_arn, region_name=region,
            memory_size=128, storage_size=512, vpc_config=vpc_config
        )

        return {"message": "Deployment successful", "image_uri": image_uri, "lambda_arn": response['FunctionArn']}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Advanced deployment endpoint
@deploy_router.post("/advanced-deploy")
async def advanced_deploy(request: AdvancedDeployRequest, files: List[UploadFile] = File(...)):
    try:
        # Ensure Docker is running
        docker_running = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if docker_running.returncode != 0:
            raise HTTPException(status_code=500, detail="Docker daemon is not running. Please start Docker daemon.")

        # Ensure AWS CLI is installed
        aws_cli_installed = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        if aws_cli_installed.returncode != 0:
            await install_aws_cli()

        # Save uploaded files
        for file in files:
            file_location = f"./{file.filename}"
            with open(file_location, "wb+") as file_object:
                file_object.write(file.file.read())

        # Create Dockerfile with advanced options
        dockerfile_content = f"""
        FROM {request.base_image}
        """
        for command in request.build_commands:
            dockerfile_content += f"\nRUN {command}"
        dockerfile_content += "\nCOPY . ."
        dockerfile_content += '\nCMD ["app.lambda_handler"]'

        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)

        # Build the Docker image
        image_name = f"{request.repository_name}:{request.image_tag}"
        build_result = subprocess.run(["docker", "build", "-t", image_name, "."], capture_output=True, text=True)
        if build_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Docker build failed: {build_result.stderr}")

        # Push the Docker image to ECR
        region = request.region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        image_uri = push_docker_image_to_ecr(request.repository_name, request.image_tag, region_name=region)

        # Ensure IAM role exists
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        role_arn = ensure_iam_role("lambda-execution-role", account_id)

        # Create or update the Lambda function
        vpc_config = {
            'SubnetIds': request.subnet_ids or [],
            'SecurityGroupIds': request.security_group_ids or []
        } if request.vpc_id else None
        response = create_or_update_lambda_function(
            request.function_name, image_uri, role_arn, region_name=region,
            memory_size=128, storage_size=512, vpc_config=vpc_config
        )

        return {"message": "Advanced deployment successful", "image_uri": image_uri, "lambda_arn": response['FunctionArn']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))