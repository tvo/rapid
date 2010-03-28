#!/bin/bash

set -e

DOCDIR=docs/html/

cd $(dirname $0)/..

pydoc -w rapid
if [ ! -d ${DOCDIR} ] ; then
	mkdir -p ${DOCDIR}
fi
mv rapid.html ${DOCDIR}/index.html
cd rapid
for f in $(ls *.py ) ; do
	module=${f%.py}
	if [ ${module} != __init__ ] ; then
		pydoc -w ${module}
		mv ${module}.html ../${DOCDIR}/rapid.${module}.html 
	fi
done

cd $(dirname $0)/..
git add ${DOCDIR}
git commit -m 'automatic docs update'
