import gradio as gr
import subprocess
import os
import boto3
from fastapi import HTTPException
from typing import List, Optional

# Function to install AWS CLI
def install_aws_cli():
    subprocess.run(["curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["unzip", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install"], check=True)
    subprocess.run(["rm", "-rf", "awscliv2.zip", "aws"], check=True)

# Function to ensure IAM role exists
def ensure_iam_role(role_name, account_id):
    iam_client = boto3.client('iam')
    try:
        role = iam_client.get_role(RoleName=role_name)
        return role['Role']['Arn']
    except iam_client.exceptions.NoSuchEntityException:
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
            Description="Role for Lambda execution"
        )
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        return role['Role']['Arn']

# Function to deploy the application
def deploy(python_script, requirements, repository_name, image_tag, function_name, memory_size, storage_size, environment_variables, subnet_ids, security_group_ids, vpc_id, region):
    try:
        # Ensure Docker is running
        docker_running = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if docker_running.returncode != 0:
            return "Docker daemon is not running. Please start Docker daemon."

        # Ensure AWS CLI is installed
        aws_cli_installed = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        if aws_cli_installed.returncode != 0:
            install_aws_cli()

        # Step 1: Create a virtual environment
        subprocess.run(["python3", "-m", "venv", "venv"], check=True)

        # Step 2: Write the Python script to a temporary file
        temp_dir = "/tmp/deployment"
        os.makedirs(temp_dir, exist_ok=True)
        python_script_path = os.path.join(temp_dir, "app.py")
        with open(python_script_path, "w") as f:
            f.write(python_script)

        # Step 3: Write the requirements to a file
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        with open(requirements_path, "w") as f:
            f.write(requirements)

        # Step 4: Install dependencies
        subprocess.run(["venv/bin/pip", "install", "-r", requirements_path], check=True)

        # Step 5: Create a Dockerfile
        dockerfile_content = f"""
        FROM public.ecr.aws/lambda/python:3.8
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY app.py .
        CMD ["app.lambda_handler"]
        """
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        # Step 6: Build the Docker image
        image_name = f"{repository_name}:{image_tag}"
        build_result = subprocess.run(["docker", "build", "-t", image_name, temp_dir], capture_output=True, text=True)

        if build_result.returncode != 0:
            return f"Docker build failed: {build_result.stderr}"

        # Step 7: Authenticate Docker to AWS ECR
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
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
            return f"Docker login failed: {login_result.stderr}"

        # Step 8: Create ECR repository if it doesn't exist
        ecr_client = boto3.client('ecr', region_name=region)
        try:
            ecr_client.create_repository(repositoryName=repository_name)
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass

        # Step 9: Tag and push the Docker image to ECR
        subprocess.run(["docker", "tag", image_name, f"{ecr_uri}/{image_name}"], check=True)
        subprocess.run(["docker", "push", f"{ecr_uri}/{image_name}"], check=True)

        # Step 10: Create or update the Lambda function
        role_name = "lambda-execution-role"
        role_arn = ensure_iam_role(role_name, account_id)

        lambda_client = boto3.client('lambda', region_name=region)
        try:
            response = lambda_client.create_function(
                FunctionName=function_name,
                Role=role_arn,
                Code={
                    'ImageUri': f"{ecr_uri}/{image_name}"
                },
                PackageType='Image',
                Publish=True,
                MemorySize=memory_size,
                EphemeralStorage={
                    'Size': storage_size
                },
                Environment={
                    'Variables': environment_variables or {}
                },
                VpcConfig={
                    'SubnetIds': subnet_ids or [],
                    'SecurityGroupIds': security_group_ids or []
                } if vpc_id else {}
            )
        except lambda_client.exceptions.ResourceConflictException:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ImageUri=f"{ecr_uri}/{image_name}",
                Publish=True
            )
            if vpc_id:
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    MemorySize=memory_size,
                    EphemeralStorage={
                        'Size': storage_size
                    },
                    Environment={
                        'Variables': environment_variables or {}
                    },
                    VpcConfig={
                        'SubnetIds': subnet_ids or [],
                        'SecurityGroupIds': security_group_ids or []
                    }
                )

        return {"message": "Deployment successful", "image_uri": f"{ecr_uri}/{image_name}", "lambda_arn": response['FunctionArn']}
    except subprocess.CalledProcessError as e:
        return str(e)
    except Exception as e:
        return str(e)

# Gradio Interface
def gradio_interface():
    with gr.Blocks() as demo:
        with gr.Row():
            with gr.Column():
                python_script = gr.Textbox(label="Python Script", lines=10, placeholder="Enter your Python script here")
                requirements = gr.Textbox(label="Requirements", lines=5, placeholder="Enter your requirements here")
                repository_name = gr.Textbox(label="Repository Name", placeholder="Enter the ECR repository name")
                image_tag = gr.Textbox(label="Image Tag", placeholder="Enter the Docker image tag")
                function_name = gr.Textbox(label="Lambda Function Name", placeholder="Enter the Lambda function name")
                memory_size = gr.Number(label="Memory Size (MB)", value=128)
                storage_size = gr.Number(label="Storage Size (MB)", value=512)
                environment_variables = gr.Textbox(label="Environment Variables (JSON)", placeholder="Enter environment variables as JSON")
                subnet_ids = gr.Textbox(label="Subnet IDs (comma-separated)", placeholder="Enter subnet IDs if using VPC")
                security_group_ids = gr.Textbox(label="Security Group IDs (comma-separated)", placeholder="Enter security group IDs if using VPC")
                vpc_id = gr.Textbox(label="VPC ID", placeholder="Enter VPC ID if using VPC")
                region = gr.Textbox(label="AWS Region", placeholder="Enter AWS region", value="us-west-2")
                deploy_button = gr.Button("Deploy")

            with gr.Column():
                output = gr.Textbox(label="Output", lines=20, interactive=False)

        deploy_button.click(
            deploy,
            inputs=[
                python_script, requirements, repository_name, image_tag, function_name,
                memory_size, storage_size, environment_variables, subnet_ids, security_group_ids, vpc_id, region
            ],
            outputs=output
        )

    demo.launch()

if __name__ == "__main__":
    gradio_interface()