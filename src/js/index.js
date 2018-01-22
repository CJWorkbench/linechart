import React from 'react'
import ReactDOM from 'react-dom'
import SimpleChartParameter from './SimpleChart'

ReactDOM.render(
    <div>
      <SimpleChartParameter
        chartType='line'
        renderedSVGClassName='linechart-svg'
      ></SimpleChartParameter>
    </div>,
    document.getElementById('root')
);
