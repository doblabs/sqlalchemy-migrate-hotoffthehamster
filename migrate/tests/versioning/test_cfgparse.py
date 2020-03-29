#!/usr/bin/python
# -*- coding: utf-8 -*-

from sqlalchemy_migrate_hotoffthehamster.versioning import cfgparse
from sqlalchemy_migrate_hotoffthehamster.versioning.repository import *
from sqlalchemy_migrate_hotoffthehamster.versioning.template import Template
from sqlalchemy_migrate_hotoffthehamster.tests import fixture


class TestConfigParser(fixture.Base):

    def test_to_dict(self):
        """Correctly interpret config results as dictionaries"""
        parser = cfgparse.Parser(dict(default_value=42))
        self.assertTrue(len(parser.sections()) == 0)
        parser.add_section('section')
        parser.set('section','option','value')
        self.assertEqual(parser.get('section', 'option'), 'value')
        self.assertEqual(parser.to_dict()['section']['option'], 'value')

    def test_table_config(self):
        """We should be able to specify the table to be used with a repository"""
        default_text = Repository.prepare_config(Template().get_repository(),
            'repository_name', {})
        specified_text = Repository.prepare_config(Template().get_repository(),
            'repository_name', {'version_table': '_other_table'})
        self.assertNotEqual(default_text, specified_text)
