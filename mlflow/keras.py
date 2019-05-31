"""
The ``mlflow.keras`` module provides an API for logging and loading Keras models. This module
exports Keras models with the following flavors:

Keras (native) format
    This is the main flavor that can be loaded back into Keras.
:py:mod:`mlflow.pyfunc`
    Produced for use by generic pyfunc-based deployment tools and batch inference.
"""

from __future__ import absolute_import

import os
import yaml

import pandas as pd

from mlflow import pyfunc
from mlflow.models import Model
import mlflow.tracking
from mlflow.tracking.artifact_utils import _download_artifact_from_uri
from mlflow.utils.environment import _mlflow_conda_env
from mlflow.utils.model_utils import _get_flavor_configuration

FLAVOR_NAME = "keras"


def get_default_conda_env():
    """
    :return: The default Conda environment for MLflow Models produced by calls to
    :func:`save_model()` and :func:`log_model()`.
    """
    import keras
    import tensorflow as tf

    return _mlflow_conda_env(
        additional_conda_deps=[
            "keras={}".format(keras.__version__),
            # The Keras pyfunc representation requires the TensorFlow
            # backend for Keras. Therefore, the conda environment must
            # include TensorFlow
            "tensorflow=={}".format(tf.__version__),
        ],
        additional_pip_deps=None,
        additional_conda_channels=None)


def save_model(keras_model, path, conda_env=None, mlflow_model=Model()):
    """
    Save a Keras model to a path on the local file system.

    :param keras_model: Keras model to be saved.
    :param path: Local path where the model is to be saved.
    :param conda_env: Either a dictionary representation of a Conda environment or the path to a
                      Conda environment yaml file. If provided, this decribes the environment
                      this model should be run in. At minimum, it should specify the dependencies
                      contained in :func:`get_default_conda_env()`. If `None`, the default
                      :func:`get_default_conda_env()` environment is added to the model.
                      The following is an *example* dictionary representation of a Conda
                      environment::

                        {
                            'name': 'mlflow-env',
                            'channels': ['defaults'],
                            'dependencies': [
                                'python=3.7.0',
                                'keras=2.2.4',
                                'tensorflow=1.8.0'
                            ]
                        }

    :param mlflow_model: MLflow model config this flavor is being added to.

    >>> import mlflow
    >>> # Build, compile, and train your model
    >>> keras_model = ...
    >>> keras_model_path = ...
    >>> keras_model.compile(optimizer="rmsprop", loss="mse", metrics=["accuracy"])
    >>> results = keras_model.fit(
    ...     x_train, y_train, epochs=20, batch_size = 128, validation_data=(x_val, y_val))
    ... # Save the model as an MLflow Model
    >>> mlflow.keras.save_model(keras_model, keras_model_path)
    """
    import keras

    path = os.path.abspath(path)
    if os.path.exists(path):
        raise Exception("Path '{}' already exists".format(path))
    os.makedirs(path)
    model_data_subpath = "model.h5"
    keras_model.save(os.path.join(path, model_data_subpath))

    conda_env_subpath = "conda.yaml"
    if conda_env is None:
        conda_env = get_default_conda_env()
    elif not isinstance(conda_env, dict):
        with open(conda_env, "r") as f:
            conda_env = yaml.safe_load(f)
    with open(os.path.join(path, conda_env_subpath), "w") as f:
        yaml.safe_dump(conda_env, stream=f, default_flow_style=False)

    pyfunc.add_to_model(mlflow_model, loader_module="mlflow.keras",
                        data=model_data_subpath, env=conda_env_subpath)
    mlflow_model.add_flavor(FLAVOR_NAME, keras_version=keras.__version__, data=model_data_subpath)
    mlflow_model.save(os.path.join(path, "MLmodel"))


def log_model(keras_model, artifact_path, conda_env=None, **kwargs):
    """
    Log a Keras model as an MLflow artifact for the current run.

    :param keras_model: Keras model to be saved.
    :param artifact_path: Run-relative artifact path.
    :param conda_env: Either a dictionary representation of a Conda environment or the path to a
                      Conda environment yaml file. If provided, this decribes the environment
                      this model should be run in. At minimum, it should specify the dependencies
                      contained in :func:`get_default_conda_env()`. If `None`, the default
                      :func:`mlflow.keras.get_default_conda_env()` environment is added to the
                      model. The following is an *example* dictionary representation of a Conda
                      environment::

                        {
                            'name': 'mlflow-env',
                            'channels': ['defaults'],
                            'dependencies': [
                                'python=3.7.0',
                                'keras=2.2.4',
                                'tensorflow=1.8.0'
                            ]
                        }

    :param kwargs: kwargs to pass to ``keras_model.save`` method.

    >>> from keras import Dense, layers
    >>> import mlflow
    >>> # Build, compile, and train your model
    >>> keras_model = ...
    >>> keras_model.compile(optimizer="rmsprop", loss="mse", metrics=["accuracy"])
    >>> results = keras_model.fit(
    ...     x_train, y_train, epochs=20, batch_size = 128, validation_data=(x_val, y_val))
    >>> # Log metrics and log the model
    >>> with mlflow.start_run() as run:
    >>>   mlflow.keras.log_model(keras_model, "models")
    """
    Model.log(artifact_path=artifact_path, flavor=mlflow.keras,
              keras_model=keras_model, conda_env=conda_env, **kwargs)


def _load_model(model_file):
    import keras
    import keras.models
    import h5py

    from distutils.version import StrictVersion

    if StrictVersion(keras.__version__) >= StrictVersion("2.2.3"):
        # NOTE: Keras 2.2.3 does not work with unicode paths in python2. Pass in h5py.File instead
        # of string to avoid issues.
        with h5py.File(os.path.abspath(model_file), "r") as model_file:
            return keras.models.load_model(model_file)
    else:
        # NOTE: Older versions of Keras only handle filepath.
        return keras.models.load_model(model_file)


class _KerasModelWrapper:
    def __init__(self, keras_model, graph, sess):
        self.keras_model = keras_model
        self._graph = graph
        self._sess = sess

    def predict(self, dataframe):
        with self._graph.as_default():
            with self._sess.as_default():
                predicted = pd.DataFrame(self.keras_model.predict(dataframe))
        predicted.index = dataframe.index
        return predicted


def _load_pyfunc(path):
    """
    Load PyFunc implementation. Called by ``pyfunc.load_pyfunc``.

    :param path: Local filesystem path to the MLflow Model with the ``keras`` flavor.
    """
    import keras.backend as K
    import tensorflow as tf

    if K._BACKEND == 'tensorflow':
        graph = tf.Graph()
        sess = tf.Session(graph=graph)
        # By default tf backed models depend on the global graph and session.
        # We create an use new Graph and Session and store them with the model
        # This way the model is independent on the global state.
        with graph.as_default():
            with sess.as_default():  # pylint:disable=not-context-manager
                K.set_learning_phase(0)
                m = _load_model(path)
        return _KerasModelWrapper(m, graph, sess)
    else:
        raise Exception("Unsupported backend '%s'" % K._BACKEND)


def load_model(model_uri):
    """
    Load a Keras model from a local file (if ``run_id`` is None) or a run.

    :param model_uri: The location, in URI format, of the MLflow model, for example:

                      - ``/Users/me/path/to/local/model``
                      - ``relative/path/to/local/model``
                      - ``s3://my_bucket/path/to/model``
                      - ``runs:/<mlflow_run_id>/run-relative/path/to/model``

                      For more information about supported URI schemes, see the
                      `Artifacts Documentation <https://www.mlflow.org/docs/latest/tracking.html#
                      supported-artifact-stores>`_.

    :return: A Keras model instance.

    >>> # Load persisted model as a Keras model or as a PyFunc, call predict() on a Pandas DataFrame
    >>> keras_model = mlflow.keras.load_model("models", run_id="96771d893a5e46159d9f3b49bf9013e2")
    >>> predictions = keras_model.predict(x_test)
    """
    local_model_path = _download_artifact_from_uri(artifact_uri=model_uri)
    flavor_conf = _get_flavor_configuration(model_path=local_model_path, flavor_name=FLAVOR_NAME)
    # Flavor configurations for models saved in MLflow version <= 0.8.0 may not contain a
    # `data` key; in this case, we assume the model artifact path to be `model.h5`
    keras_model_artifacts_path = os.path.join(local_model_path, flavor_conf.get("data", "model.h5"))
    return _load_model(model_file=keras_model_artifacts_path)
