import os


class fake_system():
    def __init__(self, os_in):
        self.tmp = os_in.system
    def __enter__(self):
        os.system = lambda x: None
        return
    def __exit__(self, type, value, traceback):
        os.system = self.tmp

with fake_system(os): 
    os.system("ls ~/") # Return nothing 
os.system("ls ~/")  # Normal ls output