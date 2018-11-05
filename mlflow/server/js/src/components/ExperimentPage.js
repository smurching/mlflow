import React, { Component } from 'react';
import './ExperimentPage.css';
import PropTypes from 'prop-types';
import {
  getExperimentApi,
  getFromLocalstorageApi,
  getUUID,
  searchRunsApi,
  setInLocalstorageApi
} from '../Actions';

import {
  getFromLocalStorage,
} from "../reducers/Reducers";
import { connect } from 'react-redux';
import ExperimentView from './ExperimentView';
import RequestStateWrapper from './RequestStateWrapper';
import KeyFilter from '../utils/KeyFilter';
import { ViewType } from '../sdk/MlflowEnums';
import _ from "lodash";
import {SearchUtils} from "../utils/SearchUtils";
import LocalStorageUtils from "../utils/LocalStorageUtils";


export const LIFECYCLE_FILTER = { ACTIVE: 'Active', DELETED: 'Deleted' };

class ExperimentPage extends Component {
  constructor(props) {
    super(props);
    this.onSearch = this.onSearch.bind(this);
    this.getRequestIds = this.getRequestIds.bind(this);
    // TODO should we set prop defaults elsehwere?
  }

  static defaultProps = {
    searchInput: "",
    metricKeyFilterString: "",
    paramKeyFilterString: "",
  };

  static propTypes = {
    experimentId: PropTypes.number.isRequired,
    dispatchSearchRuns: PropTypes.func.isRequired,
    paramKeyFilterString: PropTypes.string.isRequired,
    metricKeyFilterString: PropTypes.string.isRequired,
    searchInput: PropTypes.string.isRequired,
  };

  state = {
    getExperimentRequestId: getUUID(),
    searchRunsRequestId: getUUID(),
    cachedStateRequestId: getUUID(),
    lastExperimentId: undefined,
    lifecycleFilter: LIFECYCLE_FILTER.ACTIVE,
  };

  store = LocalStorageUtils.getStoreForExperiment(this.props.experimentId);

  static getStateKey() {
    return "ExperimentPage";
  }

  setStateWrapper(newState) {
    // Caches certain fields in local storage. New fields can be persisted in local storage here.
    const { paramKeyFilterString, metricKeyFilterString, searchInput } = newState;
    this.props.dispatch(setInLocalstorageApi(
      LocalStorageUtils.getScopeForExperiment(this.props.experimentId),
      ExperimentPage.getStateKey(this.props.experimentId),
      {
        paramKeyFilterString,
        metricKeyFilterString,
        searchInput,
      }));
  }

  static loadState(experimentId) {
    // TODO state has dependency on props here...
    const store = LocalStorageUtils.getStoreForExperiment(experimentId);
    return store.getItem(ExperimentPage.getStateKey()).then((cachedState) => {
      if (cachedState) {
        // Load defaults, override with whatever's in local storage (if anything)
        const res = {
          ...ExperimentPage.defaultState,
          ...cachedState,
        };
        console.log("Returning " + JSON.stringify(res));
        return res;
      }
      return _.cloneDeep(ExperimentPage.defaultState);
    });
  }

  static getDerivedStateFromProps(props, state) {
    console.log("In gertDerivedStateFromProps, props: " + JSON.stringify(props) + ", state: " + JSON.stringify(state));
    if (props.experimentId !== state.lastExperimentId) {
      const newState = {
        getExperimentRequestId: getUUID(),
        searchRunsRequestId: getUUID(),
        cachedStateRequestId: getUUID(),
        lastExperimentId: props.experimentId,
        lifecycleFilter: LIFECYCLE_FILTER.ACTIVE,
      };
      props.dispatch(getExperimentApi(props.experimentId, newState.getExperimentRequestId));
      props.dispatch(searchRunsApi(
        [props.experimentId],
        SearchUtils.parseSearchInput(props.searchInput),
        lifecycleFilterToRunViewType(newState.lifecycleFilter),
        newState.searchRunsRequestId));
      props.dispatch(getFromLocalstorageApi(
        LocalStorageUtils.getScopeForExperiment(props.experimentId),
        ExperimentPage.getStateKey(),
        newState.cachedStateRequestId,
      ));
      return newState;
    }
    return null;
  }

  onSearch(paramKeyFilterString, metricKeyFilterString, searchInput, lifecycleFilterInput) {
    const andedExpressions = SearchUtils.parseSearchInput(searchInput);
    this.setStateWrapper({
      paramKeyFilterString,
      metricKeyFilterString,
      searchInput,
    });
    this.setState({
      lifecycleFilter: lifecycleFilterInput
    });
    const searchRunsRequestId = this.props.dispatchSearchRuns(
      this.props.experimentId, andedExpressions, lifecycleFilterInput);
    this.setState({ searchRunsRequestId });
  }

  render() {
    console.log(JSON.stringify(this.state));
    console.log("ExperimentPage.render(), paramKeyFilter: " + this.state.paramKeyFilterString);
    console.log("ExperimentPage.render(), metricKeyFilterString: " + this.state.metricKeyFilterString);

    return (
      <div className="ExperimentPage">
        <RequestStateWrapper requestIds={this.getRequestIds()}>
          <ExperimentView
            paramKeyFilter={new KeyFilter(this.props.paramKeyFilterString)}
            metricKeyFilter={new KeyFilter(this.props.metricKeyFilterString)}
            experimentId={this.props.experimentId}
            searchRunsRequestId={this.state.searchRunsRequestId}
            lifecycleFilter={this.state.lifecycleFilter}
            onSearch={this.onSearch}
            searchInput={this.props.searchInput}
          />
        </RequestStateWrapper>
      </div>
    );
  }

  getRequestIds() {
    return [this.state.getExperimentRequestId, this.state.searchRunsRequestId, this.state.cachedStateRequestId];
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    dispatch,
    dispatchSearchRuns: (experimentId, andedExpressions, lifecycleFilterInput) => {
      const requestId = getUUID();
      dispatch(searchRunsApi([experimentId], andedExpressions,
        lifecycleFilterToRunViewType(lifecycleFilterInput), requestId));
      return requestId;
    }
  };
};

const lifecycleFilterToRunViewType = (lifecycleFilter) => {
  if (lifecycleFilter === LIFECYCLE_FILTER.ACTIVE) {
    return ViewType.ACTIVE_ONLY;
  } else {
    return ViewType.DELETED_ONLY;
  }
};

const mapStateToProps = (state, ownProps) => {
  const localStorageProps = getFromLocalStorage(state, LocalStorageUtils.getScopeForExperiment(ownProps.experimentId), ExperimentPage.getStateKey());
  if (localStorageProps) {
    const res = {
      ...ownProps,
      ...localStorageProps,
    };
    console.log("@SID ExperimentPage mapStateToProps, got props: " + JSON.stringify(res));
    return res;
  }
  return ownProps;
};

export default connect(mapStateToProps, mapDispatchToProps)(ExperimentPage);
