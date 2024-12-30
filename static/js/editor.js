class NotebookEditor {
    constructor(container) {
        this.container = container;
        this.cells = [];
        this.initializeFileInput();
        this.setupEventListeners();
        // Add an empty code cell by default
        this.addCell('code');
    }

    initializeFileInput() {
        const fileInput = document.getElementById('notebookFile');
        fileInput.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            if (file) {
                this.uploadNotebook(file);
                fileInput.value = ''; // Clear the input after upload
            }
        });
    }

    async uploadNotebook(file) {
        try {
            const formData = new FormData();
            formData.append('notebook', file);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'success') {
                // Clear existing cells
                while (this.cells.length > 0) {
                    const cell = this.cells[0];
                    const cellDiv = document.getElementById(cell.id);
                    if (cellDiv) {
                        cellDiv.remove();
                    }
                    this.cells.splice(0, 1);
                }

                // Create new cells from uploaded notebook
                result.cells.forEach(cell => {
                    const newCell = this.addCell(cell.type);
                    newCell.editor.setValue(cell.source);
                });
            } else {
                throw new Error(result.message || 'Unknown error occurred');
            }
        } catch (error) {
            alert('Error uploading notebook: ' + error.message);
        }
    }

    setupEventListeners() {
        document.getElementById('addCodeCell').addEventListener('click', () => this.addCell('code'));
        document.getElementById('addMarkdownCell').addEventListener('click', () => this.addCell('markdown'));
        document.getElementById('saveNotebook').addEventListener('click', () => this.saveNotebook());
        
        // Setup upload functionality
        const uploadBtn = document.getElementById('uploadNotebook');
        const fileInput = document.getElementById('notebookFile');
        
        uploadBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }

    addCell(type = 'code', content = '') {
        const cell = {
            type: type,
            id: `cell-${Date.now()}`,
            editor: null
        };

        const cellDiv = document.createElement('div');
        cellDiv.className = 'cell';
        cellDiv.id = cell.id;

        const headerDiv = document.createElement('div');
        headerDiv.className = 'cell-header';
        headerDiv.innerHTML = `
            <span class="cell-type">${type.charAt(0).toUpperCase() + type.slice(1)}</span>
            <div class="cell-controls">
                ${type === 'markdown' ? '<button class="polish-markdown me-2 btn-custom">🦾 AI Polish</button>' : ''}
                ${type === 'code' ? '<button class="optimize-code me-2 btn-custom">🦾 AI Optimize</button>' : ''}
                ${type === 'code' ? '<button class="run-code me-2 btn-custom">▶ Run</button>' : ''}
                ${type === 'code' ? '<button class="format-code me-2 btn-custom">🔧 Format</button>' : ''}
                <button class="move-cell btn-custom" data-direction="up">↑</button>
                <button class="move-cell btn-custom" data-direction="down">↓</button>
                <button class="delete-cell btn-custom">×</button>
                <button class="ai-chat btn-custom">🤖 Chat</button>
            </div>
        `;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'cell-content';

        const outputDiv = document.createElement('div');
        outputDiv.className = 'cell-output';
        outputDiv.style.display = 'none';

        cellDiv.appendChild(headerDiv);
        cellDiv.appendChild(contentDiv);
        cellDiv.appendChild(outputDiv);
        this.container.appendChild(cellDiv);

        // Setup CodeMirror
        cell.editor = CodeMirror(contentDiv, {
            mode: type === 'code' ? 'python' : 'markdown',
            theme: 'default',
            lineWrapping: true,
            lineNumbers: type === 'code',
            viewportMargin: Infinity,
            extraKeys: {
                'Tab': function(cm) {
                    cm.replaceSelection('    ');
                }
            },
            value: content
        });

        this.cells.push(cell);
        this.setupCellControls(cellDiv, cell);
        return cell;
    }

    setupCellControls(cellDiv, cell) {
        const deleteBtn = cellDiv.querySelector('.delete-cell');
        deleteBtn.addEventListener('click', () => {
            const index = this.cells.indexOf(cell);
            if (index > -1) {
                this.cells.splice(index, 1);
                cellDiv.remove();
            }
        });

        if (cell.type === 'markdown') {
            const polishBtn = cellDiv.querySelector('.polish-markdown');
            polishBtn.addEventListener('click', async () => {
                const content = cell.editor.getValue();
                try {
                    polishBtn.disabled = true;
                    polishBtn.textContent = 'Polishing...';
                    
                    const response = await fetch('/api/polish', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ text: content })
                    });

                    const result = await response.json();
                    if (result.status === 'success') {
                        cell.editor.setValue(result.text);
                    } else {
                        throw new Error(result.message || 'Unknown error occurred');
                    }
                } catch (error) {
                    alert('Error polishing markdown: ' + error.message);
                } finally {
                    polishBtn.disabled = false;
                    polishBtn.textContent = '🦾 AI Polish';
                }
            });
        }

        if (cell.type === 'code') {
            const optimizeBtn = cellDiv.querySelector('.optimize-code');
            optimizeBtn.addEventListener('click', async () => {
                const content = cell.editor.getValue();
                try {
                    optimizeBtn.disabled = true;
                    optimizeBtn.textContent = 'Optimizing...';
                    
                    const response = await fetch('/api/optimize', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ code: content })
                    });

                    const result = await response.json();
                    if (result.status === 'success') {
                        cell.editor.setValue(result.code);
                    } else {
                        throw new Error(result.message || 'Unknown error occurred');
                    }
                } catch (error) {
                    alert('Error optimizing code: ' + error.message);
                } finally {
                    optimizeBtn.disabled = false;
                    optimizeBtn.textContent = '🦾 AI Optimize';
                }
            });

            const runBtn = cellDiv.querySelector('.run-code');
            const outputDiv = cellDiv.querySelector('.cell-output');
            
            runBtn.addEventListener('click', async () => {
                const code = cell.editor.getValue();
                outputDiv.innerHTML = '<div class="alert alert-info">Running...</div>';
                outputDiv.style.display = 'block';
                
                try {
                    const response = await fetch('/api/execute', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ code: code })
                    });

                    const result = await response.json();
                    if (result.status === 'success') {
                        outputDiv.innerHTML = '';
                        
                        for (const output of result.outputs) {
                            const outputElement = document.createElement('div');
                            outputElement.className = 'output-item';
                            
                            if (output.type === 'stream') {
                                outputElement.className += ' stream-output';
                                outputElement.innerText = output.text;
                            } else if (output.type === 'execute_result' || output.type === 'display_data') {
                                if (output.data['text/html']) {
                                    outputElement.innerHTML = output.data['text/html'];
                                } else if (output.data['image/png']) {
                                    outputElement.innerHTML = `<img src="data:image/png;base64,${output.data['image/png']}" />`;
                                } else if (output.data['text/plain']) {
                                    outputElement.innerText = output.data['text/plain'];
                                }
                            } else if (output.type === 'error') {
                                outputElement.className += ' error-output';
                                outputElement.innerHTML = `<pre class="error">${output.traceback.join('\n')}</pre>`;
                            }
                            
                            outputDiv.appendChild(outputElement);
                        }
                    } else {
                        throw new Error(result.message || 'Unknown error occurred');
                    }
                } catch (error) {
                    outputDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
                }
            });

            const formatBtn = cellDiv.querySelector('.format-code');
            formatBtn.addEventListener('click', async () => {
                const code = cell.editor.getValue();
                try {
                    const response = await fetch('/api/format', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ code: code })
                    });

                    const result = await response.json();
                    if (result.status === 'success') {
                        cell.editor.setValue(result.formatted_code);
                    } else {
                        throw new Error(result.message || 'Formatting failed');
                    }
                } catch (error) {
                    alert('Error formatting code: ' + error.message);
                }
            });
        }

        const moveButtons = cellDiv.querySelectorAll('.move-cell');
        moveButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const direction = btn.dataset.direction;
                const index = this.cells.indexOf(cell);
                if (direction === 'up' && index > 0) {
                    this.swapCells(index, index - 1);
                } else if (direction === 'down' && index < this.cells.length - 1) {
                    this.swapCells(index, index + 1);
                }
            });
        });

        const chatBtn = cellDiv.querySelector('.ai-chat');
        chatBtn.addEventListener('click', () => this.handleChat(cell));
    }

    swapCells(index1, index2) {
        // Swap cells in the array
        [this.cells[index1], this.cells[index2]] = [this.cells[index2], this.cells[index1]];
        
        // Get the DOM elements
        const div1 = document.getElementById(this.cells[index1].id);
        const div2 = document.getElementById(this.cells[index2].id);
        
        // Store a reference to the next sibling before any swapping
        const nextSibling = div2.nextSibling;
        
        // If moving up (index2 < index1), insert div2 before div1
        if (index2 < index1) {
            div1.parentNode.insertBefore(div2, div1);
        }
        // If moving down (index2 > index1), insert div1 after div2
        else {
            if (nextSibling) {
                div1.parentNode.insertBefore(div2, nextSibling);
            } else {
                div1.parentNode.appendChild(div2);
            }
            div1.parentNode.insertBefore(div1, div2);
        }
    }

    async saveNotebook() {
        const notebookData = {
            cells: this.cells.map(cell => ({
                type: cell.type,
                source: cell.editor.getValue()
            }))
        };

        try {
            // Default to Desktop location
            const defaultPath = 'C:\\Users\\xinzhong\\Desktop\\notebook.ipynb';
            const filepath = prompt('Enter the full path to save the notebook:', defaultPath);
            
            if (!filepath) return;
            
            let finalPath = filepath;
            if (!finalPath.endsWith('.ipynb')) {
                finalPath += '.ipynb';
            }

            // Replace forward slashes with backslashes for Windows
            finalPath = finalPath.replace(/\//g, '\\');

            // Send the save request to the server
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filepath: finalPath,
                    cells: notebookData.cells
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                alert('Notebook saved successfully!');
            } else {
                throw new Error(result.message || 'Unknown error occurred');
            }
        } catch (error) {
            alert('Error saving notebook: ' + error.message);
        }
    }

    async handleChat(cell) {
        const prompt = window.prompt('Enter your prompt:');
        if (!prompt) return;

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: prompt,
                    context: cell.editor.getValue(),
                    cell_type: cell.type
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                const cleanReply = result.reply.trimStart();  // Remove leading whitespace and newlines
                if (window.confirm('Apply this response to the cell?\n\n' + cleanReply)) {
                    cell.editor.setValue(cleanReply);
                }
            } else {
                throw new Error(result.message || 'Unknown error occurred');
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }
}

// Initialize the notebook editor when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.notebookEditor = new NotebookEditor(document.getElementById('notebook-container'));
});
