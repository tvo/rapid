#!/bin/bash
# Author: Tobi Vollebregt

set -e
set -o pipefail

function check_version {
	if [ "$2" != "$VERSION" ]; then
		echo "$1 version mismatch, expected: $VERSION, actual: $2"
		exit 1
	fi
}

VERSION=$1
DIR=`mktemp -d`
trap "rm -rf $DIR" EXIT

if [ -z "$VERSION" ]; then
	echo "Usage: $0 <version>"
	echo "Example: $0 v0.4.2"
	exit 1
fi

echo "archiving to $DIR..."
git archive --format=tar HEAD | tar x -C $DIR

cd $DIR
	echo "checking version numbers against $VERSION..."
	check_version CHANGES.txt `head -n1 CHANGES.txt | cut -d, -f1`
	check_version setup.py v`grep -E -o '[0-9]+\.[0-9]+\.[0-9]+' setup.py`

	echo "creating README.txt..."
	make README.txt

	echo "creating source distribution..."
	python setup.py sdist

	echo "testing whether it installs correctly..."
	TEST_INSTALL=$OLDPWD/tools/test_install.sh
	$TEST_INSTALL $DIR/dist/*
cd $OLDPWD

# if all steps before succeeded we will continue with tagging and uploading

echo "tagging HEAD as $VERSION..."
git tag -a $VERSION -m "version $VERSION"

echo "pushing tag $VERSION to origin..."
git push origin $VERSION

echo "archiving to $DIR..."
git archive --format=tar $VERSION | tar x -C $DIR

cd $DIR
	# re-do this, as $Format:...$ attributes in README.markdown may have changed
	# rm needed because git archive messes with file modification times..
	echo "recreating README.txt..."
	rm -f README.txt && make README.txt

	echo "creating and uploading source distribution..."
	python setup.py sdist upload
cd $OLDPWD

echo "moving the source distribution to local directory dist..."
[ -d dist ] && mv -v $DIR/dist/* dist
