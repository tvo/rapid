# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='rapid-spring',
    version='0.2.0',
    author='Tobi Vollebregt',
    author_email='tobivollebregt@gmail.com',
    packages=['rapid'],
    scripts=['bin/rapid','bin/rapid-gui'],
    url='http://pypi.python.org/pypi/rapid-spring/',
    license='LICENSE.txt',
    description='spring content downloading',
    long_description=open('README.txt').read(),
    install_requires=['bitarray'],
)
