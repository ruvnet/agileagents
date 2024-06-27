
import os
import sys
import time
import re
import json
import logging
import lzstring
import httpx

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

app = FastAPI()

class RedirectToDocsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/":
            return RedirectResponse(url="/docs")
        response = await call_next(request)
        return response

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
        """

        # Generate the Gradio UI code using GPT-4o function calling
        response = completion(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": gradio_requirements},
                {"role": "user", "content": request.prompt}
            ]
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
            async with httpx.AsyncClient() as client:
                gradio_ui_response = await client.post("http://0.0.0.0:8000/gradio_ui/", json=gradio_request_data)
                gradio_ui_response_data = gradio_ui_response.json()

                # Log the response from the /gradio_ui endpoint for debugging
                print(f"Response from /gradio_ui endpoint: {gradio_ui_response_data}")

                return {
                    "openai_response": response.dict(),
                    "gradio_ui_response": gradio_ui_response_data,
                    "generated_code": gradio_code,
                    "posted_data": gradio_request_data  # Log the data that was posted
                }
        else:
            error_message = "Failed to generate Gradio code from OpenAI response."
            print(error_message)
            return {
                "openai_response": response.dict(),
                "error": error_message
            }
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(error_message)
        raise HTTPException(status_code=500, detail=error_message)



if __name__ == "__main__":
    # Specify the port you want to check and free
    port_to_check = 8000
    kill_process_on_port(port_to_check)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port_to_check)