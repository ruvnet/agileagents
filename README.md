# Agile Agents (A2)

Agile Agents (A2) is an open-source framework for the creation and deployment of serverless intelligent agents using public and private container repositories. The framework supports deployment to AWS, Azure, and GCP, with optional configurations for Azure and GCP.

## Project Structure

```
project_root/
├── deployment/
│   ├── aws/
│   │   ├── deploy.py
│   │   └── requirements.txt
│   │   └── samples/
│   │       └── deploy_sample.json
│   ├── azure/
│   │   ├── deploy.py
│   │   └── requirements.txt
│   │   └── samples/
│   │       └── deploy_sample.json
│   ├── gcp/
│   │   ├── deploy.py
│   │   └── requirements.txt
│   │   └── samples/
│   │       └── deploy_sample.json
├── main.py
├── routers/
│   ├── costs_router.py
│   ├── iam_router.py
│   ├── management_router.py
│   ├── misc_router.py
│   └── bedrock_router.py
├── models/
│   ├── base_models.py
│   └── specific_models.py
├── services/
│   ├── aws_services.py
│   ├── azure_services.py
│   └── gcp_services.py
├── utils/
│   ├── aws_utils.py
│   ├── azure_utils.py
│   └── gcp_utils.py
├── Dockerfile
├── .gitignore
├── requirements.txt
├── packages.txt
├── readme.md
└── setup.sh
```

## Setup

### Prerequisites

- Python 3.8+
- Docker
- AWS CLI
- Azure CLI
- Google Cloud SDK

### Installation

1. Clone the repository:

```sh
git clone https://github.com/your-repo/agile-agents.git
cd agile-agents
```

2. Run the setup script to install dependencies and set up the project structure:

```sh
chmod +x setup.sh
./setup.sh
```

3. Set up your environment variables:

```sh
export AWS_ACCESS_KEY_ID=your_aws_access_key_id
export AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
export AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
export GOOGLE_CLOUD_PROJECT=your_gcp_project_id
export ENABLE_AZURE=true  # Set to true to enable Azure deployments
export ENABLE_GCP=true    # Set to true to enable GCP deployments
```

### Running the Application

You can run the application using Uvicorn:

```sh
uvicorn app:app --host 0.0.0.0 --port 8000
```

### Building and Running with Docker

1. Build the Docker image:

```sh
docker build -t agile-agents .
```

2. Run the Docker container:

```sh
docker run -d -p 8000:8000 --name agile-agents agile-agents
```

### Endpoints

The API includes several endpoints for managing deployments, costs, IAM, and Bedrock models.
### Endpoints

The API includes several endpoints for managing deployments, costs, IAM, and Bedrock models.

#### Costs Router

- **POST /costs/get-cost-and-usage** - Get Cost And Usage
- **POST /costs/describe-budget** - Describe Budget
- **GET /costs/describe-report-definitions** - Describe Report Definitions
- **POST /costs/get-products** - Get Products

#### IAM Router

- **POST /iam/create-user** - Create User
- **GET /iam/list-users** - List Users
- **POST /iam/create-role** - Create Role
- **POST /iam/attach-policy-to-role** - Attach Policy To Role
- **POST /iam/create-policy** - Create Policy
- **POST /iam/assume-role** - Assume Role
- **POST /iam/create-access-key** - Create Access Key

#### Management Router

- **POST /management/deploy-multiple-functions** - Deploy Multiple Functions
- **GET /management/invoke-lambda** - Invoke Lambda
- **POST /management/invoke-multiple-functions** - Invoke Multiple Functions
- **GET /management/list-lambda-functions** - List Lambda Functions
- **DELETE /management/delete-lambda-function** - Delete Lambda Function
- **GET /management/list-ecr-repositories** - List ECR Repositories
- **DELETE /management/delete-ecr-repository** - Delete ECR Repository
- **GET /management/s3-buckets** - Get S3 Buckets
- **POST /management/upload-to-s3** - Upload To S3
- **POST /management/create-ec2-instance** - Create EC2 Instance Endpoint
- **GET /management/ec2-instances** - Get EC2 Instances

#### Misc Router

- **GET /misc/regions** - List Regions

#### Bedrock Router

- **GET /bedrock/list-foundation-models** - List Foundation Models
- **POST /bedrock/invoke-model** - Invoke Model

#### Deployment Router

- **POST /deployment/deploy** - Deploy
- **POST /deployment/advanced-deploy** - Advanced Deploy

### Sample JSON for Endpoints

Sample JSON files for each endpoint can be found in the `samples` directory under `deployment/aws/samples`, `deployment/azure/samples`, and `deployment/gcp/samples`.

#### AWS Sample

```json
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
```

#### Azure Sample

```json
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
```

#### GCP Sample

```json
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
```

### Contribution

Contributions are welcome! Please submit a pull request or open an issue to discuss any changes.

### License

This project is licensed under the MIT License.
