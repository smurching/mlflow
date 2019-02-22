import React, { Component } from 'react';
import PropTypes from 'prop-types';
import RunModelsView from './RunModelsView';
import { getUUID, listModelsApi } from '../Actions';
import { connect } from 'react-redux';
import RequestStateWrapper from './RequestStateWrapper';
import spinner from '../static/mlflow-spinner.png';

class RunModelsPage extends Component {
  static propTypes = {
    runUuid: PropTypes.string.isRequired,
    listModels: PropTypes.func.isRequired,
  };

  state = {
    listModelsRequestId: getUUID(),
  };

  componentWillMount() {
    this.props.listModels(this.props.runUuid, undefined, this.state.listModelsRequestId);
  }

  pendingRenderFunc() {
    return (<div>
      <img alt="" className="loading-spinner" src={spinner}/>
      {' '}loading...
    </div>);
  }

  render() {
    return <RequestStateWrapper
      requestIds={[this.state.listModelsRequestId]}
      pendingRenderFunc={this.pendingRenderFunc}
    >
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
