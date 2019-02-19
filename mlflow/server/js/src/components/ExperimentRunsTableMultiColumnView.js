import React, { Component } from 'react';
import { connect } from 'react-redux';
import PropTypes from 'prop-types';
import { Table } from 'react-bootstrap';
import ExperimentViewUtil from './ExperimentViewUtil';
import classNames from 'classnames';
import { RunInfo } from '../sdk/MlflowMessages';

/**
 * Table view for displaying runs associated with an experiment. Renders each metric and param
 * value associated with a run in its own column.
 */
class ExperimentRunsTableMultiColumnView extends Component {
  constructor(props) {
    super(props);
    this.getRow = this.getRow.bind(this);
  }

  static propTypes = {
    runInfosByRunId: PropTypes.object.isRequired,
    // List of list of params in all the visible runs
    paramsByRunId: PropTypes.object.isRequired,
    // List of list of metrics in all the visible runs
    metricsByRunId: PropTypes.object.isRequired,
    // List of tags dictionary in all the visible runs.
    tagsByRunId: PropTypes.object.isRequired,
    // Run ID to children ID map
    runIdToChildrenIds: PropTypes.object.isRequired,
    // Function which takes one parameter (runId)
    onCheckbox: PropTypes.func.isRequired,
    onCheckAll: PropTypes.func.isRequired,
    onExpand: PropTypes.func.isRequired,
    isAllChecked: PropTypes.bool.isRequired,
    onSortBy: PropTypes.func.isRequired,
    sortState: PropTypes.object.isRequired,
    runsSelected: PropTypes.object.isRequired,
    runsExpanded: PropTypes.object.isRequired,
    metricRanges: PropTypes.object.isRequired,
  };

  getRow({ runId, isParent, hasExpander, expanderOpen, sortedRunIds, displayIndex }) {
    const {
      runInfosByRunId,
      paramsByRunId,
      metricsByRunId,
      runIdToChildrenIds,
      paramKeyList,
      metricKeyList,
      onCheckbox,
      runsSelected,
      tagsByRunId,
      onExpand,
      metricRanges,
    } = this.props;
    const runInfo = runInfosByRunId[runId];
    const paramsMap = paramsByRunId[runId];
    const metricsMap = metricsByRunId[runId];
    const childrenIds = runIdToChildrenIds[runId];
    const numParams = paramKeyList.length;
    const numMetrics = metricKeyList.length;
    const selected = runsSelected[runInfo.run_uuid] === true;
    const rowContents = [
      ExperimentViewUtil.getCheckboxForRow(selected,
        (event) => onCheckbox(event, displayIndex, sortedRunIds), "td"),
      ExperimentViewUtil.getExpander(
        hasExpander, expanderOpen, () => onExpand(runInfo.run_uuid, childrenIds), runInfo.run_uuid,
        "td"),
    ];
    ExperimentViewUtil.getRunInfoCellsForRow(runInfo, tagsByRunId[runId], isParent, "td")
      .forEach((col) => rowContents.push(col));
    paramKeyList.forEach((paramKey) => {
      rowContents.push(ExperimentViewUtil.getUnbaggedParamCell(paramKey, paramsMap, "td"));
    });
    if (numParams === 0) {
      rowContents.push(<td className="left-border" key={"meta-param-empty"}/>);
    }
    metricKeyList.forEach((metricKey) => {
      rowContents.push(
        ExperimentViewUtil.getUnbaggedMetricCell(metricKey, metricsMap, metricRanges, "td"));
    });
    if (numMetrics === 0) {
      rowContents.push(<td className="left-border" key="meta-metric-empty" />);
    }
    return {
      key: runInfo.run_uuid,
      contents: rowContents,
      isChild: !isParent,
    };
  }

  getMetricParamHeaderCells() {
    const {
      paramKeyList,
      metricKeyList,
      onSortBy,
      sortState
    } = this.props;
    const numParams = paramKeyList.length;
    const numMetrics = metricKeyList.length;
    const columns = [];

    const getHeaderCell = (isParam, key, i) => {
      const isMetric = !isParam;
      const sortIcon = ExperimentViewUtil.getSortIcon(sortState, isMetric, isParam, key);
      const className = classNames("bottom-row", "sortable", { "left-border": i === 0 });
      const elemKey = (isParam ? "param-" : "metric-") + key;
      return (
        <th
          key={elemKey} className={className}
          onClick={() => onSortBy(isMetric, isParam, key)}
        >
          <span
            style={styles.metricParamNameContainer}
            className="run-table-container"
          >
            {key}
          </span>
          <span style={styles.sortIconContainer}>{sortIcon}</span>
        </th>);
    };

    paramKeyList.forEach((paramKey, i) => {
      columns.push(getHeaderCell(true, paramKey, i));
    });
    if (numParams === 0) {
      columns.push(<th key="meta-param-empty" className="bottom-row left-border">(n/a)</th>);
    }

    metricKeyList.forEach((metricKey, i) => {
      columns.push(getHeaderCell(false, metricKey, i));
    });
    if (numMetrics === 0) {
      columns.push(<th key="meta-metric-empty" className="bottom-row left-border">(n/a)</th>);
    }
    return columns;
  }

  render() {
    const {
      runInfosByRunId,
      onCheckAll,
      isAllChecked,
      onSortBy,
      sortState,
      tagsByRunId,
      runsExpanded,
      paramKeyList,
      metricKeyList,
      runIdToChildrenIds,
      paramsByRunId,
      metricsByRunId
    } = this.props;
    const rowMetadatas = ExperimentViewUtil.getRowRenderMetadata({
      runInfosByRunId,
      runIdToChildrenIds,
      sortState,
      tagsByRunId,
      metricsByRunId,
      paramsByRunId,
      runsExpanded});

    const sortedRunIds = ExperimentViewUtil.getRunIdsSortedByDisplayOrder(rowMetadatas);
    const runIdToSortedIndex = new Map(sortedRunIds.map((val, index) => [val, index]));
    const rows = rowMetadatas.map((row, index) => this.getRow({...row, sortedRunIds,
      displayIndex: runIdToSortedIndex.get(rowMetadatas[index].runId)}));
    const columns = [
      ExperimentViewUtil.getSelectAllCheckbox(onCheckAll, isAllChecked, "th"),
      ExperimentViewUtil.getExpanderHeader("th"),
    ];
    ExperimentViewUtil.getRunMetadataHeaderCells(onSortBy, sortState, "th")
      .forEach((cell) => columns.push(cell));
    this.getMetricParamHeaderCells().forEach((cell) => columns.push(cell));
    return (<Table className="ExperimentViewMultiColumn" hover>
      <colgroup span="9"/>
      <colgroup span={paramKeyList.length}/>
      <colgroup span={metricKeyList.length}/>
      <tbody>
      <tr>
        <th className="top-row" scope="colgroup" colSpan="7"/>
        <th
          className="top-row left-border"
          scope="colgroup"
          colSpan={paramKeyList.length}
        >
          Parameters
        </th>
        <th className="top-row left-border" scope="colgroup"
          colSpan={metricKeyList.length}>Metrics
        </th>
      </tr>
      <tr>
        {columns}
      </tr>
      {ExperimentViewUtil.renderRows(rows)}
      </tbody>
    </Table>);
  }
}

const styles = {
  sortIconContainer: {
    marginLeft: 2,
    minWidth: 12.5,
    display: 'inline-block',
  },
  metricParamNameContainer: {
    verticalAlign: "middle",
    display: "inline-block",
  },
};

const mapStateToProps = (state, ownProps) => {
  const { metricsByRunId } = ownProps;
  return {metricRanges: ExperimentViewUtil.computeMetricRanges(metricsByRunId)};
};

export default connect(mapStateToProps)(ExperimentRunsTableMultiColumnView);
