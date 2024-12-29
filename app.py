from flask import Flask, render_template, request, jsonify
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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

@app.route('/api/polish-markdown', methods=['POST'])
def polish_markdown():
    try:
        data = request.json
        markdown_text = data.get('text', '')
        
        if not markdown_text:
            return jsonify({"status": "error", "message": "No text provided"}), 400

        # Call OpenAI API to polish the markdown
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that polishes markdown text to make it more professional, clear, and well-structured. Maintain the original meaning but improve the writing quality."},
                {"role": "user", "content": f"Please polish the following markdown text and only return the polished text without any explanation or comments. Markdown text:\n\n{markdown_text}"}
            ]
        )
        
        polished_text = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "polished_text": polished_text
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/optimize-code', methods=['POST'])
def optimize_code():
    try:
        data = request.json
        code = data.get('code', '')
        
        if not code:
            return jsonify({"status": "error", "message": "No code provided"}), 400

        # Call OpenAI API to optimize the code
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert programmer that optimizes code for better performance, readability, and maintainability. Keep the core functionality intact while improving the code quality. Only return the optimized code without any explanations or comments."},
                {"role": "user", "content": f"Please optimize this code and return only the optimized code without any explanations:\n\n{code}"}
            ]
        )
        
        optimized_code = response.choices[0].message.content.strip()
        
        # Clean up markdown code block markers if present
        if optimized_code.startswith('```python\n'):
            optimized_code = optimized_code[len('```python\n'):]
        elif optimized_code.startswith('```\n'):
            optimized_code = optimized_code[len('```\n'):]
            
        if optimized_code.endswith('\n```'):
            optimized_code = optimized_code[:-4]
        elif optimized_code.endswith('```'):
            optimized_code = optimized_code[:-3]
            
        optimized_code = optimized_code.strip()
        
        return jsonify({
            "status": "success",
            "optimized_code": optimized_code
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data or 'prompt' not in data or 'cell_type' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing prompt or cell type"
            }), 400

        prompt = data['prompt']
        cell_type = data['cell_type']
        
        # Add cell type context to the prompt
        if cell_type == 'code':
            system_prompt = "You are a Python programming expert. Provide only the code without any explanations or markdown. Do not include ```python or ``` markers."
        else:
            system_prompt = "You are a technical writing expert. Provide the response in markdown format. Do not include ```markdown or ``` markers."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        content = response.choices[0].message.content.strip()
        
        return jsonify({
            "status": "success",
            "response": content
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

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

if __name__ == '__main__':
    app.run(debug=True)
