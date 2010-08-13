# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='rapid-spring',
    version='0.3.2',
    author='Tobi Vollebregt',
    author_email='tobivollebregt@gmail.com',
    packages=['rapid', 'rapid.unitsync'],
    scripts=['bin/rapid','bin/rapid-gui'],
    url='http://pypi.python.org/pypi/rapid-spring/',
    license='LICENSE.txt',
    description='spring content downloading',
    long_description=open('README.txt').read(),
    requires=['bitarray'],
)
