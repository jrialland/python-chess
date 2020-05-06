#!/usr/bin/env python3

import setuptools


import chess3

setuptools.setup(
      name='chess3',
      version= chess3.__version__,
      description='chess library',
      author='Julien Rialland',
      author_email='julien.rialland@gmail.com',
      url='https://github.com/jrialland/python-chess',
      packages=['chess3'],
      classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Games/Entertainment"
      ],
      python_requires='>=3.6',
)

