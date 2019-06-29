import os
import random
import uuid

import pytest
import mock
import numpy as np
import pandas as pd
from six.moves import reload_module as reload

import mlflow
from mlflow.entities import LifecycleStage, SourceType, Run, RunInfo, RunData, RunStatus, Metric, \
    Param, RunTag, ViewType
from mlflow.exceptions import MlflowException
from mlflow.store import SEARCH_MAX_RESULTS_PANDAS
from mlflow.tracking.client import MlflowClient
import mlflow.tracking.fluent
import mlflow.tracking.context
from mlflow.tracking.fluent import start_run, _get_experiment_id, _get_experiment_id_from_env, \
    search_runs, _EXPERIMENT_NAME_ENV_VAR, _EXPERIMENT_ID_ENV_VAR, _RUN_ID_ENV_VAR
from mlflow.utils.file_utils import TempDir
from mlflow.utils import mlflow_tags


class HelperEnv:
    @classmethod
    def assert_values(cls, exp_id, name):
        assert os.environ.get(_EXPERIMENT_NAME_ENV_VAR) == name
        assert os.environ.get(_EXPERIMENT_ID_ENV_VAR) == exp_id

    @classmethod
    def set_values(cls, id=None, name=None):
        if id:
            os.environ[_EXPERIMENT_ID_ENV_VAR] = str(id)
        elif os.environ.get(_EXPERIMENT_ID_ENV_VAR):
            del os.environ[_EXPERIMENT_ID_ENV_VAR]

        if name:
            os.environ[_EXPERIMENT_NAME_ENV_VAR] = str(name)
        elif os.environ.get(_EXPERIMENT_NAME_ENV_VAR):
            del os.environ[_EXPERIMENT_NAME_ENV_VAR]


def create_run(run_id="", exp_id="", uid="", start=0, metrics=None, params=None, tags=None,
               status=RunStatus.FINISHED, a_uri=None):
    return Run(
        RunInfo(
            run_uuid=run_id,
            run_id=run_id,
            experiment_id=exp_id,
            user_id=uid,
            status=status,
            start_time=start,
            end_time=0,
            lifecycle_stage=LifecycleStage.ACTIVE,
            artifact_uri=a_uri
        ), RunData(
            metrics=metrics,
            params=params,
            tags=tags
        ))


@pytest.fixture(autouse=True)
def reset_experiment_id():
    """
    This fixture resets the active experiment id *after* the execution of the test case in which
    its included
    """
    yield
    HelperEnv.set_values()
    mlflow.tracking.fluent._active_experiment_id = None


@pytest.fixture(autouse=True)
def reload_context_module():
    """Reload the context module to clear caches."""
    reload(mlflow.tracking.context)


def test_get_experiment_id_from_env():
    # When no env variables are set
    HelperEnv.assert_values(None, None)
    assert _get_experiment_id_from_env() is None

    # set only ID
    random_id = random.randint(1, 1e6)
    HelperEnv.set_values(id=random_id)
    HelperEnv.assert_values(str(random_id), None)
    assert _get_experiment_id_from_env() == str(random_id)

    # set only name
    with TempDir(chdr=True):
        name = "random experiment %d" % random.randint(1, 1e6)
        exp_id = mlflow.create_experiment(name)
        assert exp_id is not None
        HelperEnv.set_values(name=name)
        HelperEnv.assert_values(None, name)
        assert _get_experiment_id_from_env() == exp_id

    # set both: assert that name variable takes precedence
    with TempDir(chdr=True):
        name = "random experiment %d" % random.randint(1, 1e6)
        exp_id = mlflow.create_experiment(name)
        assert exp_id is not None
        random_id = random.randint(1, 1e6)
        HelperEnv.set_values(name=name, id=random_id)
        HelperEnv.assert_values(str(random_id), name)
        assert _get_experiment_id_from_env() == exp_id


def test_get_experiment_id_with_active_experiment_returns_active_experiment_id():
    # Create a new experiment and set that as active experiment
    with TempDir(chdr=True):
        name = "Random experiment %d" % random.randint(1, 1e6)
        exp_id = mlflow.create_experiment(name)
        assert exp_id is not None
        mlflow.set_experiment(name)
        assert _get_experiment_id() == exp_id


def test_get_experiment_id_with_no_active_experiments_returns_zero():
    assert _get_experiment_id() == "0"


def test_get_experiment_id_in_databricks_detects_notebook_id_by_default():
    notebook_id = 768

    with mock.patch("mlflow.tracking.fluent.is_in_databricks_notebook") as notebook_detection_mock,\
            mock.patch("mlflow.tracking.fluent.get_notebook_id") as notebook_id_mock:
        notebook_detection_mock.return_value = True
        notebook_id_mock.return_value = notebook_id
        assert _get_experiment_id() == notebook_id


def test_get_experiment_id_in_databricks_with_active_experiment_returns_active_experiment_id():
    with TempDir(chdr=True):
        exp_name = "random experiment %d" % random.randint(1, 1e6)
        exp_id = mlflow.create_experiment(exp_name)
        mlflow.set_experiment(exp_name)
        notebook_id = str(int(exp_id) + 73)

    with mock.patch("mlflow.tracking.fluent.is_in_databricks_notebook") as notebook_detection_mock,\
            mock.patch("mlflow.tracking.fluent.get_notebook_id") as notebook_id_mock:
        notebook_detection_mock.return_value = True
        notebook_id_mock.return_value = notebook_id

        assert _get_experiment_id() != notebook_id
        assert _get_experiment_id() == exp_id


def test_get_experiment_id_in_databricks_with_experiment_defined_in_env_returns_env_experiment_id():
    with TempDir(chdr=True):
        exp_name = "random experiment %d" % random.randint(1, 1e6)
        exp_id = mlflow.create_experiment(exp_name)
        notebook_id = str(int(exp_id) + 73)
        HelperEnv.set_values(id=exp_id)

    with mock.patch("mlflow.tracking.fluent.is_in_databricks_notebook") as notebook_detection_mock,\
            mock.patch("mlflow.tracking.fluent.get_notebook_id") as notebook_id_mock:
        notebook_detection_mock.side_effect = lambda *args, **kwargs: True
        notebook_id_mock.side_effect = lambda *args, **kwargs: notebook_id

        assert _get_experiment_id() != notebook_id
        assert _get_experiment_id() == exp_id


@pytest.fixture
def empty_active_run_stack():
    with mock.patch("mlflow.tracking.fluent._active_run_stack", []):
        yield


def is_from_run(active_run, run):
    return active_run.info == run.info and active_run.data == run.data


def test_start_run_defaults(empty_active_run_stack):

    mock_experiment_id = mock.Mock()
    experiment_id_patch = mock.patch(
        "mlflow.tracking.fluent._get_experiment_id", return_value=mock_experiment_id
    )
    databricks_notebook_patch = mock.patch(
        "mlflow.tracking.fluent.is_in_databricks_notebook", return_value=False
    )
    mock_user = mock.Mock()
    user_patch = mock.patch(
        "mlflow.tracking.context._get_user", return_value=mock_user
    )
    mock_source_name = mock.Mock()
    source_name_patch = mock.patch(
        "mlflow.tracking.context._get_source_name", return_value=mock_source_name
    )
    source_type_patch = mock.patch(
        "mlflow.tracking.context._get_source_type", return_value=SourceType.NOTEBOOK
    )
    mock_source_version = mock.Mock()
    source_version_patch = mock.patch(
        "mlflow.tracking.context._get_source_version", return_value=mock_source_version
    )

    expected_tags = {
        mlflow_tags.MLFLOW_USER: mock_user,
        mlflow_tags.MLFLOW_SOURCE_NAME: mock_source_name,
        mlflow_tags.MLFLOW_SOURCE_TYPE: SourceType.to_string(SourceType.NOTEBOOK),
        mlflow_tags.MLFLOW_GIT_COMMIT: mock_source_version
    }

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    with experiment_id_patch, databricks_notebook_patch, user_patch, source_name_patch, \
            source_type_patch, source_version_patch, create_run_patch:
        active_run = start_run()
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            tags=expected_tags
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_defaults_databricks_notebook(empty_active_run_stack):

    mock_experiment_id = mock.Mock()
    experiment_id_patch = mock.patch(
        "mlflow.tracking.fluent._get_experiment_id", return_value=mock_experiment_id
    )
    databricks_notebook_patch = mock.patch(
        "mlflow.utils.databricks_utils.is_in_databricks_notebook", return_value=True
    )
    mock_user = mock.Mock()
    user_patch = mock.patch(
        "mlflow.tracking.context._get_user", return_value=mock_user
    )
    mock_source_version = mock.Mock()
    source_version_patch = mock.patch(
        "mlflow.tracking.context._get_source_version", return_value=mock_source_version
    )
    mock_notebook_id = mock.Mock()
    notebook_id_patch = mock.patch(
        "mlflow.utils.databricks_utils.get_notebook_id", return_value=mock_notebook_id
    )
    mock_notebook_path = mock.Mock()
    notebook_path_patch = mock.patch(
        "mlflow.utils.databricks_utils.get_notebook_path", return_value=mock_notebook_path
    )
    mock_webapp_url = mock.Mock()
    webapp_url_patch = mock.patch(
        "mlflow.utils.databricks_utils.get_webapp_url", return_value=mock_webapp_url
    )

    expected_tags = {
        mlflow_tags.MLFLOW_USER: mock_user,
        mlflow_tags.MLFLOW_SOURCE_NAME: mock_notebook_path,
        mlflow_tags.MLFLOW_SOURCE_TYPE: SourceType.to_string(SourceType.NOTEBOOK),
        mlflow_tags.MLFLOW_GIT_COMMIT: mock_source_version,
        mlflow_tags.MLFLOW_DATABRICKS_NOTEBOOK_ID: mock_notebook_id,
        mlflow_tags.MLFLOW_DATABRICKS_NOTEBOOK_PATH: mock_notebook_path,
        mlflow_tags.MLFLOW_DATABRICKS_WEBAPP_URL: mock_webapp_url
    }

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    with experiment_id_patch, databricks_notebook_patch, user_patch, source_version_patch, \
            notebook_id_patch, notebook_path_patch, webapp_url_patch, create_run_patch:
        active_run = start_run()
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            tags=expected_tags
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_with_parent():

    parent_run = mock.Mock()
    mock_experiment_id = mock.Mock()
    mock_source_name = mock.Mock()
    mock_run_name = mock.Mock()

    active_run_stack_patch = mock.patch("mlflow.tracking.fluent._active_run_stack", [parent_run])

    databricks_notebook_patch = mock.patch(
        "mlflow.tracking.fluent.is_in_databricks_notebook", return_value=False
    )
    mock_user = mock.Mock()
    user_patch = mock.patch(
        "mlflow.tracking.context._get_user", return_value=mock_user
    )
    source_name_patch = mock.patch(
        "mlflow.tracking.context._get_source_name", return_value=mock_source_name
    )

    expected_tags = {
        mlflow_tags.MLFLOW_USER: mock_user,
        mlflow_tags.MLFLOW_SOURCE_NAME: mock_source_name,
        mlflow_tags.MLFLOW_SOURCE_TYPE: SourceType.to_string(SourceType.LOCAL),
        mlflow_tags.MLFLOW_PARENT_RUN_ID: parent_run.info.run_id
    }

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    with databricks_notebook_patch, active_run_stack_patch, create_run_patch, user_patch, \
            source_name_patch:
        active_run = start_run(
            experiment_id=mock_experiment_id, nested=True
        )
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            tags=expected_tags
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_with_parent_non_nested():
    with mock.patch("mlflow.tracking.fluent._active_run_stack", [mock.Mock()]):
        with pytest.raises(Exception):
            start_run()


def test_start_run_existing_run(empty_active_run_stack):
    mock_run = mock.Mock()
    mock_run.info.lifecycle_stage = LifecycleStage.ACTIVE

    run_id = uuid.uuid4().hex

    with mock.patch.object(MlflowClient, "get_run", return_value=mock_run):
        active_run = start_run(run_id)

        assert is_from_run(active_run, mock_run)
        MlflowClient.get_run.assert_called_once_with(run_id)


def test_start_run_existing_run_from_environment(empty_active_run_stack):
    mock_run = mock.Mock()
    mock_run.info.lifecycle_stage = LifecycleStage.ACTIVE

    run_id = uuid.uuid4().hex
    env_patch = mock.patch.dict("os.environ", {_RUN_ID_ENV_VAR: run_id})

    with env_patch, mock.patch.object(MlflowClient, "get_run", return_value=mock_run):
        active_run = start_run()

        assert is_from_run(active_run, mock_run)
        MlflowClient.get_run.assert_called_once_with(run_id)


def test_start_run_existing_run_deleted(empty_active_run_stack):
    mock_run = mock.Mock()
    mock_run.info.lifecycle_stage = LifecycleStage.DELETED

    run_id = uuid.uuid4().hex

    with mock.patch.object(MlflowClient, "get_run", return_value=mock_run):
        with pytest.raises(MlflowException):
            start_run(run_id)


def test_search_runs_attributes():
    runs = [create_run(status=RunStatus.FINISHED, a_uri="dbfs:/test", run_id='abc', exp_id="123"),
            create_run(status=RunStatus.SCHEDULED, a_uri="dbfs:/test2", run_id='def', exp_id="321")]
    with mock.patch.object(MlflowClient, "search_runs", return_value=runs):
        pdf = search_runs()
        data = {'status': [RunStatus.FINISHED, RunStatus.SCHEDULED],
                'artifact_uri': ["dbfs:/test", "dbfs:/test2"],
                'run_id': ['abc', 'def'],
                'experiment_id': ["123", "321"]}
        expected_df = pd.DataFrame(data)
        pd.testing.assert_frame_equal(pdf, expected_df, check_like=True, check_frame_type=False)


def test_search_runs_data():
    runs = [
        create_run(
            metrics=[Metric("mse", 0.2, 0, 0)],
            params=[Param("param", "value")],
            tags=[RunTag("tag", "value")]),
        create_run(
            metrics=[Metric("mse", 0.6, 0, 0), Metric("loss", 1.2, 0, 5)],
            params=[Param("param2", "val"), Param("k", "v")],
            tags=[RunTag("tag2", "v2")])]
    with mock.patch.object(MlflowClient, "search_runs", return_value=runs):
        pdf = search_runs()
        data = {
            'status': [RunStatus.FINISHED]*2,
            'artifact_uri': [None]*2,
            'run_id': ['']*2,
            'experiment_id': [""]*2,
            'metrics.mse': [0.2, 0.6],
            'metrics.loss': [np.nan, 1.2],
            'params.param': ["value", None],
            'params.param2': [None, "val"],
            'params.k': [None, "v"],
            'tags.tag': ["value", None],
            'tags.tag2': [None, "v2"]}
        expected_df = pd.DataFrame(data)
        pd.testing.assert_frame_equal(pdf, expected_df, check_like=True, check_frame_type=False)


def test_search_runs_no_arguments():
    # When no experiment ID is specified,
    # it should try to get the implicit one or create a new experiment
    mock_experiment_id = mock.Mock()
    experiment_id_patch = mock.patch(
        "mlflow.tracking.fluent._get_experiment_id", return_value=mock_experiment_id
    )
    with experiment_id_patch, mock.patch.object(MlflowClient, "search_runs", return_value=[]):
        pdf = search_runs()
        MlflowClient.search_runs.assert_called_once_with(
            mock_experiment_id, '', ViewType.ACTIVE_ONLY, SEARCH_MAX_RESULTS_PANDAS, None
        )


def test_search_runs_with_arguments():
    mock_experiment_ids = mock.Mock()
    mock_filter_string = mock.Mock()
    mock_view_type = mock.Mock()
    mock_max_results = mock.Mock()
    mock_order_by = mock.Mock()
    with mock.patch.object(MlflowClient, "search_runs", return_value=[]):
        pdf = search_runs(mock_experiment_ids, mock_filter_string, mock_view_type,
                          mock_max_results, mock_order_by)
        MlflowClient.search_runs.assert_called_once_with(
            mock_experiment_ids,
            mock_filter_string,
            mock_view_type,
            mock_max_results,
            mock_order_by
        )
