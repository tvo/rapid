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

    easy_install rapid-spring

If you do not have the script *easy\_install* available then use
your distribution's package manager to install the
python-setuptools (or similar) package.

::

    apt-get install python-setuptools      # Debian/Ubuntu
    yum install python-setuptools-devel    # Fedora

Usage
=====

::

    rapid <verb> [<argument>]

Where *verb* is one of:


-  update\|upgrade: Install the latest package for all pinned tags.
-  pin: Pins a tag and installs the latest package for that tag.
-  unpin: Unpins a tag. Does not uninstall any packages.
-  install: Install a package. Does not pin any tags.
-  uninstall: Uninstall a package. Unpin its tag if any.
-  list-tags: List all tags that contain *argument*.
-  list-pinned-tags: Idem, but only pinned tags.
-  list-packages: List all packages whose name contains *argument*.
-  list-installed-packages: Idem, but only installed packages.
-  uninstall-unpinned: Keep only the pinned tags and all
   dependencies.
-  collect-pool: Remove pool files not needed by any installed
   package.

Examples:
---------

::

    rapid pin xta:latest           # installs latest XTA
    rapid pin 's44:latest mutator' # installs latest Spring: 1944
    rapid upgrade                  # upgrade all pinned tags

(the other commands are for advanced users mostly)

Bugs/quirks
===========


-  No known bugs/quirks

Feature suggestions
===================


-  make-sdz command (similar to make-sdd) could be useful


