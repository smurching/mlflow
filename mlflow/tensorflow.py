"""
The ``mlflow.tensorflow`` module provides an API for logging and loading TensorFlow models.
This module exports TensorFlow models with the following flavors:

TensorFlow (native) format
    This is the main flavor that can be loaded back into TensorFlow.
:py:mod:`mlflow.pyfunc`
    Produced for use by generic pyfunc-based deployment tools and batch inference.
"""

from __future__ import absolute_import

import os
import shutil
import yaml
import logging

import pandas

import mlflow
from mlflow import pyfunc
from mlflow.exceptions import MlflowException
from mlflow.models import Model
from mlflow.protos.databricks_pb2 import DIRECTORY_NOT_EMPTY
from mlflow.tracking.artifact_utils import _download_artifact_from_uri
from mlflow.utils import keyword_only
from mlflow.utils.environment import _mlflow_conda_env
from mlflow.utils.file_utils import _copy_file_or_tree
from mlflow.utils.model_utils import _get_flavor_configuration

FLAVOR_NAME = "tensorflow"

_logger = logging.getLogger(__name__)


def get_default_conda_env():
    """
    :return: The default Conda environment for MLflow Models produced by calls to
    :func:`save_model()` and :func:`log_model()`.
    """
    import tensorflow as tf
    return _mlflow_conda_env(
        additional_conda_deps=[
            "tensorflow={}".format(tf.__version__),
        ],
        additional_pip_deps=None,
        additional_conda_channels=None)


@keyword_only
def log_model(tf_saved_model_dir, tf_meta_graph_tags, tf_signature_def_key, artifact_path,
              conda_env=None):
    """
    Log a *serialized* collection of TensorFlow graphs and variables as an MLflow model
    for the current run. This method operates on TensorFlow variables and graphs that have been
    serialized in TensorFlow's ``SavedModel`` format. For more information about ``SavedModel``
    format, see the TensorFlow documentation:
    https://www.tensorflow.org/guide/saved_model#save_and_restore_models.

    :param tf_saved_model_dir: Path to the directory containing serialized TensorFlow variables and
                               graphs in ``SavedModel`` format.
    :param tf_meta_graph_tags: A list of tags identifying the model's metagraph within the
                               serialized ``SavedModel`` object. For more information, see the
                               ``tags`` parameter of the
                               ``tf.saved_model.builder.SavedModelBuilder`` method.
    :param tf_signature_def_key: A string identifying the input/output signature associated with the
                                 model. This is a key within the serialized ``SavedModel`` signature
                                 definition mapping. For more information, see the
                                 ``signature_def_map`` parameter of the
                                 ``tf.saved_model.builder.SavedModelBuilder`` method.
    :param artifact_path: The run-relative path to which to log model artifacts.
    :param conda_env: Either a dictionary representation of a Conda environment or the path to a
                      Conda environment yaml file. If provided, this decribes the environment
                      this model should be run in. At minimum, it should specify the dependencies
                      contained in :func:`get_default_conda_env()`. If ``None``, the default
                      :func:`get_default_conda_env()` environment is added to the model. The
                      following is an *example* dictionary representation of a Conda environment::

                        {
                            'name': 'mlflow-env',
                            'channels': ['defaults'],
                            'dependencies': [
                                'python=3.7.0',
                                'tensorflow=1.8.0'
                            ]
                        }

    """
    return Model.log(artifact_path=artifact_path, flavor=mlflow.tensorflow,
                     tf_saved_model_dir=tf_saved_model_dir, tf_meta_graph_tags=tf_meta_graph_tags,
                     tf_signature_def_key=tf_signature_def_key, conda_env=conda_env)


@keyword_only
def save_model(tf_saved_model_dir, tf_meta_graph_tags, tf_signature_def_key, path,
               mlflow_model=Model(), conda_env=None):
    """
    Save a *serialized* collection of TensorFlow graphs and variables as an MLflow model
    to a local path. This method operates on TensorFlow variables and graphs that have been
    serialized in TensorFlow's ``SavedModel`` format. For more information about ``SavedModel``
    format, see the TensorFlow documentation:
    https://www.tensorflow.org/guide/saved_model#save_and_restore_models.

    :param tf_saved_model_dir: Path to the directory containing serialized TensorFlow variables and
                               graphs in ``SavedModel`` format.
    :param tf_meta_graph_tags: A list of tags identifying the model's metagraph within the
                               serialized ``SavedModel`` object. For more information, see the
                               ``tags`` parameter of the
                               ``tf.saved_model.builder.savedmodelbuilder`` method.
    :param tf_signature_def_key: A string identifying the input/output signature associated with the
                                 model. This is a key within the serialized ``savedmodel``
                                 signature definition mapping. For more information, see the
                                 ``signature_def_map`` parameter of the
                                 ``tf.saved_model.builder.savedmodelbuilder`` method.
    :param path: Local path where the MLflow model is to be saved.
    :param mlflow_model: MLflow model configuration to which to add the ``tensorflow`` flavor.
    :param conda_env: Either a dictionary representation of a Conda environment or the path to a
                      Conda environment yaml file. If provided, this decribes the environment
                      this model should be run in. At minimum, it should specify the dependencies
                      contained in :func:`get_default_conda_env()`. If ``None``, the default
                      :func:`get_default_conda_env()` environment is added to the model. The
                      following is an *example* dictionary representation of a Conda environment::

                        {
                            'name': 'mlflow-env',
                            'channels': ['defaults'],
                            'dependencies': [
                                'python=3.7.0',
                                'tensorflow=1.8.0'
                            ]
                        }

    """
    _logger.info(
        "Validating the specified TensorFlow model by attempting to load it in a new TensorFlow"
        " graph...")
    _validate_saved_model(tf_saved_model_dir=tf_saved_model_dir,
                          tf_meta_graph_tags=tf_meta_graph_tags,
                          tf_signature_def_key=tf_signature_def_key)
    _logger.info("Validation succeeded!")

    if os.path.exists(path):
        raise MlflowException("Path '{}' already exists".format(path), DIRECTORY_NOT_EMPTY)
    os.makedirs(path)
    root_relative_path = _copy_file_or_tree(src=tf_saved_model_dir, dst=path, dst_dir=None)
    model_dir_subpath = "tfmodel"
    shutil.move(os.path.join(path, root_relative_path), os.path.join(path, model_dir_subpath))

    conda_env_subpath = "conda.yaml"
    if conda_env is None:
        conda_env = get_default_conda_env()
    elif not isinstance(conda_env, dict):
        with open(conda_env, "r") as f:
            conda_env = yaml.safe_load(f)
    with open(os.path.join(path, conda_env_subpath), "w") as f:
        yaml.safe_dump(conda_env, stream=f, default_flow_style=False)

    mlflow_model.add_flavor(FLAVOR_NAME, saved_model_dir=model_dir_subpath,
                            meta_graph_tags=tf_meta_graph_tags,
                            signature_def_key=tf_signature_def_key)
    pyfunc.add_to_model(mlflow_model, loader_module="mlflow.tensorflow", env=conda_env_subpath)
    mlflow_model.save(os.path.join(path, "MLmodel"))


def _validate_saved_model(tf_saved_model_dir, tf_meta_graph_tags, tf_signature_def_key):
    """
    Validate the TensorFlow SavedModel by attempting to load it in a new TensorFlow graph.
    If the loading process fails, any exceptions thrown by TensorFlow are propagated.
    """
    import tensorflow as tf

    validation_tf_graph = tf.Graph()
    validation_tf_sess = tf.Session(graph=validation_tf_graph)
    with validation_tf_graph.as_default():
        _load_tensorflow_saved_model(tf_saved_model_dir=tf_saved_model_dir,
                                     tf_sess=validation_tf_sess,
                                     tf_meta_graph_tags=tf_meta_graph_tags,
                                     tf_signature_def_key=tf_signature_def_key)


def load_model(model_uri, tf_sess):
    """
    Load an MLflow model that contains the TensorFlow flavor from the specified path.

    **This method must be called within a TensorFlow graph context.**

    :param model_uri: The location, in URI format, of the MLflow model, for example:

                      - ``/Users/me/path/to/local/model``
                      - ``relative/path/to/local/model``
                      - ``s3://my_bucket/path/to/model``
                      - ``runs:/<mlflow_run_id>/run-relative/path/to/model``

                      For more information about supported URI schemes, see the
                      `Artifacts Documentation <https://www.mlflow.org/docs/latest/tracking.html#
                      supported-artifact-stores>`_.

    :param tf_sess: The TensorFlow session in which to load the model.
    :return: A TensorFlow signature definition of type:
             ``tensorflow.core.protobuf.meta_graph_pb2.SignatureDef``. This defines the input and
             output tensors for model inference.

    >>> import mlflow.tensorflow
    >>> import tensorflow as tf
    >>> tf_graph = tf.Graph()
    >>> tf_sess = tf.Session(graph=tf_graph)
    >>> with tf_graph.as_default():
    >>>     signature_definition = mlflow.tensorflow.load_model(path="model_path", tf_sess=tf_sess)
    >>>     input_tensors = [tf_graph.get_tensor_by_name(input_signature.name)
    >>>                      for _, input_signature in signature_def.inputs.items()]
    >>>     output_tensors = [tf_graph.get_tensor_by_name(output_signature.name)
    >>>                       for _, output_signature in signature_def.outputs.items()]
    """
    local_model_path = _download_artifact_from_uri(artifact_uri=model_uri)
    tf_saved_model_dir, tf_meta_graph_tags, tf_signature_def_key =\
        _get_and_parse_flavor_configuration(model_path=local_model_path)
    return _load_tensorflow_saved_model(tf_saved_model_dir=tf_saved_model_dir, tf_sess=tf_sess,
                                        tf_meta_graph_tags=tf_meta_graph_tags,
                                        tf_signature_def_key=tf_signature_def_key)


def _load_tensorflow_saved_model(tf_saved_model_dir, tf_sess, tf_meta_graph_tags,
                                 tf_signature_def_key):
    """
    Load a specified TensorFlow model consisting of a TensorFlow meta graph and signature definition
    from a serialized TensorFlow ``SavedModel`` collection.

    :param tf_saved_model_dir: The local filesystem path or run-relative artifact path to the model.
    :param tf_sess: The TensorFlow session in which to load the metagraph.
    :param tf_meta_graph_tags: A list of tags identifying the model's metagraph within the
                               serialized ``SavedModel`` object. For more information, see the
                               ``tags`` parameter of the `tf.saved_model.builder.SavedModelBuilder
                               method <https://www.tensorflow.org/api_docs/python/tf/saved_model/
                               builder/SavedModelBuilder#add_meta_graph>`_.
    :param tf_signature_def_key: A string identifying the input/output signature associated with the
                                 model. This is a key within the serialized ``SavedModel``'s
                                 signature definition mapping. For more information, see the
                                 ``signature_def_map`` parameter of the
                                 ``tf.saved_model.builder.SavedModelBuilder`` method.
    :return: A TensorFlow signature definition of type:
             ``tensorflow.core.protobuf.meta_graph_pb2.SignatureDef``. This defines input and
             output tensors within the specified metagraph for inference.
    """
    import tensorflow as tf

    meta_graph_def = tf.saved_model.loader.load(
            sess=tf_sess,
            tags=tf_meta_graph_tags,
            export_dir=tf_saved_model_dir)
    if tf_signature_def_key not in meta_graph_def.signature_def:
        raise MlflowException("Could not find signature def key %s" % tf_signature_def_key)
    return meta_graph_def.signature_def[tf_signature_def_key]


def _get_and_parse_flavor_configuration(model_path):
    """
    :param path: Local filesystem path to the MLflow Model with the ``tensorflow`` flavor.
    :return: A triple containing the following elements:

             - ``tf_saved_model_dir``: The local filesystem path to the underlying TensorFlow
                                       SavedModel directory.
             - ``tf_meta_graph_tags``: A list of tags identifying the TensorFlow model's metagraph
                                       within the serialized ``SavedModel`` object.
             - ``tf_signature_def_key``: A string identifying the input/output signature associated
                                         with the model. This is a key within the serialized
                                         ``SavedModel``'s signature definition mapping.
    """
    flavor_conf = _get_flavor_configuration(model_path=model_path, flavor_name=FLAVOR_NAME)
    tf_saved_model_dir = os.path.join(model_path, flavor_conf['saved_model_dir'])
    tf_meta_graph_tags = flavor_conf['meta_graph_tags']
    tf_signature_def_key = flavor_conf['signature_def_key']
    return tf_saved_model_dir, tf_meta_graph_tags, tf_signature_def_key


def _load_pyfunc(path):
    """
    Load PyFunc implementation. Called by ``pyfunc.load_pyfunc``. This function loads an MLflow
    model with the TensorFlow flavor into a new TensorFlow graph and exposes it behind the
    ``pyfunc.predict`` interface.

    :param path: Local filesystem path to the MLflow Model with the ``tensorflow`` flavor.
    """
    import tensorflow as tf

    tf_saved_model_dir, tf_meta_graph_tags, tf_signature_def_key =\
        _get_and_parse_flavor_configuration(model_path=path)

    tf_graph = tf.Graph()
    tf_sess = tf.Session(graph=tf_graph)
    with tf_graph.as_default():
        signature_def = _load_tensorflow_saved_model(
            tf_saved_model_dir=tf_saved_model_dir, tf_sess=tf_sess,
            tf_meta_graph_tags=tf_meta_graph_tags, tf_signature_def_key=tf_signature_def_key)

    return _TFWrapper(tf_sess=tf_sess, tf_graph=tf_graph, signature_def=signature_def)


class _TFWrapper(object):
    """
    Wrapper class that exposes a TensorFlow model for inference via a ``predict`` function such that
    ``predict(data: pandas.DataFrame) -> pandas.DataFrame``.
    """
    def __init__(self, tf_sess, tf_graph, signature_def):
        """
        :param tf_sess: The TensorFlow session used to evaluate the model.
        :param tf_graph: The TensorFlow graph containing the model.
        :param signature_def: The TensorFlow signature definition used to transform input dataframes
                              into tensors and output vectors into dataframes.
        """
        self.tf_sess = tf_sess
        self.tf_graph = tf_graph
        # We assume that input keys in the signature definition correspond to input DataFrame column
        # names
        self.input_tensor_mapping = {
                tensor_column_name: tf_graph.get_tensor_by_name(tensor_info.name)
                for tensor_column_name, tensor_info in signature_def.inputs.items()
        }
        # We assume that output keys in the signature definition correspond to output DataFrame
        # column names
        self.output_tensors = {
                sigdef_output: tf_graph.get_tensor_by_name(tnsr_info.name)
                for sigdef_output, tnsr_info in signature_def.outputs.items()
        }

    def predict(self, df):
        with self.tf_graph.as_default():
            # Build the feed dict, mapping input tensors to DataFrame column values.
            feed_dict = {
                    self.input_tensor_mapping[tensor_column_name]: df[tensor_column_name].values
                    for tensor_column_name in self.input_tensor_mapping.keys()
            }
            raw_preds = self.tf_sess.run(self.output_tensors, feed_dict=feed_dict)
            pred_dict = {column_name: values.ravel() for column_name, values in raw_preds.items()}
            return pandas.DataFrame(data=pred_dict)
