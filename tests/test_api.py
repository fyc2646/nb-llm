import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'<!DOCTYPE html>' in response.data

def test_execute_code(client):
    response = client.post('/api/execute', 
                         json={'code': 'print("Hello, World!")'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert any(output.get('text') == 'Hello, World!\n' 
              for output in data['outputs']
              if output.get('type') == 'stream')

def test_format_code(client):
    unformatted_code = '''
def messy_function   (x,y ):
    if x>0:
     return x+y
    else :
        return x-y
'''
    response = client.post('/api/format', json={'code': unformatted_code})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'def messy_function(x, y):' in data['formatted_code']

def test_invalid_code_execution(client):
    response = client.post('/api/execute', 
                         json={'code': 'invalid python code'})
    assert response.status_code == 200  # We return 200 even for execution errors
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert any(output.get('type') == 'error' 
              for output in data['outputs'])
