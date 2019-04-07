#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='moodleteacher',
    version='0.1.9',
    url='https://github.com/troeger/moodleteacher',
    license='BSD',
    author='Peter Tröger',
    description='A Moodle client library for teachers.',
    author_email='peter@troeger.eu',
    classifiers=[
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3'
    ],
    install_requires=['requests', 'pexpect'],
    extras_require={
        'ui': ['wxPython', 'PyMuPDF']
    },
    packages=['moodleteacher']
)
