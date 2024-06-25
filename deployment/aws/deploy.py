import os
import subprocess
import json
import boto3
import logging

from fastapi import APIRouter, HTTPException, File, UploadFile
from models.base_models import DeployRequest, AdvancedDeployRequest
from services.aws_services import (
    get_aws_client,
    ensure_iam_role,
    create_ecr_repository,
    push_docker_image_to_ecr,
    create_or_update_lambda_function,
)
from typing import List, Optional  # Add this import
import uuid  # Add this import to generate unique filenames

deploy_router = APIRouter()

# Function to install AWS CLI
async def install_aws_cli():
    subprocess.run(["curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["unzip", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install"], check=True)
    subprocess.run(["rm", "-rf", "awscliv2.zip", "aws"], check=True)


# Define the logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# Function to validate AWS credentials using AWS CLI
def validate_aws_cli_credentials():
    try:
        result = subprocess.run(["aws", "sts", "get-caller-identity"], capture_output=True, text=True)
        if result.returncode != 0:
            raise HTTPException(status_code=401, detail="Invalid AWS CLI credentials")
        logger.info("AWS CLI credentials validated successfully.")
    except Exception as e:
        logger.error(f"AWS CLI credentials validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid AWS CLI credentials")

# Function to validate AWS credentials using boto3
def validate_boto3_credentials():
    try:
        boto3.client('sts').get_caller_identity()
        logger.info("boto3 credentials validated successfully.")
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"boto3 credentials validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid boto3 credentials")

# Endpoint to list security groups
@deploy_router.get("/list-security-groups")
async def list_security_groups(region: Optional[str] = None):
    try:
        # Validate AWS credentials
        validate_aws_cli_credentials()
        validate_boto3_credentials()

        # Set region
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")

        # Create EC2 client
        ec2_client = boto3.client('ec2', region_name=region)

        # Describe security groups
        response = ec2_client.describe_security_groups()
        security_groups = response['SecurityGroups']

        # Extract and return relevant information
        sg_info = [{"GroupId": sg['GroupId'], "GroupName": sg['GroupName'], "Description": sg['Description']} for sg in security_groups]
        return {"security_groups": sg_info}

    except Exception as e:
        logger.error(f"An error occurred while listing security groups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while listing security groups: {str(e)}")


#docker deploy endpoint 
@deploy_router.post("/dockerdeploy")
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

        # Step 1: Create a virtual environment
        subprocess.run(["python3", "-m", "venv", "venv"], check=True)

        # Step 2: Write the Python script to a temporary file
        temp_dir = "/tmp/deployment"
        os.makedirs(temp_dir, exist_ok=True)
        python_script_path = os.path.join(temp_dir, "app.py")
        with open(python_script_path, "w") as f:
            f.write(request.python_script)

        # Step 3: Write the requirements to a file
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        with open(requirements_path, "w") as f:
            f.write(request.requirements)

        # Step 4: Install dependencies
        subprocess.run(["venv/bin/pip", "install", "-r", requirements_path], check=True)

        # Step 5: Create a Dockerfile with the specified attributes
        dockerfile_content = f"""
        FROM {request.dockerfile_base_image}
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY app.py .
        CMD {request.dockerfile_cmd}
        """
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Step 6: Build the Docker image
        image_name = f"{request.repository_name}:{request.image_tag}"
        build_result = subprocess.run(["docker", "build", "-t", image_name, temp_dir], capture_output=True, text=True)

        if build_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Docker build failed: {build_result.stderr}")

        # Step 7: Authenticate Docker to AWS ECR
        region = request.region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
        
        login_password = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", region], 
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        login_result = subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", ecr_uri],
            input=login_password, text=True, capture_output=True
        )

        if login_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Docker login failed: {login_result.stderr}")

        # Step 8: Create ECR repository if it doesn't exist
        ecr_client = boto3.client('ecr', region_name=region)
        try:
            ecr_client.create_repository(repositoryName=request.repository_name)
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass

        # Step 9: Tag and push the Docker image to ECR
        subprocess.run(["docker", "tag", image_name, f"{ecr_uri}/{image_name}"], check=True)
        subprocess.run(["docker", "push", f"{ecr_uri}/{image_name}"], check=True)

        # Step 10: Create or update the Lambda function
        role_name = "lambda-execution-role"
        role_arn = ensure_iam_role(role_name, account_id)

        lambda_client = boto3.client('lambda', region_name=region)
        function_name = request.function_name
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Role=role_arn,
                Code={
                    'ImageUri': f"{ecr_uri}/{image_name}"
                },
                PackageType='Image',
                Publish=True,
                MemorySize=request.memory_size,
                EphemeralStorage={
                    'Size': request.storage_size
                },
                Environment={
                    'Variables': request.environment_variables or {}
                },
                VpcConfig={
                    'SubnetIds': request.subnet_ids or [],
                    'SecurityGroupIds': request.security_group_ids or []
                } if request.vpc_id else {}
            )
        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ImageUri=f"{ecr_uri}/{image_name}",
                Publish=True
            )
            if request.vpc_id:
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    MemorySize=request.memory_size,
                    EphemeralStorage={
                        'Size': request.storage_size
                    },
                    Environment={
                        'Variables': request.environment_variables or {}
                    },
                    VpcConfig={
                        'SubnetIds': request.subnet_ids or [],
                        'SecurityGroupIds': request.security_group_ids or []
                    }
                )

        return {"message": "Deployment successful", "image_uri": f"{ecr_uri}/{image_name}", "lambda_arn": response['FunctionArn']}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        # Step 1: Create a virtual environment
        subprocess.run(["python3", "-m", "venv", "venv"], check=True)

        # Step 2: Write the Python script to a temporary file
        temp_dir = "/tmp/deployment"
        os.makedirs(temp_dir, exist_ok=True)
        python_script_path = os.path.join(temp_dir, "app.py")
        with open(python_script_path, "w") as f:
            f.write(request.python_script)

        # Step 3: Write the requirements to a file
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        with open(requirements_path, "w") as f:
            f.write(request.requirements)

        # Step 4: Install dependencies
        subprocess.run(["venv/bin/pip", "install", "-r", requirements_path], check=True)

        # Step 5: Create a Dockerfile
        dockerfile_content = f"""
        FROM public.ecr.aws/lambda/python:3.9
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY app.py .
        CMD ["app.lambda_handler"]
        """
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Step 6: Build the Docker image
        image_name = f"{request.repository_name}:{request.image_tag}"
        build_result = subprocess.run(["docker", "build", "-t", image_name, temp_dir], capture_output=True, text=True)

        if build_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Docker build failed: {build_result.stderr}")

        # Step 7: Authenticate Docker to AWS ECR
        region = request.region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
        
        login_password = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", region], 
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        login_result = subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", ecr_uri],
            input=login_password, text=True, capture_output=True
        )

        if login_result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Docker login failed: {login_result.stderr}")

        # Step 8: Create ECR repository if it doesn't exist
        ecr_client = boto3.client('ecr', region_name=region)
        try:
            ecr_client.create_repository(repositoryName=request.repository_name)
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass

        # Step 9: Tag and push the Docker image to ECR
        subprocess.run(["docker", "tag", image_name, f"{ecr_uri}/{image_name}"], check=True)
        subprocess.run(["docker", "push", f"{ecr_uri}/{image_name}"], check=True)

        # Step 10: Create or update the Lambda function
        role_name = "lambda-execution-role"
        role_arn = ensure_iam_role(role_name, account_id)

        lambda_client = boto3.client('lambda', region_name=region)
        function_name = request.function_name
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Role=role_arn,
                Code={
                    'ImageUri': f"{ecr_uri}/{image_name}"
                },
                PackageType='Image',
                Publish=True,
                MemorySize=request.memory_size,
                EphemeralStorage={
                    'Size': request.storage_size
                },
                Environment={
                    'Variables': request.environment_variables or {}
                },
                VpcConfig={
                    'SubnetIds': request.subnet_ids or [],
                    'SecurityGroupIds': request.security_group_ids or []
                } if request.vpc_id else {}
            )
        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ImageUri=f"{ecr_uri}/{image_name}",
                Publish=True
            )
            if request.vpc_id:
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    MemorySize=request.memory_size,
                    EphemeralStorage={
                        'Size': request.storage_size
                    },
                    Environment={
                        'Variables': request.environment_variables or {}
                    },
                    VpcConfig={
                        'SubnetIds': request.subnet_ids or [],
                        'SecurityGroupIds': request.security_group_ids or []
                    }
                )

        return {"message": "Deployment successful", "image_uri": f"{ecr_uri}/{image_name}", "lambda_arn": response['FunctionArn']}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

 

# Advanced deployment endpoint
@deploy_router.post("/advanced-deploy")
async def advanced_deploy(request: AdvancedDeployRequest, files: List[UploadFile] = File(...)):
    try:
        # Ensure Docker is running
        docker_running = await run_subprocess("docker info")
        
        # Ensure AWS CLI is installed
        try:
            await run_subprocess("aws --version")
        except subprocess.CalledProcessError:
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
        build_result = await run_subprocess(f"docker build -t {image_name} .")

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