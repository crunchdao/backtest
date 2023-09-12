#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as fd:
    requirements = fd.read().splitlines()

setup(
    name='crunchdao-backtest',
    version='1.0.1',
    description='CrunchDAO backtester',
    author='Enzo Caceres, CrunchDAO',
    author_email='enzo.caceres@crunchdao.com',
    packages=find_packages(),
    install_requires=requirements,
)