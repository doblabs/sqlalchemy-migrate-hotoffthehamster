"""
   SQLAlchemy migrate provides two APIs :mod:`migrate.versioning` for
   database schema version and repository management and
   :mod:`migrate.changeset` that allows to define database schema changes
   using Python.
"""

import pkg_resources

from sqlalchemy_migrate_hotoffthehamster.versioning import *
from sqlalchemy_migrate_hotoffthehamster.changeset import *

__version__ = pkg_resources.get_provider(
    pkg_resources.Requirement.parse('sqlalchemy-migrate-hotoffthehamster')).version
