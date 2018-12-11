import React, { Component } from 'react';
import { connect } from 'react-redux';
import PropTypes from 'prop-types';
import ExperimentViewUtil from "./ExperimentViewUtil";
import { RunInfo } from '../sdk/MlflowMessages';
import classNames from 'classnames';
import { Dropdown, MenuItem } from 'react-bootstrap';
import ExperimentRunsSortToggle from './ExperimentRunsSortToggle';
import Utils from '../utils/Utils';
import BaggedCell from "./BaggedCell";
import { Portal } from 'react-overlays';

import {CellMeasurer, CellMeasurerCache, Grid, AutoSizer, ScrollSync} from 'react-virtualized';


import ReactDOM from 'react-dom';
import { Column, Table } from 'react-virtualized';
import 'react-virtualized/styles.css';
import EmptyIfClosedMenu from "./EmptyIfClosedMenu"


// Table data as an array of objects
const list = [...Array(10000).keys()].map((i) => {
  return {
    name: "Person " + i, description:  'Software engineer',
  };
});


const styles = {
  sortArrow: {
    marginLeft: "2px",
  },
  sortContainer: {
    minHeight: "18px",
  },
  sortToggle: {
    cursor: "pointer",
  },
  sortKeyName: {
    display: "inline-block"
  },
  metricParamCellContent: {
    display: "inline-block",
    maxWidth: 120,
  },
  metricParamNameContainer: {
    verticalAlign: "middle",
    display: "inline-block",
  },
  metricParamHeaderContainer: {
    verticalAlign: "middle",
    // display: "inline-block",
    maxWidth: 120,
  }
};

/**
 * Compact table view for displaying runs associated with an experiment. Renders metrics/params in
 * a single table cell per run (as opposed to one cell per metric/param).
 */
class ExperimentRunsTableCompactView extends Component {
  constructor(props) {
    super(props);
    this.getRow = this.getRow.bind(this);
    this.onHover = this.onHover.bind(this);
  }

  static propTypes = {
    runInfos: PropTypes.arrayOf(RunInfo).isRequired,
    // List of list of params in all the visible runs
    paramsList: PropTypes.arrayOf(Array).isRequired,
    // List of list of metrics in all the visible runs
    metricsList: PropTypes.arrayOf(Array).isRequired,
    // List of tags dictionary in all the visible runs.
    tagsList: PropTypes.arrayOf(Object).isRequired,
    // Function which takes one parameter (runId)
    onCheckbox: PropTypes.func.isRequired,
    onCheckAll: PropTypes.func.isRequired,
    onExpand: PropTypes.func.isRequired,
    isAllChecked: PropTypes.bool.isRequired,
    onSortBy: PropTypes.func.isRequired,
    sortState: PropTypes.object.isRequired,
    runsSelected: PropTypes.object.isRequired,
    runsExpanded: PropTypes.object.isRequired,
    setSortByHandler: PropTypes.func.isRequired,
    paramKeyList: PropTypes.arrayOf(String).isRequired,
    metricKeyList: PropTypes.arrayOf(String).isRequired,
    metricRanges: PropTypes.object.isRequired,
    // Handler for adding a metric or parameter to the set of bagged columns. All bagged metrics
    // are displayed in a single column, while each unbagged metric has its own column. Similar
    // logic applies for params.
    onAddBagged: PropTypes.func.isRequired,
    // Handler for removing a metric or parameter from the set of bagged columns.
    onRemoveBagged: PropTypes.func.isRequired,
    // Array of keys corresponding to unbagged params
    unbaggedParams: PropTypes.arrayOf(String).isRequired,
    // Array of keys corresponding to unbagged metrics
    unbaggedMetrics: PropTypes.arrayOf(String).isRequired,
  };

  state = {
    hoverState: {isMetric: false, isParam: false, key: ""},
    showPortal: false,
  };

  onHover({isParam, isMetric, key}) {
    this.setState({ hoverState: {isParam, isMetric, key} });
  }

  /** Returns a row of table content (i.e. a non-header row) corresponding to a single run. */
  getRow({ idx, isParent, hasExpander, expanderOpen, childrenIds }) {
    const {
      runInfos,
      paramsList,
      metricsList,
      onCheckbox,
      sortState,
      runsSelected,
      tagsList,
      setSortByHandler,
      onExpand,
      paramKeyList,
      metricKeyList,
      metricRanges,
      unbaggedMetrics,
      unbaggedParams,
      onRemoveBagged,
    } = this.props;
    const paramsMap =ExperimentViewUtil.toParamsMap(paramsList[idx]);
    const metricsMap = ExperimentViewUtil.toMetricsMap(metricsList[idx]);
    const tagsMap = tagsList[idx];
    const runInfo = runInfos[idx];
    const hoverState = this.state.hoverState;
    const selected = runsSelected[runInfo.run_uuid] === true;
    const rowContents = [
      ExperimentViewUtil.getCheckboxForRow(selected, () => onCheckbox(runInfo.run_uuid), "div"),
      ExperimentViewUtil.getExpander(
        hasExpander, expanderOpen, () => onExpand(runInfo.run_uuid, childrenIds), runInfo.run_uuid, "div")
    ];
    ExperimentViewUtil.getRunInfoCellsForRow(runInfo, tagsMap, isParent, "div")
      .forEach((col) => rowContents.push(col));

    const unbaggedParamSet = new Set(unbaggedParams);
    const unbaggedMetricSet = new Set(unbaggedMetrics);
    const baggedParams = paramKeyList.filter((paramKey) =>
      !unbaggedParamSet.has(paramKey) && paramsMap[paramKey] !== undefined);
    const baggedMetrics = metricKeyList.filter((metricKey) =>
      !unbaggedMetricSet.has(metricKey) && metricsMap[metricKey] !== undefined);

    // Add params (unbagged, then bagged)
    unbaggedParams.forEach((paramKey) => {
      rowContents.push(ExperimentViewUtil.getUnbaggedParamCell(paramKey, paramsMap, "div"));
    });
    // Add bagged params
    const paramsCellContents = baggedParams.map((paramKey) => {
      const isHovered = hoverState.isParam && hoverState.key === paramKey;
      const keyname = "param-" + paramKey;
      const sortIcon = ExperimentViewUtil.getSortIcon(sortState, false, true, paramKey);
      return (<BaggedCell
        key={keyname}
        sortIcon={sortIcon}
        keyName={paramKey} value={paramsMap[paramKey].getValue()} onHover={this.onHover}
        setSortByHandler={setSortByHandler} isMetric={false} isParam={true} isHovered={isHovered}
        onRemoveBagged={onRemoveBagged}/>);
    });
    if (this.shouldShowBaggedColumn(true)) {
      rowContents.push(
        <div key={"params-container-cell-" + runInfo.run_uuid}>
          {paramsCellContents}
          {/*{[...Array(10).keys()].map(() => <div>{[Array(10).keys()].map(() => <div>{idx.toString().repeat(20)}</div>)}</div>)}*/}
        </div>);
    }

    // Add metrics (unbagged, then bagged)
    unbaggedMetrics.forEach((metricKey) => {
      rowContents.push(
        ExperimentViewUtil.getUnbaggedMetricCell(metricKey, metricsMap, metricRanges, "div"));
    });

    // Add bagged metrics
    const metricsCellContents = baggedMetrics.map((metricKey) => {
    // const metricsCellContents = [...Array(100).keys()].map((metricKey) => {
      const keyname = "metric-" + metricKey;
      const isHovered = hoverState.isMetric && hoverState.key === metricKey;
      const sortIcon = ExperimentViewUtil.getSortIcon(sortState, true, false, metricKey);
      return (
        <BaggedCell key={keyname}
                    keyName={metricKey} value={metricsMap[metricKey].getValue().toString()} onHover={this.onHover}
                    sortIcon={sortIcon}
                    setSortByHandler={setSortByHandler} isMetric={true} isParam={false} isHovered={isHovered}
                    onRemoveBagged={onRemoveBagged}/>
      );
    });
    if (this.shouldShowBaggedColumn(false)) {
      rowContents.push(
        <div key={"metrics-container-cell-" + runInfo.run_uuid}>
          {metricsCellContents}
        </div>
      );
    }

    const sortValue = ExperimentViewUtil.computeSortValue(
      sortState, metricsMap, paramsMap, runInfo, tagsMap);
    return {
      key: runInfo.run_uuid,
      sortValue,
      contents: rowContents,
      isChild: !isParent,
    };
  }

  getSortInfo(isMetric, isParam) {
    const { sortState, onSortBy } = this.props;
    const sortIcon = sortState.ascending ?
      <i className="fas fa-caret-up" style={styles.sortArrow}/> :
      <i className="fas fa-caret-down" style={styles.sortArrow}/>;
    if (sortState.isMetric === isMetric && sortState.isParam === isParam) {
      return (
        <span
          style={styles.sortToggle}
          onClick={() => onSortBy(isMetric, isParam, sortState.key)}
        >
        <span style={styles.sortKeyName} className="run-table-container">
          (sort: {sortState.key}
        </span>
          {sortIcon}
          <span>)</span>
      </span>);
    }
    return undefined;
  }

  /**
   * Returns true if our table should contain a column for displaying bagged params (if isParam is
   * truthy) or bagged metrics.
   */
  shouldShowBaggedColumn(isParam) {
    const { metricKeyList, paramKeyList, unbaggedMetrics, unbaggedParams } = this.props;
    if (isParam) {
      return unbaggedParams.length !== paramKeyList.length || paramKeyList.length === 0;
    }
    return unbaggedMetrics.length !== metricKeyList.length || metricKeyList.length === 0;
  }

  /**
   * Returns an array of header-row cells (DOM elements) corresponding to metric / parameter
   * columns.
   */
  getMetricParamHeaderCells() {
    const {
      setSortByHandler,
      sortState,
      paramKeyList,
      metricKeyList,
      unbaggedMetrics,
      unbaggedParams,
      onAddBagged,
    } = this.props;
    const columns = [];
    const getHeaderCell = (isParam, key, i) => {
      const isMetric = !isParam;
      const sortIcon = ExperimentViewUtil.getSortIcon(sortState, isMetric, isParam, key);
      const className = classNames("bottom-row");
      const elemKey = (isParam ? "param-" : "metric-") + key;
      const keyContainerWidth = sortIcon ? "calc(100% - 20px)" : "100%";
      const id = key + "-" + isParam;
      const child = <Dropdown style={{width: "100%"}}>
        <ExperimentRunsSortToggle
          bsRole="toggle"
          className="metric-param-sort-toggle"
        >
          <span style={{maxWidth: keyContainerWidth, overflow: "hidden", display: "inline-block", verticalAlign: "middle"}}>{key}</span>
          <span style={ExperimentViewUtil.styles.sortIconContainer}>{sortIcon}</span>
        </ExperimentRunsSortToggle>
        <EmptyIfClosedMenu className="mlflow-menu" bsRole="menu">
          <MenuItem
            className="mlflow-menu-item"
            onClick={() => setSortByHandler(!isParam, isParam, key, true)}
          >
            Sort ascending
          </MenuItem>
          <MenuItem
            className="mlflow-menu-item"
            onClick={() => setSortByHandler(!isParam, isParam, key, false)}
          >
            Sort descending
          </MenuItem>
          <MenuItem
            className="mlflow-menu-item"
            onClick={() => onAddBagged(isParam, key)}
          >
            Collapse column
          </MenuItem>
        </EmptyIfClosedMenu>
      </Dropdown>;
      return (
        <div
          key={elemKey}
          className={className}
          style={{height: "100%"}}
          id={id}
        >
          <span
            style={styles.metricParamHeaderContainer}
            // TODO remove run-table-container here to fix horiz alignment issues?
            className="run-table-container"
          >
            <div onClick={() => this.setState({showPortal: true})}>click mee</div>
            <Portal container={() => this.refs.container}>
              {this.state.showPortal && child}
            </Portal>
          </span>
        </div>);
    };

    const paramClassName = classNames("bottom-row", {"left-border": unbaggedParams.length === 0});
    const metricClassName = classNames("bottom-row", {"left-border": unbaggedMetrics.length === 0});
    unbaggedParams.forEach((paramKey, i) => {
      columns.push(getHeaderCell(true, paramKey, i));
    });

    if (this.shouldShowBaggedColumn(true)) {
      columns.push(<div key="meta-bagged-params left-border" className={paramClassName}>
        Parameters
      </div>);
    }
    unbaggedMetrics.forEach((metricKey, i) => {
      columns.push(getHeaderCell(false, metricKey, i));
    });
    if (this.shouldShowBaggedColumn(false)) {
      columns.push(<div key="meta-bagged-metrics left-border" className={metricClassName}>
        Metrics
      </div>);
    }
    return columns;
  }

  _cache = new CellMeasurerCache({
    fixedWidth: true,
    minHeight: 32,
  });

  _lastSortState = this.props.sortState;
  _lastRunsExpanded = this.props.runsExpanded;
  _lastUnbaggedMetrics = this.props.unbaggedMetrics;
  _lastUnbaggedParams = this.props.unbaggedParams;


  render() {
    const {
      runInfos,
      onCheckAll,
      isAllChecked,
      onSortBy,
      sortState,
      tagsList,
      runsExpanded,
      unbaggedMetrics,
      unbaggedParams,
    } = this.props;
    const rows = ExperimentViewUtil.getRows({
      runInfos,
      sortState,
      tagsList,
      runsExpanded,
      getRow: this.getRow });

    const headerCells = [
      ExperimentViewUtil.getSelectAllCheckbox(onCheckAll, isAllChecked, "div"),
      // placeholder for expander header cell,
      ExperimentViewUtil.getExpanderHeader("div"),
    ];
    ExperimentViewUtil.getRunMetadataHeaderCells(onSortBy, sortState, "div")
      .forEach((headerCell) => headerCells.push(headerCell));
    this.getMetricParamHeaderCells().forEach((cell) => headerCells.push(cell));

    const baseColStyle = {padding: 8}; //{display: "flex", alignItems: "flex-start"};

    // Run metadata column renderers
    const colRenderers = [...Array(7).keys()].map((colIdx) => {
      return ({rowIndex}) => {
        return <div style={{...baseColStyle}}>{rows[rowIndex].contents[colIdx]}</div>;
      }
    });
    // Unbagged parameters
    unbaggedParams.forEach((unbaggedParam, idx) => {
      const unbaggedParamRenderer = ({rowIndex, style}) => {
        return <div style={{...baseColStyle}}>{rows[rowIndex].contents[7 + idx]}</div>;
      };
      colRenderers.push(unbaggedParamRenderer)
    });

    // Bagged params
    const baggedParamRenderer = ({rowIndex, parent, key}) => {
      return (
        <div
          style={{
            ...baseColStyle,
            whiteSpace: 'normal',
          }}>
          {rows[rowIndex].contents[7 + unbaggedParams.length]}
        </div>);
    };
    colRenderers.push(baggedParamRenderer);

    // Unbagged metrics
    unbaggedMetrics.forEach((unbaggedMetric, idx) => {
      const unbaggedMetricRenderer = ({rowIndex}) => {
        return <div style={{...baseColStyle}}>
          {rows[rowIndex].contents[8 + unbaggedParams.length + idx]}
          </div>;
      };
      colRenderers.push(unbaggedMetricRenderer);
    });

    const baggedMetricRenderer = ({rowIndex, parent, key}) => {
      return (
        <div
          style={{
            ...baseColStyle,
            whiteSpace: 'normal',
          }}>
          {rows[rowIndex].contents[8 + unbaggedParams.length + unbaggedMetrics.length]}
        </div>);
    };
    colRenderers.push(baggedMetricRenderer);
    const _renderHeaderCell = ({columnIndex, style, key}) => {
      // const columnSpecificStyle = columnIndex === 0 ? {} : {borderRight: "1px solid #e2e2e2"};
      const customStyles = {
        borderLeft: columnIndex >= 7 ? "1px solid #e2e2e2" : "",
        borderBottom: "1px solid #e2e2e2",
        padding: 8,
      };
      const finalStyle = {...style, ...customStyles, overflow: "visible"};
      return <div style={finalStyle} key={key}>{headerCells[columnIndex]}</div>;
    };

    return (
      <React.Fragment>
        <ScrollSync>
          {({
              clientHeight,
              clientWidth,
              onScroll,
              scrollHeight,
              scrollLeft,
              scrollTop,
              scrollWidth,
            }) => {
            return (<div id="autosizer-parent" className="flex-container" ref='container'>
              <AutoSizer>
                {({width, height}) => {
                  if (this._lastSortState !== sortState) {
                    this._lastSortState = sortState;

                    console.log("Clearing all because sort state changed!");
                    this._cache.clearAll();
                  }
                  if (this._lastRunsExpanded !== runsExpanded) {
                    this._lastRunsExpanded = runsExpanded;
                    console.log("Clearing all because runs expanded changed!");
                    this._cache.clearAll();
                  }
                  if (this._lastUnbaggedMetrics !== unbaggedMetrics) {
                    this._lastUnbaggedMetrics = unbaggedMetrics;
                    this._cache.clearAll();
                  }
                  if (this._lastUnbaggedParams !== unbaggedParams) {
                    this._lastUnbaggedParams = unbaggedParams;
                    this._cache.clearAll();
                  }
                  // Metadata columns have widths of 150, besides checkbox, expander, and date cols
                  const colWidths = [30, 30, 180];
                  [...Array(4).keys()].forEach(() => colWidths.push(150));
                  // Unbagged params have widths of 250
                  [...Array(unbaggedParams.length).keys()].forEach(() => colWidths.push(250));
                  // Bagged params have widths of 250
                  [...Array(1).keys()].forEach(() => colWidths.push(250));
                  // Unbagged metrics have widths of 250
                  [...Array(unbaggedMetrics.length).keys()].forEach(() => colWidths.push(250));
                  // Bagged metrics have widths of 250
                  [...Array(1).keys()].forEach(() => colWidths.push(250));
                  const estimatedWidth = 30 * 2 + 150 + 150 * 5 + 250 * (unbaggedMetrics.length + unbaggedParams.length + 2);

                  return (
                    <div id="autosizer-return-container">
                      <Grid
                        // className={styles.HeaderGrid}
                        columnWidth={({index}) => {
                          return colWidths[index];
                        }}
                        columnCount={rows[0].contents.length}
                        height={48}
                        cellRenderer={_renderHeaderCell}
                        rowHeight={48}
                        rowCount={1}
                        scrollLeft={scrollLeft}
                        onScroll={onScroll}
                        width={width}
                        // width={width - scrollbarSize()}
                      />
                  <Grid
                    width={width}
                    deferredMeasurementCache={this._cache}
                    columnCount={rows[0].contents.length}
                    height={height - 48}
                    columnWidth={({index}) => {
                      return colWidths[index];
                    }}
                    overscanRowCount={2}
                    rowHeight={this._cache.rowHeight}
                    rowCount={rows.length}
                    estimatedColumnSize={estimatedWidth}
                    onScroll={onScroll}
                    scrollLeft={scrollLeft}
                    cellRenderer={({ columnIndex, key, rowIndex, style, parent }) => {
                      // TODO propagate key inside fn
                      return <CellMeasurer
                        cache={this._cache}
                        columnIndex={columnIndex}
                        key={key}
                        parent={parent}
                        rowIndex={rowIndex}
                      >

                        <div className="hi-from-sid"  style={{
                          ...style,
                          borderLeft: columnIndex >= 7 ? "1px solid #e2e2e2" : "",
                          borderBottom: "1px solid #e2e2e2"
                        }}>{
                          colRenderers[columnIndex]({key, rowIndex, parent})
                        }</div>
                      </CellMeasurer>
                    }}
                  >
                  </Grid>
                  </div>);
                }}
              </AutoSizer>
            </div>);
          }}
        </ScrollSync>
      </React.Fragment>
    );
  }
}

const mapStateToProps = (state, ownProps) => {
  const { metricsList } = ownProps;
  return {metricRanges: ExperimentViewUtil.computeMetricRanges(metricsList)};
};

export default connect(mapStateToProps)(ExperimentRunsTableCompactView);
