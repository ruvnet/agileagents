### Deployment JSON

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

### Invoke JSON

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

#venv works.
{
    "repository_name": "dynamic-code-execution-function",
    "image_tag": "latest",
    "python_script": "import json\nimport os\nimport subprocess\n\n\ndef lambda_handler(event, context):\n    try:\n        code = event.get('code')\n        temp_dir = '/tmp/deployment'\n        os.makedirs(temp_dir, exist_ok=True)\n\n        # Step 2: Write the Python script to a temporary file\n        python_script_path = os.path.join(temp_dir, 'script.py')\n        with open(python_script_path, 'w') as f:\n            f.write(code)\n\n        # Step 3: Write the requirements to a file\n        requirements_path = os.path.join(temp_dir, 'requirements.txt')\n        with open(requirements_path, 'w') as f:\n            f.write('')  # Assuming no specific requirements for now\n\n        # Step 4: Create a virtual environment\n        subprocess.run(['python3', '-m', 'venv', 'venv'], check=True, cwd=temp_dir)\n\n        # Step 5: Install dependencies\n        result = subprocess.run(\n            ['venv/bin/pip', 'install', '-r', requirements_path],\n            capture_output=True,\n            text=True,\n            cwd=temp_dir\n        )\n\n        # Check if the pip install command failed\n        if result.returncode != 0:\n            return {\n                'statusCode': 500,\n                'error': 'pip install failed',\n                'stdout': result.stdout,\n                'stderr': result.stderr\n            }\n\n        # Step 6: Execute the script within the virtual environment\n        exec_result = subprocess.run(\n            ['venv/bin/python', python_script_path],\n            capture_output=True,\n            text=True,\n            cwd=temp_dir\n        )\n\n        return {\n            'statusCode': 200,\n            'stdout': exec_result.stdout,\n            'stderr': exec_result.stderr\n        }\n\n    except subprocess.CalledProcessError as e:\n        return {\n            'statusCode': 500,\n            'error': str(e)\n        }\n    except Exception as e:\n        return {\n            'statusCode': 500,\n            'error': str(e)\n        }",
    "requirements": "",
    "function_name": "dynamic-code-execution-function",
    "region": "us-west-2",
    "memory_size": 128,
    "timeout": 900
}

## request
{
    "function_name": "dynamic-code-execution-function",
    "region": "us-west-2",
    "payload": {
        "code": "print('Hello from the dynamically executed code!')"
    }
}

