#!/usr/bin/python3
# coding=utf8

import os

from setuptools import setup, find_packages

setup(name='gitindexfs',
      version='0.1',
      description=('A read-only FUSE-based filesystem allowing you to browse '
                   'a git repository\'s index'),
      long_description='',
      keywords='git,fuse,filesystem,fs',
      author='Martin Hostettler',
      author_email='',
      url='http://github.com/textshell/gitindexfs',
      license='MIT',
      packages=find_packages(),
      install_requires=['dulwich', 'fusepy', 'click', 'logbook'],
      entry_points={
          'console_scripts': [
              'gitindexfs = gitindexfs.cli:main',
          ]
      })
