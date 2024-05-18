import gradio as gr
import requests
import json

# Define the base URL for the API
BASE_URL = "http://127.0.0.1:8000"

def get_regions():
    url = f"{BASE_URL}/misc/regions"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["regions"]
    else:
        return []

# Function to get lambda functions in a specific region
def get_lambda_functions(region):
    response = requests.get(f"{BASE_URL}/management/list-lambda-functions", params={"region": region})
    if response.status_code == 200:
        return response.json()["functions"]
    else:
        return []

# Function to update lambda functions dropdown based on selected region
def update_lambda_functions(region):
    functions = get_lambda_functions(region)
    if not functions:
        functions = ["No functions available"]
    return gr.Dropdown(choices=functions, interactive=True)

def get_cost_and_usage(granularity, time_period, metrics):
    url = f"{BASE_URL}/costs/get-cost-and-usage"
    payload = {
        "time_period": time_period,
        "metrics": metrics
    }
    params = {
        "granularity": granularity
    }
    response = requests.post(url, json=payload, params=params)
    return response.json()

def describe_budget(account_id, budget_name):
    url = f"{BASE_URL}/costs/describe-budget"
    payload = {
        "AccountId": account_id,
        "BudgetName": budget_name
    }
    response = requests.post(url, json=payload)
    return response.json()

def describe_report_definitions():
    url = f"{BASE_URL}/costs/describe-report-definitions"
    response = requests.get(url)
    return response.json()

def get_products(service_code, filters):
    url = f"{BASE_URL}/costs/get-products"
    params = {
        "service_code": service_code
    }
    response = requests.post(url, json=filters, params=params)
    return response.json()

def create_user(user_name):
    url = f"{BASE_URL}/iam/create-user"
    payload = {
        "user_name": user_name
    }
    response = requests.post(url, json=payload)
    return response.json()

def list_users():
    url = f"{BASE_URL}/iam/list-users"
    response = requests.get(url)
    return response.json()

def create_role(role_name, assume_role_policy_document):
    url = f"{BASE_URL}/iam/create-role"
    payload = {
        "role_name": role_name,
        "assume_role_policy_document": assume_role_policy_document
    }
    response = requests.post(url, json=payload)
    return response.json()

def attach_policy_to_role(role_name, policy_arn):
    url = f"{BASE_URL}/iam/attach-policy-to-role"
    params = {
        "role_name": role_name,
        "policy_arn": policy_arn
    }
    response = requests.post(url, params=params)
    return response.json()

def create_policy(policy_name, policy_document):
    url = f"{BASE_URL}/iam/create-policy"
    payload = {
        "policy_name": policy_name,
        "policy_document": policy_document
    }
    response = requests.post(url, json=payload)
    return response.json()

def assume_role(role_arn, role_session_name):
    url = f"{BASE_URL}/iam/assume-role"
    payload = {
        "role_arn": role_arn,
        "role_session_name": role_session_name
    }
    response = requests.post(url, json=payload)
    return response.json()

def create_access_key(user_name):
    url = f"{BASE_URL}/iam/create-access-key"
    payload = {
        "user_name": user_name
    }
    response = requests.post(url, json=payload)
    return response.json()

def deploy_multiple_functions(repository_name, image_tag, function_name_prefix, number_of_functions, vpc_id, subnet_ids, security_group_ids, region, log_retention_days):
    url = f"{BASE_URL}/management/deploy-multiple-functions"
    payload = {
        "repository_name": repository_name,
        "image_tag": image_tag,
        "function_name_prefix": function_name_prefix,
        "number_of_functions": number_of_functions,
        "vpc_id": vpc_id,
        "subnet_ids": subnet_ids,
        "security_group_ids": security_group_ids,
        "region": region,
        "log_retention_days": log_retention_days
    }
    response = requests.post(url, json=payload)
    return response.json()


def invoke_lambda(function_name, region):
    url = f"{BASE_URL}/management/invoke-lambda"
    params = {
        "function_name": function_name,
        "region": region
    }
    response = requests.get(url, params=params)
    return response.json()


def invoke_multiple_functions(function_name_prefix, number_of_functions, payload, region):
    url = f"{BASE_URL}/management/invoke-multiple-functions"
    try:
        payload_dict = json.loads(payload)  # Convert JSON string to dictionary
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format for payload"}
    
    payload_data = {
        "function_name_prefix": function_name_prefix,
        "number_of_functions": number_of_functions,
        "payload": payload_dict,
        "region": region
    }
    response = requests.post(url, json=payload_data)
    return response.json()

def list_lambda_functions(region):
    url = f"{BASE_URL}/management/list-lambda-functions"
    params = {
        "region": region
    }
    response = requests.get(url, params=params)
    return response.json()

def delete_lambda_function(function_name, region):
    url = f"{BASE_URL}/management/delete-lambda-function"
    params = {
        "function_name": function_name,
        "region": region
    }
    response = requests.delete(url, params=params)
    return response.json()

def list_ecr_repositories():
    url = f"{BASE_URL}/management/list-ecr-repositories"
    response = requests.get(url)
    return response.json()

def delete_ecr_repository(repository_name):
    url = f"{BASE_URL}/management/delete-ecr-repository"
    params = {
        "repository_name": repository_name
    }
    response = requests.delete(url, params=params)
    return response.json()

def get_s3_buckets():
    url = f"{BASE_URL}/management/s3-buckets"
    response = requests.get(url)
    return response.json()

def upload_to_s3(file_name, bucket_name, object_name):
    url = f"{BASE_URL}/management/upload-to-s3"
    params = {
        "file_name": file_name,
        "bucket_name": bucket_name,
        "object_name": object_name
    }
    response = requests.post(url, params=params)
    return response.json()

def create_ec2_instance(image_id, instance_type, key_name, security_group, region_name):
    url = f"{BASE_URL}/management/create-ec2-instance"
    params = {
        "image_id": image_id,
        "instance_type": instance_type,
        "key_name": key_name,
        "security_group": security_group,
        "region_name": region_name
    }
    response = requests.post(url, params=params)
    return response.json()

def get_ec2_instances(instance_ids, region_name):
    url = f"{BASE_URL}/management/ec2-instances"
    params = {
        "region_name": region_name
    }
    payload = instance_ids
    response = requests.get(url, json=payload, params=params)
    return response.json()

def list_regions():
    url = f"{BASE_URL}/misc/regions"
    response = requests.get(url)
    return response.json()

def list_foundation_models(region):
    url = f"{BASE_URL}/bedrock/list-foundation-models"
    params = {
        "region": region
    }
    response = requests.get(url, params=params)
    return response.json()

def invoke_model(model_id, region, prompt, max_tokens_to_sample, temperature, top_p):
    url = f"{BASE_URL}/bedrock/invoke-model"
    params = {
        "model_id": model_id,
        "region": region
    }
    payload = {
        "prompt": prompt,
        "max_tokens_to_sample": max_tokens_to_sample,
        "temperature": temperature,
        "top_p": top_p
    }
    response = requests.post(url, json=payload, params=params)
    return response.json()

def deploy(repository_name, image_tag, python_script, requirements, function_name, region, vpc_id, subnet_ids, security_group_ids):
    url = f"{BASE_URL}/deployment/deploy"
    payload = {
        "repository_name": repository_name,
        "image_tag": image_tag,
        "python_script": python_script,
        "requirements": requirements,
        "function_name": function_name,
        "region": region,
        "vpc_id": vpc_id,
        "subnet_ids": subnet_ids,
        "security_group_ids": security_group_ids
    }
    response = requests.post(url, json=payload)
    return response.json()

def advanced_deploy(repository_name, image_tag, base_image, build_commands, function_name, region, vpc_id, subnet_ids, security_group_ids, files):
    url = f"{BASE_URL}/deployment/advanced-deploy"
    payload = {
        "repository_name": repository_name,
        "image_tag": image_tag,
        "base_image": base_image,
        "build_commands": build_commands,
        "function_name": function_name,
        "region": region,
        "vpc_id": vpc_id,
        "subnet_ids": subnet_ids,
        "security_group_ids": security_group_ids,
        "files": files
    }
    response = requests.post(url, json=payload)
    return response.json()

# Define the Gradio interface
def create_gradio_interface():
    regions_list = get_regions()
    
    with gr.Blocks() as app:
        with gr.Tab("Dashboard"):
            gr.Markdown(
                """
                # Agile Agents Dashboard
                Welcome to the Agile Agents Dashboard. Use the tabs to navigate through the different functionalities available.
                """
            )
            with gr.Accordion("Quick Links"):
                gr.Markdown(
                    """
                    - **[Management](#Management)**: Manage AWS resources.
                    - **[Deployment](#Deployment)**: Deploy and manage deployments.
                    - **[Misc](#Misc)**: Miscellaneous operations.
                    - **[Bedrock](#Bedrock)**: Interact with foundation models.
                    - **[IAM](#IAM)**: Manage IAM users, roles, and policies.
                    """
                )

        with gr.Tab("Management"):
            with gr.Column():
                gr.Markdown("## Manage your AWS resources efficiently with these tools and operations.")
                
                with gr.Tab("Function Management"):
                    with gr.Column():
                        with gr.Tab("Deploy Functions"):
                            gr.Markdown("Deploy multiple AWS Lambda functions with the provided configuration.")
                            repository_name = gr.Textbox(label="Repository Name", placeholder="my_repository")
                            image_tag = gr.Textbox(label="Image Tag", placeholder="latest")
                            function_name_prefix = gr.Textbox(label="Function Name Prefix", placeholder="my_lambda_function")
                            number_of_functions = gr.Number(label="Number of Functions", value=0)
                            vpc_id = gr.Textbox(label="VPC ID (optional)")
                            subnet_ids = gr.Textbox(label="Subnet IDs (optional)", placeholder='["subnet-12345678"]')
                            security_group_ids = gr.Textbox(label="Security Group IDs (optional)", placeholder='["sg-12345678"]')
                            region = gr.Dropdown(label="Region", choices=regions_list, value="us-east-1")
                            log_retention_days = gr.Number(label="Log Retention Days", value=7)
                            gr.Button("Deploy Multiple Functions").click(deploy_multiple_functions, inputs=[
                                repository_name, image_tag, function_name_prefix, number_of_functions,
                                vpc_id, subnet_ids, security_group_ids, region, log_retention_days
                            ], outputs=gr.JSON())

                        with gr.Tab("Invoke Functions"):
                            gr.Markdown("### Invoke Multiple Functions")
                            gr.Markdown("Invoke one or multiple AWS Lambda functions.")
                            region_invoke = gr.Dropdown(label="Region", choices=regions_list, value="us-east-1")
                            functions_state = gr.State([])
                            function_name_prefix = gr.Dropdown(label="Function Name Prefix", choices=[], interactive=True)
                            region_invoke.change(fn=update_lambda_functions, inputs=region_invoke, outputs=function_name_prefix)
                            number_of_functions = gr.Number(label="Number of Functions", value=0)
                            payload = gr.Textbox(label="Payload", placeholder='{"key1": "value1", "key2": "value2"}', value='{"key1": "value1", "key2": "value2"}')
                            gr.Button("Invoke Multiple Functions").click(invoke_multiple_functions, inputs=[
                                function_name_prefix, number_of_functions, payload, region_invoke
                            ], outputs=gr.JSON())

                            gr.Markdown("#### Invoke Lambda")
                            gr.Markdown("Invoke a specific AWS Lambda function.")
                            region_invoke_lambda = gr.Dropdown(label="Region", choices=regions_list, value="us-east-1")
                            functions_state_invoke = gr.State([])
                            function_name_invoke = gr.Dropdown(label="Function Name", choices=[], interactive=True)
                            region_invoke_lambda.change(fn=update_lambda_functions, inputs=region_invoke_lambda, outputs=function_name_invoke)
                            gr.Button("Invoke Lambda").click(invoke_lambda, inputs=[function_name_invoke, region_invoke_lambda], outputs=gr.JSON())
        
 
                        with gr.Tab("Manage Functions"):                            
                            gr.Markdown("#### List Lambda Functions")
                            gr.Markdown("List all AWS Lambda functions in a specified region.")
                            region_list = gr.Dropdown(label="Region", choices=regions_list, value="us-east-1")
                            gr.Button("List Lambda Functions").click(list_lambda_functions, inputs=[region_list], outputs=gr.JSON())

                            gr.Markdown("#### Delete Lambda Function")
                            gr.Markdown("Delete a specified AWS Lambda function.")
                            region_delete = gr.Dropdown(label="Region", choices=regions_list, value="us-east-1")
                            functions_state_delete = gr.State([])
                            function_name_delete = gr.Dropdown(label="Function Name", choices=[], interactive=True)
                            region_delete.change(fn=update_lambda_functions, inputs=region_delete, outputs=function_name_delete)
                            gr.Button("Delete Lambda Function").click(delete_lambda_function, inputs=[function_name_delete, region_delete], outputs=gr.JSON())

                with gr.Tab("ECR Management"):
                    with gr.Column():
                        gr.Markdown("### ECR Management")
                        gr.Markdown("Manage your Elastic Container Registry (ECR) repositories.")
                        
                        gr.Markdown("#### List ECR Repositories")
                        gr.Markdown("List all your ECR repositories.")
                        gr.Button("List ECR Repositories").click(list_ecr_repositories, outputs=gr.JSON())
                        
                        gr.Markdown("#### Delete ECR Repository")
                        gr.Markdown("Delete a specified ECR repository.")
                        repository_name = gr.Textbox(label="Repository Name", placeholder="my_repository")
                        gr.Button("Delete ECR Repository").click(delete_ecr_repository, inputs=[repository_name], outputs=gr.JSON())

                with gr.Tab("S3 Management"):
                    with gr.Column():
                        gr.Markdown("### S3 Management")
                        gr.Markdown("Manage your Amazon S3 buckets and objects.")
                        
                        gr.Markdown("#### List S3 Buckets")
                        gr.Markdown("List all your S3 buckets.")
                        gr.Button("Get S3 Buckets").click(get_s3_buckets, outputs=gr.JSON())
                        
                        gr.Markdown("#### Upload to S3")
                        gr.Markdown("Upload a file to a specified S3 bucket.")
                        file_name = gr.Textbox(label="File Name", placeholder="file.txt")
                        bucket_name = gr.Textbox(label="Bucket Name", placeholder="my_bucket")
                        object_name = gr.Textbox(label="Object Name (optional)")
                        gr.Button("Upload to S3").click(upload_to_s3, inputs=[file_name, bucket_name, object_name], outputs=gr.JSON())

                with gr.Tab("EC2 Management"):
                    with gr.Column():
                        gr.Markdown("### EC2 Management")
                        gr.Markdown("Manage your EC2 instances.")
                        
                        gr.Markdown("#### Create EC2 Instance")
                        gr.Markdown("Create a new EC2 instance with the provided configuration.")
                        image_id = gr.Textbox(label="Image ID", placeholder="ami-12345678")
                        instance_type = gr.Textbox(label="Instance Type", placeholder="t2.micro")
                        key_name = gr.Textbox(label="Key Name", placeholder="my_key_pair")
                        security_group = gr.Textbox(label="Security Group", placeholder="default")
                        region_name = gr.Dropdown(label="Region Name (optional)", choices=regions_list, value="us-east-1")
                        gr.Button("Create EC2 Instance").click(create_ec2_instance, inputs=[
                            image_id, instance_type, key_name, security_group, region_name
                        ], outputs=gr.JSON())

                        gr.Markdown("#### Get EC2 Instances")
                        gr.Markdown("Get details of your EC2 instances.")
                        instance_ids = gr.Textbox(label="Instance IDs (optional)", placeholder='["i-12345678"]')
                        region_name = gr.Dropdown(label="Region Name (optional)", choices=regions_list, value="us-east-1")
                        gr.Button("Get EC2 Instances").click(get_ec2_instances, inputs=[instance_ids, region_name], outputs=gr.JSON())

        with gr.Tab("Deployment"):
                with gr.Column():
                    gr.Markdown("## Manage your AWS deployments efficiently with these tools and operations.")
                    
                    with gr.Tab("Basic Deployment"):
                        gr.Markdown("### Basic Deployment")
                        gr.Markdown("Deploy an AWS Lambda function with the provided configuration.")
                        repository_name = gr.Textbox(label="Repository Name (required)", placeholder="my_repository")
                        image_tag = gr.Textbox(label="Image Tag (required)", placeholder="latest")
                        python_script = gr.Textbox(label="Python Script (required)", placeholder="main.py")
                        requirements = gr.Textbox(label="Requirements (required)", placeholder="requirements.txt")
                        function_name = gr.Textbox(label="Function Name (required)", placeholder="my_function")
                        region = gr.Dropdown(label="Region (optional)", choices=regions_list, value="us-east-1")
                        vpc_id = gr.Textbox(label="VPC ID (optional)", placeholder="vpc-12345678")
                        subnet_ids = gr.Textbox(label="Subnet IDs (optional)")
                        security_group_ids = gr.Textbox(label="Security Group IDs (optional)")
                        gr.Button("Deploy").click(deploy, inputs=[
                            repository_name, image_tag, python_script, requirements, function_name,
                            region, vpc_id, subnet_ids, security_group_ids
                        ], outputs=gr.JSON())

                    with gr.Tab("Advanced Deployment"):
                        gr.Markdown("### Advanced Deployment")
                        gr.Markdown("Deploy an AWS Lambda function with advanced configuration options.")
                        repository_name = gr.Textbox(label="Repository Name (required)", placeholder="my_repository")
                        image_tag = gr.Textbox(label="Image Tag (required)", placeholder="latest")
                        base_image = gr.Textbox(label="Base Image (required)", placeholder="base_image")
                        build_commands = gr.Textbox(label="Build Commands (required)")
                        function_name = gr.Textbox(label="Function Name (required)", placeholder="my_function")
                        region = gr.Dropdown(label="Region (optional)", choices=regions_list, value="us-east-1")
                        vpc_id = gr.Textbox(label="VPC ID (optional)", placeholder="vpc-12345678")
                        subnet_ids = gr.Textbox(label="Subnet IDs (optional)")
                        security_group_ids = gr.Textbox(label="Security Group IDs (optional)")
                        files = gr.File(label="Files (required)", file_count="multiple")
                        gr.Button("Advanced Deploy").click(advanced_deploy, inputs=[
                            repository_name, image_tag, base_image, build_commands, function_name,
                            region, vpc_id, subnet_ids, security_group_ids, files
                        ], outputs=gr.JSON())


        with gr.Tab("Misc"):
            with gr.Accordion("Miscellaneous Operations"):
                gr.Button("List Regions").click(list_regions, outputs=gr.JSON())

        with gr.Tab("Bedrock"):
            with gr.Accordion("Bedrock Operations"):
                with gr.Tab("Foundation Models"):
                    region = gr.Textbox(label="Region (optional)", placeholder="us-east-1")
                    gr.Button("List Foundation Models").click(list_foundation_models, inputs=[region], outputs=gr.JSON())

                with gr.Tab("Invoke Model"):
                    model_id = gr.Textbox(label="Model ID", placeholder="foundation_model_id")
                    region = gr.Textbox(label="Region (optional)", placeholder="us-east-1")
                    prompt = gr.Textbox(label="Prompt", placeholder="Your prompt here")
                    max_tokens_to_sample = gr.Number(label="Max Tokens to Sample", value=300)
                    temperature = gr.Number(label="Temperature", value=0.1)
                    top_p = gr.Number(label="Top P", value=0.9)
                    gr.Button("Invoke Model").click(invoke_model, inputs=[model_id, region, prompt, max_tokens_to_sample, temperature, top_p], outputs=gr.JSON())

        with gr.Tab("IAM"):
            with gr.Accordion("IAM Operations"):
                with gr.Tab("User Management"):
                    user_name = gr.Textbox(label="User Name", placeholder="new_user")
                    gr.Button("Create User").click(create_user, inputs=[user_name], outputs=gr.JSON())
                    
                    gr.Button("List Users").click(list_users, outputs=gr.JSON())

                with gr.Tab("Role Management"):
                    role_name = gr.Textbox(label="Role Name", placeholder="new_role")
                    assume_role_policy_document = gr.JSON(label="Assume Role Policy Document")
                    gr.Button("Create Role").click(create_role, inputs=[role_name, assume_role_policy_document], outputs=gr.JSON())

                    role_name = gr.Textbox(label="Role Name", placeholder="existing_role")
                    policy_arn = gr.Textbox(label="Policy ARN", placeholder="arn:aws:iam::aws:policy/AdministratorAccess")
                    gr.Button("Attach Policy To Role").click(attach_policy_to_role, inputs=[role_name, policy_arn], outputs=gr.JSON())

                    policy_name = gr.Textbox(label="Policy Name", placeholder="new_policy")
                    policy_document = gr.JSON(label="Policy Document")
                    gr.Button("Create Policy").click(create_policy, inputs=[policy_name, policy_document], outputs=gr.JSON())

                    role_arn = gr.Textbox(label="Role ARN", placeholder="arn:aws:iam::123456789012:role/role_name")
                    role_session_name = gr.Textbox(label="Role Session Name", placeholder="session_name")
                    gr.Button("Assume Role").click(assume_role, inputs=[role_arn, role_session_name], outputs=gr.JSON())

                with gr.Tab("Access Key Management"):
                    user_name = gr.Textbox(label="User Name", placeholder="existing_user")
                    gr.Button("Create Access Key").click(create_access_key, inputs=[user_name], outputs=gr.JSON())

    return app

if __name__ == "__main__":
    create_gradio_interface().launch(server_name="0.0.0.0", server_port=7860)
