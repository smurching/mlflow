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
import { SearchUtils } from '../utils/SearchUtils';
import { saveAs } from 'file-saver';
import { getLatestMetrics } from '../reducers/MetricReducer';
import KeyFilter from '../utils/KeyFilter';
import LocalStorageUtils from '../utils/LocalStorageUtils';

import ExperimentRunsTableMultiColumnView from "./ExperimentRunsTableMultiColumnView";
import ExperimentRunsTableCompactView from "./ExperimentRunsTableCompactView";
import { LIFECYCLE_FILTER } from './ExperimentPage';
import ExperimentViewUtil from './ExperimentViewUtil';
import DeleteRunModal from './modals/DeleteRunModal';
import RestoreRunModal from './modals/RestoreRunModal';

import _ from 'lodash';

export const DEFAULT_EXPANDED_VALUE = true;


class ExperimentView extends Component {
  constructor(props) {
    super(props);
    this.onCheckbox = this.onCheckbox.bind(this);
    this.onCompare = this.onCompare.bind(this);
    this.onDownloadCsv = this.onDownloadCsv.bind(this);
    this.onParamKeyFilterInput = this.onParamKeyFilterInput.bind(this);
    this.onMetricKeyFilterInput = this.onMetricKeyFilterInput.bind(this);
    this.onSearchInput = this.onSearchInput.bind(this);
    this.onSearch = this.onSearch.bind(this);
    this.onClear = this.onClear.bind(this);
    this.onSortBy = this.onSortBy.bind(this);
    this.isAllChecked = this.isAllChecked.bind(this);
    this.onCheckbox = this.onCheckbox.bind(this);
    this.onCheckAll = this.onCheckAll.bind(this);
    this.setSortBy = this.setSortBy.bind(this);
    this.onDeleteRun = this.onDeleteRun.bind(this);
    this.onRestoreRun = this.onRestoreRun.bind(this);
    this.onLifecycleFilterInput = this.onLifecycleFilterInput.bind(this);
    this.onCloseDeleteRunModal = this.onCloseDeleteRunModal.bind(this);
    this.onCloseRestoreRunModal = this.onCloseRestoreRunModal.bind(this);
    this.onExpand = this.onExpand.bind(this);
    this.addBagged = this.addBagged.bind(this);
    this.removeBagged = this.removeBagged.bind(this);
  }

  static propTypes = {
    onSearch: PropTypes.func.isRequired,
    runInfos: PropTypes.arrayOf(RunInfo).isRequired,
    experiment: PropTypes.instanceOf(Experiment).isRequired,
    history: PropTypes.any,

    // List of all parameter keys available in the runs we're viewing
    paramKeyList: PropTypes.arrayOf(String).isRequired,
    // List of all metric keys available in the runs we're viewing
    metricKeyList: PropTypes.arrayOf(String).isRequired,

    // List of list of params in all the visible runs
    paramsList: PropTypes.arrayOf(Array).isRequired,
    // List of list of metrics in all the visible runs
    metricsList: PropTypes.arrayOf(Array).isRequired,
    // List of tags dictionary in all the visible runs.
    tagsList: PropTypes.arrayOf(Object).isRequired,

    // Input to the paramKeyFilter field
    paramKeyFilter: PropTypes.instanceOf(KeyFilter).isRequired,
    // Input to the paramKeyFilter field
    metricKeyFilter: PropTypes.instanceOf(KeyFilter).isRequired,

    // Input to the lifecycleFilter field
    lifecycleFilter: PropTypes.string.isRequired,

    // The initial searchInput
    searchInput: PropTypes.string.isRequired,
  };

  store = LocalStorageUtils.getStoreForExperiment(
    this.props.experiment.experiment_id, this.props.experiment.creation_time);

  defaultState = {
    runsHiddenByExpander: {},
    // By default all runs are expanded. In this state, runs are explicitly expanded or unexpanded.
    runsExpanded: {},
    runsSelected: {},
    paramKeyFilterInput: '',
    metricKeyFilterInput: '',
    lifecycleFilterInput: LIFECYCLE_FILTER.ACTIVE,
    searchInput: '',
    searchErrorMessage: undefined,
    sort: {
      ascending: false,
      isMetric: false,
      isParam: false,
      key: "start_time"
    },
    showMultiColumns: true,
    showDeleteRunModal: false,
    showRestoreRunModal: false,
    // Arrays of "unbagged", or split-out metrics and parameters. We maintain these as lists to help
    // keep them ordered (i.e. splitting out a column shouldn't change the ordering of columns
    // that have already been split out)
    unbaggedMetrics: [],
    unbaggedParams: [],
  };

  state = this.loadState();

  getStateKey() {
    return "ExperimentView";
  }

  setStateWrapper(newState, callback) {
    this.setState(newState, () => {
      this.store.setItem(this.getStateKey(), this.state).then(() => {
        if (callback) {
          callback();
        }
      });
    });
  }

  loadState() {
    const cachedState = this.store.getItem(this.getStateKey());
    const runsSelected = this.defaultState.runsSelected;
    console.log("Loading cached state " + JSON.stringify(cachedState));
    if (cachedState) {
      return  {
        // Include default state as a safeguard against missing data in localstorage (e.g. if
        // fields change)
        ..._.cloneDeep(this.defaultState),
        ...cachedState,
        runsSelected, // Don't save selected runs across page reloads
      };
    }
    return _.cloneDeep(this.defaultState);
  }

  shouldComponentUpdate(nextProps, nextState) {
    // Don't update the component if a modal is showing before and after the update try.
    if (this.state.showDeleteRunModal && nextState.showDeleteRunModal) return false;
    if (this.state.showRestoreRunModal && nextState.showRestoreRunModal) return false;
    return true;
  }


  static getDerivedStateFromProps(nextProps, prevState) {
    // Compute the actual runs selected. (A run cannot be selected if it is not passed in as a
    // prop)
    const newRunsSelected = {};
    nextProps.runInfos.forEach((rInfo) => {
      const prevRunSelected = prevState.runsSelected[rInfo.run_uuid];
      if (prevRunSelected) {
        newRunsSelected[rInfo.run_uuid] = prevRunSelected;
      }
    });
    const { searchInput, paramKeyFilter, metricKeyFilter, lifecycleFilter } = nextProps;
    const paramKeyFilterInput = paramKeyFilter.getFilterString();
    const metricKeyFilterInput = metricKeyFilter.getFilterString();
    return {
      ...prevState,
      searchInput,
      paramKeyFilterInput,
      metricKeyFilterInput,
      lifecycleFilterInput: lifecycleFilter,
      runsSelected: newRunsSelected,
    };
  }

  setShowMultiColumns(value) {
    this.setStateWrapper({ showMultiColumns: value });
  }

  onDeleteRun() {
    this.setStateWrapper({ showDeleteRunModal: true });
  }

  onRestoreRun() {
    this.setStateWrapper({ showRestoreRunModal: true });
  }

  onCloseDeleteRunModal() {
    this.setStateWrapper({ showDeleteRunModal: false });
  }

  onCloseRestoreRunModal() {
    this.setStateWrapper({ showRestoreRunModal: false });
  }

  // Mark a column as "bagged" by removing it from the unbagged array
  addBagged(isParam, colName) {
    const unbagged = isParam ? this.state.unbaggedParams : this.state.unbaggedMetrics;
    const idx = unbagged.indexOf(colName);
    const newUnbagged = idx >= 0 ?
      unbagged.slice(0, idx).concat(unbagged.slice(idx + 1, unbagged.length)) : unbagged;
    const stateKey = isParam ? "unbaggedParams" : "unbaggedMetrics";
    this.setStateWrapper({[stateKey]: newUnbagged});
  }

  // Split out a column (add it to array of unbagged cols)
  removeBagged(isParam, colName) {
    const unbagged = isParam ? this.state.unbaggedParams : this.state.unbaggedMetrics;
    const stateKey = isParam ? "unbaggedParams" : "unbaggedMetrics";
    this.setStateWrapper({[stateKey]: unbagged.concat([colName])});
  }

  /**
   * Mark a column as bagged by removing it from the appropriate array of unbagged columns.
   * @param isParam If true, the column is assumed to be a metric column; if false, the column is
   *                assumed to be a param column.
   * @param colName Name of the column (metric or param key).
   */
  addBagged(isParam, colName) {
    const unbagged = isParam ? this.state.unbaggedParams : this.state.unbaggedMetrics;
    const idx = unbagged.indexOf(colName);
    const newUnbagged = idx >= 0 ?
      unbagged.slice(0, idx).concat(unbagged.slice(idx + 1, unbagged.length)) : unbagged;
    const stateKey = isParam ? "unbaggedParams" : "unbaggedMetrics";
    this.setState({[stateKey]: newUnbagged});
  }

  /**
   * Mark a column as unbagged by adding it to the appropriate array of unbagged columns.
   * @param isParam If true, the column is assumed to be a metric column; if false, the column is
   *                assumed to be a param column.
   * @param colName Name of the column (metric or param key).
   */
  removeBagged(isParam, colName) {
    const unbagged = isParam ? this.state.unbaggedParams : this.state.unbaggedMetrics;
    const stateKey = isParam ? "unbaggedParams" : "unbaggedMetrics";
    this.setState({[stateKey]: unbagged.concat([colName])});
  }

  render() {
    const { experiment_id, name, artifact_location } = this.props.experiment;
    const {
      runInfos,
      paramKeyFilter,
      metricKeyFilter,
    } = this.props;

    // Apply our parameter and metric key filters to just pass the filtered, sorted lists
    // of parameter and metric names around later
    const paramKeyList = paramKeyFilter.apply(this.props.paramKeyList);
    const metricKeyList = metricKeyFilter.apply(this.props.metricKeyList);
    const compareDisabled = Object.keys(this.state.runsSelected).length < 2;
    const deleteDisabled = Object.keys(this.state.runsSelected).length < 1;
    const restoreDisabled = Object.keys(this.state.runsSelected).length < 1;
    return (
      <div className="ExperimentView">
        <DeleteRunModal
          isOpen={this.state.showDeleteRunModal}
          onClose={this.onCloseDeleteRunModal}
          selectedRunIds={Object.keys(this.state.runsSelected)}
        />
        <RestoreRunModal
          isOpen={this.state.showRestoreRunModal}
          onClose={this.onCloseRestoreRunModal}
          selectedRunIds={Object.keys(this.state.runsSelected)}
        />
        <h1>{name}</h1>
        <div className="metadata">
          <span className="metadata">
            <span className="metadata-header">Experiment ID:</span>
            {experiment_id}
          </span>
          <span className="metadata">
            <span className="metadata-header">Artifact Location:</span>
            {artifact_location}
          </span>
        </div>
        <div className="ExperimentView-runs">
          {this.state.searchErrorMessage !== undefined ?
            <div className="error-message">
              <span className="error-message">{this.state.searchErrorMessage}</span>
            </div> :
            null
          }
          <form className="ExperimentView-search-controls" onSubmit={this.onSearch}>
            <div className="ExperimentView-search-buttons">
              <input type="submit"
                     className="search-button btn btn-primary"
                     onClick={this.onSearch}
                     value="Search"
              />
              <Button className="clear-button" onClick={this.onClear}>Clear</Button>
            </div>
            <div className="ExperimentView-search-inputs">
              <div className="ExperimentView-search">
                <div className="ExperimentView-search-input">
                  <label className="filter-label">Search Runs:</label>
                  <div className="filter-wrapper">
                    <input type="text"
                           placeholder={'metrics.rmse < 1 and params.model = "tree"'}
                           value={this.state.searchInput}
                           onChange={this.onSearchInput}
                    />
                  </div>
                </div>
                <div className="ExperimentView-lifecycle-input">
                  <label className="filter-label" style={styles.lifecycleButtonLabel}>State:</label>
                  <div className="filter-wrapper" style={styles.lifecycleButtonFilterWrapper}>
                    <DropdownButton
                      id={"ExperimentView-lifecycle-button-id"}
                      className="ExperimentView-lifecycle-button"
                      key={this.state.lifecycleFilterInput}
                      bsStyle='default'
                      title={this.state.lifecycleFilterInput}
                    >
                      <MenuItem
                        active={this.state.lifecycleFilterInput === LIFECYCLE_FILTER.ACTIVE}
                        onSelect={this.onLifecycleFilterInput}
                        eventKey={LIFECYCLE_FILTER.ACTIVE}
                      >
                        {LIFECYCLE_FILTER.ACTIVE}
                      </MenuItem>
                      <MenuItem
                        active={this.state.lifecycleFilterInput === LIFECYCLE_FILTER.DELETED}
                        onSelect={this.onLifecycleFilterInput}
                        eventKey={LIFECYCLE_FILTER.DELETED}
                      >
                        {LIFECYCLE_FILTER.DELETED}
                      </MenuItem>
                    </DropdownButton>
                  </div>
                </div>
              </div>
              <div className="ExperimentView-keyFilters">
                <div className="ExperimentView-paramKeyFilter">
                  <label className="filter-label">Filter Params:</label>
                  <div className="filter-wrapper">
                    <input type="text"
                           placeholder="alpha, lr"
                           value={this.state.paramKeyFilterInput}
                           onChange={this.onParamKeyFilterInput}
                    />
                  </div>
                </div>
                <div className="ExperimentView-metricKeyFilter">
                  <label className="filter-label">Filter Metrics:</label>
                  <div className="filter-wrapper">
                    <input type="text"
                           placeholder="rmse, r2"
                           value={this.state.metricKeyFilterInput}
                           onChange={this.onMetricKeyFilterInput}
                    />
                  </div>
                </div>
              </div>
            </div>
          </form>
          <div className="ExperimentView-run-buttons">
            <span className="run-count">
              {runInfos.length} matching {runInfos.length === 1 ? 'run' : 'runs'}
            </span>
            <Button className="btn-primary" disabled={compareDisabled} onClick={this.onCompare}>
              Compare
            </Button>
            {
              this.props.lifecycleFilter === LIFECYCLE_FILTER.ACTIVE ?
              <Button disabled={deleteDisabled} onClick={this.onDeleteRun}>
                Delete
              </Button> : null
            }
            {
              this.props.lifecycleFilter === LIFECYCLE_FILTER.DELETED ?
              <Button disabled={restoreDisabled} onClick={this.onRestoreRun}>
                Restore
              </Button> : null
            }
            <Button onClick={this.onDownloadCsv}>
              Download CSV <i className="fas fa-download"/>
            </Button>
            <span style={{cursor: "pointer"}}>
                <ButtonGroup style={styles.tableToggleButtonGroup}>
                <Button
                  onClick={() => this.setShowMultiColumns(true)}
                  title="Grid view"
                  className={classNames({ "active": this.state.showMultiColumns })}
                >
                  <i className={"fas fa-table"}/>
                </Button>
                <Button
                  onClick={() => this.setShowMultiColumns(false)}
                  title="Compact view"
                  className={classNames({ "active": !this.state.showMultiColumns })}
                >
                  <i className={"fas fa-list"}/>
                </Button>
                </ButtonGroup>
            </span>
          </div>
          {this.state.showMultiColumns ?
            <ExperimentRunsTableMultiColumnView
              onCheckbox={this.onCheckbox}
              runInfos={this.props.runInfos}
              paramsList={this.props.paramsList}
              metricsList={this.props.metricsList}
              tagsList={this.props.tagsList}
              paramKeyList={paramKeyList}
              metricKeyList={metricKeyList}
              onCheckAll={this.onCheckAll}
              isAllChecked={this.isAllChecked()}
              onSortBy={this.onSortBy}
              sortState={this.state.sort}
              runsSelected={this.state.runsSelected}
              runsExpanded={this.state.runsExpanded}
              onExpand={this.onExpand}
            /> :
            <ExperimentRunsTableCompactView
              onCheckbox={this.onCheckbox}
              runInfos={this.props.runInfos}
              // Bagged param and metric keys
              paramKeyList={paramKeyList}
              metricKeyList={metricKeyList}
              paramsList={this.props.paramsList}
              metricsList={this.props.metricsList}
              tagsList={this.props.tagsList}
              onCheckAll={this.onCheckAll}
              isAllChecked={this.isAllChecked()}
              onSortBy={this.onSortBy}
              sortState={this.state.sort}
              runsSelected={this.state.runsSelected}
              setSortByHandler={this.setSortBy}
              runsExpanded={this.state.runsExpanded}
              onExpand={this.onExpand}
              unbaggedMetrics={this.state.unbaggedMetrics}
              unbaggedParams={this.state.unbaggedParams}
              onAddBagged={this.addBagged}
              onRemoveBagged={this.removeBagged}
            />
          }
        </div>
      </div>
    );
  }

  onSortBy(isMetric, isParam, key) {
    const sort = this.state.sort;
    this.setSortBy(isMetric, isParam, key, !sort.ascending);
  }

  setSortBy(isMetric, isParam, key, ascending) {
    this.setStateWrapper({sort: {
      ascending: ascending,
      key: key,
      isMetric: isMetric,
      isParam: isParam
    }});
  }

  onCheckbox(runUuid) {
    const newState = Object.assign({}, this.state);
    if (this.state.runsSelected[runUuid]) {
      delete newState.runsSelected[runUuid];
      this.setStateWrapper(newState);
    } else {
      this.setStateWrapper({
        runsSelected: {
          ...this.state.runsSelected,
          [runUuid]: true,
        }
      });
    }
  }

  isAllChecked() {
    return Object.keys(this.state.runsSelected).length === this.props.runInfos.length;
  }

  onCheckAll() {
    if (this.isAllChecked()) {
      this.setStateWrapper({runsSelected: {}});
    } else {
      const runsSelected = {};
      this.props.runInfos.forEach(({run_uuid}) => {
        runsSelected[run_uuid] = true;
      });
      this.setStateWrapper({runsSelected: runsSelected});
    }
  }

  onExpand(runId, childrenIds) {
    const newExpanderState = !ExperimentViewUtil.isExpanderOpen(this.state.runsExpanded, runId);
    const newRunsHiddenByExpander = {...this.state.runsHiddenByExpander};
    childrenIds.forEach((childId) => {
      newRunsHiddenByExpander[childId] = !newExpanderState;
    });
    this.setStateWrapper({
      runsExpanded: {
        ...this.state.runsExpanded,
        [runId]: newExpanderState,
      },
      runsHiddenByExpander: newRunsHiddenByExpander,
    });
    // Deselect the children
    const newRunsSelected = {...this.state.runsSelected};
    if (newExpanderState === false) {
      childrenIds.forEach((childId) => {
        if (newRunsSelected[childId]) {
          delete newRunsSelected[childId];
        }
      });
      this.setStateWrapper({ runsSelected: newRunsSelected });
    }
  }

  onParamKeyFilterInput(event) {
    this.setState({ paramKeyFilterInput: event.target.value });
  }

  onMetricKeyFilterInput(event) {
    this.setState({ metricKeyFilterInput: event.target.value });
  }

  onSearchInput(event) {
    this.setState({ searchInput: event.target.value });
  }

  onLifecycleFilterInput(newLifecycleInput) {
    this.setStateWrapper({ lifecycleFilterInput: newLifecycleInput }, this.onSearch);
  }

  onSearch(e) {
    if (e !== undefined) {
      e.preventDefault();
    }
    const {
      paramKeyFilterInput,
      metricKeyFilterInput,
      searchInput,
      lifecycleFilterInput
    } = this.state;
    try {
      this.props.onSearch(paramKeyFilterInput, metricKeyFilterInput, searchInput, lifecycleFilterInput);
    } catch (ex) {
      this.setStateWrapper({ searchErrorMessage: ex.errorMessage });
    }
  }

  onClear() {
    // When user clicks "Clear", preserve multicolumn toggle state.
    const clearState = {
      ..._.cloneDeep(this.defaultState),
      showMultiColumns: this.state.showMultiColumns,
    };
    this.setStateWrapper(clearState, () => {
      this.props.onSearch("", "", "", LIFECYCLE_FILTER.ACTIVE);
    });
  }

  onCompare() {
    const runsSelectedList = Object.keys(this.state.runsSelected);
    this.props.history.push(Routes.getCompareRunPageRoute(
      runsSelectedList, this.props.experiment.getExperimentId()));
  }

  onDownloadCsv() {
    const csv = ExperimentView.runInfosToCsv(
      this.props.runInfos,
      this.props.paramKeyFilter.apply(this.props.paramKeyList),
      this.props.metricKeyFilter.apply(this.props.metricKeyList),
      this.props.paramsList,
      this.props.metricsList);
    const blob = new Blob([csv], { type: 'application/csv;charset=utf-8' });
    saveAs(blob, "runs.csv");
  }

  /**
   * Format a string for insertion into a CSV file.
   */
  static csvEscape(str) {
    if (str === undefined) {
      return "";
    }
    if (/[,"\r\n]/.test(str)) {
      return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
  }

  /**
   * Convert a table to a CSV string.
   *
   * @param columns Names of columns
   * @param data Array of rows, each of which are an array of field values
   */
  static tableToCsv(columns, data) {
    let csv = '';
    let i;

    for (i = 0; i < columns.length; i++) {
      csv += ExperimentView.csvEscape(columns[i]);
      if (i < columns.length - 1) {
        csv += ',';
      }
    }
    csv += '\n';

    for (i = 0; i < data.length; i++) {
      for (let j = 0; j < data[i].length; j++) {
        csv += ExperimentView.csvEscape(data[i][j]);
        if (j < data[i].length - 1) {
          csv += ',';
        }
      }
      csv += '\n';
    }

    return csv;
  }

  /**
   * Convert an array of run infos to a CSV string, extracting the params and metrics in the
   * provided lists.
   */
  static runInfosToCsv(
    runInfos,
    paramKeyList,
    metricKeyList,
    paramsList,
    metricsList) {
    const columns = [
      "Run ID",
      "Name",
      "Source Type",
      "Source Name",
      "User",
      "Status",
    ];
    paramKeyList.forEach(paramKey => {
      columns.push(paramKey);
    });
    metricKeyList.forEach(metricKey => {
      columns.push(metricKey);
    });

    const data = runInfos.map((runInfo, index) => {
      const row = [
        runInfo.run_uuid,
        runInfo.name,
        runInfo.source_type,
        runInfo.source_name,
        runInfo.user_id,
        runInfo.status,
      ];
      const paramsMap = ExperimentViewUtil.toParamsMap(paramsList[index]);
      const metricsMap = ExperimentViewUtil.toMetricsMap(metricsList[index]);
      paramKeyList.forEach((paramKey) => {
        if (paramsMap[paramKey]) {
          row.push(paramsMap[paramKey].getValue());
        } else {
          row.push("");
        }
      });
      metricKeyList.forEach((metricKey) => {
        if (metricsMap[metricKey]) {
          row.push(metricsMap[metricKey].getValue());
        } else {
          row.push("");
        }
      });
      return row;
    });

    return ExperimentView.tableToCsv(columns, data);
  }
}

const mapStateToProps = (state, ownProps) => {
  const { lifecycleFilter, searchRunsRequestId } = ownProps;
  const searchRunApi = getApis([searchRunsRequestId], state)[0];
  // The runUuids we should serve.
  let runUuids;
  if (searchRunApi.data.runs) {
    runUuids = new Set(searchRunApi.data.runs.map((r) => r.info.run_uuid));
  } else {
    runUuids = new Set();
  }
  const runInfos = getRunInfos(state).filter((rInfo) =>
    runUuids.has(rInfo.getRunUuid())
  ).filter((rInfo) => {
    if (lifecycleFilter === LIFECYCLE_FILTER.ACTIVE) {
      return rInfo.lifecycle_stage === 'active';
    } else {
      return rInfo.lifecycle_stage === 'deleted';
    }
  });
  const experiment = getExperiment(ownProps.experimentId, state);
  const metricKeysSet = new Set();
  const paramKeysSet = new Set();
  const metricsList = runInfos.map((runInfo) => {
    const metrics = Object.values(getLatestMetrics(runInfo.getRunUuid(), state));
    metrics.forEach((metric) => {
      metricKeysSet.add(metric.key);
    });
    return metrics;
  });
  const paramsList = runInfos.map((runInfo) => {
    const params = Object.values(getParams(runInfo.getRunUuid(), state));
    params.forEach((param) => {
      paramKeysSet.add(param.key);
    });
    return params;
  });

  const tagsList = runInfos.map((runInfo) => getRunTags(runInfo.getRunUuid(), state));
  return {
    runInfos,
    experiment,
    metricKeyList: Array.from(metricKeysSet.values()).sort(),
    paramKeyList: Array.from(paramKeysSet.values()).sort(),
    metricsList,
    paramsList,
    tagsList,
  };
};

const styles = {
  lifecycleButtonLabel: {
    width: '60px'
  },
  lifecycleButtonFilterWrapper: {
    marginLeft: '60px',
  },
  tableToggleButtonGroup: {
    marginLeft: '16px',
  },
};

export default withRouter(connect(mapStateToProps)(ExperimentView));
