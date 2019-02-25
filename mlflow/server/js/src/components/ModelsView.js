import React, { Component } from 'react';
import PropTypes from 'prop-types';
import classNames from 'classnames';
import { connect } from 'react-redux';
import './ExperimentView.css';
import { getApis, getExperiment, getParams, getRunInfos, getRunTags } from '../reducers/Reducers';
import { withRouter } from 'react-router-dom';
import Routes from '../Routes';
import { Button, ButtonGroup, DropdownButton, MenuItem } from 'react-bootstrap';
import { Experiment, RunInfo } from '../sdk/MlflowMessages';
import { saveAs } from 'file-saver';
import { getLatestMetrics } from '../reducers/MetricReducer';
import KeyFilter from '../utils/KeyFilter';

import ExperimentRunsTableMultiColumnView from "./ExperimentRunsTableMultiColumnView";
import ExperimentRunsTableCompactView from "./ExperimentRunsTableCompactView";
import { LIFECYCLE_FILTER } from './ExperimentPage';
import ExperimentViewUtil from './ExperimentViewUtil';
import DeleteRunModal from './modals/DeleteRunModal';
import RestoreRunModal from './modals/RestoreRunModal';

import LocalStorageUtils from "../utils/LocalStorageUtils";
import { ExperimentViewPersistedState } from "../sdk/MlflowLocalStorageMessages";
import { Table } from 'react-bootstrap';

import Utils from '../utils/Utils';


class ModelsView extends Component {

  static propTypes = {
    // Array of objects (TODO immutable.js) with keys
    //   // Data about where the model is stored
    //   optional string run_id = 1;
    //   optional string path = 2;
    //   // Data stored by server
    //   // UUID of model, assigned by server. Can be used to reference model
    //   optional string model_id = 3;
    //   // Model name & version (autoincrementing int). (name, version) can be used to reference model
    //   // as well
    //   optional string name = 4;
    //   optional int64 version = 5;
    models: PropTypes.arrayOf(PropTypes.object).isRequired
  };

  render() {
    const {
      models,
    } = this.props;
    const modelRows = models.map((model) => {
      return (<tr>
        <td>{model.name}</td>
        <td>{model.run_id}</td>
        <td>{model.model_id}</td>
        <td>{model.path}</td>
        <td>{model.version}</td>
      </tr>)
    });

    return (
      <div className="ModelsView runs-table-flex-container">
        <Table>
          <thead>
          <tr className="top-row">
            <th className="left-border">Name</th>
            <th className="left-border">Run ID</th>
            <th className="left-border">Model ID</th>
            <th className="left-border">Path</th>
            <th className="left-border right-border">Version</th>
          </tr>
          </thead>
          <tbody>
          {modelRows}
          </tbody>
        </Table>
      </div>
    );
  }

}

const mapStateToProps = (state, ownProps) => {
  const models = [
    {run_id: "abc", path: "relative/artifact/path", model_id: "defg", name: "SklearnWinequalityModel", version: 0},
    {run_id: "hijkl", path: "relative/artifact/path2", model_id: "mnop", name: "SklearnWinequalityModel", version: 1}
  ];
  return {
    models
  };
};

const styles = {
  lifecycleButtonLabel: {
    width: '32px'
  },
  lifecycleButtonFilterWrapper: {
    marginLeft: '48px',
  },
  tableToggleButtonGroup: {
    marginLeft: '16px',
  },
};

export default withRouter(connect(mapStateToProps)(ModelsView));
