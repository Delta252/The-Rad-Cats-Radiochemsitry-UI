import sys
import os
try:
    assert sys.version_info >= (3, 10)
except:
    print("WARNING: Update python compiler to >3.10\n")

packages = ['pip', 'pyserial', 'Pillow', 'customtkinter', 'opencv-python', 'requests', 'flask', 'chump', 'setuptools', 'matplotlib']
for package in packages:
    os.system('py -m pip install --upgrade ' + package)
