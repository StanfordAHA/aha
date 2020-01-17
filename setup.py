from setuptools import setup
import subprocess
import sys
import os

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", package])

# TODO: only install these if they're not present in `pip list`

install(os.path.join(os.getcwd(), 'ast_tools'))
install(os.path.join(os.getcwd(), 'hwtypes'))
install(os.path.join(os.getcwd(), 'pycoreir'))
install(os.path.join(os.getcwd(), 'kratos'))
install(os.path.join(os.getcwd(), 'magma'))
install(os.path.join(os.getcwd(), 'cosa'))
install(os.path.join(os.getcwd(), 'fault'))
install(os.path.join(os.getcwd(), 'mantle'))
install(os.path.join(os.getcwd(), 'canal'))
install(os.path.join(os.getcwd(), 'gemstone'))
install(os.path.join(os.getcwd(), 'peak'))
install(os.path.join(os.getcwd(), 'lassen'))
install(os.path.join(os.getcwd(), 'cgra_pnr/cyclone'))
install(os.path.join(os.getcwd(), 'cgra_pnr/thunder'))
install(os.path.join(os.getcwd(), 'archipelago'))

# TODO: `pip list` and ensure that all the above are pointing to sources

setup(
    name='aha',
    author='Teguh Hofstee',
    url='https://github.com/hofstee/aha',

    python_requires='>=3.7',
    install_requires = [
        'genesis2',
    ],

    entry_points = {
        'console_scripts': ['aha=aha:main'],
    },
)
