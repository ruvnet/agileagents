# aws_services.py

import boto3
import json
import subprocess
from botocore.exceptions import ClientError
import base64

# Function to initialize an AWS client
def get_aws_client(service_name, region_name=None):
    """
    Initialize an AWS client for a given service.

    Args:
        service_name (str): The name of the AWS service (e.g., 's3', 'ec2').
        region_name (str, optional): The AWS region. If not provided, uses the default region.

    Returns:
        boto3.client: The Boto3 client for the specified service.
    """
    return boto3.client(service_name, region_name=region_name)

# Function to ensure IAM role exists, creating it if it does not
def ensure_iam_role(role_name, account_id, service='lambda.amazonaws.com'):
    """
    Ensure an IAM role exists, creating it if it does not.

    Args:
        role_name (str): The name of the IAM role.
        account_id (str): The AWS account ID.
        service (str): The AWS service that will assume the role (default is 'lambda.amazonaws.com').

    Returns:
        str: The ARN of the IAM role.
    """
    iam_client = get_aws_client('iam')
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
                        "Service": service
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

# Function to create an ECR repository if it does not exist
def create_ecr_repository(repository_name, region_name=None):
    """
    Create an ECR repository if it does not exist.

    Args:
        repository_name (str): The name of the ECR repository.
        region_name (str, optional): The AWS region. If not provided, uses the default region.

    Returns:
        dict: The response from the create_repository call.
    """
    ecr_client = get_aws_client('ecr', region_name=region_name)
    try:
        response = ecr_client.create_repository(repositoryName=repository_name)
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        response = ecr_client.describe_repositories(repositoryNames=[repository_name])
    return response

# Function to push a Docker image to ECR

def push_docker_image_to_ecr(repository_name, image_tag, region_name=None):
    """
    Push a Docker image to an ECR repository.

    Args:
        repository_name (str): The name of the ECR repository.
        image_tag (str): The tag of the Docker image.
        region_name (str, optional): The AWS region. If not provided, uses the default region.

    Returns:
        str: The URI of the pushed Docker image.
    """
    ecr_client = get_aws_client('ecr', region_name=region_name)
    account_id = boto3.client('sts').get_caller_identity().get('Account')
    ecr_uri = f"{account_id}.dkr.ecr.{region_name}.amazonaws.com"
    
    # Get ECR login token and authenticate Docker
    auth_token = ecr_client.get_authorization_token()['authorizationData'][0]['authorizationToken']
    username, password = base64.b64decode(auth_token).decode().split(':')
    
    login_command = f"docker login -u {username} -p {password} {ecr_uri}"
    login_result = subprocess.run(login_command, shell=True, capture_output=True, text=True)
    if login_result.returncode != 0:
        raise Exception(f"Docker login failed: {login_result.stderr}")
    
    image_uri = f"{ecr_uri}/{repository_name}:{image_tag}"
    subprocess.run(["docker", "tag", f"{repository_name}:{image_tag}", image_uri], check=True)
    subprocess.run(["docker", "push", image_uri], check=True)
    
    return image_uri

# Function to create or update a Lambda function with a Docker image
def create_or_update_lambda_function(function_name, image_uri, role_arn, region_name=None, memory_size=128, storage_size=512, vpc_config=None):
    """
    Create or update a Lambda function with a Docker image.

    Args:
        function_name (str): The name of the Lambda function.
        image_uri (str): The URI of the Docker image.
        role_arn (str): The ARN of the IAM role.
        region_name (str, optional): The AWS region. If not provided, uses the default region.
        memory_size (int, optional): The memory size for the Lambda function (default is 128 MB).
        storage_size (int, optional): The ephemeral storage size for the Lambda function (default is 512 MB).
        vpc_config (dict, optional): The VPC configuration for the Lambda function (default is None).

    Returns:
        dict: The response from the create_function or update_function_code call.
    """
    lambda_client = get_aws_client('lambda', region_name=region_name)
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Role=role_arn,
            Code={'ImageUri': image_uri},
            PackageType='Image',
            Publish=True,
            MemorySize=memory_size,
            EphemeralStorage={'Size': storage_size},
            VpcConfig=vpc_config if vpc_config else {}
        )
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri,
            Publish=True
        )
        if vpc_config:
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                MemorySize=memory_size,
                EphemeralStorage={'Size': storage_size},
                VpcConfig=vpc_config
            )
    return response

# Additional utility functions can be added here for other AWS services...

# Function to list all S3 buckets
def list_s3_buckets():
    """
    List all S3 buckets in the AWS account.

    Returns:
        list: A list of bucket names.
    """
    s3_client = get_aws_client('s3')
    response = s3_client.list_buckets()
    return [bucket['Name'] for bucket in response['Buckets']]

# Function to upload a file to an S3 bucket
def upload_file_to_s3(file_name, bucket_name, object_name=None):
    """
    Upload a file to an S3 bucket.

    Args:
        file_name (str): The file to upload.
        bucket_name (str): The name of the bucket to upload to.
        object_name (str, optional): The S3 object name. If not specified, file_name is used.

    Returns:
        bool: True if file was uploaded, else False.
    """
    s3_client = get_aws_client('s3')
    if object_name is None:
        object_name = file_name

    try:
        s3_client.upload_file(file_name, bucket_name, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

# Function to create a new EC2 instance
def create_ec2_instance(image_id, instance_type, key_name, security_group, region_name=None):
    """
    Create a new EC2 instance.

    Args:
        image_id (str): The ID of the AMI.
        instance_type (str): The instance type (e.g., 't2.micro').
        key_name (str): The name of the key pair.
        security_group (str): The name of the security group.
        region_name (str, optional): The AWS region. If not provided, uses the default region.

    Returns:
        dict: Information about the created instance.
    """
    ec2_client = get_aws_client('ec2', region_name=region_name)
    response = ec2_client.run_instances(
        ImageId=image_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroups=[security_group],
        MinCount=1,
        MaxCount=1
    )
    return response['Instances'][0]

# Function to describe EC2 instances
def describe_ec2_instances(instance_ids=None, region_name=None):
    """
    Describe EC2 instances.

    Args:
        instance_ids (list, optional): A list of instance IDs to describe. If not provided, describes all instances.
        region_name (str, optional): The AWS region. If not provided, uses the default region.

    Returns:
        dict: Information about the instances.
    """
    ec2_client = get_aws_client('ec2', region_name=region_name)
    if instance_ids:
        response = ec2_client.describe_instances(InstanceIds=instance_ids)
    else:
        response = ec2_client.describe_instances()
    return response['Reservations']
