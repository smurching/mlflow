import React, { Component } from 'react'
import PropTypes from 'prop-types';
import { connect } from 'react-redux';

import { Formik, Field } from 'formik';

import { validationSchema } from './validation';


/** TODO: Can we make this a generic class that renders a form? */
class RenameRunFormView extends Component {

  static propTypes = {
    onSubmit: PropTypes.func.isRequired
  }

  getInputProps(renderProps, name, label) {
    return {
      name,
      label,
      onChange: renderProps.handleChange,
      onBlur: renderProps.handleBlur,
      value: renderProps.values[name],
      error: renderProps.errors[name],
      touched: renderProps.touched[name],
    }
  }

  handleSubmit = (
    values,
    {
      props,
      setSubmitting,
      setErrors /* setValues, setStatus, and other goodies */,
    }) => {
      return this.props.onSubmit(values).catch((err) => {
        setErrors(err.errors)
      }).finally(() => {
        setSubmitting(false)
      })
    }

  renderForm = (renderProps) => {
    const {
      handleSubmit,
      isSubmitting,
    } = renderProps;
    const { classes } = this.props;
    return <form onSubmit={handleSubmit}>
      <h3> Rename Run </h3>
      <div>
        <div> Please enter a new name for the run: </div>
        <Field
          type="newRunName"
          name="newRunName"
          label="New Run Name"
          autoFocus
        />
      </div>
      <button type="submit" disabled={isSubmitting}>
        Save
      </button>
    </form>;
  }

  render() {
    const { initialValues } = this.props;
    return <div>
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={this.handleSubmit}
        render={this.renderForm}/>
    </div>
  }
}

function mapStateToProps(state, ownProps) {
  return {
  }
}


export default connect(mapStateToProps)(RenameRunFormView)