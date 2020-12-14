from __future__ import annotations

import datetime
import json
import math
from string import Formatter
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

import numpy as np
import pandas as pd
from cjwmodule import i18n
from dateutil.relativedelta import relativedelta
from pandas.api.types import is_numeric_dtype

MaxNAxisLabels = 300
MaxSpecialCaseNTicks = 8


def _migrate_params_vneg1_to_v0(params):
    """
    v-1: an 'x_data_type' param integer.

    v0: no 'x_data_type'.
    """
    return {k: v for k, v in params.items() if k != "x_data_type"}


def _migrate_params_v0_to_v1(params):
    """
    v0: params['y_columns'] is JSON-encoded.

    v1: params['y_columns'] is List[Dict[{ name, color }, str]].
    """
    json_y_columns = params["y_columns"]
    if not json_y_columns:
        # empty str => no columns
        y_columns = []
    else:
        y_columns = json.loads(json_y_columns)
    return {**params, "y_columns": y_columns}


def migrate_params(params):
    if "x_data_type" in params:
        params = _migrate_params_vneg1_to_v0(params)
    if isinstance(params["y_columns"], str):
        params = _migrate_params_v0_to_v1(params)

    return params


def python_format_to_d3_tick_format(python_format: str) -> str:
    """
    Build a d3-scale tickFormat specification based on Python str.

    >>> python_format_to_d3_tick_format('{:,.2f}')
    ',.2f'
    >>> # d3-scale likes to mess about with precision. Its "r" format does
    >>> # what we want; if we left it blank, we'd see format(30) == '3e+1'.
    >>> python_format_to_d3_tick_format('{:,}')
    ',r'
    """
    # Formatter.parse() returns Iterable[(literal, field_name, format_spec,
    # conversion)]
    specifier = next(Formatter().parse(python_format))[2]
    if not specifier or specifier[-1] not in "bcdoxXneEfFgGn%":
        specifier += "r"
    return specifier


class GentleValueError(ValueError):
    """A ValueError that should not display in red to the user.

    The first argument must be an `i18n.I18nMessage`.

    On first load, we don't want to display an error, even though the user
    hasn't selected what to chart. So we'll display the error in the iframe:
    we'll be gentle with the user.
    """

    @property
    def i18n_message(self):
        return self.args[0]


def _nice_date_ticks(
    max_date: datetime.date,
    n_periods_in_domain: int,
    period: Union[datetime.timedelta, relativedelta],
) -> List[datetime.date]:
    n_domain_values = n_periods_in_domain + 1
    n_periods_between_ticks = math.ceil(n_domain_values / (MaxSpecialCaseNTicks - 1))
    n_ticks = math.ceil(n_periods_in_domain / n_periods_between_ticks) + 1
    tick_timedelta = n_periods_between_ticks * period
    tick0 = max_date - (n_ticks - 1) * tick_timedelta
    return [(tick0 + tick_timedelta * i) for i in range(n_ticks)]


class XSeries(NamedTuple):
    series: pd.Series
    column: Any
    """RenderColumn (has a '.name', '.type' and '.format')."""

    @property
    def name(self):
        return self.column.name

    @property
    def vega_data_type(self) -> str:
        if self.column.type == "timestamp":
            return "temporal"
        elif self.column.type == "number":
            return "quantitative"
        else:  # text
            return "ordinal"

    @property
    def d3_tick_format(self) -> str:
        if self.column.type == "number":
            return python_format_to_d3_tick_format(self.column.format)
        else:
            return None

    @property
    def json_compatible_values(self) -> pd.Series:
        """Array of str or int or float values for the X axis of the chart.

        In particular: datetime64 values will be converted to str.
        """
        if self.column.type == "timestamp":
            return self.series.map(pd.Timestamp.isoformat) + "Z"
        else:
            return self.series

    @property
    def timestamp_tick_values_and_format(
        self,
    ) -> Optional[Tuple[List[datetime.date], str]]:
        """Array of ISO8601 strings of timestamps that should be ticks.

        None if this is not a timestamp series.

        None if we do not special-case this arrangement of timestamps.

        Special cases:

            * All values are midnight UTC on the same weekday: this is
              a "week" series. Impute missing timestamps and return the regular
              monotonic series -- a series of dates of interest. If there are
              >MaxSpecialCaseNTicks, pick the lowest interval that produces
              fewer ticks. Make sure the _last_ date is always a tick, and
              impute a start tick that may come before all dates in the series.
        """
        if self.column.type != "timestamp":
            return None

        if not self.series.dt.normalize().equals(self.series):
            # Dates with times. Fallback to vega-lite (D3) defaults
            return None

        # Okay, we have whole dates.

        if self.series.dt.is_year_start.all():
            # All dates are the first of the year. Treat this as "years".
            series_min = self.series.min()
            series_max = self.series.max()
            period = relativedelta(years=1)  # Python doesn't do year math
            n_periods_in_domain = (
                series_max.to_period("Y") - series_min.to_period("Y")
            ).n
            return (
                _nice_date_ticks(series_max.date(), n_periods_in_domain, period),
                "%Y",  # "2020"
            )

        if self.series.dt.is_month_start.all():
            # All dates are the first of the month. Treat this as "months".
            series_min = self.series.min()
            series_max = self.series.max()
            period = relativedelta(months=1)  # Python doesn't do month math
            n_periods_in_domain = (
                series_max.to_period("M") - series_min.to_period("M")
            ).n
            return (
                _nice_date_ticks(series_max.date(), n_periods_in_domain, period),
                "%b %Y",  # "Jan 2020"
            )

        if self.series.dt.dayofweek.nunique() == 1:
            # All dates fall on the same weekday. Treat this as "weeks".
            min_date = self.series.min().date()
            max_date = self.series.max().date()
            period = datetime.timedelta(weeks=1)
            n_periods_in_domain = (max_date - min_date) / period
            return (
                _nice_date_ticks(max_date, n_periods_in_domain, period),
                "%b %-d, %Y",  # "Jan 3, 2020"
            )


class YSeries(NamedTuple):
    series: pd.Series
    color: str
    tick_format: str
    """Python string format specifier, like '{:,}'."""

    @property
    def name(self):
        return self.series.name

    @property
    def d3_tick_format(self):
        return python_format_to_d3_tick_format(self.tick_format)


class Chart(NamedTuple):
    """Fully-sane parameters. Columns are series."""

    title: str
    x_axis_label: str
    x_axis_tick_format: str
    y_axis_label: str
    x_series: XSeries
    y_columns: List[YSeries]
    y_axis_tick_format: str

    def to_vega_data_values(self) -> List[Dict[str, Any]]:
        """Build a dict for Vega's .data.values Array.

        Return value is a list of dict records. Each has
        {'x': 'X Name', 'line': 'Line Name', 'y': 1.0}
        """
        # We use column names 'x' and f'y{colname}' to prevent conflicts (e.g.,
        # colname='x'). After melt(), we'll drop the 'y' prefix.
        data = {"x": self.x_series.json_compatible_values}
        for y_column in self.y_columns:
            data["y" + y_column.name] = y_column.series
        dataframe = pd.DataFrame(data)
        vertical = dataframe.melt("x", var_name="line", value_name="y")
        vertical.dropna(inplace=True)
        vertical["line"] = vertical["line"].str[1:]  # drop 'y' prefix
        return vertical.to_dict(orient="records")

    def to_vega_x_encoding(self) -> Dict[str, Any]:
        ret = {
            "field": "x",
            "type": self.x_series.vega_data_type,
            "axis": {"title": self.x_axis_label},
        }

        if self.x_series.vega_data_type == "quantitative":
            if self.x_axis_tick_format is not None:
                ret["axis"]["format"] = self.x_axis_tick_format

            if self.x_axis_tick_format and self.x_axis_tick_format[-1] == "d":
                ret["axis"]["tickMinStep"] = 1
        elif self.x_series.vega_data_type == "ordinal":
            ret["axis"]["labelAngle"] = 0
            ret["axis"]["labelOverlap"] = False
            ret["sort"] = None
        elif self.x_series.vega_data_type == "temporal":
            special_case = self.x_series.timestamp_tick_values_and_format
            if special_case:
                ticks, tick_format = special_case
                ret["axis"]["values"] = [tick.isoformat() for tick in ticks]
                ret["axis"]["labelExpr"] = f'utcFormat(datum.value, "{tick_format}")'
                ret["axis"]["labelOverlap"] = "parity"  # no auto-rotating
                ret["axis"]["labelSeparation"] = 5
                ret["scale"] = {
                    "domainMin": {
                        "expr": "utc(%d, %d, %d)"
                        % (ticks[0].year, ticks[0].month - 1, ticks[0].day)
                    }
                }

        return ret

    def to_vega(self) -> Dict[str, Any]:
        """Build a Vega line chart."""
        ret = {
            "$schema": "https://vega.github.io/schema/vega-lite/v4.json",
            "title": self.title,
            "config": {
                "title": {
                    "offset": 15,
                    "color": "#383838",
                    "font": "Nunito Sans, Helvetica, sans-serif",
                    "fontSize": 20,
                    "fontWeight": "normal",
                },
                "axis": {
                    "tickSize": 3,
                    "titlePadding": 20,
                    "titleFontSize": 15,
                    "titleFontWeight": 100,
                    "titleColor": "#686768",
                    "titleFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFont": "Nunito Sans, Helvetica, sans-serif",
                    "labelFontWeight": 400,
                    "labelColor": "#383838",
                    "labelFontSize": 12,
                    "labelPadding": 10,
                    "gridOpacity": 0.5,
                },
            },
            "data": {"values": self.to_vega_data_values()},
            "mark": {
                "type": "line",
                "point": {
                    "shape": "circle",
                    "size": 36,
                },
            },
            "encoding": {
                "x": self.to_vega_x_encoding(),
                "y": {
                    "field": "y",
                    "type": "quantitative",
                    "axis": {
                        "title": self.y_axis_label,
                        "format": self.y_axis_tick_format,
                    },
                },
                "color": {
                    "field": "line",
                    "type": "nominal",
                    "scale": {
                        "domain": [y.name for y in self.y_columns],
                        "range": [y.color for y in self.y_columns],
                    },
                },
            },
        }

        if self.y_axis_tick_format[-1] == "d":
            ret["encoding"]["y"]["axis"]["tickMinStep"] = 1

        if len(self.y_columns) == 1:
            ret["encoding"]["color"]["legend"] = None
        else:
            ret["encoding"]["color"]["legend"] = {"title": None}
            ret["config"]["legend"] = {
                "symbolType": "circle",
                "titlePadding": 20,
                "padding": 15,
                "offset": 0,
                "labelFontSize": 12,
                "rowPadding": 10,
                "labelFont": "Nunito Sans, Helvetica, sans-serif",
                "labelColor": "#383838",
                "labelFontWeight": "normal",
            }

        return ret


class YColumn(NamedTuple):
    column: str
    color: str


class Form(NamedTuple):
    """Parameter dict specified by the user: valid types, unchecked values."""

    title: str
    x_axis_label: str
    y_axis_label: str
    x_column: str
    y_columns: List[YColumn]

    @classmethod
    def from_params(cls, *, y_columns: List[Dict[str, str]], **kwargs):
        return cls(**kwargs, y_columns=[YColumn(**d) for d in y_columns])

    def _make_x_series_and_mask(
        self, table: pd.DataFrame, input_columns: Dict[str, Any]
    ) -> Tuple[XSeries, np.array]:
        """Create an XSeries ready for charting, or raise GentleValueError."""
        if not self.x_column:
            raise GentleValueError(
                i18n.trans("noXAxisError.message", "Please choose an X-axis column")
            )

        series = table[self.x_column]
        column = input_columns[self.x_column]
        nulls = series.isna()
        safe_x_values = series[~nulls]  # so we can min(), len(), etc
        safe_x_values.reset_index(drop=True, inplace=True)

        if column.type == "text" and len(safe_x_values) > MaxNAxisLabels:
            raise GentleValueError(
                i18n.trans(
                    "tooManyTextValuesError.message",
                    'Column "{x_column}" has {n_safe_x_values} text values. We cannot fit them all on the X axis. '
                    'Please change the input table to have 10 or fewer rows, or convert "{x_column}" to number or date.',
                    {
                        "x_column": self.x_column,
                        "n_safe_x_values": len(safe_x_values),
                    },
                )
            )

        if not len(safe_x_values):
            raise GentleValueError(
                i18n.trans(
                    "noValuesError.message",
                    'Column "{column_name}" has no values. Please select a column with data.',
                    {"column_name": self.x_column},
                )
            )

        if not len(safe_x_values[safe_x_values != safe_x_values[0]]):
            raise GentleValueError(
                i18n.trans(
                    "onlyOneValueError.message",
                    'Column "{column_name}" has only 1 value. Please select a column with 2 or more values.',
                    {"column_name": self.x_column},
                )
            )

        return XSeries(safe_x_values, column), ~nulls

    def make_chart(self, table: pd.DataFrame, input_columns: Dict[str, Any]) -> Chart:
        """Create a Chart ready for charting, or raise GentleValueError.

        Features:
        * Error if X column is missing
        * Error if X column does not have two values
        * Error if X column is all-NaN
        * Error if too many X values in text mode (since we can't chart them)
        * X column can be number or date
        * Missing X dates lead to missing records
        * Missing X floats lead to missing records
        * Missing Y values are omitted
        * Error if no Y columns chosen
        * Error if a Y column is the X column
        * Error if a Y column has fewer than 1 non-missing value
        * Default title, X and Y axis labels
        """
        x_series, mask = self._make_x_series_and_mask(table, input_columns)

        if not self.y_columns:
            raise GentleValueError(
                i18n.trans("noYAxisError.message", "Please choose a Y-axis column")
            )

        y_columns = []
        for ycolumn in self.y_columns:
            if ycolumn.column == self.x_column:
                raise GentleValueError(
                    i18n.trans(
                        "sameAxesError.message",
                        "You cannot plot Y-axis column {column_name} because it is the X-axis column",
                        {"column_name": ycolumn.column},
                    )
                )

            series = table[ycolumn.column]

            if not is_numeric_dtype(series.dtype):
                raise GentleValueError(
                    i18n.trans(
                        "axisNotNumericError.message",
                        'Cannot plot Y-axis column "{column_name}" because it is not numeric. '
                        "Convert it to a number before plotting it.",
                        {"column_name": ycolumn.column},
                    )
                )

            series = series[mask]  # line up with x_series
            series.reset_index(drop=True, inplace=True)

            print(repr(series))

            # Find how many Y values can actually be plotted on the X axis. If
            # there aren't going to be any Y values on the chart, raise an
            # error.
            if not series.count():
                raise GentleValueError(
                    i18n.trans(
                        "emptyAxisError.message",
                        'Cannot plot Y-axis column "{column_name}" because it has no values',
                        {"column_name": ycolumn.column},
                    )
                )

            y_columns.append(
                YSeries(series, ycolumn.color, input_columns[ycolumn.column].format)
            )

        title = self.title or "Line Chart"
        x_axis_label = self.x_axis_label or x_series.name
        y_axis_label = self.y_axis_label or y_columns[0].name

        return Chart(
            title=title,
            x_axis_label=x_axis_label,
            x_axis_tick_format=x_series.d3_tick_format,
            y_axis_label=y_axis_label,
            x_series=x_series,
            y_columns=y_columns,
            y_axis_tick_format=y_columns[0].d3_tick_format,
        )


def render(table, params, *, input_columns):
    form = Form.from_params(**params)
    try:
        chart = form.make_chart(table, input_columns)
    except GentleValueError as err:
        return (
            table,
            err.i18n_message,
            {
                "error": "Please correct the error in this step's data or parameters"
            },  # TODO_i18n
        )

    json_dict = chart.to_vega()
    return (table, "", json_dict)
