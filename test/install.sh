#!/bin/bash

# Tests whether dependencies are installed properly when rapid is installed through easy_install.

function indent {
	$@ 2>&1 | sed 's/^/	/g'
	return ${PIPESTATUS[0]}
}

function test {
	indent rapid && echo SUCCESS || echo FAILURE
}

DIR=.test

echo "setting up virtualenv"
indent virtualenv $DIR
cd $DIR
. bin/activate

echo "trying pip"
indent pip install rapid-spring
test
echo y | indent pip uninstall rapid-spring

echo "trying easy_install"
indent easy_install rapid-spring
test

echo "cleaning"
cd $OLDPWD
indent deactivate
rm -r $DIR
