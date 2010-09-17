# Copyright (C) 2010 Tobi Vollebregt
# pylint: disable-msg=E1103,W0622

import sys
import unittest
from cStringIO import StringIO
from rapid.ui.tui import TextUserInteraction


OPTIONS = ['foo', 'bar', 'baz']


class Test(unittest.TestCase):

	def setUp(self):
		self.old_stdin = sys.stdin
		self.old_stdout = sys.stdout
		sys.stdout = StringIO()
		self.ui = TextUserInteraction()

	def tearDown(self):
		sys.stdout = self.old_stdout
		sys.stdin = self.old_stdin

	def test_init(self):
		self.assertFalse(self.ui.force)

	def _test_confirm(self, input, output):
		sys.stdin = StringIO(input)
		self.assertEqual(output, self.ui.confirm('Are you sure?'))
		self.assertEqual('Are you sure? [y/N]: ', sys.stdout.getvalue())

	def test_confirm_yes(self):
		self._test_confirm('y', True)

	def test_confirm_no(self):
		self._test_confirm('n', False)

	def test_confirm_invalid(self):
		self._test_confirm('x', False)

	def _test_choose_many(self, input, output):
		sys.stdin = StringIO(input)
		which = self.ui.choose_many('Header', OPTIONS, 'Which?')
		self.assertEqual(output, which)
		self.assertTrue(sys.stdout.getvalue().startswith(
			'Header\n 1.  foo\n 2.  bar\n 3.  baz\nWhich? [enter number(s) or "all"]: '))

	def test_choose_many_1(self):
		self._test_choose_many('1', OPTIONS[0:1])

	def test_choose_many_2(self):
		self._test_choose_many('2, 3', OPTIONS[1:3])

	def test_choose_many_all(self):
		self._test_choose_many('all', OPTIONS)

	def test_choose_many_invalid(self):
		self._test_choose_many('lalala', [])

	def test_choose_many_oob(self):
		self._test_choose_many('4', [])
		self.assertTrue(sys.stdout.getvalue().endswith(
			'IndexError: list index out of range\n'))

	def _test_select(self, needle, output, input = '', options = None):
		sys.stdin = StringIO(input)
		which = self.ui.select('item', needle, options or OPTIONS)
		self.assertEqual(output, which)

	def test_select_no_matches(self):
		self._test_select('x', [])
		self.assertEqual('No items matching "x" found.\n', sys.stdout.getvalue())

	def test_select_too_many_matches(self):
		self._test_select('x', [], options = ['x'] * 33 + ['xy'] * 33 + ['zx'] * 34)
		self.assertTrue(sys.stdout.getvalue().startswith(
			'100 or more items matching "x" found'))

	def test_select_one(self):
		self._test_select('Oo', ['foo'])
		self.assertEqual('', sys.stdout.getvalue())

	def test_select_many(self):
		self._test_select('ba', ['bar', 'baz'], input = '1,2')
		self.assertTrue(sys.stdout.getvalue().startswith(
			'Multiple items matching "ba" found:\n'))

	def test_output_table(self):
		self.ui.output_header('=header=')
		self.ui.output_detail('line 1')
		self.ui.output_detail('line 2')
		self.assertEqual('=header=\nline 1\nline 2\n', sys.stdout.getvalue())

	def test_important_warning(self):
		self.ui.important_warning('!! WARNING !!')
		output = sys.stdout.getvalue()
		self.assertEqual(2 * 79 + 2, output.count('#'))
		self.assertEqual(5, output.count('\n'))


if __name__ == "__main__":
	unittest.main()
