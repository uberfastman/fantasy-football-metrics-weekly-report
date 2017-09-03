"""Set of tests for the placeholder checking"""

from unittest import TestCase

from nose.tools import raises

from yql import YQLQuery


class YQLQueryTest(TestCase):
    @raises(ValueError)
    def test_empty_args_raises_valueerror(self):
        query = YQLQuery("SELECT * from foo where dog=@dog")
        params = {}
        query.validate(params)

    @raises(ValueError)
    def test_incorrect_args_raises_valueerror(self):
        query = YQLQuery("SELECT * from foo where dog=@dog")
        params = {'test': 'fail'}
        query.validate(params)

    @raises(ValueError)
    def test_params_raises_when_not_dict(self):
        query = YQLQuery("SELECT * from foo where dog=@dog")
        params = ['test']
        query.validate(params)

    @raises(ValueError)
    def test_unecessary_args_raises_valueerror(self):
        query = YQLQuery("SELECT * from foo where dog='test'")
        params = {'test': 'fail'}
        query.validate(params)

    @raises(ValueError)
    def test_incorrect_type_raises_valueerror(self):
        query = YQLQuery("SELECT * from foo where dog=@test")
        params = ('fail')
        query.validate(params)

    @raises(ValueError)
    def test_requires_substitutions(self):
        query = YQLQuery("SELECT * from foo where dog=@dog")
        query.validate()

    def test_placeholder_regex_one(self):
        query = YQLQuery("SELECT * from foo where email='foo@foo.com'")
        placeholders = query.get_placeholder_keys()
        self.assertEqual(placeholders, [])

    def test_placeholder_regex_two(self):
        query = YQLQuery("SELECT * from foo where email=@foo'")
        placeholders = query.get_placeholder_keys()
        self.assertEqual(placeholders, ['foo'])

    def test_placeholder_regex_three(self):
        query = YQLQuery("SELECT * from foo where email=@foo and test=@bar'")
        placeholders = query.get_placeholder_keys()
        self.assertEqual(placeholders, ['foo', 'bar'])

    def test_placeholder_regex_four(self):
        query = YQLQuery("SELECT * from foo where foo='bar' LIMIT @foo")
        placeholders = query.get_placeholder_keys()
        self.assertEqual(placeholders, ['foo'])

    def test_placeholder_regex_five(self):
        query = YQLQuery("""SELECT * from foo
                    where foo='bar' LIMIT
                    @foo""")
        placeholders = query.get_placeholder_keys()
        self.assertEqual(placeholders, ['foo'])
