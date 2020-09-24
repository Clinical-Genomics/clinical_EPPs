#!/usr/bin/env python

from setuptools import setup, find_packages
import glob
import os

setup(name='clinical_EPPs',
        version='1.0',
        description='',
        author='Maya Brandi',
        author_email='maya.brandi@scilifelab.se',
        packages=find_packages(),
        scripts=glob.glob("EPPs/*.py"),
        include_package_data=True,
        entry_points={
        'console_scripts': ['epps=clinical_EPPs.commands:cli'],
    },

     )
