#!/bin/bash

# Tests whether dependencies are installed properly when rapid is installed through easy_install.

function indent {
	$@ 2>&1 | sed 's/^/	/g'
}

function test {
	indent rapid
}

DIR=.test
PACKAGE=rapid-spring

echo "setting up virtualenv"
indent virtualenv $DIR
cd $DIR
. bin/activate

echo "trying pip"
indent pip install $PACKAGE
test
echo y | indent pip uninstall $PACKAGE

echo "trying easy_install"
indent easy_install $PACKAGE
test

echo "cleaning"
cd $OLDPWD
indent deactivate
rm -r $DIR
