#!/bin/bash
# Author: Tobi Vollebregt

# Tests whether dependencies are installed properly when rapid is installed
# through pip and easy_install.

function indent {
	$@ 2>&1 | sed 's/^/	/g'
}

function test {
	if rapid | grep -q '^Usage: '; then
		echo "SUCCESS"
	else
		echo "FAILURE"
		EXIT_STATUS=1
	fi
}

function setup {
	echo "setting up virtualenv"
	DIR=`mktemp -d`
	trap "rm -rf $DIR" EXIT
	indent virtualenv --clear --no-site-packages $DIR
	cd $DIR
	. bin/activate
}

function teardown {
	echo "cleaning"
	cd $OLDPWD
	deactivate
}

PACKAGE=${1:-rapid-spring} #==0.4.0
EXIT_STATUS=0

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

exit $EXIT_STATUS
