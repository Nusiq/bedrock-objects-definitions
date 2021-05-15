from setuptools import setup
import os

# Path to file with VERSION
init_path = os.path.join(
    os.path.dirname(__file__),
    'src', 'bedrock_example', '__init__.py'
)

# Line that defines VERSION
version_line = list(filter(
        lambda line: line.startswith('VERSION'),
        open(init_path)
))[0]

# Evaluate line and create VERSION and __version__
VERSION = eval(version_line.split('=')[-1])
__version__ = '.'.join([str(x) for x in VERSION])

setup(version=__version__)
