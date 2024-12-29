class NotebookEditor {
    constructor(container) {
        this.container = container;
        this.cells = [];
        this.initializeFileInput();
        this.setupEventListeners();
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
                ${type === 'markdown' ? '<button class="polish-markdown me-2">AI Polish</button>' : ''}
                ${type === 'code' ? '<button class="optimize-code me-2">AI Optimize</button>' : ''}
                <button class="move-cell" data-direction="up">↑</button>
                <button class="move-cell" data-direction="down">↓</button>
                <button class="delete-cell">×</button>
                <button class="ai-chat">AI Chat</button>
            </div>
        `;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'cell-content';

        cellDiv.appendChild(headerDiv);
        cellDiv.appendChild(contentDiv);
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
                    
                    const response = await fetch('/api/polish-markdown', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ text: content })
                    });

                    const result = await response.json();
                    if (result.status === 'success') {
                        cell.editor.setValue(result.polished_text);
                    } else {
                        throw new Error(result.message || 'Unknown error occurred');
                    }
                } catch (error) {
                    alert('Error polishing markdown: ' + error.message);
                } finally {
                    polishBtn.disabled = false;
                    polishBtn.textContent = 'AI Polish';
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
                    
                    const response = await fetch('/api/optimize-code', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ code: content })
                    });

                    const result = await response.json();
                    if (result.status === 'success') {
                        cell.editor.setValue(result.optimized_code);
                    } else {
                        throw new Error(result.message || 'Unknown error occurred');
                    }
                } catch (error) {
                    alert('Error optimizing code: ' + error.message);
                } finally {
                    optimizeBtn.disabled = false;
                    optimizeBtn.textContent = 'AI Optimize';
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
        [this.cells[index1], this.cells[index2]] = [this.cells[index2], this.cells[index1]];
        const cell1 = this.cells[index1];
        const cell2 = this.cells[index2];
        const div1 = document.getElementById(cell1.id);
        const div2 = document.getElementById(cell2.id);

        if (index2 < index1) {
            div2.parentNode.insertBefore(div1, div2);
        } else {
            div2.parentNode.insertBefore(div1, div2.nextSibling);
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
                    cell_type: cell.type
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                if (window.confirm('Apply this response to the cell?\n\n' + result.response)) {
                    cell.editor.setValue(result.response);
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
