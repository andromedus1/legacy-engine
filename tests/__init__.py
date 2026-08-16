"""Project test package for shared hermetic fixtures.

The historical suite contains both ``tests.*`` and sibling-module imports.  Keep the
test root ahead of unrelated site-packages so both established forms resolve to this
repository during collection.
"""

from pathlib import Path
import sys

_TEST_ROOT = str(Path(__file__).parent)
if _TEST_ROOT not in sys.path:
    sys.path.insert(0, _TEST_ROOT)
