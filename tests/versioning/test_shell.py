#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tempfile

import six
from six.moves import cStringIO
from sqlalchemy import MetaData, Table

from sqlalchemy_migrate_hotoffthehamster.exceptions import *
from sqlalchemy_migrate_hotoffthehamster.versioning.repository import Repository
from sqlalchemy_migrate_hotoffthehamster.versioning import shell, api
from sqlalchemy_migrate_hotoffthehamster.tests.fixture import Shell, DB, usedb
from sqlalchemy_migrate_hotoffthehamster.tests.fixture import models


class TestShellCommands(Shell):
    """Tests sqlalchemy_migrate_hotoffthehamster.py commands"""

    def test_help(self):
        """Displays default help dialog"""
        self.assertEqual(self.env.run('migrate-hoth -h').returncode, 0)
        self.assertEqual(self.env.run('migrate-hoth --help').returncode, 0)
        self.assertEqual(self.env.run('migrate-hoth help').returncode, 0)

    def test_help_commands(self):
        """Display help on a specific command"""
        # we can only test that we get some output
        for cmd in api.__all__:
            result = self.env.run('migrate-hoth help %s' % cmd)
            self.assertTrue(isinstance(result.stdout, six.string_types))
            self.assertTrue(result.stdout)
            self.assertFalse(result.stderr)

    def test_shutdown_logging(self):
        """Try to shutdown logging output"""
        repos = self.tmp_repos()
        result = self.env.run('migrate-hoth create %s repository_name' % repos)
        result = self.env.run('migrate-hoth version %s --disable_logging' % repos)
        self.assertEqual(result.stdout, '')
        result = self.env.run('migrate-hoth version %s -q' % repos)
        self.assertEqual(result.stdout, '')

        # TODO: assert logging messages to 0
        shell.main(['version', repos], logging=False)

    # 2023-12-15: This test calls `del sys.modules[module]`, which hopefully
    # looks awful and smells awkward to you.
    #
    # - The run_module call is how Python implements `python -m <module>`:
    #
    #   - "The runpy module is used to locate and run Python modules without
    #      importing them first. Its main use is to implement the -m command
    #      line switch that allows scripts to be located using the Python
    #      module namespace rather than the filesystem."
    #
    #      - REFER: https://docs.python.org/3/library/runpy.html
    #
    # - Given that runpy doesn't import the module first, but rather just
    #   runs it (however that works), it's designed to emit a warning if
    #   the module being executed was previously imported, e.g.,
    #
    #     <frozen runpy>:128: RuntimeWarning:
    #       'sqlalchemy_migrate_hotoffthehamster.versioning.shell'
    #     found in sys.modules after import of package
    #       'sqlalchemy_migrate_hotoffthehamster.versioning',
    #     but prior to execution
    #       'sqlalchemy_migrate_hotoffthehamster.versioning.shell';
    #     this may result in unpredictable behaviour
    #
    # - At first, I tried to silence the warning by using import aliases,
    #   e.g., instead of this:
    #
    #     from sqlalchemy_migrate_hotoffthehamster.versioning import shell, api
    #
    #   I tried this:
    #
    #     from sqlalchemy_migrate_hotoffthehamster import versioning as migrate_versioning
    #
    #   which sorta worked, but not completely.
    #
    # - Next, I ran this test from its own module. But `pytest` runs everything
    #   within a single invocation, so I was not surprised that that didn't work,
    #   either.
    #
    # - Finally, as a last resort, I added code to manipulate sys.modules
    #   directly (an anti-pattern, for sure), which (thankfully?) works.
    #
    #   - And note that once a module is loaded in Python, there's not technically
    #     a way to unload it. We can delete it from `sys.modules`, which appeases
    #     runpy (I'd guess it just doesn't see the module, even though it's still
    #     there). So while runpy no longer warns us that the universe is unsettled,
    #     I fear that playing god and meddling with sys.modules is an imperfect
    #     solution. But Hey, It Works (At Least For Now)!
    def test_main_with_runpy(self):
        if sys.version_info[:2] == (2, 4):
            self.skipTest("runpy is not part of python2.4")
        from runpy import run_module
        try:
            original = sys.argv
            sys.argv=['X','--help']

            # See comment above function def; this Good Idea or Bad Idea? Who Knows.
            module_name = 'sqlalchemy_migrate_hotoffthehamster.versioning.shell'
            if module_name in sys.modules:
                del sys.modules[module_name]

            run_module(module_name, run_name='__main__')

        finally:
            sys.argv = original

    def _check_error(self,args,code,expected,**kw):
        original = sys.stderr
        try:
            actual = cStringIO()
            sys.stderr = actual
            try:
                shell.main(args,**kw)
            except SystemExit as e:
                self.assertEqual(code,e.args[0])
            else:
                self.fail('No exception raised')
        finally:
            sys.stderr = original
        actual = actual.getvalue()
        self.assertTrue(expected in actual,'%r not in:\n"""\n%s\n"""'%(expected,actual))

    def test_main(self):
        """Test main() function"""
        repos = self.tmp_repos()
        shell.main(['help'])
        shell.main(['help', 'create'])
        shell.main(['create', 'repo_name', '--preview_sql'], repository=repos)
        shell.main(['version', '--', '--repository=%s' % repos])
        shell.main(['version', '-d', '--repository=%s' % repos, '--version=2'])

        self._check_error(['foobar'],2,'error: Invalid command foobar')
        self._check_error(['create', 'f', 'o', 'o'],2,'error: Too many arguments for command create: o')
        self._check_error(['create'],2,'error: Not enough arguments for command create: repository, name not specified')
        self._check_error(['create', 'repo_name'],2,'already exists', repository=repos)

    def test_create(self):
        """Repositories are created successfully"""
        repos = self.tmp_repos()

        # Creating a file that doesn't exist should succeed
        result = self.env.run('migrate-hoth create %s repository_name' % repos)

        # Files should actually be created
        self.assertTrue(os.path.exists(repos))

        # The default table should not be None
        repos_ = Repository(repos)
        self.assertNotEqual(repos_.config.get('db_settings', 'version_table'), 'None')

        # Can't create it again: it already exists
        result = self.env.run('migrate-hoth create %s repository_name' % repos,
            expect_error=True)
        self.assertEqual(result.returncode, 2)

    def test_script(self):
        """We can create a migration script via the command line"""
        repos = self.tmp_repos()
        result = self.env.run('migrate-hoth create %s repository_name' % repos)

        result = self.env.run('migrate-hoth script --repository=%s Desc' % repos)
        self.assertTrue(os.path.exists('%s/versions/001_Desc.py' % repos))

        result = self.env.run('migrate-hoth script More %s' % repos)
        self.assertTrue(os.path.exists('%s/versions/002_More.py' % repos))

        result = self.env.run('migrate-hoth script "Some Random name" %s' % repos)
        self.assertTrue(os.path.exists('%s/versions/003_Some_Random_name.py' % repos))

    def test_script_sql(self):
        """We can create a migration sql script via the command line"""
        repos = self.tmp_repos()
        result = self.env.run('migrate-hoth create %s repository_name' % repos)

        result = self.env.run('migrate-hoth script_sql mydb foo %s' % repos)
        self.assertTrue(os.path.exists('%s/versions/001_foo_mydb_upgrade.sql' % repos))
        self.assertTrue(os.path.exists('%s/versions/001_foo_mydb_downgrade.sql' % repos))

        # Test creating a second
        result = self.env.run('migrate-hoth script_sql postgres foo --repository=%s' % repos)
        self.assertTrue(os.path.exists('%s/versions/002_foo_postgres_upgrade.sql' % repos))
        self.assertTrue(os.path.exists('%s/versions/002_foo_postgres_downgrade.sql' % repos))

        # TODO: test --previews

    def test_manage(self):
        """Create a project management script"""
        script = self.tmp_py()
        self.assertTrue(not os.path.exists(script))

        # No attempt is made to verify correctness of the repository path here
        result = self.env.run('migrate-hoth manage %s --repository=/bla/' % script)
        self.assertTrue(os.path.exists(script))


class TestShellRepository(Shell):
    """Shell commands on an existing repository/python script"""

    def setUp(self):
        """Create repository, python change script"""
        super(TestShellRepository, self).setUp()
        self.path_repos = self.tmp_repos()
        result = self.env.run('migrate-hoth create %s repository_name' % self.path_repos)

    def test_version(self):
        """Correctly detect repository version"""
        # Version: 0 (no scripts yet); successful execution
        result = self.env.run('migrate-hoth version --repository=%s' % self.path_repos)
        self.assertEqual(result.stdout.strip(), "0")

        # Also works as a positional param
        result = self.env.run('migrate-hoth version %s' % self.path_repos)
        self.assertEqual(result.stdout.strip(), "0")

        # Create a script and version should increment
        result = self.env.run('migrate-hoth script Desc %s' % self.path_repos)
        result = self.env.run('migrate-hoth version %s' % self.path_repos)
        self.assertEqual(result.stdout.strip(), "1")

    def test_source(self):
        """Correctly fetch a script's source"""
        result = self.env.run('migrate-hoth script Desc --repository=%s' % self.path_repos)

        filename = '%s/versions/001_Desc.py' % self.path_repos
        source = open(filename).read()
        self.assertTrue(source.find('def upgrade') >= 0)

        # Version is now 1
        result = self.env.run('migrate-hoth version %s' % self.path_repos)
        self.assertEqual(result.stdout.strip(), "1")

        # Output/verify the source of version 1
        result = self.env.run('migrate-hoth source 1 --repository=%s' % self.path_repos)
        self.assertEqual(result.stdout.strip(), source.strip())

        # We can also send the source to a file... test that too
        result = self.env.run('migrate-hoth source 1 %s --repository=%s' %
            (filename, self.path_repos))
        self.assertTrue(os.path.exists(filename))
        fd = open(filename)
        result = fd.read()
        self.assertTrue(result.strip() == source.strip())


class TestShellDatabase(Shell, DB):
    """Commands associated with a particular database"""
    # We'll need to clean up after ourself, since the shell creates its own txn;
    # we need to connect to the DB to see if things worked

    level = DB.CONNECT

    @usedb()
    def test_version_control(self):
        """Ensure we can set version control on a database"""
        path_repos = repos = self.tmp_repos()
        url = self.url
        result = self.env.run('migrate-hoth create %s repository_name' % repos)

        result = self.env.run('migrate-hoth drop_version_control %(url)s %(repos)s'\
            % locals(), expect_error=True)
        self.assertEqual(result.returncode, 1)
        result = self.env.run('migrate-hoth version_control %(url)s %(repos)s' % locals())

        # Clean up
        result = self.env.run('migrate-hoth drop_version_control %(url)s %(repos)s' % locals())
        # Attempting to drop vc from a database without it should fail
        result = self.env.run('migrate-hoth drop_version_control %(url)s %(repos)s'\
            % locals(), expect_error=True)
        self.assertEqual(result.returncode, 1)

    @usedb()
    def test_wrapped_kwargs(self):
        """Commands with default arguments set by manage.py"""
        path_repos = repos = self.tmp_repos()
        url = self.url
        result = self.env.run('migrate-hoth create --name=repository_name %s' % repos)
        result = self.env.run('migrate-hoth drop_version_control %(url)s %(repos)s' % locals(), expect_error=True)
        self.assertEqual(result.returncode, 1)
        result = self.env.run('migrate-hoth version_control %(url)s %(repos)s' % locals())

        result = self.env.run('migrate-hoth drop_version_control %(url)s %(repos)s' % locals())

    @usedb()
    def test_version_control_specified(self):
        """Ensure we can set version control to a particular version"""
        path_repos = self.tmp_repos()
        url = self.url
        result = self.env.run('migrate-hoth create --name=repository_name %s' % path_repos)
        result = self.env.run('migrate-hoth drop_version_control %(url)s %(path_repos)s' % locals(), expect_error=True)
        self.assertEqual(result.returncode, 1)

        # Fill the repository
        path_script = self.tmp_py()
        version = 2
        for i in range(version):
            result = self.env.run('migrate-hoth script Desc --repository=%s' % path_repos)

        # Repository version is correct
        result = self.env.run('migrate-hoth version %s' % path_repos)
        self.assertEqual(result.stdout.strip(), str(version))

        # Apply versioning to DB
        result = self.env.run('migrate-hoth version_control %(url)s %(path_repos)s %(version)s' % locals())

        # Test db version number (should start at 2)
        result = self.env.run('migrate-hoth db_version %(url)s %(path_repos)s' % locals())
        self.assertEqual(result.stdout.strip(), str(version))

        # Clean up
        result = self.env.run('migrate-hoth drop_version_control %(url)s %(path_repos)s' % locals())

    @usedb()
    def test_upgrade(self):
        """Can upgrade a versioned database"""
        # Create a repository
        repos_name = 'repos_name'
        repos_path = self.tmp()
        result = self.env.run('migrate-hoth create %(repos_path)s %(repos_name)s' % locals())
        self.assertEqual(self.run_version(repos_path), 0)

        # Version the DB
        result = self.env.run('migrate-hoth drop_version_control %s %s' % (self.url, repos_path), expect_error=True)
        result = self.env.run('migrate-hoth version_control %s %s' % (self.url, repos_path))

        # Upgrades with latest version == 0
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)
        result = self.env.run('migrate-hoth upgrade %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)
        result = self.env.run('migrate-hoth upgrade %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)
        result = self.env.run('migrate-hoth upgrade %s %s 1' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 1)
        result = self.env.run('migrate-hoth upgrade %s %s -1' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 2)

        # Add a script to the repository; upgrade the db
        result = self.env.run('migrate-hoth script Desc --repository=%s' % (repos_path))
        self.assertEqual(self.run_version(repos_path), 1)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        # Test preview
        result = self.env.run('migrate-hoth upgrade %s %s 0 --preview_sql' % (self.url, repos_path))
        result = self.env.run('migrate-hoth upgrade %s %s 0 --preview_py' % (self.url, repos_path))

        result = self.env.run('migrate-hoth upgrade %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_db_version(self.url, repos_path), 1)

        # Downgrade must have a valid version specified
        result = self.env.run('migrate-hoth downgrade %s %s' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 2)
        result = self.env.run('migrate-hoth downgrade %s %s -1' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 2)
        result = self.env.run('migrate-hoth downgrade %s %s 2' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.run_db_version(self.url, repos_path), 1)

        result = self.env.run('migrate-hoth downgrade %s %s 0' % (self.url, repos_path))
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        result = self.env.run('migrate-hoth downgrade %s %s 1' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        result = self.env.run('migrate-hoth drop_version_control %s %s' % (self.url, repos_path))

    def _run_test_sqlfile(self, upgrade_script, downgrade_script):
        # TODO: add test script that checks if db really changed
        repos_path = self.tmp()
        repos_name = 'repos'

        result = self.env.run('migrate-hoth create %s %s' % (repos_path, repos_name))
        result = self.env.run('migrate-hoth drop_version_control %s %s' % (self.url, repos_path), expect_error=True)
        result = self.env.run('migrate-hoth version_control %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_version(repos_path), 0)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        beforeCount = len(os.listdir(os.path.join(repos_path, 'versions')))  # hmm, this number changes sometimes based on running from svn
        result = self.env.run('migrate-hoth script_sql %s --repository=%s' % ('postgres', repos_path))
        self.assertEqual(self.run_version(repos_path), 1)
        self.assertEqual(len(os.listdir(os.path.join(repos_path, 'versions'))), beforeCount + 2)

        open('%s/versions/001_postgres_upgrade.sql' % repos_path, 'a').write(upgrade_script)
        open('%s/versions/001_postgres_downgrade.sql' % repos_path, 'a').write(downgrade_script)

        self.assertEqual(self.run_db_version(self.url, repos_path), 0)
        self.assertRaises(Exception, self.engine.text('select * from t_table').execute)

        result = self.env.run('migrate-hoth upgrade %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_db_version(self.url, repos_path), 1)
        self.engine.text('select * from t_table').execute()

        result = self.env.run('migrate-hoth downgrade %s %s 0' % (self.url, repos_path))
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)
        self.assertRaises(Exception, self.engine.text('select * from t_table').execute)

    # The tests below are written with some postgres syntax, but the stuff
    # being tested (.sql files) ought to work with any db.
    @usedb(supported='postgres')
    def test_sqlfile(self):
        upgrade_script = """
        create table t_table (
            id serial,
            primary key(id)
        );
        """
        downgrade_script = """
        drop table t_table;
        """
        self.meta.drop_all()
        self._run_test_sqlfile(upgrade_script, downgrade_script)

    @usedb(supported='postgres')
    def test_sqlfile_comment(self):
        upgrade_script = """
        -- Comments in SQL break postgres autocommit
        create table t_table (
            id serial,
            primary key(id)
        );
        """
        downgrade_script = """
        -- Comments in SQL break postgres autocommit
        drop table t_table;
        """
        self._run_test_sqlfile(upgrade_script, downgrade_script)

    @usedb()
    def test_command_test(self):
        repos_name = 'repos_name'
        repos_path = self.tmp()

        result = self.env.run('migrate-hoth create repository_name --repository=%s' % repos_path)
        result = self.env.run('migrate-hoth drop_version_control %s %s' % (self.url, repos_path), expect_error=True)
        result = self.env.run('migrate-hoth version_control %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_version(repos_path), 0)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        # Empty script should succeed
        result = self.env.run('migrate-hoth script Desc %s' % repos_path)
        result = self.env.run('migrate-hoth test %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_version(repos_path), 1)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        # Error script should fail
        script_path = self.tmp_py()
        script_text='''
        from sqlalchemy import *
        from sqlalchemy_migrate_hotoffthehamster import *

        def upgrade():
            print 'fgsfds'
            raise Exception()

        def downgrade():
            print 'sdfsgf'
            raise Exception()
        '''.replace("\n        ", "\n")
        file = open(script_path, 'w')
        file.write(script_text)
        file.close()

        result = self.env.run('migrate-hoth test %s %s bla' % (self.url, repos_path), expect_error=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.run_version(repos_path), 1)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        # Nonempty script using migrate_engine should succeed
        script_path = self.tmp_py()
        script_text = '''
        from sqlalchemy import *
        from sqlalchemy_migrate_hotoffthehamster import *

        from sqlalchemy_migrate_hotoffthehamster.changeset import schema

        meta = MetaData(migrate_engine)
        account = Table('account', meta,
            Column('id', Integer, primary_key=True),
            Column('login', Text),
            Column('passwd', Text),
        )
        def upgrade():
            # Upgrade operations go here. Don't create your own engine; use the engine
            # named 'migrate_engine' imported from sqlalchemy_migrate_hotoffthehamster.
            meta.create_all()

        def downgrade():
            # Operations to reverse the above upgrade go here.
            meta.drop_all()
        '''.replace("\n        ", "\n")
        file = open(script_path, 'w')
        file.write(script_text)
        file.close()
        result = self.env.run('migrate-hoth test %s %s' % (self.url, repos_path))
        self.assertEqual(self.run_version(repos_path), 1)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

    @usedb()
    def test_rundiffs_in_shell(self):
        # This is a variant of the test_schemadiff tests but run through the shell level.
        # These shell tests are hard to debug (since they keep forking processes)
        # so they shouldn't replace the lower-level tests.
        repos_name = 'repos_name'
        repos_path = self.tmp()
        script_path = self.tmp_py()
        model_module = 'sqlalchemy_migrate_hotoffthehamster.tests.fixture.models:meta_rundiffs'
        old_model_module = 'sqlalchemy_migrate_hotoffthehamster.tests.fixture.models:meta_old_rundiffs'

        # Create empty repository.
        self.meta = MetaData(self.engine)
        self.meta.reflect()
        self.meta.drop_all()  # in case junk tables are lying around in the test database

        result = self.env.run(
            'migrate-hoth create %s %s' % (repos_path, repos_name),
            expect_stderr=True)
        result = self.env.run(
            'migrate-hoth drop_version_control %s %s' % (self.url, repos_path),
            expect_stderr=True, expect_error=True)
        result = self.env.run(
            'migrate-hoth version_control %s %s' % (self.url, repos_path),
            expect_stderr=True)
        self.assertEqual(self.run_version(repos_path), 0)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)

        # Setup helper script.
        result = self.env.run(
            'migrate-hoth manage %s --repository=%s --url=%s --model=%s'\
            % (script_path, repos_path, self.url, model_module),
            expect_stderr=True)
        self.assertTrue(os.path.exists(script_path))

        # Model is defined but database is empty.
        result = self.env.run('migrate-hoth compare_model_to_db %s %s --model=%s' \
            % (self.url, repos_path, model_module), expect_stderr=True)
        self.assertTrue(
            "tables missing from database: tmp_account_rundiffs"
            in result.stdout)

        # Test Deprecation
        result = self.env.run('migrate-hoth compare_model_to_db %s %s --model=%s' \
            % (self.url, repos_path, model_module.replace(":", ".")),
            expect_stderr=True, expect_error=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(
            "tables missing from database: tmp_account_rundiffs"
            in result.stdout)

        # Update db to latest model.
        result = self.env.run('migrate-hoth update_db_from_model %s %s %s'\
            % (self.url, repos_path, model_module), expect_stderr=True)
        self.assertEqual(self.run_version(repos_path), 0)
        self.assertEqual(self.run_db_version(self.url, repos_path), 0)  # version did not get bumped yet because new version not yet created

        result = self.env.run('migrate-hoth compare_model_to_db %s %s %s'\
            % (self.url, repos_path, model_module), expect_stderr=True)
        self.assertTrue("No schema diffs" in result.stdout)

        result = self.env.run(
            'migrate-hoth drop_version_control %s %s' % (self.url, repos_path),
            expect_stderr=True, expect_error=True)
        result = self.env.run(
            'migrate-hoth version_control %s %s' % (self.url, repos_path),
            expect_stderr=True)

        result = self.env.run(
            'migrate-hoth create_model %s %s' % (self.url, repos_path),
            expect_stderr=True)
        temp_dict = dict()
        six.exec_(result.stdout, temp_dict)

        # TODO: breaks on SA06 and SA05 - in need of total refactor - use different approach

        # TODO: compare whole table
        self.compare_columns_equal(models.tmp_account_rundiffs.c, temp_dict['tmp_account_rundiffs'].c, ['type'])
        ##self.assertTrue("""tmp_account_rundiffs = Table('tmp_account_rundiffs', meta,
  ##Column('id', Integer(),  primary_key=True, nullable=False),
  ##Column('login', String(length=None, convert_unicode=False, assert_unicode=None)),
  ##Column('passwd', String(length=None, convert_unicode=False, assert_unicode=None))""" in result.stdout)

        ## We're happy with db changes, make first db upgrade script to go from version 0 -> 1.
        #result = self.env.run('migrate-hoth make_update_script_for_model', expect_error=True, expect_stderr=True)
        #self.assertTrue('Not enough arguments' in result.stderr)

        #result_script = self.env.run('migrate-hoth make_update_script_for_model %s %s %s %s'\
            #% (self.url, repos_path, old_model_module, model_module))
        #self.assertEqualIgnoreWhitespace(result_script.stdout,
        #'''from sqlalchemy import *
        #from sqlalchemy_migrate_hotoffthehamster import *

        #from sqlalchemy_migrate_hotoffthehamster.changeset import schema

        #meta = MetaData()
        #tmp_account_rundiffs = Table('tmp_account_rundiffs', meta,
          #Column('id', Integer(),  primary_key=True, nullable=False),
          #Column('login', Text(length=None, convert_unicode=False, assert_unicode=None, unicode_error=None, _warn_on_bytestring=False)),
          #Column('passwd', Text(length=None, convert_unicode=False, assert_unicode=None, unicode_error=None, _warn_on_bytestring=False)),
        #)

        #def upgrade(migrate_engine):
            ## Upgrade operations go here. Don't create your own engine; bind migrate_engine
            ## to your metadata
            #meta.bind = migrate_engine
            #tmp_account_rundiffs.create()

        #def downgrade(migrate_engine):
            ## Operations to reverse the above upgrade go here.
            #meta.bind = migrate_engine
            #tmp_account_rundiffs.drop()''')

        ## Save the upgrade script.
        #result = self.env.run('migrate-hoth script Desc %s' % repos_path)
        #upgrade_script_path = '%s/versions/001_Desc.py' % repos_path
        #open(upgrade_script_path, 'w').write(result_script.stdout)

        #result = self.env.run('migrate-hoth compare_model_to_db %s %s %s'\
            #% (self.url, repos_path, model_module))
        #self.assertTrue("No schema diffs" in result.stdout)

        self.meta.drop_all()  # in case junk tables are lying around in the test database
