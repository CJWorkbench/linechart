2020-12-14.01
-------------

* Timestamp X axis: detect and special-case "year", "month" and "week" columns.
  Ticks will line up with boundaries.
* Timestamp X axis: always format as UTC (data is always UTC).
* Circle marks: increase size.
* Tooltip: on hover, show a legend with all Y values at the given X value.
* CHANGE: null Y values now appear as "gaps" in their lines. If you are seeing
  gaps you don't want, filter out rows where y=null before creating your
  chart.)

2020-10-02.01
-------------

* (internal) rename "datetime" to "timestamp"
