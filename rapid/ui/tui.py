# Copyright (C) 2010 Tobi Vollebregt

import re

class TextUserInteraction:
	def __init__(self, force=False):
		self.force = force

	def confirm(self, text):
		""" Ask the user for confirmation."""
		return self.force or raw_input(text + ' [y/N]: ').startswith('y')

	def _to_i_bounds_check(self, text, lower, upper):
		i = int(text)
		if i < lower or i > upper:
			# raise IndexError with standard message
			arr = [] ; arr[i]
		return i

	def choose_many(self, header, options, question):
		""" Let the user choose multiple options from a list."""
		print header
		for i in range(len(options)):
			print '%2i.  %s' % (i + 1, options[i])
		which = raw_input(question + ' [enter number(s) or "all"]: ')
		if which.lower().strip() == 'all':
			return options
		which = re.split(r'[\s,]+', which)
		try:
			n = len(options)
			which = [self._to_i_bounds_check(x, 1, n) - 1 for x in which]
		except (ValueError, IndexError) as e:
			print type(e).__name__ + ':', str(e)
			return []
		return [options[x] for x in which]

	def _select_core(self, needle, haystack):
		""" Override/patch this to implement other search strategy.
		This variant implements a simple case-insensitive substring search."""
		n = needle.lower()
		return filter(lambda s: n in str(s).lower(), haystack)

	def select(self, noun, needle, haystack):
		""" Select items from a list based on needle, and take appropriate
		action based on the number of results this returns."""
		selected = self._select_core(needle, haystack)

		if len(selected) == 0:
			print 'No %ss matching "%s" found.' % (noun, needle)
			return selected

		if len(selected) >= 100:
			print '100 or more %ss matching "%s" found, please narrow your search.' % (noun, needle)
			return []

		if len(selected) > 1:
			return self.choose_many('Multiple %ss matching "%s" found:' % (noun, needle), selected, 'Which %s do you mean?' % noun)

		return selected

	def output_header(self, text):
		""" Output the header of a list/table."""
		print text

	def output_detail(self, text):
		""" Output a detail row of a list/table.
		TODO: Interface should be improved."""
		print text

	def important_warning(self, *lines):
		""" Display an important warning to the user."""
		print
		print '#' * 79
		for line in lines:
			print '# %-75s #' % line.center(75)
		print '#' * 79
		print
