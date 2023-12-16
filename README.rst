@@@@@@@@@@@@@@@@@@
SQLAlchemy Migrate
@@@@@@@@@@@@@@@@@@

.. CXREF:
   https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/adding-a-workflow-status-badge

.. image:: https://github.com/doblabs/sqlalchemy-migrate-hotoffthehamster/actions/workflows/checks-unspecial.yml/badge.svg?branch=release
  :target: https://github.com/doblabs/sqlalchemy-migrate-hotoffthehamster/actions/workflows/checks-unspecial.yml/badge.svg?branch=release
  :alt: Build Status

.. CXREF: https://app.codecov.io/github.com/doblabs/sqlalchemy-migrate-hotoffthehamster/settings/badge

.. image:: https://codecov.io/gh/doblabs/sqlalchemy-migrate-hotoffthehamster/branch/release/graph/badge.svg?token=XXX
  :target: https://app.codecov.io/gh/doblabs/sqlalchemy-migrate-hotoffthehamster
  :alt: Coverage Status

.. image:: https://readthedocs.org/projects/sqlalchemy-migrate-hotoffthehamster/badge/?version=latest
  :target: https://sqlalchemy-migrate-hotoffthehamster.readthedocs.io/en/latest/
  :alt: Documentation Status

.. image:: https://img.shields.io/github/v/release/doblabs/sqlalchemy-migrate-hotoffthehamster.svg?style=flat
  :target: https://github.com/doblabs/sqlalchemy-migrate-hotoffthehamster/releases
  :alt: GitHub Release Status

.. image:: https://img.shields.io/pypi/v/sqlalchemy-migrate-hotoffthehamster.svg
  :target: https://pypi.org/project/sqlalchemy-migrate-hotoffthehamster/
  :alt: PyPI Release Status

.. image:: https://img.shields.io/pypi/pyversions/sqlalchemy-migrate-hotoffthehamster.svg
  :target: https://pypi.org/project/sqlalchemy-migrate-hotoffthehamster/
  :alt: PyPI Supported Python Versions

.. image:: https://img.shields.io/github/license/doblabs/sqlalchemy-migrate-hotoffthehamster.svg?style=flat
  :target: https://github.com/doblabs/sqlalchemy-migrate-hotoffthehamster/blob/release/LICENSE
  :alt: License Status

|

Fork from http://code.google.com/p/sqlalchemy-migrate/ to get it working with
SQLAlchemy 0.8.

Inspired by Ruby on Rails' migrations, Migrate provides a way to deal with
database schema changes in `SQLAlchemy <http://sqlalchemy.org>`_ projects.

Migrate extends SQLAlchemy to have database changeset handling. It provides a
database change repository mechanism which can be used from the command line as
well as from inside python code.

####
Help
####

Sphinx documentation is available at the project page `readthedocs.org
<https://sqlalchemy-migrate.readthedocs.org/>`_.

Users and developers can be found at #openstack-dev on Freenode IRC
network and at the public users mailing list `migrate-users
<http://groups.google.com/group/migrate-users>`_.

New releases and major changes are announced at the public announce mailing
list `openstack-dev
<http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-dev>`_
and at the Python package index `sqlalchemy-migrate
<http://pypi.python.org/pypi/sqlalchemy-migrate>`_.

Homepage is located at `stackforge
<http://github.com/stackforge/sqlalchemy-migrate/>`_

You can also clone a current `development version
<http://github.com/stackforge/sqlalchemy-migrate>`_


##############
Tests and Bugs
##############

To run automated tests:

* install tox: ``pip install -U tox``
* run tox: ``tox``
* to test only a specific Python version: ``tox -e py27`` (Python 2.7)

Please report any issues with sqlalchemy-migrate to the issue tracker at
`Launchpad issues
<https://bugs.launchpad.net/sqlalchemy-migrate>`_
