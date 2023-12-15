#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import tempfile

from sqlalchemy_migrate_hotoffthehamster.tests.fixture import base


class Pathed(base.Base):
    # Temporary files

    _tmpdir = tempfile.mkdtemp()

    def setUp(self, skip_testtools_setUp=False):
        # DUNNO/2023-12-15: I forked this project 4 years ago, a few months
        # before the upstream fork was seemingly abandoned (or absorbed into
        # a larger OpenDev project?). But I didn't get tests running again
        # until now, and many of them initially failed with testtools.TestCase
        # complaining that either setUp or tearDown had already been called.
        # - This backstory only necessary to say that I'd guess this used to
        #   work, and that maybe testtools.TestCase changed its behavior.
        # - My (limited) understanding (I've tried to avoid becoming too
        #   intimiate with this project, and I'm not familiar with TestCase)
        #   is that, as a subclass of TestCase, setUp and tearDown are called
        #   automatically.
        #   - But this project also calls setUp and tearDown from the
        #     `@fixture.usedb()` decorator.
        #   - Without being more intimate with the code, I don't want to
        #     not call setUp and tearDown from the decorator. So my sol'n
        #     is this irreverent bool passed around to guard against calling
        #     TestCase.setUp/tearDown from the usedb() decorator.
        if not skip_testtools_setUp:
            # Base doesn't define setUp, so this goes to testtools.TestCase.
            super(Pathed, self).setUp()

        self.temp_usable_dir = tempfile.mkdtemp()
        sys.path.append(self.temp_usable_dir)

    def tearDown(self, skip_testtools_tearDown=False):
        # See long comment in setUp re: skip_testtools_tearDown usage.
        if not skip_testtools_tearDown:
            # Base doesn't define setUp, so this goes to testtools.TestCase.
            super(Pathed, self).tearDown()

        try:
            sys.path.remove(self.temp_usable_dir)
        except:
            pass # w00t?
        Pathed.purge(self.temp_usable_dir)

    @classmethod
    def _tmp(cls, prefix='', suffix=''):
        """Generate a temporary file name that doesn't exist
        All filenames are generated inside a temporary directory created by
        tempfile.mkdtemp(); only the creating user has access to this directory.
        It should be secure to return a nonexistant temp filename in this
        directory, unless the user is messing with their own files.
        """
        file, ret = tempfile.mkstemp(suffix,prefix,cls._tmpdir)
        os.close(file)
        os.remove(ret)
        return ret

    @classmethod
    def tmp(cls, *p, **k):
        return cls._tmp(*p, **k)

    @classmethod
    def tmp_py(cls, *p, **k):
        return cls._tmp(suffix='.py', *p, **k)

    @classmethod
    def tmp_sql(cls, *p, **k):
        return cls._tmp(suffix='.sql', *p, **k)

    @classmethod
    def tmp_named(cls, name):
        return os.path.join(cls._tmpdir, name)

    @classmethod
    def tmp_repos(cls, *p, **k):
        return cls._tmp(*p, **k)

    @classmethod
    def purge(cls, path):
        """Removes this path if it exists, in preparation for tests
        Careful - all tests should take place in /tmp.
        We don't want to accidentally wipe stuff out...
        """
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
                if path.endswith('.py'):
                    pyc = path + 'c'
                    if os.path.exists(pyc):
                        os.remove(pyc)
