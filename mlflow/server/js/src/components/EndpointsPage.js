import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { getExperimentApi, getUUID, searchRunsApi } from '../Actions';
import { connect } from 'react-redux';
import RequestStateWrapper from './RequestStateWrapper';
import EndpointsView from "./EndpointsView";


class EndpointsPage extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <div className="ExperimentPage runs-table-flex-container" style={{height: "100%"}}>
        <RequestStateWrapper
          requestIds={[]}
        >
          <EndpointsView/>
        </RequestStateWrapper>
      </div>
    );
  }


}

const mapDispatchToProps = (dispatch) => {
  return {
    dispatch,
    dispatchListModels: () => {
      const requestId = getUUID();
      // dispatch(searchRunsApi([experimentId], andedExpressions,
      //   lifecycleFilterToRunViewType(lifecycleFilterInput), requestId));
      return requestId;
    }
  };
};

export default connect(undefined, mapDispatchToProps)(EndpointsPage);
