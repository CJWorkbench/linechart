import React from 'react'
import ReactDOM from 'react-dom'
import SimpleChartParameter from './SimpleChart'
import 'bootstrap/dist/css/bootstrap.css'

ReactDOM.render(
    <div>
      <SimpleChartParameter
        chartType='line'
        renderedSVGClassName='linechart-svg'
      ></SimpleChartParameter>
    </div>,
    document.getElementById('root')
);
