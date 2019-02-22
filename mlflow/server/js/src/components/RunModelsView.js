import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import {
  getBasename, getExtension, IMAGE_EXTENSIONS,
  TEXT_EXTENSIONS
} from '../utils/FileUtils';
import { getModelText } from '../reducers/Reducers';
import { ArtifactNode as ArtifactUtils, ArtifactNode } from '../utils/ArtifactUtils';
import { decorators, Treebeard } from 'react-treebeard';
import bytes from 'bytes';
import './ArtifactView.css';
import ShowArtifactPage from './artifact-view-components/ShowArtifactPage';
import spinner from '../static/mlflow-spinner.png';
import {listModelsApi} from "../Actions";
import ExperimentViewUtil from "./ExperimentViewUtil";
import yaml from 'yaml-js';
import JSONFormatter from 'json-formatter-js'
import ReactJson from 'react-json-view'
import { Table } from 'react-bootstrap';

class RunModelsView extends Component {
  constructor(props) {
    super(props);
  }

  static propTypes = {
    runUuid: PropTypes.string.isRequired,
    // Array of text of MLModel files
    modelTextArray: PropTypes.arrayOf(PropTypes.string).isRequired,
    // artifactRootUri: PropTypes.string.isRequired,
  };

  state = {
    activeNodeId: undefined,
  };

  parseModelFile(text) {
    return yaml.load(text);
  }

  render() {
    const { modelTextArray } = this.props;
    const modelRows = modelTextArray.map((modelText) => {
      const parsed = this.parseModelFile(modelText);
      const flavors = parsed.flavors || {};
      return <tr>
        <td>
          <ReactJson
            displayDataTypes={false}
            src={flavors}
            collapsed={1}
            enableClipboard={false}
            displayObjectSize={false}
          />
        </td>
        <td className="left-border">{parsed.run_id}</td>
        <td className="left-border">{parsed.utc_time_created}</td>
      </tr>
    });
    return (
     <Table style={{width: "calc(100% - 128px)"}}>
       <tr className="top-row">
         <th>Flavors</th>
         <th className="left-border">Run ID</th>
         <th className="left-border">Time Created</th>
       </tr>
       {modelRows}
     </Table>
    );
  }
}

const mapStateToProps = (state, ownProps) => {
  const { runUuid } = ownProps;
  return {modelTextArray: getModelText(runUuid, state)};
};

export default connect(mapStateToProps)(RunModelsView);