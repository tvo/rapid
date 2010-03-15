# Requirements

 * Python (tested on 2.6.2)
 * [python-bitarray](http://pypi.python.org/pypi/bitarray/0.3.2)

# Usage

    rapid <verb> [<argument>]

Where *verb* is one of:

 * update|upgrade: Install the latest package for all pinned tags.
 * pin: Pins a tag and installs the latest package for that tag.
 * unpin: Unpins a tag. Does not uninstall any packages.
 * install: Install a package. Does not pin any tags.
 * uninstall: Uninstall a package. Unpin its tag if any.
 * list-tags: List all tags that contain *argument*.
 * list-pinned-tags: Idem, but only pinned tags.
 * list-packages: List all packages whose name contains *argument*.
 * list-installed-packages: Idem, but only installed packages.

## Examples:

    rapid pin xta:latest           # installs latest XTA
    rapid pin 's44:latest mutator' # installs latest Spring: 1944
    rapid upgrade                  # upgrade all pinned tags

(the other commands are for advanced users mostly)
