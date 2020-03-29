import abc
from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import INTERNAL_ERROR


class BasePlugin(abc.ABC):
    """
    Abstract base class for deployment plugin developers. Every plugin for deployment
    must be inherited from this base class and should define the abstract methods.

    .. Note::
        In case of exceptions, plugins must raise an ``MlflowException`` instead of native
        python exceptions

    .. Note::
        MLFlow's deployment CLI parses all the extra arguments as key value argument.
        The CLI only take long options (options prefixed with double hyphen and has more
        than one character) and parse them as keyword arguments. Hence each argument is
        excepted to be a pair. For example: --host localhost. This also means that the
        parser will not parse any boolean flag options. A flag option is essentially returns
        a boolean based on the presence of the option/flag in the command and does not
        associate with a value. The `-v` option for verbose execution is a good example for
        flab option
    """

    @staticmethod
    def _validate_deployment_flavor(model_config, flavor, target_supported):
        """
        Checks that the specified flavor is a supported deployment flavor
        and is contained in the specified model. If one of these conditions
        is not met, an exception is thrown.
        """
        if flavor not in target_supported or flavor not in model_config.flavors:
            model_supported = tuple(model_config.flavors.keys())
            allowed = set(target_supported).intersection(model_supported)
            raise MlflowException("The specified flavor `{}` is not allowed. The flavor must"
                                  " be supported by the target ({}) and should be saved as "
                                  "part of ``Model`` ({}) Please use one of the allowed "
                                  "flavor: {}".format(flavor, target_supported,
                                                      model_supported, allowed),
                                  error_code=INTERNAL_ERROR)

    @abc.abstractmethod
    def create(self, model_uri, flavor=None, **kwargs):
        """
        This function will be called by :py:func:`deployments.create <mlflow.deployments.create>`.

        :param model_uri: The location, in URI format, of the MLflow model
        :param flavor: The name of the flavor of the model to use for deployment. if this is
                       ``None``, the plugin need to choose the flavor. In any case, it's better
                       to validate the flavor by calling `_validate_deployment_flavor` method
        :param kwargs: The keyword arguments either parsed from the CLI options or passed by the
                       user specifically using the python API
        :return: dict, A python dictionary with keys ``deployment_id`` and ``flavor``
        """
        pass

    @abc.abstractmethod
    def delete(self, deployment_id, **kwargs):
        """
        This function will be called by :py:func:`deployments.delete <mlflow.deployments.delete>`.

        :param deployment_id: The ID generated by the plugin while creating the deployment
        :param kwargs: The keyword arguments either parsed from the CLI options or passed by the
                       user specifically using the python API
        :return: None
        """
        pass

    @abc.abstractmethod
    def update(self, deployment_id, model_uri=None, flavor=None, **kwargs):
        """
        This function will be called by :py:func:`deployments.update <mlflow.deployments.update>`.

        :param deployment_id: The ID generated by the plugin while creating the deployment
        :param model_uri: The location, in URI format, of the MLflow model
        :param flavor: The name of the flavor of the model to use for deployment. if this is
                   ``None``, the plugin need to choose the flavor. In any case, it's better
                   to validate the flavor by calling `_validate_deployment_flavor` method
        :param kwargs: The keyword arguments either parsed from the CLI options or passed by the
                       user specifically using the python API
        :return: None
        """
        pass

    @abc.abstractmethod
    def list(self, **kwargs):
        """
        This function will be called by :py:func:`deployments.list <mlflow.deployments.list>`.
        It is the plugin's discretion whether to list only the deployments made by this plugin
        or all the deployments exist in the target. Although it is ideal and recommended to list
        only the one created by this plugin. The API might change to impose that strictly in
        the future.

        :param kwargs: The keyword arguments either parsed from the CLI options or passed by the
                       user specifically using the python API
        :return: list, A list of deployment IDs
        """
        pass

    @abc.abstractmethod
    def describe(self, deployment_id, **kwargs):
        """
        This function will be called by
        :py:func:`deployments.describe <mlflow.deployments.describe>`.

        :param deployment_id: The ID generated by the plugin while creating the deployment
        :param kwargs: The keyword arguments either parsed from the CLI options or passed by the
                       user specifically using the python API
        :return: dict, A dictionary with all the important descriptions
        """
        pass
