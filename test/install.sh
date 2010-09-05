#!/bin/bash

# Tests whether dependencies are installed properly when rapid is installed
# through pip and easy_install.

function indent {
	$@ 2>&1 | sed 's/^/	/g'
}

function test {
	indent rapid
}

function setup {
	echo "setting up virtualenv"
	indent virtualenv $DIR
	cd $DIR
	. bin/activate
}

function teardown {
	echo "cleaning"
	cd $OLDPWD
	deactivate
	rm -r $DIR
}

DIR=.test
PACKAGE=rapid-spring #==0.4.0

setup
echo "trying pip"
indent pip install $PACKAGE
test
teardown

setup
echo "trying easy_install"
indent easy_install $PACKAGE
test
teardown
