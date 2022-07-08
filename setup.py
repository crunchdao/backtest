#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as fd:
    requirements = fd.read().splitlines()

setup(
    name='datacrunch-backtest',
    version='1.0.0',
    description='Simple backtester',
    author='Enzo CACERES',
    author_email='caceresenzo1502@gmail.com',
    packages=find_packages(),
    install_requires=requirements,
)
