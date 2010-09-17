# Author: Tobi Vollebregt

'''
Quick hack to be able to keep using `import unittest' everywhere,
and still be able to actually use unittest2 features on python 2.6
(unittest2 is a backport of python 2.7 unittest to earlier versions)
'''

import sys
if sys.hexversion < 0x02070000:
	import unittest2
	sys.modules['unittest'] = unittest2
