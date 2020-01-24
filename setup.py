import deps
from setuptools import setup
import subprocess
import sys
import os

setup(
    name='aha',
    author='Teguh Hofstee',
    url='https://github.com/hofstee/aha',

    python_requires='>=3.7',
    install_requires = [
        'genesis2',
        'networkx',
        'packaging',
        'pydot',
    ],

    entry_points = {
        'console_scripts': ['aha=aha:main'],
    },
)

def install(package):
    if os.path.exists(os.path.join('package', 'setup.py')):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", package])

# TODO: only install these if they're not present in `pip list`

modules = {
    'archipelago': 'archipelago',
    'ast_tools': 'ast_tools',
    'buffer-mapping': 'BufferMapping',
    'canal': 'canal',
    'coreir': 'pycoreir',
    'cosa': 'cosa',
    'fault': 'fault',
    'garnet': 'garnet',
    'gemstone': 'gemstone',
    'hwtypes': 'hwtypes',
    'kratos': 'kratos',
    'lassen': 'lassen',
    'magma-lang': 'magma',
    'mantle': 'mantle',
    'peak': 'peak',
    'pycyclone': 'cgra_pnr/cyclone',
    'pythunder': 'cgra_pnr/thunder',
}

for dep in deps.order_deps(modules):
    install(os.path.join(os.getcwd(), modules[dep]))

# TODO: `pip list` and ensure that all the above are pointing to sources

