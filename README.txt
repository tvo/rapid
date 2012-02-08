Requirements
============


-  Python (tested on 2.6.2 and 2.6.4)
-  `python-bitarray <http://pypi.python.org/pypi/bitarray/>`_
   (``pip install bitarray``)

Installation
============

Linux
-----

You can use *pip* to get the package from the
`Python Package Index <http://pypi.python.org/pypi/rapid-spring/>`_.

::

    pip install rapid-spring --upgrade

If you do not have the script *pip* available then use your
distribution's package manager to install the python-pip (or
similar) package.

::

    apt-get install python-pip   # Debian/Ubuntu
    yum install python-pip       # Fedora

Windows
-------

As there is currently no binary package, go through the following
steps to run rapid on Windows:


-  Download and install
   `python 2.6 <http://www.python.org/download/releases/2.6/>`_
-  Download and install
   `setuptools <http://pypi.python.org/pypi/setuptools#files>`_ (for
   python 2.6!)
-  Suppose you installed python in ``c:\python26``, make sure the
   PATH environment variable contains ``c:\python26`` and
   ``c:\python26\scripts``
-  Open a console and run ``easy_install -U rapid-spring``
-  Rapid is now installed! Continue reading to learn how to use
   rapid :-)

Why python 2.6? Simple answer: bitarray binary packages are not
available yet for python 2.7

Usage
=====

::

    rapid [options...] <verb>  [arguments...]

Where the different verbs and their arguments are:


-  ``upgrade``: Install the latest package for all pinned tags.
-  ``clean-upgrade``: Equivalent to 'upgrade' followed by
   'uninstall-unpinned'.
-  ``pin <tag(s)>``: Pins tags and installs the latest packages for
   those tags.
-  ``unpin <tag(s)>``: Unpins tags. Does not uninstall any
   packages.
-  ``install <package(s)>``: Install packages. Does not pin any
   tags.
-  ``uninstall <package(s)>``: Uninstall packages. Unpins their
   tags if any.
-  ``list-tags [tag]``: List all tags that match *tag*.
-  ``list-pinned-tags [tag]``: Idem, but only pinned tags.
-  ``list-packages [package]``: List all packages whose name
   contains *package*.
-  ``list-installed-packages [package]``: Idem, but only installed
   packages.
-  ``uninstall-unpinned``: Keep only the pinned tags and all
   dependencies.
-  ``collect-pool``: Remove pool files not needed by any installed
   package.
-  ``make-sdd <tag|package> <dir>``: Extract pool files of a
   package into ``~/.spring/mods/<dir>``.

Examples:
---------

::

    rapid pin xta:latest   # installs latest XTA
    rapid pin s44:latest   # installs latest Spring: 1944
    rapid upgrade          # upgrade all pinned tags

Other commands are for power users mostly, e.g.:

::

    rapid list-tags '^(?!ba).*:(latest|stable|test)$' --regex

This displays all tags ending with ':latest', ':stable' or ':test',
which do not start with the string 'ba'.

Options:
--------


-  -h, --help show this help message and exit
-  --datadir=DATADIR Override the default data directory.
   (~/.spring on Linux or the one reported by unitsync on Windows)
-  --unitsync Use unitsync to locate the data directory Spring
   uses.
-  --no-unitsync Do not use unitsync.
-  -r, --regex Use regular expressions instead of substring matches
   for pin, unpin, install, uninstall and all list-\* commands.
-  -y, --yes Answer all confirmations with yes. MAY BE DANGEROUS!

Bugs/quirks
===========


-  ``~/.spring/packages`` isn't scanned. This means that packages
   which have been installed using a different tool (e.g.
   SpringDownloader.exe) and were removed from the server (I don't
   think that ever happens now) before rapid was ever started, will
   not be picked up by rapid. As such, they can not be uninstalled,
   don't appear in listings, and collect-gc may even break them by
   removing their pool files.

-  unitsync is noisy on standard output. This should be fixed in
   unitsync however, and not worked around in rapid.

-  unitsync insists on scanning all maps and mods while we only
   want to know the location of the data directory. This should also
   be fixed in unitsync.


Please file any other bugs you find on
`the issue tracker <http://github.com/tvo/rapid/issues>`_.

Feature suggestions
===================


-  make-sdz command (similar to make-sdd) could be useful
-  Improve the GUI (``rapid-gui``)
-  Add GUI progressbar, even for the commandline script (may be
   useful when integrating it in another app)
-  Machine friendly progressbar, so other apps can parse it and
   render their own progressbar

--------------

Exported from git commit :math:`$Format:%H$`


