# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='rapid-spring',
    version='0.1.1',
    author='Tobi Vollebregt',
    author_email='',
    packages=['rapid'],
    scripts=['bin/rapid','bin/rapid-gui'],
    url='http://pypi.python.org/pypi/rapid-spring/',
    license='LICENSE.txt',
    description='spring contentt downloading',
    long_description=open('README.txt').read(),
)