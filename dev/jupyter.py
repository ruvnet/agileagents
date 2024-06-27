import os
import sys
import time
import re
import json
import logging
import lzstring
import httpx
import traceback

import threading
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jupyter_client import KernelManager
from io import StringIO
from litellm import completion

from urllib.parse import quote
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Initialize logger
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

app = FastAPI()

class RedirectToDocsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/":
            return RedirectResponse(url="/docs")
        response = await call_next(request)
        return response

app.add_middleware(RedirectToDocsMiddleware)

class CodeRequest(BaseModel):
    code: str

class PromptRequest(BaseModel):
    prompt: str

class SessionRegistry:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()

    def add_session(self, session_id, output, url):
        with self.lock:
            self.sessions[session_id] = {"output": output, "url": url}

    def get_session(self, session_id):
        with self.lock:
            return self.sessions.get(session_id)

    def remove_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]

registry = SessionRegistry()

def run_gradio_session(code, session_id, result_event):
    km = KernelManager()
    try:
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
    except Exception as e:
        print(f"Kernel startup error: {e}")
        registry.add_session(session_id, f"Kernel startup error: {e}", "")
        result_event.set()  # Signal that an error occurred
        return

    try:
        kc.execute(code)
        output = ""
        public_url = ""
        while True:
            try:
                msg = kc.get_iopub_msg(timeout=10)
                msg_type = msg['header']['msg_type']
                content = msg['content']

                print(f"Message received: {msg}")  # Debugging information

                if msg_type == 'stream':
                    output += content['text'] + "\n"
                elif msg_type in ['display_data', 'execute_result']:
                    if 'text/plain' in content['data']:
                        output += content['data']['text/plain'] + "\n"
                    if 'text/html' in content['data']:
                        output += content['data']['text/html'] + "\n"
                        # Extract URL from iframe src
                        match = re.search(r'src=\"(https://[^\"]+)\"', content['data']['text/html'])
                        if match:
                            public_url = match.group(1)
                        registry.add_session(session_id, output, public_url)
                        result_event.set()  # Signal that the result is ready
                        break  # Stop once we get the URL
                elif msg_type == 'status' and content['execution_state'] == 'idle':
                    break  # Stop once execution is idle
                elif msg_type == 'error':
                    print(f"Error message received: {content['evalue']}")
                    registry.add_session(session_id, f"Error: {content['evalue']}", "")
                    result_event.set()  # Signal that an error occurred
                    return
            except Exception as e:
                print(f"Exception while getting message: {e}")
                registry.add_session(session_id, f"Exception: {e}", "")
                result_event.set()  # Signal that an error occurred
                return

        # Set the event to allow immediate response from the main thread
        registry.add_session(session_id, output, public_url)
        result_event.set()

        # Keep the process running indefinitely to keep Gradio session alive
        while True:
            time.sleep(1)

    except Exception as e:
        print(f"Execution error: {e}")
        registry.add_session(session_id, f"Execution error: {e}", "")
        result_event.set()  # Signal that an error occurred
    finally:
        try:
            kc.stop_channels()
            km.shutdown_kernel()
        except Exception as e:
            print(f"Error during kernel shutdown: {e}")
            registry.add_session(session_id, f"Error during kernel shutdown: {e}", "")
            result_event.set()

@app.post("/run_code/")
async def run_code(request: CodeRequest):
    if "gradio" not in request.code:
        # Execute non-Gradio code directly
        original_stdout = sys.stdout  # Save a reference to the original standard output
        sys.stdout = StringIO()  # Redirect standard output to a StringIO object
        try:
            exec(request.code)
            output = sys.stdout.getvalue()  # Retrieve the output from the StringIO object
        except Exception as e:
            sys.stdout = original_stdout  # Reset the standard output to its original value
            raise HTTPException(status_code=400, detail=f"Code execution error: {e}")
        finally:
            sys.stdout = original_stdout  # Ensure the standard output is reset to its original value
        
        return {"output": output}
    
    # For Gradio-related code, handle sessions
    session_id = str(time.time())
    result_event = threading.Event()
    thread = threading.Thread(target=run_gradio_session, args=(request.code, session_id, result_event))
    thread.start()

    # Return the session ID immediately
    if result_event.wait(timeout=10):  # Allow some time to initialize
        session_info = registry.get_session(session_id)
        if session_info:
            return {
                "output": session_info["output"],
                "url": session_info["url"],
                "session_id": session_id,
                "activity_duration": "72 hours"
            }
        else:
            return {"output": "Session started, but no output yet.", "url": "", "session_id": session_id}
    else:
        return {"output": "Timeout waiting for session start.", "url": "", "session_id": session_id}

@app.get("/session/{session_id}")
async def get_session_update(session_id: str):
    session_info = registry.get_session(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "output": session_info["output"],
        "url": session_info["url"],
        "session_id": session_id,
        "activity_duration": "72 hours"
    }

def kill_process_on_port(port):
    try:
        # Find the PID of the process using the port
        result = subprocess.run(["lsof", "-t", f"-i:{port}"], capture_output=True, text=True)
        pids = result.stdout.strip().split()
        for pid in pids:
            # Check the process name to avoid killing unintended processes
            process_name = subprocess.run(["ps", "-p", pid, "-o", "comm="], capture_output=True, text=True).stdout.strip()
            if process_name in ["uvicorn", "python"]:
                os.kill(int(pid), 9)
                print(f"Killed process {pid} ({process_name}) on port {port}")
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")

@app.post("/gradio_ui/")
async def gradio_ui(request: CodeRequest):
    session_id = str(time.time())
    code_with_gradio = request.code + "\n\nurl = iface.launch(share=True)\nprint(\"Public URL:\", url)"
    result_event = threading.Event()
    thread = threading.Thread(target=run_gradio_session, args=(code_with_gradio, session_id, result_event))
    thread.start()

    # Return the session ID immediately
    if result_event.wait(timeout=10):  # Allow some time to initialize
        session_info = registry.get_session(session_id)
        if session_info:
            return {
                "output": session_info["output"],
                "url": session_info["url"],
                "session_id": session_id,
                "activity_duration": "72 hours"
            }
        else:
            return {"output": "Session started, but no output yet.", "url": "", "session_id": session_id}
    else:
        return {"output": "Timeout waiting for session start.", "url": "", "session_id": session_id}

@app.post("/generate_ui/")
async def generate_ui(request: PromptRequest):
    try:
        # Define the Gradio requirements
        gradio_requirements = """
        You are an expert in generating Gradio UIs. Include 'share=True' in the 'launch()' function. Respond only with the Python code. Ensure the code adheres to these requirements:
        - Use gr.Blocks() for building the UI.
        - Components: Textbox, Button, Slider, Row, Column, etc.
        - Event Handling: Use .click() or .change() methods for interactions.
        - Layout: Use gr.Row() and gr.Column() for layout.
         1. **Components**: Gradio supports various components including but not limited to:
        - `Textbox`: For text input/output.
        - `Dropdown`: For selection from a list of options.
        - `Checkbox`: For boolean input.
        - `Slider`: For numerical input with a range.
        - `Button`: For triggering actions.
        - `File`: For file uploads.
        - `Image`: For displaying images.
        - `Plot`: For displaying plots.
        - `DataFrame`: For displaying tabular data.
        - `Video`: For displaying videos.
        - `Audio`: For playing audio files.
        2. **Attributes**: Components have various attributes to customize their behavior:
            - `label`: Text label for the component.
            - `placeholder`: Placeholder text (for text inputs).
            - `choices`: List of choices (for dropdowns).
            - `value`: Default value.
            - `minimum` and `maximum`: Range for sliders.
            - `step`: Step size for sliders.
            - `interactive`: Boolean to enable/disable user interaction.
        3. **Layout**: Gradio supports flexible layouts using:
            - `gr.Row()`: To arrange components horizontally.
            - `gr.Column()`: To arrange components vertically.
            - `gr.Tabs()`: To create tabbed interfaces.
            - `gr.Accordion()`: To create collapsible sections.
        4. **Event Handling**: Components can trigger functions on events such as:
            - `click`: Triggered by a button click.
            - `change`: Triggered by a change in the component's value.
            - `submit`: Triggered by form submission.
        5. **Preprocessing and Postprocessing**: Components can automatically handle data conversion:
            - `type`: For `Image` components, valid types are 'numpy', 'pil', 'filepath'.
            - `fn`: The function to wrap a user interface around.
            - `inputs` and `outputs`: Specify the Gradio components used for input and output.
        6. **Advanced Features**: Gradio supports advanced features like:
            - `Blocks()`: For building complex layouts.
            - `Interface()`: For simple to complex function wrapping.
            - `launch(share=True)`: To enable sharing of the UI via a public link.
        7. Best Practices:
            - Always use unique and meaningful IDs for components.
            - Handle file uploads and data frames properly to avoid attribute errors.
            - Ensure all event handlers and callbacks are correctly defined and referenced.
            - Validate inputs and outputs to match expected data types and structures.
            - Test the UI for responsiveness and proper functionality across different devices and browsers.
            """
        
        # Generate the Gradio UI code using GPT-4o function calling
        response = completion(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": gradio_requirements},
                {"role": "user", "content": request.prompt}
            ],
            temperature=0.2,  # Lower temperature for more deterministic output
            top_p=0.9  # Lower top_p for more conservative output
        )

        # Log the full raw response from OpenAI for debugging
        print(f"Raw response from OpenAI: {response}")

        if response.choices[0].message.content:
            gradio_code = response.choices[0].message.content.strip("```python\n").strip("```")
            gradio_code += "\n\ndemo.launch(share=True)"

            # Log the generated Gradio code for debugging
            print(f"Generated Gradio code: {gradio_code}")

            # Prepare the request to /gradio_ui endpoint
            gradio_request_data = {"code": gradio_code}
            print(f"Posting to /gradio_ui with data: {gradio_request_data}")

            # Post the generated code to /gradio_ui endpoint
            async with httpx.AsyncClient(timeout=60.0) as client:  # Set a higher timeout value here
                max_attempts = 10
                for attempt in range(max_attempts):
                    try:
                        gradio_ui_response = await client.post("http://0.0.0.0:8000/gradio_ui/", json=gradio_request_data)
                        gradio_ui_response_data = gradio_ui_response.json()

                        if "error" in gradio_ui_response_data["output"].lower():
                            # Generate a prompt to fix the error
                            error_fix_prompt = (
                                f"The generated code produced an error: {gradio_ui_response_data['output']}.\n"
                                f"Please analyze the following code and identify the issue. Provide a detailed explanation of the error and a corrected version of the code. "
                                f"Ensure the corrected code is fully functional and adheres to Gradio best practices. Respond only with the corrected Python code and nothing else.\n"
                                f"Here is the code with the error:\n```python\n{gradio_code}\n```"
                            )
                            error_fix_response = completion(
                                model="gpt-4o",
                                messages=[
                                    {"role": "system", "content": "You are an expert in fixing Gradio UI code issues. Respond only with the corrected Python code and nothing else."},
                                    {"role": "user", "content": error_fix_prompt}
                                ],
                                temperature=0.2,  # Lower temperature for more deterministic output
                                top_p=0.9  # Lower top_p for more conservative output
                            )

                            if error_fix_response.choices[0].message.content:
                                fixed_code = error_fix_response.choices[0].message.content.strip("```python\n").strip("```")
                                fixed_code += "\n\ndemo.launch(share=True)"
                                gradio_request_data["code"] = fixed_code

                                # Log the fixed code for debugging
                                print(f"Attempt {attempt+1}: Posting fixed code to /gradio_ui with data: {gradio_request_data}")
                            else:
                                print(f"Attempt {attempt+1}: Failed to generate fixed code from OpenAI response.")
                                break
                        else:
                            # Log the successful response from the /gradio_ui endpoint for debugging
                            print(f"Attempt {attempt+1}: Response from /gradio_ui endpoint: {gradio_ui_response_data}")

                            return {
                                "openai_response": response.dict(),
                                "gradio_ui_response": gradio_ui_response_data,
                                "generated_code": gradio_code,
                                "posted_data": gradio_request_data  # Log the data that was posted
                            }
                    except httpx.ReadTimeout:
                        print(f"Attempt {attempt+1}: ReadTimeout occurred, retrying...")

                else:
                    error_message = "Failed to fix the Gradio code after multiple attempts."
                    print(error_message)
                    return {
                        "openai_response": response.dict(),
                        "error": error_message
                    }
        else:
            error_message = "Failed to generate Gradio code from OpenAI response."
            print(error_message)
            return {
                "openai_response": response.dict(),
                "error": error_message
            }
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        raise HTTPException(status_code=500, detail=error_message)


# Code for generating CodeSandbox URLs
def compress_and_encode(json_data):
    """Compress and encode JSON data for embedding in URL."""
    lz = lzstring.LZString()
    compressed = lz.compressToBase64(json_data)
    return quote(compressed)

def create_codesandbox(files):
    """Generate CodeSandbox URL based on the provided files."""
    parameters = {"files": files}
    parameters_json = json.dumps(parameters)
    encoded_compressed_parameters = compress_and_encode(parameters_json)
    url = f"https://codesandbox.io/api/v1/sandboxes/define?json=1&parameters={encoded_compressed_parameters}"
    
    response = httpx.post(url)
    if response.status_code == 200:
        response_data = response.json()
        sandbox_id = response_data.get('sandbox_id')
        return {
            "sandbox_id": sandbox_id,
            "final_url": f"https://codesandbox.io/s/{sandbox_id}",
            "sandbox_url": f"https://{sandbox_id}.csb.app/"
        }
    else:
        logger.error(f"Error creating sandbox: {response.text}")
        return None

def is_valid_verification(response):
    """Check if the verification response is valid."""
    try:
        message_content = response['choices'][0]['message']['content'].strip().upper()
        return "VALID" in message_content
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing verification response: {e}")
        return False

def verify_and_refine_code(function_response, retry_count=3):
    verification_prompt = (
        "Please verify that the following code files are correct and functional. "
        "Respond with 'VALID' if the code is correct or 'INVALID' if there are issues. "
        "Evaluate the code for the following aspects: "
        "1. Correctness: Ensure the code does what is expected based on the prompt. "
        "2. Functionality: Verify that the code runs without errors and performs the intended task. "
        "3. Completeness: Check that all necessary files and dependencies are included. "
        "4. Formatting: Ensure the code is properly formatted and adheres to coding standards. "
        "5. Syntax: Verify that there are no syntax errors in the code. "
        "6. Best Practices: Ensure the code follows best practices for readability, maintainability, and performance. "
        "7. Deployment: Confirm that the code is ready to be deployed to CodeSandbox and includes necessary configurations. "
        f"Here are the code files: {function_response}"
    )

    for _ in range(retry_count):
        verification_response = completion(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert in code verification."},
                {"role": "user", "content": verification_prompt}
            ]
        )
        logger.info(f"Verification response: {verification_response}")
        if is_valid_verification(verification_response):
            return True

    return False

def generate_code_files(prompt, timeout=320.0, retry_count=3):
    for attempt in range(retry_count):
        try:
            response = completion(
                model="gpt-4o",
                messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in generating clean, efficient, and modern Python code for Gradio UIs. "
                        "Generate only the necessary code files based on the given prompt. "
                        "Ensure the code is fully functional, formatted correctly, and includes all necessary dependencies. "
                        "Include error handling, comments, and modular code structure where applicable. "
                        "Provide multiple functionalities and configuration options if relevant. "
                        "Include detailed comments explaining the purpose and functionality of each section of the code. "
                        "Adhere to best practices for readability, maintainability, and performance. "
                        "Use modern Python features and ensure compatibility with the latest standards. "
                        "Perform recursive self-assessment with three internal loops for code review and improvement. "
                        "For example, respond with: "
                        '{"app.py": {"content": "code here"}, "requirements.txt": {"content": "code here"}, "README.md": {"content": "code here"}}'
                    )
                },
                {"role": "user", "content": prompt}
            ],

                functions=[
                    {
                        "name": "generate_code_files",
                        "description": "Generates code files",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "app.py": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"}
                                    },
                                    "required": ["content"]
                                },
                                "requirements.txt": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"}
                                    },
                                    "required": ["content"]
                                },
                                "README.md": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string"}
                                    },
                                    "required": ["content"]
                                }
                            },
                            "required": ["app.py", "requirements.txt", "README.md"]
                        }
                    }
                ],
                function_call="auto",
                timeout=timeout
            )

            logger.info(f"Raw response: {response}")

            if response.choices[0].finish_reason == 'function_call':
                function_response = response.choices[0].message.function_call.arguments
                if not function_response:
                    logger.error("Function call returned empty response.")
                    continue

                # Try to load the function response as JSON
                try:
                    code_files = json.loads(function_response)
                except json.JSONDecodeError as e:
                    logger.error(f"JSONDecodeError: {e}")
                    prompt += f"\nError encountered: {str(e)}"
                    continue

                # Perform verification
                if verify_and_refine_code(function_response):
                    logger.info(f"Verified code files: {code_files}")
                    return code_files
                else:
                    logger.error("Code verification failed after retries.")
                    continue

            logger.error("No valid function call arguments found in the response")
        except Exception as e:
            logger.exception("An error occurred during code generation")
    return None

@app.post("/generate_sandbox/")
async def generate_sandbox(request: PromptRequest):
    try:
        # Generate the code files using the provided prompt
        code_files = generate_code_files(request.prompt)
        
        if code_files:
            # Create CodeSandbox URL
            sandbox_info = create_codesandbox(code_files)
            
            if sandbox_info:
                final_url = sandbox_info['final_url']
                return {
                    "generated_code_files": code_files,
                    "sandbox_url": final_url
                }
            else:
                error_message = "Failed to create CodeSandbox URL."
                print(error_message)
                return {
                    "error": error_message
                }
        else:
            error_message = "Failed to generate code files."
            print(error_message)
            return {
                "error": error_message
            }
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(error_message)
        raise HTTPException(status_code=500, detail=error_message)


def get_final_sandbox_url(sandbox_id):
    """Retrieve the final sandbox URL using the sandbox_id."""
    if sandbox_id:
        final_url = f"https://codesandbox.io/s/{sandbox_id}"
        return final_url
    return None

def generate_code(prompt):
    files = generate_code_files(prompt)
    if files:
        sandbox_info = create_codesandbox(files)
        if sandbox_info:
            final_url = sandbox_info['final_url']
            print(f"Final URL: {final_url}")  # Print the final URL to the console
            return final_url
    return None

if __name__ == "__main__":
    # Specify the port you want to check and free
    port_to_check = 8000
    kill_process_on_port(port_to_check)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port_to_check)
