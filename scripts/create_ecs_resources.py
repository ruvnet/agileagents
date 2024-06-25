# create_ecs_resources.py creates ECS resources including a cluster, task definition, and service.

import boto3
import os

AWS_REGION = 'us-west-2'
CLUSTER_NAME = 'my_video_processor_cluster'
TASK_DEFINITION_NAME = 'my_video_processor_task'
SERVICE_NAME = 'my_video_processor_service'
ECR_REPOSITORY = 'my_video_processor_repo'
IMAGE_TAG = 'latest'

def create_ecs_resources():
    client = boto3.client('ecs', region_name=AWS_REGION)

    # Create ECS Cluster
    client.create_cluster(clusterName=CLUSTER_NAME)

    # Register Task Definition
    response = client.register_task_definition(
        family=TASK_DEFINITION_NAME,
        networkMode='awsvpc',
        containerDefinitions=[
            {
                'name': 'my_video_processor_container',
                'image': f'{os.environ["AWS_ACCOUNT_ID"]}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPOSITORY}:{IMAGE_TAG}',
                'memory': 512,
                'cpu': 256,
                'essential': True,
                'portMappings': [
                    {
                        'containerPort': 5000,
                        'hostPort': 5000,
                        'protocol': 'tcp'
                    }
                ],
                'environment': [
                    {'name': 'OPENAI_API_KEY', 'value': os.environ['OPENAI_API_KEY']},
                    {'name': 'RTSP_STREAM_URL', 'value': os.environ['RTSP_STREAM_URL']},
                    {'name': 'FRAME_RATE', 'value': os.environ['FRAME_RATE']}
                ]
            }
        ],
        requiresCompatibilities=['FARGATE'],
        executionRoleArn=os.environ['EXECUTION_ROLE_ARN'],
        taskRoleArn=os.environ['TASK_ROLE_ARN'],
        memory='1024',
        cpu='512'
    )

    # Create ECS Service
    client.create_service(
        cluster=CLUSTER_NAME,
        serviceName=SERVICE_NAME,
        taskDefinition=TASK_DEFINITION_NAME,
        desiredCount=1,
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': [os.environ['SUBNET_ID']],
                'assignPublicIp': 'ENABLED'
            }
        }
    )

if __name__ == "__main__":
    create_ecs_resources()