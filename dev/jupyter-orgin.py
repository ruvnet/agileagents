import os
import sys
import time
from jupyter_client import KernelManager

print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("Sys path:", sys.path)

def run_jupyter_code():
    code = '''
import gradio as gr

# Define various functions for the UI
def greet(name):
    return "Hello " + name + "!"

def square(number):
    return number ** 2

def cube(number):
    return number ** 3

# Define the components for each tab and accordion section
greet_interface = gr.Interface(fn=greet, inputs=gr.Textbox(label="Enter your name"), outputs=gr.Textbox(label="Output"))

square_interface = gr.Interface(fn=square, inputs=gr.Number(label="Enter a number"), outputs=gr.Number(label="Squared Output"))

cube_interface = gr.Interface(fn=cube, inputs=gr.Number(label="Enter a number"), outputs=gr.Number(label="Cubed Output"))

# Define an accordion layout
accordion = gr.Accordion("Agentic Functions", [square_interface, cube_interface])

# Define the tabbed layout
with gr.Blocks() as iface:
    with gr.Tab("Greet"):
        greet_interface.render()
    with gr.Tab("Calculations"):
        accordion.render()

url = iface.launch(share=True)
print("Public URL:", url)
'''


    km = KernelManager()
    print("KernelManager initialized")

    try:
        km.start_kernel()
        print("Kernel started")
    except Exception as e:
        print(f"Error starting kernel: {e}")
        return

    try:
        kc = km.client()
        kc.start_channels()
        print("Channels started")
    except Exception as e:
        print(f"Error starting channels: {e}")
        return

    try:
        # Execute the code in the Jupyter kernel
        kc.execute(code)
        print("Code executed in Jupyter kernel")

        # Get the output
        while True:
            try:
                msg = kc.get_iopub_msg(timeout=10)
                msg_type = msg['header']['msg_type']
                content = msg['content']

                if msg_type == 'stream':
                    print("Stream:", content['text'])
                elif msg_type == 'display_data':
                    print("Display Data:", content['data'])
                elif msg_type == 'execute_result':
                    print("Execute Result:", content['data'])
                    if 'text/plain' in content['data'] and 'http' in content['data']['text/plain']:
                        public_url = content['data']['text/plain']
                        print(f"Gradio interface is running at: {public_url}")
                elif msg_type == 'error':
                    print("Error:", content['evalue'])
                    break
            except Exception as e:
                print(f"Exception while getting message: {e}")
                break

        print("Gradio interface is running. Press Ctrl+C to stop.")

        # Keep the process running indefinitely
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Shutting down Gradio interface...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            kc.stop_channels()
            km.shutdown_kernel()
            print("Kernel shutdown")
        except Exception as e:
            print(f"Error during shutdown: {e}")

if __name__ == "__main__":
    print("Starting Jupyter code execution")
    run_jupyter_code()
    print("Finished Jupyter code execution")
