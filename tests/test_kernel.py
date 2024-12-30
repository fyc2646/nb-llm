import pytest
from app import KernelConnection

def test_kernel_initialization():
    kernel = KernelConnection()
    assert kernel.km is not None
    assert kernel.kc is not None
    kernel.shutdown()

def test_kernel_execution():
    kernel = KernelConnection()
    # Test simple execution
    outputs = kernel.execute('2 + 2')
    assert any(output.get('data', {}).get('text/plain') == '4' 
              for output in outputs 
              if output.get('type') == 'execute_result')
    
    # Test variable persistence
    kernel.execute('x = 42')
    outputs = kernel.execute('x')
    assert any(output.get('data', {}).get('text/plain') == '42'
              for output in outputs
              if output.get('type') == 'execute_result')
    
    kernel.shutdown()

def test_kernel_error_handling():
    kernel = KernelConnection()
    outputs = kernel.execute('undefined_variable')
    assert any(output.get('type') == 'error' for output in outputs)
    kernel.shutdown()

def test_kernel_matplotlib():
    kernel = KernelConnection()
    code = '''
import matplotlib.pyplot as plt
import numpy as np
x = np.linspace(0, 2*np.pi, 100)
plt.plot(x, np.sin(x))
plt.show()
'''
    outputs = kernel.execute(code)
    assert any(output.get('data', {}).get('image/png') is not None 
              for output in outputs 
              if output.get('type') in ['display_data', 'execute_result'])
    kernel.shutdown()
