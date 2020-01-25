import React, { Component } from 'react';
import PropTypes from 'prop-types';


export default class EmptyIfUnhovered extends Component {
  state = {
    hovered: false,
  };

  propTypes = {
    unhoveredChildren: PropTypes.arrayOf(PropTypes.object),
    hoveredChildren: PropTypes.arrayOf(PropTypes.object),
  };


  render() {
    const { hoveredChildren, unhoveredChildren } = this.props;
    const { hovered } = this.state;
    return (<span onMouseEnter={() => this.setState({hovered: true})}
                 onMouseLeave={() => this.setState({hovered: false})}>
      {hovered ? hoveredChildren : unhoveredChildren}
    </span>);
  }
}
