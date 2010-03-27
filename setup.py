# -*- coding: utf-8 -*-
from distutils.core import setup
import os, sys

if 0 != os.system('pandoc -f markdown -t rst README.markdown -o README.txt'):
	print
	print 'Do you have pandoc installed?'
	print 'http://johnmacfarlane.net/pandoc/'
	print
	sys.exit(1)

setup(
    name='rapid-spring',
    version='0.1.7',
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
