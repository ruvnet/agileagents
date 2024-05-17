from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import boto3
from botocore.exceptions import ClientError
import json

from models.base_models import InvokeConfig

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

@router.post("/deploy-multiple-functions")
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

@router.get("/invoke-lambda")
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

@router.post("/invoke-multiple-functions")
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
    
@router.get("/list-lambda-functions")
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


@router.delete("/delete-lambda-function")
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

@router.get("/list-ecr-repositories")
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

@router.delete("/delete-ecr-repository")
async def delete_ecr_repository(repository_name: str):
    try:
        # Initialize boto3 ECR client
        region = "us-west-2"  # Change to your desired region
        ecr_client = boto3.client('ecr', region_name=region)
        
        # Delete the ECR repository
        ecr_client.delete_repository(repositoryName=repository_name, force=True)

        return {"message": f"ECR repository {repository_name} deleted successfully."}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))