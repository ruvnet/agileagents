```
  __  ____ 
 / _\(___ \
/    \/ __/
\_/\_(____)

Agile Agents
v.0.1 : ruv
```
# Agile Agents (A2)

Agile Agents (A2) is an open-source framework for the creation and deployment of serverless intelligent agents using public and private container repositories. The framework supports deployment to AWS, Azure, and GCP, with optional configurations for Azure and GCP.

### Key Features

- **Automated Deployment**: Streamline the deployment of Python applications to AWS Lambda with minimal configuration. Agile Agents automates the creation of virtual environments, dependency installation, Docker image building, and pushing to AWS Elastic Container Registry (ECR).

- **Multi-Function Deployment**: Deploy multiple Lambda functions simultaneously, facilitating large-scale applications or microservices architectures, and enabling parallel development and deployment workflows.

- **Advanced Deployment Options**: Customize your deployments with advanced Docker build options, including the ability to specify base images, build commands, and more, supporting flexibility and adaptability in your CI/CD pipeline.

- **Flexible Configuration**: Support for VPC configurations, security group settings, and subnet specifications ensures secure and optimized network configurations for your Lambda functions, aligning with best practices for Agile infrastructure.

- **Monitoring and Logging**: Integrated with AWS CloudWatch for capturing logs and metrics, Agile Agents enables you to monitor the performance and health of your Lambda functions, promoting a culture of continuous feedback and improvement.

- **Cost Management**: Utilize AWS Cost Explorer and Budget APIs to track and manage your AWS costs effectively, helping your team stay within budget constraints and make informed decisions.

- **Error Handling and Alerts**: Incorporate AWS SNS or SQS for error handling and alerting, ensuring you are promptly notified of any issues, facilitating quick responses and maintaining high service quality.

- **Permissions and Security**: Easily manage IAM policies and roles for your Lambda functions, ensuring appropriate access control and security, crucial for maintaining compliance and protecting sensitive data.

- **Regional Deployments**: Deploy functions across multiple AWS regions, providing flexibility and resilience for your applications, and supporting global Agile teams.

- **User-Friendly API**: A comprehensive set of API endpoints allows for easy integration and automation of deployment processes, supporting Agile practices like continuous integration and continuous deployment (CI/CD).

### Use Cases

- **Microservices**: Deploy and manage a swarm of microservices, each running as an independent Lambda function, supporting modular and iterative development.
  
- **Batch Processing**: Execute large-scale batch processing tasks by deploying multiple Lambda functions that process data in parallel, enhancing efficiency and scalability.
  
- **Event-Driven Architectures**: Build event-driven systems that respond to various triggers and events, scaling automatically based on demand, promoting responsiveness and flexibility.
  
- **Cost Optimization**: Track and manage AWS costs, ensuring efficient usage of resources and budget adherence, enabling Agile teams to deliver value while controlling expenses.

### Public and Private Agent Repositories

Agile Agents (A2) supports access to both public and private agent repositories, facilitating collaboration and deployment of various intelligent agents.

#### Public Repositories

Public repositories provide access to a wide range of pre-built agents and deployment patterns, enabling teams to quickly integrate and deploy solutions without starting from scratch.

- **Agent Marketplace**: Access a marketplace of publicly available agents, each designed for specific tasks such as data processing, machine learning, and automation.
- **Deployment Patterns**: Utilize community-contributed deployment patterns to streamline your deployment processes.
- **Collaboration**: Share your agents and deployment strategies with the broader community to foster collaboration and innovation.

#### Private Repositories

Private repositories allow teams to securely store and manage their custom-built agents and deployment configurations, ensuring control over proprietary solutions.

- **Team Collaboration**: Facilitate collaboration within your team by sharing agents and deployment patterns in a secure, controlled environment.
- **Custom Solutions**: Develop and deploy tailored solutions specific to your organization's needs.
- **Security and Access Control**: Implement fine-grained access controls to ensure only authorized team members can access and deploy sensitive agents.

#### Pre-Built Agent-Centric Applications

Access a library of pre-built agent-centric applications designed to accelerate development and deployment:

- **Data Processing Pipelines**: Deploy agents that handle data ingestion, transformation, and storage, optimized for scalability and efficiency.
- **Machine Learning Models**: Integrate agents pre-configured with popular machine learning frameworks for predictive analytics and AI-driven insights.
- **Automation Tools**: Leverage agents designed to automate repetitive tasks, enhancing productivity and reducing manual effort.
- **Monitoring and Alerts**: Implement agents that monitor system performance and send alerts based on predefined thresholds, ensuring high availability and reliability.

By leveraging both public and private repositories, Agile Agents (A2) empowers teams to rapidly develop, deploy, and scale intelligent agents in a secure and collaborative manner.

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
git clone https://github.com/ruvnet/agileagents
cd agileagents
```

2. Set up your environment variables:

```sh
export AWS_ACCESS_KEY_ID=your_aws_access_key_id
export AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
export AWS_DEFAULT_REGION=your_aws_default_region

export ENABLE_AZURE=true  # Set to true to enable Azure deployments
export ENABLE_GCP=true    # Set to true to enable GCP deployments

export AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
export AZURE_CLIENT_ID=your_azure_client_id
export AZURE_CLIENT_SECRET=your_azure_client_secret
export AZURE_TENANT_ID=your_azure_tenant_id
export AZURE_DEFAULT_REGION=your_azure_default_region

export GOOGLE_CLOUD_PROJECT=your_gcp_project_id
export GOOGLE_APPLICATION_CREDENTIALS=path_to_your_gcp_service_account_json
export GOOGLE_DEFAULT_REGION=your_gcp_default_region
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