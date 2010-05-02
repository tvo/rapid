Requirements
============


-  Python (tested on 2.6.2)
-  `python-bitarray <http://pypi.python.org/pypi/bitarray/0.3.2>`_
   (easy\_install bitarray)

Installation
============

Linux
-----

You can use *easy\_install* to get the package from the
`Python Package Index <http://pypi.python.org/pypi/rapid-spring/>`_.

::

    easy_install -U rapid-spring

If you do not have the script *easy\_install* available then use
your distribution's package manager to install the
python-setuptools (or similar) package.

::

    apt-get install python-setuptools      # Debian/Ubuntu
    yum install python-setuptools-devel    # Fedora

Usage
=====

::

    rapid <verb> [arguments...]

Where the different verbs and their arguments are:


-  ``upgrade``: Install the latest package for all pinned tags.
-  ``clean-upgrade``: Equivalent to 'upgrade' followed by
   'uninstall-unpinned'.
-  ``pin <tag>``: Pins a tag and installs the latest package for
   that tag.
-  ``unpin <tag>``: Unpins a tag. Does not uninstall any packages.
-  ``install <package>``: Install a package. Does not pin any tags.
-  ``uninstall <package>``: Uninstall a package. Unpin its tag if
   any.
-  ``list-tags [tag]``: List all tags that match *tag*.
-  ``list-pinned-tags [tag]``: Idem, but only pinned tags.
-  ``list-packages [package]``: List all packages whose name
   contains *argument*.
-  ``list-installed-packages [package]``: Idem, but only installed
   packages.
-  ``uninstall-unpinned``: Keep only the pinned tags and all
   dependencies. Uninstall all other packages.
-  ``collect-pool``: Remove pool files not needed by any installed
   package.
-  ``make-sdd <tag|package> <dir>``: Extract pool files of a
   package into ``~/.spring/mods/<dir>``.

Usually when a verb has a tag or a package as argument, an exact
match is not required. The ``list-*`` commands will list all
packages/tags that contain the given string and other commands will
ask you to disambiguate when multiple matching packages/tags were
found.

Examples:

::

    rapid pin xta:latest   # installs latest XTA
    rapid pin s44:latest   # installs latest Spring: 1944
    rapid upgrade          # upgrade all pinned tags

(the other commands are for advanced users mostly)

Bugs/quirks
===========


-  ``~/.spring/packages`` isn't scanned. This means that packages
   which have been installed using a different tool (e.g.
   SpringDownloader.exe) and were removed from the server (I don't
   think that ever happens now) before rapid was ever started, will
   not be picked up by rapid. As such, they can not be uninstalled,
   don't appear in listings, and collect-gc may even break them by
   removing their pool files.

Feature suggestions
===================


-  make-sdz command (similar to make-sdd) could be useful
-  Improve the GUI (``rapid-gui``)
-  Support alternative Spring data directory location


