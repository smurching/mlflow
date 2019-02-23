import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import { getModelText } from '../reducers/Reducers';
import './ArtifactView.css';
import yaml from 'yaml-js';
import ReactJson from 'react-json-view'
import { Table } from 'react-bootstrap';
import Utils from "../utils/Utils";
import _ from "lodash";

class RunModelsView extends Component {
  constructor(props) {
    super(props);
  }

  static propTypes = {
    runUuid: PropTypes.string.isRequired,
    // Array of objects of the form:
    // {
    //   path: string,
    //   mlModelFile: string,
    // }
    // where `mlModelFile` is the contents of a yaml MLModel file and `path` is the path
    // to the enclosing model directory
    modelMetadatas: PropTypes.arrayOf(PropTypes.object).isRequired,
    // artifactRootUri: PropTypes.string.isRequired,
  };

  state = {
    activeNodeId: undefined,
  };

  parseModelFile(text) {
    if (!text) {
      return {};
    }
    return yaml.load(text);
  }

  getModelDeployText(modelMetadata) {
    const parsed = this.parseModelFile(modelMetadata.fileContents);
    if (!_.has(parsed.flavors, "python_function") && !_.has(parsed.flavors, "mleap")) {
      return (
        <div>
          This model cannot be deployed via the MLflow CLI as it has neither of the supported
          flavors ("python_function" or "mleap").
        </div>
      )
    }
    const localServeCommand = "mlflow pyfunc serve -m " + modelMetadata.parentDir + " -r " +
      parsed.run_id;
    const sagemakerCommand = "mlflow sagemaker deploy -m " + modelMetadata.parentDir + " -r " +
      parsed.run_id + " -a `sagemaker-app-name`";
    const azureMLCommand = "mlflow azureml build-image -m " + modelMetadata.parentDir +
      " -r " + parsed.run_id + " -w `workspace-name`";
    return (
      <div>
        Serve locally:
        <textarea className="run-command text-area" value={localServeCommand} readOnly/>
        Deploy to SageMaker:
        <textarea className="run-command text-area" value={sagemakerCommand} readOnly/>
        Build image for AzureML:
        <textarea className="run-command text-area" value={azureMLCommand} readOnly/>
      </div>
    )
  }

  render() {
    const { modelMetadatas } = this.props;
    if (!modelMetadatas || modelMetadatas.length === 0) {
      return (<div className="empty-artifact-outer-container">
        <div className="empty-artifact-container">
          <div>
          </div>
          <div>
            <div className="no-artifacts">No Models Recorded</div>
            <div className="no-artifacts-info">
              Use the log_model APIs to record models from MLflow runs.
            </div>
          </div>
        </div>
      </div>);
    }

    const modelRows = modelMetadatas.map((modelMetadata, i) => {
      const parsed = this.parseModelFile(modelMetadata.fileContents);
      const flavors = parsed.flavors || {};
      return <tr key={"model-row-" + i}>
        <td className="left-border">{Utils.utcStringToLocalTime(parsed.utc_time_created)}</td>
        <td className="left-border">
          <ReactJson
            displayDataTypes={false}
            src={flavors}
            collapsed={1}
            enableClipboard={false}
            displayObjectSize={false}
            name={false}
          />
        </td>
        <td className="left-border right-border" style={{minWidth: 600}}>
          {this.getModelDeployText(modelMetadata)}
        </td>
      </tr>
    });
    return (
     <Table>
       <thead>
         <tr className="top-row">
           <th className="left-border">Time Created</th>
           <th className="left-border">Flavors</th>
           <th className="left-border right-border">Deploy Model</th>
         </tr>
       </thead>
       <tbody>
         {modelRows}
       </tbody>
     </Table>
    );
  }
}

const mapStateToProps = (state, ownProps) => {
  const { runUuid } = ownProps;
  return {modelMetadatas: getModelText(runUuid, state)};
};

export default connect(mapStateToProps)(RunModelsView);
