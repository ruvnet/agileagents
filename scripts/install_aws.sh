#!/bin/bash

set -e

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Please start Docker daemon."
  exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "AWS CLI is not installed. Installing AWS CLI."
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  unzip awscliv2.zip
  sudo ./aws/install
  rm -rf awscliv2.zip aws
fi

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Docker login to AWS ECR
REGION="us-west-2"  # Change to your desired region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Ensure IAM role for Lambda function
ROLE_NAME="lambda-execution-role"
TRUST_POLICY='{
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
}'

role_exists=$(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.RoleName' --output text 2>/dev/null || echo "false")
if [ "$role_exists" == "false" ]; then
  aws iam create-role --role-name ${ROLE_NAME} --assume-role-policy-document "${TRUST_POLICY}"
  echo "Role ${ROLE_NAME} created successfully."
else
  echo "Role ${ROLE_NAME} already exists."
fi

# Deactivate the virtual environment
deactivate

echo "Setup completed successfully."
