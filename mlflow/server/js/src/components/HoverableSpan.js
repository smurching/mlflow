import React, { Component } from 'react';
import PropTypes from 'prop-types';


export default class HoverableSpan extends Component {
  state = {
    hovered: false,
  };

  static propTypes = {
    renderFunc: PropTypes.func.isRequired,
  };


  render() {
    const { renderFunc } = this.props;
    const { hovered } = this.state;
    return (<span onMouseEnter={() => this.setState({hovered: true})}
                 onMouseLeave={() => this.setState({hovered: false})}>
      {renderFunc(hovered)}
    </span>);
  }
}
