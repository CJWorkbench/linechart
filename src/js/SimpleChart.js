// Chart JSX component wraps a ChartBuilder

import React from 'react'
//import { store, wfModuleStatusAction } from '../../workflow-reducer'
import PropTypes from 'prop-types'
import { errorText } from './errors'
import debounce from 'lodash.debounce'

var ChartViewActions = require("chartbuilder/src/js/actions/ChartViewActions");
var chartConfig = require("chartbuilder/src/js/charts/chart-type-configs");
//var saveSvgAsPng = require("save-svg-as-png");

/* Flux stores */
var RendererWrapper = require("chartbuilder/src/js/components/RendererWrapper");
var ChartServerActions = require("chartbuilder/src/js/actions/ChartServerActions");
var ChartPropertiesStore = require("chartbuilder/src/js/stores/ChartPropertiesStore");
var ChartMetadataStore = require("chartbuilder/src/js/stores/ChartMetadataStore");
var SessionStore = require("chartbuilder/src/js/stores/SessionStore");
var ErrorStore = require("chartbuilder/src/js/stores/ErrorStore");

// Do we actually need to do require for these?
var ChartExport = require("chartbuilder/src/js/components/ChartExport");

require("../css/chartbuilder_fonts_colors.css")
require("../css/chartbuilder.css");

// Overload the chartbuilder error messages so we can set our own
var cbErrorText = require("chartbuilder/src/js/util/error-names");
Object.keys(cbErrorText).map( (key) => {
  cbErrorText[key].text = errorText[key].text;
});

// adapter, eventually obsolete with CSV format /input call, or direct edit of ChartBuilder data model
function JSONtoCSV(d) {
  if (d && d.length > 0) {
    var colnames = Object.keys(d[0]).filter(key => key != 'index');
    var text = colnames.join(',') + '\n';
    for (var row of d) {
      text += colnames.map(name => row[name]).join(',') + '\n';
    }
    return text;
  } else {
    return '';
  }
}

export default class SimpleChartParameter extends React.Component {

  constructor(props) {
    super(props);
    this.state = { loading: true };
    this.loadingState = { loading: true, loaded_ever: true };
    this.onStateChange = this.onStateChange.bind(this);
    this.onErrorChange = this.onErrorChange.bind(this);
    this.loadChartProps = this.loadChartProps.bind(this);
    this.windowWillReceiveData = this.windowWillReceiveData.bind(this);
    // I kinda hate this... we store the last chart state we were given here, to suppress unnecessary API calls.
    // We can't put it in React state because we don't want to trigger a render... and this state doesn't change
    // the render, as this value is passed to us by the ChartBuilder component, so it's already rendered.
    // Only tricky bit is to remember to reset this when our props change.
    this.lastChartStateString = null;
  }

  // called when any change is made to chart. Update error status, save to hidden 'chartstate' text field
  onStateChange(errors) {
    var model = this.getStateFromStores();
    this.setState(Object.assign({}, model, {loading: errors || this.state.errors}));
  }

  // called when errors return -- they need to be handled seperately
  onErrorChange() {
    //this.setState({loading: false});
    var errors = ErrorStore.getAll();
    this.onStateChange(errors);
  }

  getStateFromStores() {
    // Don't get errors here. Errors default to 'valid' before input
    // has processed, so instead we wait until the first time we add
    // input data to the store.
  	return {
  		chartProps: ChartPropertiesStore.getAll(),
  		metadata: ChartMetadataStore.getAll(),
  		session: SessionStore.getAll()
  	};
  }

  // Load our input data from render API, restore start state from hidden param
  loadChart(data) {
    return { raw: JSONtoCSV(data.rows) };
  }

  loadChartProps(modelText) {
    var model;
    var defaults = chartConfig.xy.defaultProps;
    if (modelText !== "") {
      model = JSON.parse(modelText);
      this.lastChartStateString = modelText;
    } else {
      model = defaults;
    }
    model.chartProps.input = {raw: ''} //blank data to start so we correctly get errors
    return model;
  }

  componentWillMount(props) {
    var defaults = chartConfig.xy.defaultProps;
    var modelText = workbench.params.chartstate;
    var newModel = this.loadChartProps(modelText);
    defaults.chartProps.chartSettings[0].type = this.props.chartType || 'line';
    defaults.chartProps.scale.typeSettings.maxLength = 7;
    ChartServerActions.receiveModel(newModel);
  }

  // Load input data, settings when first rendered
  componentDidMount() {
    ChartPropertiesStore.addChangeListener(this.onStateChange);
    ChartMetadataStore.addChangeListener(this.onStateChange);
    ErrorStore.addChangeListener(this.onErrorChange);
    SessionStore.addChangeListener(this.onStateChange);
    ChartViewActions.updateInput('input', this.loadChart(workbench.input));

    window.addEventListener('message', this.windowWillReceiveData, false);
  }

  componentWillUnmount() {
		ChartPropertiesStore.removeChangeListener(this.onStateChange);
		ChartMetadataStore.removeChangeListener(this.onStateChange);
		ErrorStore.removeChangeListener(this.onErrorChange);
		SessionStore.removeChangeListener(this.onStateChange);
	}

  windowWillReceiveData(event) {
    ChartServerActions.receiveModel(event.data.model);
  }

  render() {
    if (typeof this.state.chartProps !== 'undefined' > 0 && this.state.metadata)  {
      return (
        <div>
          <ChartExport
            data={this.state.chartProps.data}
            enableJSONExport={false}
            svgWrapperClassName="render-svg-mobile"
            metadata={this.state.metadata}
            stepNumber={'19'}
            additionalComponents={null}
            model={this.state}
          />
          <RendererWrapper
            editable={false}
            showMetadata={true}
            model={this.state}
            enableResponsive={true}
            className="render-svg-mobile"
            svgClassName="rendered-svg-class-name" />
        </div>
      )
    } else {
      return <div></div>;
    }
  }
}

SimpleChartParameter.propTypes = {
    chartType:        PropTypes.string
}
