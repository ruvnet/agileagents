import os
import sys
import time
import threading
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jupyter_client import KernelManager

app = FastAPI()

class CodeRequest(BaseModel):
    code: str

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
                    if 'http' in content['data'].get('text/plain', ''):
                        public_url = content['data']['text/plain']
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
    session_id = str(time.time())
    result_event = threading.Event()
    thread = threading.Thread(target=run_gradio_session, args=(request.code, session_id, result_event))
    thread.start()

    # Return the session ID immediately
    if result_event.wait(timeout=5):  # Allow some time to initialize
        session_info = registry.get_session(session_id)
        if session_info:
            return {"output": session_info["output"], "url": session_info["url"], "session_id": session_id}
        else:
            return {"output": "Session started, but no output yet.", "url": "", "session_id": session_id}
    else:
        return {"output": "Timeout waiting for session start.", "url": "", "session_id": session_id}

@app.get("/get_session/{session_id}")
async def get_session(session_id: str):
    session_info = registry.get_session(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"output": session_info["output"], "url": session_info["url"], "session_id": session_id}

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

if __name__ == "__main__":
    # Specify the port you want to check and free
    port_to_check = 8000
    kill_process_on_port(port_to_check)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port_to_check)
