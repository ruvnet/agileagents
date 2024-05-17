#!/bin/bash

# Agile Agents (A2)
# An open-source framework for the creation and deployment of serverless intelligent agents with public and private container repositories.

set -e

PROJECT_NAME="Agile Agents (A2)"
ROOT_DIR="AgileAgents"

# Create project structure
echo "Creating project structure..."
mkdir -p $ROOT_DIR/{deployment/{aws,azure,gcp},routers,models,services,utils,deployment/aws/samples,deployment/azure/samples,deployment/gcp/samples}
touch $ROOT_DIR/{app.py,hello_world.json,readme.md}
touch $ROOT_DIR/deployment/aws/{deploy.py,requirements.txt}
touch $ROOT_DIR/deployment/azure/{deploy.py,requirements.txt}
touch $ROOT_DIR/deployment/gcp/{deploy.py,requirements.txt}
touch $ROOT_DIR/routers/{costs_router.py,iam_router.py,management_router.py,misc_router.py,bedrock_router.py}
touch $ROOT_DIR/models/{base_models.py,specific_models.py}
touch $ROOT_DIR/services/{aws_services.py,azure_services.py,gcp_services.py}
touch $ROOT_DIR/utils/{aws_utils.py,azure_utils.py,gcp_utils.py}

# Create root Dockerfile
cat <<EOL > $ROOT_DIR/Dockerfile
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    unzip \\
    && rm -rf /var/lib/apt/lists/*

# Set up the project directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Define the command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
EOL

# Write .gitignore
cat <<EOL > $ROOT_DIR/.gitignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
ENV/
env.bak/
venv.bak/
.DS_Store
*.swp
*.swo
*.idea
*.vscode
*.iml
*.egg-info/
dist/
build/
.aws/
.azure/
.gcp/
EOL

# Write requirements.txt
cat <<EOL > $ROOT_DIR/requirements.txt
fastapi
uvicorn
pydantic
boto3
azure-identity
azure-graphrbac
azure-mgmt-authorization
google-auth
google-cloud-storage
google-cloud-functions
google-cloud-container
google-cloud-iam
google-cloud-pubsub
google-cloud-monitoring
google-cloud-billing
google-cloud-logging
EOL

# Write packages.txt
cat <<EOL > $ROOT_DIR/packages.txt
curl
unzip
EOL

# Write README.md
cat <<EOL > $ROOT_DIR/readme.md
# Agile Agents (A2)

An open-source framework for the creation and deployment of serverless intelligent agents with public and private container repositories.
EOL

# Write sample.json for AWS
cat <<EOL > $ROOT_DIR/deployment/aws/samples/sample.json
{
    "repository_name": "example-repo",
    "image_tag": "latest",
    "python_script": "print('Hello, world!')",
    "requirements": "fastapi\nboto3",
    "function_name": "example-function",
    "region": "us-west-2",
    "vpc_id": "vpc-12345678",
    "subnet_ids": ["subnet-12345678", "subnet-87654321"],
    "security_group_ids": ["sg-12345678", "sg-87654321"]
}
EOL

# Write sample.json for Azure
cat <<EOL > $ROOT_DIR/deployment/azure/samples/sample.json
{
    "repository_name": "example-repo",
    "image_tag": "latest",
    "python_script": "print('Hello, world!')",
    "requirements": "fastapi\nazure-identity",
    "function_name": "example-function",
    "region": "westus",
    "vnet_name": "vnet-12345678",
    "subnet_name": "subnet-12345678",
    "security_group_name": "sg-12345678"
}
EOL

# Write sample.json for GCP
cat <<EOL > $ROOT_DIR/deployment/gcp/samples/sample.json
{
    "repository_name": "example-repo",
    "image_tag": "latest",
    "python_script": "print('Hello, world!')",
    "requirements": "fastapi\ngoogle-auth",
    "function_name": "example-function",
    "region": "us-central1",
    "vpc_id": "vpc-12345678",
    "subnet_ids": ["subnet-12345678", "subnet-87654321"],
    "security_group_ids": ["sg-12345678", "sg-87654321"]
}
EOL

# Check if pip is installed
if ! command -v pip &> /dev/null
then
    echo "pip could not be found, please install pip."
    exit 1
fi

# Install the requirements
echo "Installing requirements..."
pip install -r $ROOT_DIR/requirements.txt || { echo "Failed to install requirements"; exit 1; }

echo "Project structure created and requirements installed successfully."
