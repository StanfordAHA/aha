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
        'docker',
        'genesis2',
        'gitpython',
        'networkx',
        'packaging',
        'pydot==2.0.0',
        'requirements-parser',
        'tabulate',
        'pandas',
        'pulp'
    ],
    setup_requires = [
        'networkx',
        'packaging',
    ],

    entry_points = {
        'console_scripts': ['aha=aha.aha:main'],
    },
    py_modules=[],
)
