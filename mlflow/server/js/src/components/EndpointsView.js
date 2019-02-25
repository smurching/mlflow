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


class EndpointsView extends Component {

  static propTypes = {
    // Array of objects (TODO immutable.js) with keys
    //   // Public URL of the endpoint
    //   optional string url = 1;
    //   // Name of the endpoint, e.g. "churn prediction". Acts as a unique identifier across all endpoints
    //   optional string name = 2;
    //   // The model currently associated with the endpoint
    //   optional Model model = 3;
    //   // Status of the endpoint (running, stopped)
    //   optional EndpointStatus status = 4;
    endpoints: PropTypes.arrayOf(PropTypes.object).isRequired
  };

  render() {
    const {
      endpoints,
    } = this.props;
    const endpointRows = endpoints.map((endpoint) => {
      return (<tr>
        <td>{endpoint.url}</td>
        <td>{endpoint.name}</td>
        <td>{endpoint.model.model_id}</td>
        <td>{endpoint.status}</td>
      </tr>)
    });

    return (
      <div className="EndpointsView runs-table-flex-container">
        <Table>
          <thead>
          <tr className="top-row">
            <th className="left-border">Name</th>
            <th className="left-border">Model ID</th>
            <th className="left-border">Status</th>
            <th className="left-border right-border">Deployment Target</th>
          </tr>
          </thead>
          <tbody>
          {endpointRows}
          </tbody>
        </Table>
      </div>
    );
  }

}

const mapStateToProps = (state, ownProps) => {
  const endpoints = [
    {url: "http://served-model", name: "Churn Prediction", model: {model_id: "defg"}, status: "RUNNING"},
    {url: "http://served-model", name: "Wine Quality Prediction", model: {model_id: "mnop"}, status: "PENDING"}
  ];
  return {
    endpoints
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

export default withRouter(connect(mapStateToProps)(EndpointsView));
