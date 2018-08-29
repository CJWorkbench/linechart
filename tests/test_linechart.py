#!/usr/bin/env python3

import datetime
import json
import unittest
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from linechart import render, Form, YColumn, GentleValueError


class ConfigTest(unittest.TestCase):
    def assertResult(self, result, expected):
        assert_frame_equal(result[0], expected[0])
        self.assertEqual(result[1], expected[1])
        self.assertEqual(result[2], expected[2])

    def build_form(self, **kwargs):
        params = {
            'title': 'TITLE',
            'x_axis_label': 'X LABEL',
            'y_axis_label': 'Y LABEL',
            'x_column': 'A',
            'x_type': np.number,
            'y_columns': [YColumn('B', '#123456')],
        }
        params.update(kwargs)
        return Form(**params)

    def test_missing_x_param(self):
        form = self.build_form(x_column='')
        table = pd.DataFrame({'A': [1, 2], 'B': [2, 3]})
        with self.assertRaisesRegex(
            GentleValueError,
            'Please choose an X-axis column'
        ):
            form.make_chart(table)

    def test_only_one_x_value(self):
        form = self.build_form(x_column='A')
        table = pd.DataFrame({'A': [1, 1], 'B': [2, 3]})
        with self.assertRaisesRegex(
            ValueError,
            'Column "A" has only 1 value. '
            'Please select a column with 2 or more values.'
        ):
            form.make_chart(table)

    def test_no_x_values(self):
        form = self.build_form(x_column='A')
        table = pd.DataFrame({'A': [np.nan, np.nan], 'B': [2, 3]},
                             dtype=np.number)
        with self.assertRaisesRegex(
            ValueError,
            'Column "A" has no values. '
            'Please select a column with data.'
        ):
            form.make_chart(table)

    def test_x_numeric(self):
        form = self.build_form(x_column='A', x_type=np.number)
        table = pd.DataFrame({'A': [1, 2], 'B': [3, 4]},
                             dtype=np.number)
        chart = form.make_chart(table)
        assert np.array_equal(chart.x_series.series, [1, 2])

        vega = chart.to_vega()
        self.assertEqual(vega['encoding']['x']['type'], 'quantitative')
        self.assertEqual(vega['data']['values'], [
            {'x': 1, 'line': 'B', 'y': 3},
            {'x': 2, 'line': 'B', 'y': 4},
        ])

    def test_x_numeric_drop_na_x(self):
        form = self.build_form(x_column='A', x_type=np.number)
        table = pd.DataFrame({'A': [1, np.nan, 3], 'B': [3, 4, 5]},
                             dtype=np.number)
        chart = form.make_chart(table)
        vega = chart.to_vega()
        self.assertEqual(vega['encoding']['x']['type'], 'quantitative')
        self.assertEqual(vega['data']['values'], [
            {'x': 1, 'line': 'B', 'y': 3},
            {'x': 3, 'line': 'B', 'y': 5},
        ])

    def test_x_datetime(self):
        form = self.build_form(x_column='A', x_type=np.datetime64)
        t1 = datetime.datetime(2018, 8, 29, 13, 39)
        t2 = datetime.datetime(2018, 8, 29, 13, 40)
        table = pd.DataFrame({'A': [t1, t2], 'B': [3, 4]},
                             dtype=np.number)
        chart = form.make_chart(table)
        assert np.array_equal(
            chart.x_series.series,
            np.array([t1, t2], dtype='datetime64[ns]')
        )

        vega = chart.to_vega()
        self.assertEqual(vega['encoding']['x']['type'], 'temporal')
        self.assertEqual(vega['data']['values'], [
            {'x': '2018-08-29T13:39:00Z', 'line': 'B', 'y': 3},
            {'x': '2018-08-29T13:40:00Z', 'line': 'B', 'y': 4},
        ])

    def test_x_datetime_drop_na_x(self):
        form = self.build_form(x_column='A', x_type=np.datetime64)
        t1 = datetime.datetime(2018, 8, 29, 13, 39)
        t2 = datetime.datetime(2018, 8, 29, 13, 40)
        nat = np.datetime64('NaT')
        table = pd.DataFrame({'A': [t1, nat, t2], 'B': [3, 4, 5]},
                             dtype=np.number)
        chart = form.make_chart(table)
        vega = chart.to_vega()
        self.assertEqual(vega['encoding']['x']['type'], 'temporal')
        self.assertEqual(vega['data']['values'], [
            {'x': '2018-08-29T13:39:00Z', 'line': 'B', 'y': 3},
            {'x': '2018-08-29T13:40:00Z', 'line': 'B', 'y': 5},
        ])

    def test_integration_empty_params(self):
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
