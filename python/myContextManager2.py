import os
from contextlib import contextmanager

@contextmanager
def fake_system(module):
    tmp = os.system
    try:
        os.system = lambda x: None
        yield
    finally:
        os.system = tmp

with fake_system(os): 
    os.system("ls ~/") # Return nothing 
os.system("ls ~/")  # Normal ls output