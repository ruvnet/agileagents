#!/bin/bash

# Function to list all regions
function list_regions {
    echo "Available AWS Regions:"
    aws ec2 describe-regions --query 'Regions[*].RegionName' --output text --no-cli-pager
}

# ECS Management Functions
function list_clusters {
    clusters=$(aws ecs list-clusters --query 'clusterArns' --output text --no-cli-pager)
    if [ -z "$clusters" ]; then
        echo "No clusters found."
    else
        for cluster in $clusters; do
            echo "Cluster: $cluster"
            services=$(aws ecs list-services --cluster $cluster --query 'serviceArns' --output text --no-cli-pager)
            if [ -z "$services" ]; then
                echo "  No services found in cluster $cluster."
            else
                for service in $services; do
                    echo "  Service: $service"
                    tasks=$(aws ecs list-tasks --cluster $cluster --service-name $service --query 'taskArns' --output text --no-cli-pager)
                    if [ -z "$tasks" ]; then
                        echo "    No tasks found in service $service."
                    else
                        for task in $tasks; do
                            echo "    Task: $task"
                        done
                    fi
                done
            fi
        done
    fi
}

function remove_cluster {
    read -p "Enter the ARN of the cluster you want to remove: " cluster_arn
    services=$(aws ecs list-services --cluster $cluster_arn --query 'serviceArns' --output text --no-cli-pager)
    
    for service in $services; do
        echo "Deleting service: $service"
        aws ecs update-service --cluster $cluster_arn --service $service --desired-count 0 --no-cli-pager
        echo "Waiting for service to stabilize..."
        aws ecs wait services-stable --cluster $cluster_arn --services $service --no-cli-pager || { echo "Failed to stabilize service: $service"; continue; }
        echo "Deleting the service..."
        aws ecs delete-service --cluster $cluster_arn --service $service --force --no-cli-pager
    done
    
    tasks=$(aws ecs list-tasks --cluster $cluster_arn --query 'taskArns' --output text --no-cli-pager)
    for task in $tasks; do
        echo "Stopping task: $task"
        aws ecs stop-task --cluster $cluster_arn --task $task --no-cli-pager || { echo "Failed to stop task: $task"; continue; }
        echo "Waiting for task to stop..."
        aws ecs wait tasks-stopped --cluster $cluster_arn --tasks $task --no-cli-pager || { echo "Failed to stop task: $task"; continue; }
    done
    
    echo "Deleting cluster: $cluster_arn"
    aws ecs delete-cluster --cluster $cluster_arn --no-cli-pager || { echo "Failed to delete cluster: $cluster_arn"; exit 1; }
    echo "Cluster $cluster_arn removed successfully."
}

# EC2 Management Functions
function list_instances {
    read -p "Enter the region to list instances: " region
    instances=$(aws ec2 describe-instances --region $region --query 'Reservations[*].Instances[*].InstanceId' --output text --no-cli-pager)
    if [ -z "$instances" ]; then
        echo "No instances found in region $region."
    else
        for instance in $instances; do
            echo "Instance: $instance"
        done
    fi
}

function list_running_instances {
    read -p "Enter the region to list running instances: " region
    instances=$(aws ec2 describe-instances --region $region --filters "Name=instance-state-name,Values=running" --query 'Reservations[*].Instances[*].{InstanceId:InstanceId,InstanceType:InstanceType,PrivateIpAddress:PrivateIpAddress,PublicIpAddress:PublicIpAddress,State:State.Name}' --output text --no-cli-pager)
    if [ -z "$instances" ]; then
        echo "No running instances found in region $region."
    else
        echo "$instances"
    fi
}

function terminate_instance {
    read -p "Enter the region: " region
    read -p "Enter the Instance ID to terminate: " instance_id
    echo "Terminating instance: $instance_id"
    aws ec2 terminate-instances --region $region --instance-ids $instance_id --output text --no-cli-pager
    echo "Waiting for instance to terminate..."
    aws ec2 wait instance-terminated --region $region --instance-ids $instance_id --no-cli-pager
    echo "Instance $instance_id terminated successfully."
}

function terminate_all_running_instances {
    read -p "Enter the region to terminate all running instances: " region
    instances=$(aws ec2 describe-instances --region $region --filters "Name=instance-state-name,Values=running" --query 'Reservations[*].Instances[*].InstanceId' --output text --no-cli-pager)
    if [ -z "$instances" ]; then
        echo "No running instances found in region $region."
    else
        for instance in $instances; do
            echo "Terminating instance: $instance"
            aws ec2 terminate-instances --region $region --instance-ids $instance --output text --no-cli-pager
        done
        echo "Waiting for all instances to terminate..."
        aws ec2 wait instance-terminated --region $region --instance-ids $instances --no-cli-pager
        echo "All running instances in region $region terminated successfully."
    fi
}

while true; do
    echo "1. List instances in a region"
    echo "2. List running instances in a region"
    echo "3. Terminate an instance"
    echo "4. Terminate all running instances"
    echo "5. List ECS clusters, services, and tasks"
    echo "6. Remove an ECS cluster"
    echo "7. List all regions"
    echo "8. Exit"
    read -p "Choose an option: " option

    case $option in
        1)
            list_instances
            ;;
        2)
            list_running_instances
            ;;
        3)
            terminate_instance
            ;;
        4)
            terminate_all_running_instances
            ;;
        5)
            list_clusters
            ;;
        6)
            remove_cluster
            ;;
        7)
            list_regions
            ;;
        8)
            exit 0
            ;;
        *)
            echo "Invalid option, please try again."
            ;;
    esac
done
