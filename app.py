from flask import Flask, render_template, request, jsonify
import json
import os
import queue
from openai import OpenAI
from dotenv import load_dotenv
from jupyter_client import BlockingKernelClient, KernelManager
from jupyter_client.kernelspec import NoSuchKernel
import atexit

load_dotenv()

app = Flask(__name__)
client = OpenAI()  # OpenAI will automatically use OPENAI_API_KEY from environment

# Global variables for kernel management
_kernel = None

class KernelConnection:
    def __init__(self):
        self.km = None
        self.kc = None
        self.initialize()
    
    def initialize(self):
        if self.km is None:
            self.km = KernelManager(kernel_name='python3')
            self.km.start_kernel()
            self.kc = self.km.client()
            self.kc.start_channels()
            self.kc.wait_for_ready()
            # Enable matplotlib inline display
            self.execute('%matplotlib inline')
            # Test the kernel
            self.execute('print("Kernel initialized")')
    
    def execute(self, code):
        if not self.km or not self.km.is_alive():
            self.initialize()
        
        msg_id = self.kc.execute(code, store_history=True)
        outputs = []
        done = False
        
        while not done:
            try:
                msg = self.kc.get_iopub_msg(timeout=1)
                msg_type = msg['header']['msg_type']
                content = msg['content']
                
                if msg_type == 'stream':
                    outputs.append({
                        'type': 'stream',
                        'name': content['name'],
                        'text': content['text']
                    })
                elif msg_type == 'display_data':
                    outputs.append({
                        'type': 'display_data',
                        'data': content['data']
                    })
                elif msg_type == 'execute_result':
                    outputs.append({
                        'type': 'execute_result',
                        'data': content['data']
                    })
                elif msg_type == 'error':
                    outputs.append({
                        'type': 'error',
                        'ename': content['ename'],
                        'evalue': content['evalue'],
                        'traceback': content['traceback']
                    })
                elif msg_type == 'status' and content['execution_state'] == 'idle':
                    done = True
            except queue.Empty:
                continue
        
        return outputs
    
    def shutdown(self):
        if self.kc:
            self.kc.stop_channels()
        if self.km:
            self.km.shutdown_kernel(now=True)
            self.km = None
            self.kc = None

def get_kernel():
    global _kernel
    if _kernel is None:
        _kernel = KernelConnection()
    return _kernel

@atexit.register
def cleanup():
    global _kernel
    if _kernel:
        _kernel.shutdown()
        _kernel = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/save', methods=['POST'])
def save_notebook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        filepath = data.get('filepath', '')
        cells = data.get('cells', [])
        
        if not filepath or not cells:
            return jsonify({"status": "error", "message": "Missing filepath or cells"}), 400

        # Normalize path and make absolute if needed
        filepath = os.path.normpath(filepath)
        if not os.path.isabs(filepath):
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            filepath = os.path.join(desktop, filepath)

        # Ensure .ipynb extension
        if not filepath.endswith('.ipynb'):
            filepath += '.ipynb'

        # Create notebook structure
        notebook = {
            "cells": [],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "codemirror_mode": {"name": "ipython", "version": 3},
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.8.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }

        # Add cells
        for cell_data in cells:
            cell_type = cell_data.get('type')
            source = cell_data.get('source', '')
            
            if not cell_type or not isinstance(source, str):
                continue

            cell = {
                "cell_type": cell_type,
                "metadata": {},
                "source": source.splitlines(True)
            }

            if cell_type == 'code':
                cell.update({
                    "execution_count": None,
                    "outputs": []
                })

            notebook["cells"].append(cell)

        # Create directory if needed
        directory = os.path.dirname(filepath)
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception:
                # Fallback to desktop if directory creation fails
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                filepath = os.path.join(desktop, os.path.basename(filepath))
                os.makedirs(desktop, exist_ok=True)

        # Save the notebook
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        return jsonify({
            "status": "success",
            "message": f"Notebook saved successfully"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/upload', methods=['POST'])
def upload_notebook():
    try:
        if 'notebook' not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400

        file = request.files['notebook']
        if file.filename == '':
            return jsonify({"status": "error", "message": "No file selected"}), 400

        if not file.filename.endswith('.ipynb'):
            return jsonify({"status": "error", "message": "File must be a .ipynb file"}), 400

        notebook_json = json.load(file)
        cells = []

        for cell in notebook_json['cells']:
            cell_type = cell['cell_type']
            if cell_type in ['code', 'markdown']:
                source = ''.join(cell['source'])
                cells.append({
                    'type': cell_type,
                    'source': source
                })

        return jsonify({
            "status": "success",
            "cells": cells
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/polish', methods=['POST'])
def polish_markdown():
    try:
        data = request.json
        markdown_text = data.get('text')
        if not markdown_text:
            return jsonify({"status": "error", "message": "No text provided"}), 400

        # Call OpenAI API to polish the markdown
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that polishes markdown text to make it more professional, clear, and well-structured. Maintain the original meaning but improve the writing quality."},
                {"role": "user", "content": f"Please polish the following markdown text and only return the polished text without any explanation or comments. Markdown text:\n\n{markdown_text}"}
            ]
        )
        
        polished_text = response.choices[0].message.content
        return jsonify({"status": "success", "text": polished_text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/optimize', methods=['POST'])
def optimize_code():
    try:
        data = request.json
        code = data.get('code')
        if not code:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        # Call OpenAI API to optimize the code
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert programmer that optimizes code for better performance, readability, and maintainability. Keep the core functionality intact while improving the code quality. Only return the optimized code without any explanations or comments."},
                {"role": "user", "content": f"Please optimize the following code and only return the optimized code. If there are comments in the code, your optimized code should also have comments. Code to be optimized:\n\n{code}"}
            ]
        )
        
        optimized_code = response.choices[0].message.content
        return jsonify({"status": "success", "code": optimized_code})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        prompt = data.get('prompt')
        context = data.get('context', '')
        cell_type = data.get('cell_type', 'code')
        
        if not prompt:
            return jsonify({"status": "error", "message": "No prompt provided"}), 400

        # Different system prompts based on cell type
        if cell_type == 'code':
            system_prompt = "You are a Python programming expert. Provide clear, well-documented code solutions. Include helpful comments in your code to explain the logic. Return only the code without any additional explanations."
        else:
            system_prompt = "You are a technical writing expert. Provide well-structured markdown content that is clear, concise, and follows best practices for documentation. Return only the markdown content without any additional explanations."

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
            messages.append({"role": "assistant", "content": "I understand the context. How can I help you?"})
        
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        reply = response.choices[0].message.content.strip()  # Remove all surrounding whitespace
        
        # Clean up code fence markers if present
        if cell_type == 'code':
            if reply.startswith('```python'):
                reply = reply[8:].strip()  # Remove ```python
            elif reply.startswith('```'):
                reply = reply[3:].strip()  # Remove ```
            if reply.endswith('```'):
                reply = reply[:-3].strip()  # Remove trailing ```
            
            # Remove any remaining leading newlines or 'n' character
            reply = reply.lstrip('n').lstrip()
        
        return jsonify({"status": "success", "reply": reply})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/directories', methods=['GET'])
def get_directories():
    try:
        # Get common Windows directories
        directories = {
            'desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
            'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
            'downloads': os.path.join(os.path.expanduser('~'), 'Downloads')
        }
        
        # Return only directories that exist and are writable
        available_dirs = {
            key: path for key, path in directories.items() 
            if os.path.exists(path) and os.access(path, os.W_OK)
        }
                
        return jsonify({
            "status": "success",
            "directories": available_dirs
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/execute', methods=['POST'])
def execute_code():
    try:
        data = request.json
        code = data.get('code')
        if not code:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        kernel = get_kernel()
        outputs = kernel.execute(code)
        
        return jsonify({
            "status": "success",
            "outputs": outputs
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
