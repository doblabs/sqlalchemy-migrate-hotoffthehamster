#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

import six

from sqlalchemy_migrate_hotoffthehamster import exceptions
from sqlalchemy_migrate_hotoffthehamster.versioning.schema import *
from sqlalchemy_migrate_hotoffthehamster.versioning import script, schemadiff

from sqlalchemy import *

from sqlalchemy_migrate_hotoffthehamster.tests import fixture


class TestControlledSchema(fixture.Pathed, fixture.DB):
    # Transactions break postgres in this test; we'll clean up after ourselves
    level = fixture.DB.CONNECT

    def setUp(self, skip_testtools_setUp=False):
        # Called before test case runs, via testtools, and then
        # called again later by usedb() fixture.
        super(TestControlledSchema, self).setUp(skip_testtools_setUp=skip_testtools_setUp)
        self.path_repos = self.temp_usable_dir + '/repo/'
        self.repos = Repository.create(self.path_repos, 'repo_name')

    def _setup(self, url, skip_testtools_setUp=False):
        self.setUp(skip_testtools_setUp=skip_testtools_setUp)
        super(TestControlledSchema, self)._setup(url)
        self.cleanup()

    def _teardown(self, skip_testtools_tearDown=False):
        super(TestControlledSchema, self)._teardown()
        self.cleanup()
        self.tearDown(skip_testtools_tearDown=skip_testtools_tearDown)

    def cleanup(self):
        # drop existing version table if necessary
        try:
            ControlledSchema(self.engine, self.repos).drop()
        except:
            # No table to drop; that's fine, be silent
            pass

    def tearDown(self, skip_testtools_tearDown=False):
        self.cleanup()
        super(TestControlledSchema, self).tearDown(skip_testtools_tearDown=skip_testtools_tearDown)

    @fixture.usedb()
    def test_version_control(self):
        """Establish version control on a particular database"""
        # Establish version control on this database
        dbcontrol = ControlledSchema.create(self.engine, self.repos)

        # Trying to create another DB this way fails: table exists
        self.assertRaises(exceptions.DatabaseAlreadyControlledError,
            ControlledSchema.create, self.engine, self.repos)

        # We can load a controlled DB this way, too
        dbcontrol0 = ControlledSchema(self.engine, self.repos)
        self.assertEqual(dbcontrol, dbcontrol0)

        # We can also use a repository path, instead of a repository
        dbcontrol0 = ControlledSchema(self.engine, self.repos.path)
        self.assertEqual(dbcontrol, dbcontrol0)

        # We don't have to use the same connection
        engine = create_engine(self.url)
        dbcontrol0 = ControlledSchema(engine, self.repos.path)
        self.assertEqual(dbcontrol, dbcontrol0)

        # Clean up:
        dbcontrol.drop()

        # Attempting to drop vc from a db without it should fail
        self.assertRaises(exceptions.DatabaseNotControlledError, dbcontrol.drop)

        # No table defined should raise error
        self.assertRaises(exceptions.DatabaseNotControlledError,
            ControlledSchema, self.engine, self.repos)

    @fixture.usedb()
    def test_version_control_specified(self):
        """Establish version control with a specified version"""
        # Establish version control on this database
        version = 0
        dbcontrol = ControlledSchema.create(self.engine, self.repos, version)
        self.assertEqual(dbcontrol.version, version)

        # Correct when we load it, too
        dbcontrol = ControlledSchema(self.engine, self.repos)
        self.assertEqual(dbcontrol.version, version)

        dbcontrol.drop()

        # Now try it with a nonzero value
        version = 10
        for i in range(version):
            self.repos.create_script('')
        self.assertEqual(self.repos.latest, version)

        # Test with some mid-range value
        dbcontrol = ControlledSchema.create(self.engine,self.repos, 5)
        self.assertEqual(dbcontrol.version, 5)
        dbcontrol.drop()

        # Test with max value
        dbcontrol = ControlledSchema.create(self.engine, self.repos, version)
        self.assertEqual(dbcontrol.version, version)
        dbcontrol.drop()

    @fixture.usedb()
    def test_version_control_invalid(self):
        """Try to establish version control with an invalid version"""
        versions = ('Thirteen', '-1', -1, '' , 13)
        # A fresh repository doesn't go up to version 13 yet
        for version in versions:
            #self.assertRaises(ControlledSchema.InvalidVersionError,
            # Can't have custom errors with assertRaises...
            try:
                ControlledSchema.create(self.engine, self.repos, version)
                self.assertTrue(False, repr(version))
            except exceptions.InvalidVersionError:
                pass

    @fixture.usedb()
    def test_changeset(self):
        """Create changeset from controlled schema"""
        dbschema = ControlledSchema.create(self.engine, self.repos)

        # empty schema doesn't have changesets
        cs = dbschema.changeset()
        self.assertEqual(cs, {})

        for i in range(5):
            self.repos.create_script('')
        self.assertEqual(self.repos.latest, 5)

        cs = dbschema.changeset(5)
        self.assertEqual(len(cs), 5)

        # cleanup
        dbschema.drop()

    @fixture.usedb()
    def test_upgrade_runchange(self):
        dbschema = ControlledSchema.create(self.engine, self.repos)

        for i in range(10):
            self.repos.create_script('')

        self.assertEqual(self.repos.latest, 10)

        dbschema.upgrade(10)

        self.assertRaises(ValueError, dbschema.upgrade, 'a')
        self.assertRaises(exceptions.InvalidVersionError, dbschema.runchange, 20, '', 1)

        # TODO: test for table version in db

        # cleanup
        dbschema.drop()

    @fixture.usedb()
    def test_create_model(self):
        """Test workflow to generate create_model"""
        model = ControlledSchema.create_model(self.engine, self.repos, declarative=False)
        self.assertTrue(isinstance(model, six.string_types))

        model = ControlledSchema.create_model(self.engine, self.repos.path, declarative=True)
        self.assertTrue(isinstance(model, six.string_types))

    @fixture.usedb()
    def test_compare_model_to_db(self):
        meta = self.construct_model()

        diff = ControlledSchema.compare_model_to_db(self.engine, meta, self.repos)
        self.assertTrue(isinstance(diff, schemadiff.SchemaDiff))

        diff = ControlledSchema.compare_model_to_db(self.engine, meta, self.repos.path)
        self.assertTrue(isinstance(diff, schemadiff.SchemaDiff))
        meta.drop_all(self.engine)

    @fixture.usedb()
    def test_update_db_from_model(self):
        dbschema = ControlledSchema.create(self.engine, self.repos)

        meta = self.construct_model()

        dbschema.update_db_from_model(meta)

        # TODO: test for table version in db

        # cleanup
        dbschema.drop()
        meta.drop_all(self.engine)

    def construct_model(self):
        meta = MetaData()

        user = Table('temp_model_schema', meta, Column('id', Integer), Column('user', String(245)))

        return meta

    # TODO: test how are tables populated in db
