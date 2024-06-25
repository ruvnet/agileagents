# README.md

## Introduction

This README provides a guide to deploying and invoking an AWS Lambda function using FastAPI, Docker, and AWS ECR. It includes detailed instructions on the structure and approach for both the deployment JSON and the invocation JSON.

## Deployment JSON Structure

The deployment JSON is used to define the configuration for deploying a Lambda function. Below is an example of the deployment JSON structure and an explanation of each field.

### Example Deployment JSON

```json
{
    "repository_name": "complex-function-repo",
    "image_tag": "latest",
    "python_script": "import json\n\ndef lambda_handler(event, context):\n    name = event.get('name', 'World')\n    age = event.get('age', 'unknown')\n    response = {\n        'message': f'Hello {name}, you are {age} years old!',\n        'input_event': event\n    }\n    return {\n        'statusCode': 200,\n        'body': json.dumps(response)\n    }",
    "requirements": "",
    "function_name": "complex-function",
    "region": "us-west-2",
    "memory_size": 128,
    "timeout": 30
}
```

### Field Explanations

- **repository_name**: The name of the Docker repository in AWS ECR.
- **image_tag**: The tag for the Docker image.
- **python_script**: The Python script for the Lambda function. This script should include the `lambda_handler` function.
- **requirements**: A string of Python package requirements. This can be left empty if no additional packages are needed.
- **function_name**: The name of the Lambda function to be created or updated.
- **region**: The AWS region where the Lambda function will be deployed.
- **memory_size**: The memory size (in MB) allocated to the Lambda function.
- **timeout**: The timeout duration (in seconds) for the Lambda function.

## Invocation JSON Structure

The invocation JSON is used to define the parameters for invoking a deployed Lambda function. Below is an example of the invocation JSON structure and an explanation of each field.

### Example Invocation JSON

```json
{
  "function_name": "complex-function",
  "payload": {
    "name": "Alice",
    "age": 30
  },
  "region": "us-west-2"
}
```

### Field Explanations

- **function_name**: The name of the Lambda function to be invoked.
- **payload**: A JSON object containing the input parameters for the Lambda function.
- **region**: The AWS region where the Lambda function is deployed.

## Approach

### Deployment Approach

1. **Prepare Deployment JSON**: Create a deployment JSON file with the required fields.
2. **Deploy Lambda Function**:
   - Ensure Docker is running.
   - Create a virtual environment and install dependencies.
   - Write the Python script and requirements to temporary files.
   - Build the Docker image and push it to AWS ECR.
   - Create or update the Lambda function using the AWS Lambda API.

### Invocation Approach

1. **Prepare Invocation JSON**: Create an invocation JSON file with the required fields.
2. **Invoke Lambda Function**:
   - Use the AWS Lambda API to invoke the Lambda function.
   - Pass the invocation JSON payload to the Lambda function.
   - Parse and return the response from the Lambda function.

## Example Usage

### Deploying the Lambda Function

1. Save the deployment JSON to a file (e.g., `deploy.json`).
2. Use a script or a tool to deploy the Lambda function using the JSON configuration.

### Invoking the Lambda Function

1. Save the invocation JSON to a file (e.g., `invoke.json`).
2. Use a script or a tool to invoke the Lambda function using the JSON payload.

By following the above steps, you can deploy and invoke an AWS Lambda function using a structured and automated approach.


To create a function using Open Interpreter that handles a basic query, you can set up a Lambda function that uses the Open Interpreter library to respond to a prompt. Below are the deployment and invocation JSONs for a Lambda function that uses Open Interpreter to execute a basic Python command.

### Deployment JSON

```json
{
    "repository_name": "open-interpreter",
    "image_tag": "latest",
    "python_script": "from interpreter import interpreter\n\napi_key = os.environ['OPENAI_API_KEY']\ninterpreter.llm.api_key = api_key\n\nresponse = interpreter.chat('What is the capital of France?')\n\nwith open('/tmp/response.txt', 'w') as f:\n    f.write(response)\n\ndef lambda_handler(event, context):\n    with open('/tmp/response.txt', 'r') as f:\n        response = f.read()\n    return {\n        'statusCode': 200,\n        'body': json.dumps({'response': response})\n    }",
    "requirements": "open-interpreter\nrequests",
    "function_name": "open-interpreter-function",
    "region": "us-west-2",
    "memory_size": 1024,
    "timeout": 900,
    "environment_variables": {
        "OPENAI_API_KEY": "your_openai_api_key"
    }
}
```

### Invocation JSON

```json
{
    "function_name": "open-interpreter-function",
    "payload": {
        "OTHER_ENV_VAR": "some_value"
    },
    "region": "us-west-2"
}
```

### Explanation

- **Deployment JSON**: This sets up a Lambda function that initializes Open Interpreter with the OpenAI API key, asks it "What is the capital of France?", and stores the response in a temporary file. The `lambda_handler` function reads this file and returns the response as part of the API response.
- **Invocation JSON**: This invokes the Lambda function and expects the response containing the answer to the query. 

Make sure you replace `"your_openai_api_key"` with your actual OpenAI API key. This setup ensures that the Lambda function can handle queries via Open Interpreter and return the responses directly in the API response.