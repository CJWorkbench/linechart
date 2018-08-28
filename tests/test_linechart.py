#!/usr/bin/env python3

import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from linechart import render


class ConfigTest(unittest.TestCase):
    def assertResult(self, result, expected):
        assert_frame_equal(result[0], expected[0])
        self.assertEqual(result[1], expected[1])
        self.assertEqual(result[2], expected[2])

    def test_empty_params(self):
        table = pd.DataFrame({'A': [1, 2], 'B': [2, 3]})
        result = render(table, {})
        self.assertResult(result, (
            table,
            '',
            {'error': 'Please choose an X-axis column'}
        ))
