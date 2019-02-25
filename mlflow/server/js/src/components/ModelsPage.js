import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { getExperimentApi, getUUID, searchRunsApi } from '../Actions';
import { connect } from 'react-redux';
import RequestStateWrapper from './RequestStateWrapper';
import ModelsView from "./ModelsView";

export const LIFECYCLE_FILTER = { ACTIVE: 'Active', DELETED: 'Deleted' };

class ModelsPage extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    return (
      <div className="ExperimentPage runs-table-flex-container" style={{height: "100%"}}>
        <RequestStateWrapper
          requestIds={[]}
        >
          <ModelsView/>
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

export default connect(undefined, mapDispatchToProps)(ModelsPage);
