from mlflow.tracking.context.abstract_context import RunContextProvider
from mlflow.utils import databricks_utils
from mlflow.entities import SourceType
from mlflow.utils.mlflow_tags import (
    MLFLOW_SOURCE_TYPE,
    MLFLOW_SOURCE_NAME,
    MLFLOW_DATABRICKS_WEBAPP_URL,
    MLFLOW_DATABRICKS_NOTEBOOK_PATH,
    MLFLOW_DATABRICKS_NOTEBOOK_ID
)


class DatabricksNotebookRunContext(RunContextProvider):
    def __init__(self):
        self._experiment_set = False
        self._first_run_created = False

    def in_context(self):
        return databricks_utils.is_in_databricks_notebook()

    def set_experiment_hook(self, experiment_id, experiment_name):
        self._experiment_set = True
        databricks_utils._display_html(
            "Set active experiment to {name}"
            "<a href='/#mlflow/experiments/{experiment_id}'>"
            "Click here"
            "</a>"
            "to view".format(name=experiment_name, experiment_id=experiment_id)
        )

    def start_run_hook(self, experiment_id, run_id):
        """
        Customizable hook that runs after a call to mlflow.start_run
        :param experiment_id: Experiment ID of the created run
        :param run_id: ID of the created run
        """
        if self._first_run_created:
            return
        self._first_run_created = True
        databricks_utils._display_html(
            "Created MLflow run under experiment {experiment_id}"
            "<a href='/#mlflow/experiments/{experiment_id}/runs/{run_id}'>"
            "Click here"
            "</a>"
            "to view".format(experiment_id=experiment_id, run_id=run_id)
        )



    def tags(self):
        notebook_id = databricks_utils.get_notebook_id()
        notebook_path = databricks_utils.get_notebook_path()
        webapp_url = databricks_utils.get_webapp_url()
        tags = {
            MLFLOW_SOURCE_NAME: notebook_path,
            MLFLOW_SOURCE_TYPE: SourceType.to_string(SourceType.NOTEBOOK)
        }
        if notebook_id is not None:
            tags[MLFLOW_DATABRICKS_NOTEBOOK_ID] = notebook_id
        if notebook_path is not None:
            tags[MLFLOW_DATABRICKS_NOTEBOOK_PATH] = notebook_path
        if webapp_url is not None:
            tags[MLFLOW_DATABRICKS_WEBAPP_URL] = webapp_url
        return tags
