#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ast import parse
import os
from setuptools import setup


NAME = 'beancount-plugins'

def version():
    """Return version string."""
    with open(os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'beancount_plugins',
                           '__init__.py')) as input_file:
        for line in input_file:
            if line.startswith('__version__'):
                return parse(line).body[0].value.s


def readme():
    with open('README.rst') as f:
        return f.read()

INSTALL_REQUIRES = (
)

setup(
    name=NAME,
    version=version(),
    description="Library of user contributed plugins for beancount",
    long_description=readme(),
    license='BSD License',
    author='David Stephens',
    author_email='dstephens99@gmail.com',
    url='https://github.com/davidastephens/beancount-plugins',
    classifiers=[
        'Development Status :: 5 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Financial and Insurance Industry',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Utilities',
    ],
    install_requires=INSTALL_REQUIRES,
    packages=['beancount_plugins',
              'beancount_plugins.plugins',
              'beancount_plugins.plugins.split_transactions',
              'beancount_plugins.plugins.zero_sum',
              'beancount_plugins.plugins.automated_depreciation',
              ],
    #test_suite='tests',
    zip_safe=False,
)
