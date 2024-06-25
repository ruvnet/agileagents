#!/bin/bash

# List all clusters
CLUSTERS=$(aws ecs list-clusters --query 'clusterArns' --output text)

# Iterate over each cluster
for CLUSTER in $CLUSTERS; do
    echo "Cluster: $CLUSTER"
    
    # List all services in the cluster
    SERVICES=$(aws ecs list-services --cluster $CLUSTER --query 'serviceArns' --output text)
    
    # Iterate over each service
    for SERVICE in $SERVICES; do
        echo "  Service: $SERVICE"
        
        # List all tasks in the service
        TASKS=$(aws ecs list-tasks --cluster $CLUSTER --service-name $SERVICE --query 'taskArns' --output text)
        
        # Iterate over each task
        for TASK in $TASKS; do
            echo "    Task: $TASK"
            
            # Describe the task to get detailed information
            aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK --query 'tasks[*].{TaskArn:taskArn,ContainerInstanceArn:containerInstanceArn,LastStatus:lastStatus,DesiredStatus:desiredStatus,StartedAt:startedAt}'
        done
    done
done
