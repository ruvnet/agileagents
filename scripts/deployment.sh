#!/bin/bash

set -e

# Variables
AWS_REGION="us-east-1"
ECR_REPOSITORY="my_video_processor_repo"
CLUSTER_NAME="my_video_processor_cluster"
TASK_DEFINITION_NAME="my_video_processor_task"
SERVICE_NAME="my_video_processor_service"
IMAGE_TAG="latest"

function create_iam_role {
    echo "Creating IAM Role..."
    if ! aws iam get-role --role-name ecsTaskExecutionRole --output text --no-cli-pager > /dev/null 2>&1; then
        aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://scripts/ecs-trust-policy.json --output text --no-cli-pager
        aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy --output text --no-cli-pager
    else
        echo "ECS Task Execution Role already exists."
    fi
}

function create_cluster {
    echo "Creating ECS Cluster..."
    if ! aws ecs describe-clusters --clusters $CLUSTER_NAME --output text --no-cli-pager | grep "CLUSTERARNS" > /dev/null 2>&1; then
        aws ecs create-cluster --cluster-name $CLUSTER_NAME --output text --no-cli-pager
    else
        echo "ECS Cluster already exists."
    fi
}

function create_vpc {
    echo "Checking VPC..."
    VPC_ID=$(aws ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text --no-cli-pager)
    if [ -z "$VPC_ID" ]; then
        VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text --no-cli-pager)
    else
        echo "Using existing VPC: $VPC_ID"
    fi
}

function create_subnet {
    echo "Checking Subnet..."
    SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text --no-cli-pager)
    if [ -z "$SUBNET_ID" ]; then
        SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --query 'Subnet.SubnetId' --output text --no-cli-pager)
    else
        echo "Using existing Subnet: $SUBNET_ID"
    fi
}

function create_security_group {
    echo "Checking Security Group..."
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=ecs-sg" --query 'SecurityGroups[0].GroupId' --output text --no-cli-pager)
    if [ -z "$SECURITY_GROUP_ID" ]; then
        SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name ecs-sg --description "ECS Security Group" --vpc-id $VPC_ID --query 'GroupId' --output text --no-cli-pager)
        aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 5000 --cidr 0.0.0.0/0 --output text --no-cli-pager
    else
        echo "Using existing Security Group: $SECURITY_GROUP_ID"
    fi
}

function create_ecr_repository {
    echo "Creating ECR Repository..."
    if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --output text --no-cli-pager > /dev/null 2>&1; then
        aws ecr create-repository --repository-name $ECR_REPOSITORY --output text --no-cli-pager
    else
        echo "ECR Repository already exists."
    fi
}

function docker_authenticate {
    echo "Authenticating Docker to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query 'Account' --output text --no-cli-pager).dkr.ecr.$AWS_REGION.amazonaws.com
}

function build_and_push_docker_image {
    echo "Building and pushing Docker image..."
    if [ -d "../src" ]; then
        docker build -t $ECR_REPOSITORY:$IMAGE_TAG ../src
        docker tag $ECR_REPOSITORY:$IMAGE_TAG $(aws sts get-caller-identity --query 'Account' --output text --no-cli-pager).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
        docker push $(aws sts get-caller-identity --query 'Account' --output text --no-cli-pager).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
    else
        echo "Directory ../src not found. Docker build skipped."
    fi
}

function register_task_definition {
    echo "Registering ECS Task Definition..."
    TASK_ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text --no-cli-pager)
    aws ecs register-task-definition --family $TASK_DEFINITION_NAME \
        --network-mode awsvpc \
        --execution-role-arn $TASK_ROLE_ARN \
        --container-definitions "[
            {
                \"name\": \"my_video_processor_container\",
                \"image\": \"$(aws sts get-caller-identity --query 'Account' --output text --no-cli-pager).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG\",
                \"memory\": 512,
                \"cpu\": 256,
                \"essential\": true,
                \"portMappings\": [
                    {
                        \"containerPort\": 5000,
                        \"hostPort\": 5000,
                        \"protocol\": \"tcp\"
                    }
                ],
                \"environment\": [
                    {\"name\": \"OPENAI_API_KEY\", \"value\": \"$OPENAI_API_KEY\"},
                    {\"name\": \"RTSP_STREAM_URL\", \"value\": \"$RTSP_STREAM_URL\"},
                    {\"name\": \"FRAME_RATE\", \"value\": \"$FRAME_RATE\"}
                ]
            }
        ]" \
        --requires-compatibilities FARGATE \
        --memory "1024" --cpu "512" --output text --no-cli-pager
}

function create_service {
    echo "Creating ECS Service..."
    if ! aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --output text --no-cli-pager | grep "SERVICEARNS" > /dev/null 2>&1; then
        aws ecs create-service --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --task-definition $TASK_DEFINITION_NAME \
            --desired-count 1 --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={
                subnets=[$SUBNET_ID],
                securityGroups=[$SECURITY_GROUP_ID],
                assignPublicIp=ENABLED
            }" --output text --no-cli-pager
    else
        echo "ECS Service already exists."
    fi
}

function automatic_deployment {
    create_iam_role
    create_cluster
    create_vpc
    create_subnet
    create_security_group
    create_ecr_repository
    docker_authenticate
    build_and_push_docker_image
    register_task_definition
    create_service
    echo "Deployment script completed successfully."
}

while true; do
    echo "1. Automatic deployment"
    echo "2. Create IAM Role"
    echo "3. Create ECS Cluster"
    echo "4. Create VPC"
    echo "5. Create Subnet"
    echo "6. Create Security Group"
    echo "7. Create ECR Repository"
    echo "8. Authenticate Docker to ECR"
    echo "9. Build and push Docker image"
    echo "10. Register ECS Task Definition"
    echo "11. Create ECS Service"
    echo "12. Exit"
    read -p "Choose an option: " option

    case $option in
        1)
            automatic_deployment
            ;;
        2)
            create_iam_role
            ;;
        3)
            create_cluster
            ;;
        4)
            create_vpc
            ;;
        5)
            create_subnet
            ;;
        6)
            create_security_group
            ;;
        7)
            create_ecr_repository
            ;;
        8)
            docker_authenticate
            ;;
        9)
            build_and_push_docker_image
            ;;
        10)
            register_task_definition
            ;;
        11)
            create_service
            ;;
        12)
            exit 0
            ;;
        *)
            echo "Invalid option, please try again."
            ;;
    esac
done