import React from 'react';
import { Dropdown, DropdownMenu, DropdownToggle } from 'reactstrap';
import { downloadPNG, downloadSVG, downloadJSON } from './exportUtils';
var ChartExport = require("chartbuilder/src/js/components/ChartExport");

export default class ExportChart extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            dropdownOpen: false
        };
        this.toggle = this.toggle.bind(this);
        this.exportSvg = this.exportSvg.bind(this);
        this.exportPng = this.exportPng.bind(this);
    }

    toggle() {
        this.setState({
            dropdownOpen: !this.state.dropdownOpen
        });
    }

    exportSvg() {
      downloadSVG(this.props.targetSvgWrapperClassname);
    }

    exportPng() {
      downloadPNG(this.props.targetSvgWrapperClassname);
    }

    render() {
        return (
            <Dropdown isOpen={this.state.dropdownOpen} toggle={this.toggle}>
              <DropdownToggle
                tag="div"
                className="export-button"
                onClick={this.toggle}
                data-toggle="dropdown"
                aria-expanded={this.state.dropdownOpen}
              >
                Export Icon
              </DropdownToggle>
              <DropdownMenu className={this.state.dropdownOpen ? 'show' : ''} right>
                  <div onClick={this.exportSvg}>SVG</div><br />
                  <div onClick={this.exportPng}>PNG</div>
              </DropdownMenu>
            </Dropdown>
        )
    }
}
