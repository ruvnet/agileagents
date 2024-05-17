Here are the files organized according to the specified folder structure:

# Structure 
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
### `project_root/deployment/aws/deploy.py`

```python
import os
import subprocess
import json
import boto3
from fastapi import FastAPI, HTTPException, File, UploadFile, APIRouter
from pydantic import BaseModel
from typing import Optional, List
from botocore.exceptions import ClientError

async def install_aws_cli():
    subprocess.run(["curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["unzip", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install"], check=True)
    subprocess.run(["rm", "-rf", "awscliv2.zip", "aws"], check=True)

async def ensure_iam_role(role_name, account_id):
    iam_client = boto3.client('iam')
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    try:
        iam_client.get_role(RoleName=role_name)
    except iam_client.exceptions.NoSuchEntityException:
        trust_policy = {
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
        iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for Lambda function execution"
        )
    return role_arn

# Deployment endpoints
@app.post("/deploy")
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

        # Step 2: Write the Python script to a file
        with open("app.py", "w") as f:
            f.write(request.python_script)

        # Step 3: Write the requirements to a file
        with open("requirements.txt", "w") as f:
            f.write(request.requirements)

        # Step 4: Install dependencies
        subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"], check=True)

        # Step 5: Create a Dockerfile
        dockerfile_content = f"""
        FROM public.ecr.aws/lambda/python:3.8
        COPY requirements.txt .
        RUN pip install -r requirements.txt
        COPY app.py .
        CMD ["app.lambda_handler"]
        """
        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)

        # Step 6: Build the Docker image
        image_name = f"{request.repository_name}:{request.image_tag}"
        build_result = subprocess.run(["docker", "build", "-t", image_name, "."], capture_output=True, text=True)

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
        role_arn = await ensure_iam_role(role_name, account_id)
        
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
                MemorySize=request.memory_size if request.memory_size else 128,
                EphemeralStorage={
                    'Size': request.storage_size if request.storage_size else 512
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
                    MemorySize=request.memory_size if request.memory_size else 128,
                    EphemeralStorage={
                        'Size': request.storage_size if request.storage_size else 512
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

@app.post("/advanced-deploy")
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

        # Authenticate Docker to AWS ECR
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

        # Create ECR repository if it doesn't exist
        ecr_client = boto3.client('ecr', region_name=region)


        try:
            ecr_client.create_repository(repositoryName=request.repository_name)
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass

        # Tag and push the Docker image to ECR
        subprocess.run(["docker", "tag", image_name, f"{ecr_uri}/{image_name}"], check=True)
        subprocess.run(["docker", "push", f"{ecr_uri}/{image_name}"], check=True)

        # Create or update the Lambda function
        role_name = "lambda-execution-role"
        role_arn = await ensure_iam_role(role_name, account_id)
        
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
                MemorySize=request.memory_size if request.memory_size else 128,
                EphemeralStorage={
                    'Size': request.storage_size if request.storage_size else 512
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
                    MemorySize=request.memory_size if request.memory_size else 128,
                    EphemeralStorage={
                        'Size': request.storage_size if request.storage_size else 512
                    },
                    VpcConfig={
                        'SubnetIds': request.subnet_ids or [],
                        'SecurityGroupIds': request.security_group_ids or []
                    }
                )

        return {"message": "Advanced deployment successful", "image_uri": f"{ecr_uri}/{image_name}", "lambda_arn": response['FunctionArn']}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `project_root/deployment/aws/requirements.txt`

```txt
boto3
fastapi
pydantic
```

### `project_root/deployment/aws/samples/deploy_sample.json`

```json
{
    "repository_name": "my-repository",
    "image_tag": "latest",
    "python_script": "def lambda_handler(event, context):\n    return {'statusCode': 200, 'body': 'Hello World'}",
    "requirements": "requests\nnumpy",
    "function_name": "my-lambda-function",
    "region": "us-west-2",
    "vpc_id": "vpc-12345678",
    "subnet_ids": ["subnet-12345678", "subnet-87654321"],
    "security_group_ids": ["sg-12345678", "sg-87654321"]
}
```

### `project_root/main.py`

```python
from fastapi import FastAPI
from routers.costs_router import router as costs_router
from routers.iam_router import router as iam_router
from routers.management_router import router as management_router
from routers.misc_router import router as misc_router
from routers.bedrock_router import router as bedrock_router

app = FastAPI()

app.include_router(costs_router, prefix="/costs", tags=["Costs"])
app.include_router(iam_router, prefix="/iam", tags=["IAM"])
app.include_router(management_router, prefix="/management", tags=["Management"])
app.include_router(misc_router, prefix="/misc", tags=["Misc"])
app.include_router(bedrock_router, prefix="/bedrock", tags=["Bedrock"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
```

### `project_root/routers/costs_router.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import boto3

router = APIRouter()

class TimePeriod(BaseModel):
    Start: str
    End: str

class BudgetRequest(BaseModel):
    AccountId: str
    BudgetName: str

@router.post("/get-cost-and-usage")
async def get_cost_and_usage(time_period: TimePeriod, metrics: List[str] = ["UnblendedCost"], granularity: str = "MONTHLY"):
    try:
        client = boto3.client('ce')
        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': time_period.Start,
                'End': time_period.End
            },
            Granularity=granularity,
            Metrics=metrics
        )
        return response['ResultsByTime']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/describe-budget")
async def describe_budget(budget_request: BudgetRequest):
    try:
        client = boto3.client('budgets')
        response = client.describe_budget(
            AccountId=budget_request.AccountId,
            BudgetName=budget_request.BudgetName
        )
        return response['Budget']['CalculatedSpend']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/describe-report-definitions")
async def describe_report_definitions():
    try:
        client = boto3.client('cur')
        response = client.describe_report_definitions()
        return response['ReportDefinitions']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/get-products")
async def get_products(service_code: str, filters: List[dict]):
    try:
        client = boto3.client('pricing')
        response = client.get_products(
            ServiceCode=service_code,
            Filters=filters
        )
        return response['PriceList']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `project_root/routers/iam_router.py`

```python
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
```

### `project_root/routers/management_router.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import

 boto3
from botocore.exceptions import ClientError
import json

router = APIRouter()

class FunctionConfig(BaseModel):
    repository_name: str
    image_tag: str
    function_name_prefix: str
    number_of_functions: int
    vpc_id: str
    subnet_ids: List[str]
    security_group_ids: List[str]
    region: Optional[str] = None 
    log_retention_days: Optional[int] = 7

class UpdateFunctionConfig(BaseModel):
    function_name: str
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    environment_variables: Optional[dict] = None
    region: Optional[str] = None

@app.post("/deploy-multiple-functions")
async def deploy_multiple_functions(config: FunctionConfig):
    try:
        # Initialize AWS clients
        account_id = boto3.client('sts').get_caller_identity().get('Account')
        region = config.region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        ecr_client = boto3.client('ecr', region_name=region)
        lambda_client = boto3.client('lambda', region_name=region)
        logs_client = boto3.client('logs', region_name=region)
        sns_client = boto3.client('sns', region_name=region)

        # Ensure the IAM role exists
        role_name = "lambda-execution-role"
        role_arn = await ensure_iam_role(role_name, account_id)

        # Authenticate Docker to AWS ECR
        ecr_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
        login_password = subprocess.run(
            ["aws", "ecr", "get-login-password", "--region", region],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        subprocess.run(
            ["docker", "login", "--username", "AWS", "--password-stdin", ecr_uri],
            input=login_password, text=True, capture_output=True
        )

        # Ensure ECR repository exists
        try:
            ecr_client.create_repository(repositoryName=config.repository_name)
        except ecr_client.exceptions.RepositoryAlreadyExistsException:
            pass

        # Deploy multiple Lambda functions
        for i in range(config.number_of_functions):
            function_name = f"{config.function_name_prefix}-{i}"
            image_name = f"{config.repository_name}:{config.image_tag}"

            try:
                response = lambda_client.create_function(
                    FunctionName=function_name,
                    Role=role_arn,
                    Code={'ImageUri': f"{ecr_uri}/{image_name}"},
                    PackageType='Image',
                    Publish=True,
                    MemorySize=config.memory_size,
                    EphemeralStorage={'Size': config.storage_size},
                    VpcConfig={
                        'SubnetIds': config.subnet_ids,
                        'SecurityGroupIds': config.security_group_ids
                    }
                )

                # Set up CloudWatch Logs retention
                log_group_name = f"/aws/lambda/{function_name}"
                try:
                    logs_client.create_log_group(logGroupName=log_group_name)
                except logs_client.exceptions.ResourceAlreadyExistsException:
                    pass

                logs_client.put_retention_policy(
                    logGroupName=log_group_name,
                    retentionInDays=config.log_retention_days
                )

            except lambda_client.exceptions.ResourceConflictException:
                lambda_client.update_function_code(
                    FunctionName=function_name,
                    ImageUri=f"{ecr_uri}/{image_name}",
                    Publish=True
                )
                lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    MemorySize=config.memory_size,
                    EphemeralStorage={'Size': config.storage_size},
                    VpcConfig={
                        'SubnetIds': config.subnet_ids,
                        'SecurityGroupIds': config.security_group_ids
                    }
                )

        return {"message": f"Deployed {config.number_of_functions} functions successfully"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/invoke-lambda")
async def invoke_lambda(function_name: str, region: Optional[str] = None):
    try:
        # Initialize boto3 Lambda client
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        lambda_client = boto3.client('lambda', region_name=region)
        
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse'
        )
        
        # Parse the response
        response_payload = response['Payload'].read().decode('utf-8')
        response_data = json.loads(response_payload)

        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/invoke-multiple-functions")
async def invoke_multiple_functions(config: InvokeConfig):
    try:
        # Initialize AWS clients
        region = config.region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        lambda_client = boto3.client('lambda', region_name=region)
        logs_client = boto3.client('logs', region_name=region)
        cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        sns_client = boto3.client('sns', region_name=region)
        sns_topic_arn = os.getenv("SNS_TOPIC_ARN")

        responses = []

        for i in range(config.number_of_functions):
            function_name = f"{config.function_name_prefix}-{i}"
            try:
                response = lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(config.payload)
                )
                
                # Parse the response
                response_payload = response['Payload'].read().decode('utf-8')
                response_data = json.loads(response_payload)
                responses.append(response_data)

                # Log the invocation to CloudWatch
                log_group_name = f"/aws/lambda/{function_name}"
                log_stream_name = f"{function_name}-invocation"
                logs_client.create_log_stream(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name
                )
                logs_client.put_log_events(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name,
                    logEvents=[
                        {
                            'timestamp': int(time.time() * 1000),
                            'message': json.dumps(response_data)
                        }
                    ]
                )

                # Create custom CloudWatch metric
                cloudwatch_client.put_metric_data(
                    Namespace='LambdaInvocations',
                    MetricData=[
                        {
                            'MetricName': 'InvocationCount',
                            'Dimensions': [
                                {
                                    'Name': 'FunctionName',
                                    'Value': function_name
                                },
                            ],
                            'Unit': 'Count',
                            'Value': 1
                        }
                    ]
                )

            except lambda_client.exceptions.ResourceNotFoundException:
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=f"Function {function_name} not found during invocation.",
                    Subject="Lambda Function Invocation Error"
                )
                raise HTTPException(status_code=500, detail=f"Function {function_name} not found.")
            except Exception as e:
                sns_client.publish(
                    TopicArn=sns_topic_arn,
                    Message=str(e),
                    Subject="Lambda Function Invocation Error"
                )
                raise HTTPException(status_code=500, detail=str(e))

        return {"message": f"Invoked {config.number_of_functions} functions successfully", "responses": responses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/list-lambda-functions")
async def list_lambda_functions(region: Optional[str] = None):
    try:
        if region:
            lambda_client = boto3.client('lambda', region_name=region)
            response = lambda_client.list_functions()
            functions = response['Functions']
        else:
            lambda_client = boto3.client('lambda')
            paginator = lambda_client.get_paginator('list_functions')
            response_iterator = paginator.paginate()
            functions = []
            for response in response_iterator:
                functions.extend(response['Functions'])

        function_names = [func['FunctionName'] for func in functions]

        return {"functions": function_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete-lambda-function")
async def delete_lambda_function(function_name: str):
    try:
        # Initialize boto3 Lambda client
        region = "us-west-2"  # Change to your desired region
        lambda_client = boto3.client('lambda', region_name=region)
        
        # Delete the Lambda function
        lambda_client.delete_function(FunctionName=function_name)

        return {"message": f"Lambda function {function_name} deleted successfully."}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list-ecr-repositories")
async def list_ecr_repositories():
    try:
        # Initialize boto3 ECR client
        region = "us-west-2"  # Change to your desired region
        ecr_client = boto3.client('ecr', region_name=region)
        
        # List ECR repositories
        response = ecr_client.describe_repositories()
        repositories = response['repositories']

        return {"repositories": repositories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-ecr-repository")
async def delete_ecr_repository(repository_name: str):
    try:
        # Initialize boto3 ECR client
        region = "us-west-2"  # Change to your desired region
        ecr_client = boto3.client('ecr', region_name=region)
        
        # Delete the ECR repository
        ecr_client.delete_repository(repositoryName=repository_name, force=True)

        return {"message": f"ECR repository {repository_name} deleted successfully."

}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `project_root/routers/misc_router.py`

```python
from fastapi import APIRouter, HTTPException
import boto3

router = APIRouter()

@router.get("/regions")
async def list_regions():
    try:
        ec2_client = boto3.client('ec2')
        response = ec2_client.describe_regions()
        regions = response['Regions']
        region_names = [region['RegionName'] for region in regions]
        return {"regions": region_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `project_root/routers/bedrock_router.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import boto3
import json

router = APIRouter()

class BedrockModelRequest(BaseModel):
    prompt: str
    max_tokens_to_sample: Optional[int] = 300
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.9

@router.get("/list-foundation-models")
async def list_foundation_models(region: Optional[str] = None):
    try:
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        bedrock_client = boto3.client('bedrock', region_name=region)
        response = bedrock_client.list_foundation_models()
        models = response['modelSummaries']
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/invoke-model")
async def invoke_model(model_request: BedrockModelRequest, model_id: str, region: Optional[str] = None):
    try:
        region = region or os.getenv("AWS_DEFAULT_REGION", "us-west-2")
        bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=region)
        body = json.dumps({
            "prompt": model_request.prompt,
            "max_tokens_to_sample": model_request.max_tokens_to_sample,
            "temperature": model_request.temperature,
            "top_p": model_request.top_p
        })
        response = bedrock_runtime_client.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        return response_body
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `project_root/models/base_models.py`

```python
from pydantic import BaseModel
from typing import Optional, List

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

class VpcConfig(BaseModel):
    vpc_id: str
    subnet_ids: List[str]
    security_group_ids: List[str]

class FunctionConfig(BaseModel):
    repository_name: str
    image_tag: str
    function_name_prefix: str
    number_of_functions: int
    vpc_id: str
    subnet_ids: List[str]
    security_group_ids: List[str]
    region: Optional[str] = None 
    log_retention_days: Optional[int] = 7

class InvokeConfig(BaseModel):
    function_name_prefix: str
    number_of_functions: int
    payload: dict
    region: Optional[str] = None

class TimePeriod(BaseModel):
    Start: str
    End: str

class BudgetRequest(BaseModel):
    AccountId: str
    BudgetName: str

class UpdateFunctionConfig(BaseModel):
    function_name: str
    memory_size: Optional[int] = None
    timeout: Optional[int] = None
    environment_variables: Optional[dict] = None
    region: Optional[str] = None

class BedrockModelRequest(BaseModel):
    prompt: str
    max_tokens_to_sample: Optional[int] = 300
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.9

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
```

### `project_root/models/specific_models.py`

```python
# You can add any specific models related to other services here
```

### `project_root/services/aws_services.py`

```python
import boto3
from botocore.exceptions import ClientError

# Define your AWS service-related functions here
```

### `project_root/utils/aws_utils.py`

```python
import subprocess

async def install_aws_cli():
    subprocess.run(["curl", "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip", "-o", "awscliv2.zip"], check=True)
    subprocess.run(["unzip", "awscliv2.zip"], check=True)
    subprocess.run(["sudo", "./aws/install"], check=True)
    subprocess.run(["rm", "-rf", "awscliv2.zip", "aws"], check=True)
```

### `project_root/Dockerfile`

```Dockerfile
FROM python:3.8-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `project_root/.gitignore`

```gitignore
venv/
__pycache__/
*.pyc
awscliv2.zip
aws/
```

### `project_root/requirements.txt`

```txt
fastapi
uvicorn
boto3
```

### `project_root/packages.txt`

```txt
curl
unzip
```

### `project_root/readme.md`

```md
# Project Overview

This project is a FastAPI application that provides various endpoints for deploying and managing AWS resources, handling IAM roles and policies, and interacting with other AWS services.

## Folder Structure

- `deployment/aws/`: Contains deployment-related scripts and requirements for AWS.
- `routers/`: Contains the different routers for handling API endpoints.
- `models/`: Contains the Pydantic models used for request validation.
- `services/`: Contains the service-specific utility functions.
- `utils/`: Contains utility functions for various tasks.

## How to Run

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Run the FastAPI application:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Docker

To build and run the Docker container:

```bash
docker build -t my-fastapi-app .
docker run -p 8000:8000 my-fastapi-app
```

## Endpoints

### Deployment

- `POST /deploy`
- `POST /advanced-deploy`

### IAM

- `POST /create-user`
- `GET /list-users`
- `POST /create-role`
- `POST /attach-policy-to-role`
- `POST /create-policy`
- `POST /assume-role`
- `POST /create-access-key`

### Costs

- `POST /get-cost-and-usage`
- `POST /describe-budget`
- `GET /describe-report-definitions`
- `POST /get-products`

### Management

- `POST /deploy-multiple-functions`
- `GET /invoke-lambda`
- `POST /invoke-multiple-functions`
- `GET /list-lambda-functions`
- `DELETE /delete-lambda-function`
- `GET /list-ecr-repositories`
- `DELETE /delete-ecr-repository`

### Misc

- `GET /regions`

### Bedrock

- `GET /list-foundation-models`
- `POST /invoke-model`
```

### `project_root/setup.sh`

```bash
#!/bin/bash

# Update and install necessary packages
sudo apt-get update
sudo apt-get install -y $(cat packages.txt)

# Install Python packages
pip install -r requirements.txt

# Run the application
uvicorn main:app --host 0.0.0.0 --port 8000
```