#!/bin/bash

function list_regions {
    echo "Available AWS Regions:"
    aws ec2 describe-regions --query 'Regions[*].[RegionName]' --output text --no-cli-pager
}

function list_instances {
    read -p "Enter the region to list instances: " region
    instances=$(aws ec2 describe-instances --region $region --query 'Reservations[*].Instances[?State.Name!=`terminated`].InstanceId' --output text --no-cli-pager)
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
    instances=$(aws ec2 describe-instances --region $region --filters "Name=instance-state-name,Values=running" --query 'Reservations[*].Instances[*].{InstanceId:InstanceId,InstanceType:InstanceType,State:State.Name,PublicIpAddress:PublicIpAddress,PrivateIpAddress:PrivateIpAddress}' --output table --no-cli-pager)
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
    
    # Retry mechanism
    max_retries=5
    retry_count=0
    success=false

    while [ $retry_count -lt $max_retries ]; do
        instance_state=$(aws ec2 describe-instances --region $region --instance-ids $instance_id --query 'Reservations[*].Instances[*].State.Name' --output text --no-cli-pager)
        if [ "$instance_state" == "terminated" ]; then
            success=true
            break
        fi
        echo "Instance state: $instance_state. Retrying... ($((retry_count+1))/$max_retries)"
        retry_count=$((retry_count+1))
        sleep 5  # Wait for 5 seconds before retrying
    done

    if $success; then
        echo "Instance $instance_id terminated successfully."
    else
        echo "Failed to terminate instance $instance_id within the expected time."
    fi
}

function terminate_all_instances {
    read -p "Enter the region to terminate all running instances: " region
    instances=$(aws ec2 describe-instances --region $region --filters "Name=instance-state-name,Values=running" --query 'Reservations[*].Instances[*].InstanceId' --output text --no-cli-pager)
    if [ -z "$instances" ]; then
        echo "No running instances found in region $region."
        return
    fi

    for instance in $instances; do
        echo "Terminating instance: $instance"
        aws ec2 terminate-instances --region $region --instance-ids $instance --output text --no-cli-pager
        echo "Waiting for instance $instance to terminate..."
        
        # Retry mechanism
        max_retries=5
        retry_count=0
        success=false

        while [ $retry_count -lt $max_retries ]; do
            instance_state=$(aws ec2 describe-instances --region $region --instance-ids $instance --query 'Reservations[*].Instances[*].State.Name' --output text --no-cli-pager)
            if [ "$instance_state" == "terminated" ]; then
                success=true
                break
            fi
            echo "Instance state: $instance_state. Retrying... ($((retry_count+1))/$max_retries)"
            retry_count=$((retry_count+1))
            sleep 5  # Wait for 5 seconds before retrying
        done

        if $success; then
            echo "Instance $instance terminated successfully."
        else
            echo "Failed to terminate instance $instance within the expected time."
        fi
    done
}

while true; do
    echo "1. List instances in a region"
    echo "2. List running instances in a region"
    echo "3. Terminate an instance"
    echo "4. Terminate all running instances"
    echo "5. List all regions"
    echo "6. Exit"
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
            terminate_all_instances
            ;;
        5)
            list_regions
            ;;
        6)
            exit 0
            ;;
        *)
            echo "Invalid option, please try again."
            ;;
    esac
done
