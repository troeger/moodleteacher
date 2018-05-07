#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name = 'moodleteacher',
    version = '0.0.2',
    url = 'https://github.com/troeger/moodleteacher',
    license='BSD',
    author = 'Peter Tröger',
    description = 'A Moodle client library for teachers.',
    author_email = 'peter@troeger.eu',
    classifiers=[
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3.6'
    ],
    install_requires=['wxPython', 'requests', 'PyMuPDF'],
    packages = ['moodleteacher'],
)


