"""Set of tests for the YQLQuery class"""

from unittest import TestCase

from nose.tools import raises

from yql import YQLQuery


class YQLQueryTest(TestCase):
    def test_prints_query_when_cast_to_string(self):
        query = YQLQuery("SELECT * from foo")

        self.assertEqual(str(query), "SELECT * from foo")