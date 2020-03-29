# make this package available during imports as long as we support <python2.5
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from unittest import TestCase
import sqlalchemy_migrate_hotoffthehamster
import six


class TestVersionDefined(TestCase):
    def test_version(self):
        """Test for sqlalchemy_migrate_hotoffthehamster.__version__"""
        self.assertTrue(isinstance(sqlalchemy_migrate_hotoffthehamster.__version__, six.string_types))
        self.assertTrue(len(sqlalchemy_migrate_hotoffthehamster.__version__) > 0)
