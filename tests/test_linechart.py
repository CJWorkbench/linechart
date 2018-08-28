#!/usr/bin/env python3

import json
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

    def test_integration(self):
        table = pd.DataFrame({'A': [1, 2], 'B': [2, 3]})
        result = render(table, {
            'title': 'TITLE',
            'x_column': 'A',
            'x_data_type': '0',
            'y_columns': '[{"column":"B","color":"#123456"}]',
            'x_axis_label': 'X LABEL',
            'y_axis_label': 'Y LABEL'
        })
        assert_frame_equal(result[0], table)
        self.assertEqual(result[1], '')
        text = json.dumps(result[2])
        # We won't snapshot the chart: that's too brittle. (We change styling
        # more often than we change logic.) But let's make sure all our
        # parameters are in the JSON.
        self.assertIn('"TITLE"', text)
        self.assertIn('"X LABEL"', text)
        self.assertIn('"Y LABEL"', text)
        self.assertIn('"#123456"', text)
        self.assertRegex(text, '.*:\s*3[,}]')
