"""
The ``mlflow.spacy`` module provides an API for logging and loading spaCy models.
This module exports spacy models with the following flavors:

spaCy (native) format
    This is the main flavor that can be loaded back into spaCy.
:py:mod:`mlflow.pyfunc`
    Produced for use by generic pyfunc-based deployment tools and batch inference.
"""

from __future__ import absolute_import

import os

import pandas as pd
import yaml

import mlflow
from mlflow import pyfunc
from mlflow.exceptions import MlflowException
from mlflow.models import Model
from mlflow.tracking.artifact_utils import _download_artifact_from_uri
from mlflow.utils.environment import _mlflow_conda_env
from mlflow.utils.model_utils import _get_flavor_configuration

FLAVOR_NAME = "spacy"


def get_default_conda_env():
    """
    :return: The default Conda environment for MLflow Models produced by calls to
             :func:`save_model()` and :func:`log_model()`.
    """
    import spacy

    return _mlflow_conda_env(
        additional_conda_deps=None,
        additional_pip_deps=[
            "spacy=={}".format(spacy.__version__),
        ],
        additional_conda_channels=None)


def save_model(spacy_model, path, conda_env=None, mlflow_model=Model()):
    """
    Save a spaCy model to a path on the local file system.

    :param spacy_model: spaCy model to be saved.
    :param path: Local path where the model is to be saved.
    :param conda_env: Either a dictionary representation of a Conda environment or the path to a
                      Conda environment yaml file. If provided, this describes the environment
                      this model should be run in. At minimum, it should specify the dependencies
                      contained in :func:`get_default_conda_env()`. If ``None``, the default
                      :func:`get_default_conda_env()` environment is added to the model.
                      The following is an *example* dictionary representation of a Conda
                      environment::

                        {
                            'name': 'mlflow-env',
                            'channels': ['defaults'],
                            'dependencies': [
                                'python=3.7.0',
                                'pip': [
                                    'spacy==2.2.3'
                                ]
                            ]
                        }

    :param mlflow_model: :py:mod:`mlflow.models.Model` this flavor is being added to.
    """
    import spacy

    path = os.path.abspath(path)
    if os.path.exists(path):
        raise MlflowException(f"Unable to save MLflow model to {path} - path '{path}' "
                              "already exists")

    model_data_subpath = "model.spacy"
    model_data_path = os.path.join(path, model_data_subpath)
    os.makedirs(model_data_path)

    # Save spacy-model
    spacy_model.to_disk(path=model_data_path)

    conda_env_subpath = "conda.yaml"
    if conda_env is None:
        conda_env = get_default_conda_env()
    elif not isinstance(conda_env, dict):
        with open(conda_env, "r") as f:
            conda_env = yaml.safe_load(f)
    with open(os.path.join(path, conda_env_subpath), "w") as f:
        yaml.safe_dump(conda_env, stream=f, default_flow_style=False)

    pyfunc.add_to_model(mlflow_model, loader_module="mlflow.spacy",
                        data=model_data_subpath, env=conda_env_subpath)
    mlflow_model.add_flavor(FLAVOR_NAME, spacy_version=spacy.__version__, data=model_data_subpath)
    mlflow_model.save(os.path.join(path, "MLmodel"))


def log_model(spacy_model, artifact_path, conda_env=None, registered_model_name=None, **kwargs):
    """
    Log a spaCy model as an MLflow artifact for the current run.

    :param spacy_model: spaCy model to be saved.
    :param artifact_path: Run-relative artifact path.
    :param conda_env: Either a dictionary representation of a Conda environment or the path to a
                      Conda environment yaml file. If provided, this decsribes the environment
                      this model should be run in. At minimum, it should specify the dependencies
                      contained in :func:`get_default_conda_env()`. If ``None``, the default
                      :func:`get_default_conda_env()` environment is added to the model.
                      The following is an *example* dictionary representation of a Conda
                      environment::

                        {
                            'name': 'mlflow-env',
                            'channels': ['defaults'],
                            'dependencies': [
                                'python=3.7.0',
                                'pip': [
                                    'spacy==2.2.3'
                                ]
                            ]
                        }
    :param registered_model_name: Note:: Experimental: This argument may change or be removed in a
                                  future release without warning. If given, create a model
                                  version under ``registered_model_name``, also creating a
                                  registered model if one with the given name does not exist.
    :param kwargs: kwargs to pass to ``spacy.save_model`` method.
    """
    Model.log(artifact_path=artifact_path, flavor=mlflow.spacy,
              registered_model_name=registered_model_name,
              spacy_model=spacy_model, conda_env=conda_env, **kwargs)


def _load_model(path):
    import spacy

    path = os.path.abspath(path)
    return spacy.load(path)


class _SpacyModelWrapper:
    def __init__(self, spacy_model):
        self.spacy_model = spacy_model

    def predict(self, dataframe):
        """
        Only works for predicting using text categorizer.
        Not suitable for other pipeline components (e.g: parser)
        :param dataframe: pandas dataframe containing texts to be categorized
                          expected shape is (n_rows,1 column)
        :return: dataframe with predictions
        """
        if len(dataframe.columns) != 1:
            raise MlflowException('Shape of input dataframe must be (n_rows, 1column)')

        return pd.DataFrame({
            'predictions': dataframe.ix[:, 0].apply(lambda text: self.spacy_model(text).cats)
        })


def _load_pyfunc(path):
    """
    Load PyFunc implementation. Called by ``pyfunc.load_pyfunc``.

    :param path: Local filesystem path to the MLflow Model with the ``spacy`` flavor.
    """
    return _SpacyModelWrapper(_load_model(path))


def load_model(model_uri):
    """
    Load a spaCy model from a local file (if ``run_id`` is ``None``) or a run.

    :param model_uri: The location, in URI format, of the MLflow model. For example:

                      - ``/Users/me/path/to/local/model``
                      - ``relative/path/to/local/model``
                      - ``s3://my_bucket/path/to/model``
                      - ``runs:/<mlflow_run_id>/run-relative/path/to/model``
                      - ``models:/<model_name>/<model_version>``
                      - ``models:/<model_name>/<stage>``

                      For more information about supported URI schemes, see
                      `Referencing Artifacts <https://www.mlflow.org/docs/latest/concepts.html#
                      artifact-locations>`_.

    :return: A spaCy loaded model
    """
    local_model_path = _download_artifact_from_uri(artifact_uri=model_uri)
    flavor_conf = _get_flavor_configuration(model_path=local_model_path, flavor_name=FLAVOR_NAME)
    # Flavor configurations for models saved in MLflow version <= 0.8.0 may not contain a
    # `data` key; in this case, we assume the model artifact path to be `model.spacy`
    spacy_model_file_path = os.path.join(local_model_path, flavor_conf.get("data", "model.spacy"))
    return _load_model(path=spacy_model_file_path)
