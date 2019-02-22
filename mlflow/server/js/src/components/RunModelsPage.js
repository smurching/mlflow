import React, { Component } from 'react';
import PropTypes from 'prop-types';
import RunModelsView from './RunModelsView';
import { getUUID, listModelsApi } from '../Actions';
import { connect } from 'react-redux';
import RequestStateWrapper from './RequestStateWrapper';

class RunModelsPage extends Component {
  static propTypes = {
    runUuid: PropTypes.string.isRequired,
    listModels: PropTypes.func.isRequired,
    // For now, assume isHydrated is always true.
    isHydrated: PropTypes.bool,
  };

  state = {
    listModelsRequestId: getUUID(),
  };

  componentWillMount() {
    this.props.listModels(this.props.runUuid, undefined, this.state.listModelsRequestId);
  }

  render() {
    // If not hydrated then try to get the data before rendering this view.
    return <RequestStateWrapper requestIds={[this.state.listModelsRequestId]}>
      <RunModelsView runUuid={this.props.runUuid}/>
    </RequestStateWrapper>
  }
}

const mapDispatchToProps = (dispatch) => {
  const listModels = (runUuid, path, requestId) => {
    dispatch(listModelsApi(runUuid, path, requestId));
  };
  return {
    listModels
  };
};

export default connect(undefined, mapDispatchToProps)(RunModelsPage);
