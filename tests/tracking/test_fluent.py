import mock
import os
import random
import uuid

import pytest
import mock

import pytest

import mlflow
from mlflow.entities import Experiment, LifecycleStage, SourceType, Metric, Param, RunTag
from mlflow.exceptions import MlflowException
from mlflow.tracking.client import MlflowClient
import mlflow.tracking.fluent
from mlflow.tracking.fluent import start_run, _get_experiment_id, _get_experiment_id_from_env, \
    _EXPERIMENT_NAME_ENV_VAR, _EXPERIMENT_ID_ENV_VAR, _RUN_ID_ENV_VAR
from mlflow.utils.file_utils import TempDir
from mlflow.utils import mlflow_tags
from tests.projects.utils import tracking_uri_mock  # pylint: disable=unused-import


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


@pytest.fixture(autouse=True)
def reset_experiment_id():
    """
    This fixture resets the active experiment id *after* the execution of the test case in which
    its included
    """
    yield
    HelperEnv.set_values()
    mlflow.tracking.fluent._active_experiment_id = None


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


def test_get_experiment_id_with_no_active_experiments_returns_default_experiment_id():
    assert _get_experiment_id() == Experiment.DEFAULT_EXPERIMENT_ID


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
        notebook_id = exp_id + 73

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
        notebook_id = exp_id + 73
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
    mock_source_name = mock.Mock()
    source_name_patch = mock.patch(
        "mlflow.tracking.fluent._get_source_name", return_value=mock_source_name
    )
    mock_source_type = mock.Mock()
    source_type_patch = mock.patch(
        "mlflow.tracking.fluent._get_source_type", return_value=mock_source_type
    )
    mock_source_version = mock.Mock()
    source_version_patch = mock.patch(
        "mlflow.tracking.fluent._get_source_version", return_value=mock_source_version
    )

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    with experiment_id_patch, databricks_notebook_patch, source_name_patch, source_type_patch, \
            source_version_patch, create_run_patch:
        active_run = start_run()
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            run_name=None,
            source_name=mock_source_name,
            source_version=mock_source_version,
            entry_point_name=None,
            source_type=mock_source_type,
            parent_run_id=None
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_defaults_databricks_notebook(empty_active_run_stack):

    mock_experiment_id = mock.Mock()
    experiment_id_patch = mock.patch(
        "mlflow.tracking.fluent._get_experiment_id", return_value=mock_experiment_id
    )
    databricks_notebook_patch = mock.patch(
        "mlflow.tracking.fluent.is_in_databricks_notebook", return_value=True
    )
    mock_source_version = mock.Mock()
    source_version_patch = mock.patch(
        "mlflow.tracking.fluent._get_source_version", return_value=mock_source_version
    )
    mock_notebook_id = mock.Mock()
    notebook_id_patch = mock.patch(
        "mlflow.tracking.fluent.get_notebook_id", return_value=mock_notebook_id
    )
    mock_notebook_path = mock.Mock()
    notebook_path_patch = mock.patch(
        "mlflow.tracking.fluent.get_notebook_path", return_value=mock_notebook_path
    )
    mock_webapp_url = mock.Mock()
    webapp_url_patch = mock.patch(
        "mlflow.tracking.fluent.get_webapp_url", return_value=mock_webapp_url
    )

    expected_tags = {
        mlflow_tags.MLFLOW_DATABRICKS_NOTEBOOK_ID: mock_notebook_id,
        mlflow_tags.MLFLOW_DATABRICKS_NOTEBOOK_PATH: mock_notebook_path,
        mlflow_tags.MLFLOW_DATABRICKS_WEBAPP_URL: mock_webapp_url
    }

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    with experiment_id_patch, databricks_notebook_patch, source_version_patch, \
            notebook_id_patch, notebook_path_patch, webapp_url_patch, create_run_patch:
        active_run = start_run()
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            run_name=None,
            source_name=mock_notebook_path,
            source_version=mock_source_version,
            entry_point_name=None,
            source_type=SourceType.NOTEBOOK,
            tags=expected_tags,
            parent_run_id=None
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_overrides(empty_active_run_stack):

    databricks_notebook_patch = mock.patch(
        "mlflow.tracking.fluent.is_in_databricks_notebook", return_value=False
    )

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    mock_experiment_id = mock.Mock()
    mock_source_name = mock.Mock()
    mock_source_type = mock.Mock()
    mock_source_version = mock.Mock()
    mock_entry_point_name = mock.Mock()
    mock_run_name = mock.Mock()

    with databricks_notebook_patch, create_run_patch:
        active_run = start_run(
            experiment_id=mock_experiment_id, source_name=mock_source_name,
            source_version=mock_source_version, entry_point_name=mock_entry_point_name,
            source_type=mock_source_type, run_name=mock_run_name
        )
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            run_name=mock_run_name,
            source_name=mock_source_name,
            source_version=mock_source_version,
            entry_point_name=mock_entry_point_name,
            source_type=mock_source_type,
            parent_run_id=None
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_overrides_databricks_notebook(empty_active_run_stack):

    databricks_notebook_patch = mock.patch(
        "mlflow.tracking.fluent.is_in_databricks_notebook", return_value=True
    )
    mock_notebook_id = mock.Mock()
    notebook_id_patch = mock.patch(
        "mlflow.tracking.fluent.get_notebook_id", return_value=mock_notebook_id
    )
    mock_notebook_path = mock.Mock()
    notebook_path_patch = mock.patch(
        "mlflow.tracking.fluent.get_notebook_path", return_value=mock_notebook_path
    )
    mock_webapp_url = mock.Mock()
    webapp_url_patch = mock.patch(
        "mlflow.tracking.fluent.get_webapp_url", return_value=mock_webapp_url
    )

    expected_tags = {
        mlflow_tags.MLFLOW_DATABRICKS_NOTEBOOK_ID: mock_notebook_id,
        mlflow_tags.MLFLOW_DATABRICKS_NOTEBOOK_PATH: mock_notebook_path,
        mlflow_tags.MLFLOW_DATABRICKS_WEBAPP_URL: mock_webapp_url
    }

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    mock_experiment_id = mock.Mock()
    mock_source_version = mock.Mock()
    mock_entry_point_name = mock.Mock()
    mock_run_name = mock.Mock()

    with databricks_notebook_patch, create_run_patch, notebook_id_patch, notebook_path_patch, \
            webapp_url_patch:
        active_run = start_run(
            experiment_id=mock_experiment_id, source_name="ignored",
            source_version=mock_source_version, entry_point_name=mock_entry_point_name,
            source_type="ignored", run_name=mock_run_name
        )
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            run_name=mock_run_name,
            source_name=mock_notebook_path,
            source_version=mock_source_version,
            entry_point_name=mock_entry_point_name,
            source_type=SourceType.NOTEBOOK,
            tags=expected_tags,
            parent_run_id=None
        )
        assert is_from_run(active_run, MlflowClient.create_run.return_value)


def test_start_run_with_parent():

    parent_run = mock.Mock()
    active_run_stack_patch = mock.patch("mlflow.tracking.fluent._active_run_stack", [parent_run])

    databricks_notebook_patch = mock.patch(
        "mlflow.tracking.fluent.is_in_databricks_notebook", return_value=False
    )

    create_run_patch = mock.patch.object(MlflowClient, "create_run")

    mock_experiment_id = mock.Mock()
    mock_source_name = mock.Mock()
    mock_source_type = mock.Mock()
    mock_source_version = mock.Mock()
    mock_entry_point_name = mock.Mock()
    mock_run_name = mock.Mock()

    with databricks_notebook_patch, create_run_patch, active_run_stack_patch:
        active_run = start_run(
            experiment_id=mock_experiment_id, source_name=mock_source_name,
            source_version=mock_source_version, entry_point_name=mock_entry_point_name,
            source_type=mock_source_type, run_name=mock_run_name, nested=True
        )
        MlflowClient.create_run.assert_called_once_with(
            experiment_id=mock_experiment_id,
            run_name=mock_run_name,
            source_name=mock_source_name,
            source_version=mock_source_version,
            entry_point_name=mock_entry_point_name,
            source_type=mock_source_type,
            parent_run_id=parent_run.info.run_uuid
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


@mock.patch("time.time", lambda: -1)
@pytest.mark.parametrize("fluent_fn,fluent_kwargs,expected_store_kwargs", [
    (mlflow.log_metrics, {"metrics": {"a": 0.1}},
     {"run_id": "my-uuid", "metrics": [Metric("a", 0.1, -1)], "params": [], "tags": []}),
    (mlflow.log_params, {"params": {"b": "c"}},
     {"run_id": "my-uuid", "metrics": [], "params": [Param("b", "c")], "tags": []}),
    (mlflow.set_tags, {"tags": {"d": "e"}},
     {"run_id": "my-uuid", "metrics": [], "params": [], "tags": [RunTag("d", "e")]}),
])
def test_log_batch_apis_delegate_to_store(
        tracking_uri_mock,  # pylint: disable=unused-argument
        fluent_fn, fluent_kwargs, expected_store_kwargs):
    # Test that the log_metrics, log_params, set_tags fluent APIs call into to an AbstractStore
    # instance's log_batch implementation
    mock_run = mock.Mock()
    mock_run.info.lifecycle_stage = LifecycleStage.ACTIVE
    mock_run.info.run_uuid = "my-uuid"
    mock_store = mock.Mock()
    with mock.patch.object(mlflow.tracking.fluent, "_get_or_start_run", return_value=mock_run), \
            mock.patch.object(mlflow.tracking.utils, "_get_store", return_value=mock_store):
        fluent_fn(**fluent_kwargs)
        mlflow.tracking.fluent._get_or_start_run.assert_called_once()
        # Assert backing store log_batch was called with expected arguments
        _, store_call_kwargs, = mock_store.log_batch.call_args
        assert store_call_kwargs["run_id"] == expected_store_kwargs["run_id"]
        assert [dict(m) for m in store_call_kwargs["metrics"]] == \
               [dict(m) for m in expected_store_kwargs["metrics"]]
        assert [dict(p) for p in store_call_kwargs["params"]] == \
               [dict(p) for p in expected_store_kwargs["params"]]
        assert [dict(t) for t in store_call_kwargs["tags"]] == \
               [dict(t) for t in expected_store_kwargs["tags"]]


def test_log_batch_client_apis_delegate_to_store(
        tracking_uri_mock):  # pylint: disable=unused-argument
    # Test that the log_batch client API calls into an AbstractStore instance's log_batch
    # implementation
    mock_run = mock.Mock()
    mock_run.info.lifecycle_stage = LifecycleStage.ACTIVE
    mock_run.info.run_uuid = "my-uuid"
    mock_store = mock.Mock()
    with mock.patch.object(MlflowClient, "get_run", return_value=mock_run), \
         mock.patch.object(mlflow.tracking.utils, "_get_store", return_value=mock_store):
        metrics = [Metric(key="metric-key", value=3.2, timestamp=1)]
        params = [Param(key="param-key", value="param-val")]
        tags = [RunTag(key="tag-key", value="tag-val")]
        MlflowClient().log_batch("my-uuid", metrics=metrics, params=params, tags=tags)
        # Assert backing store log_batch was called with expected arguments
        _, client_call_kwargs, = mock_store.log_batch.call_args
        assert client_call_kwargs["run_id"] == "my-uuid"
        assert [dict(m) for m in client_call_kwargs["metrics"]] == \
               [dict(m) for m in metrics]
        assert [dict(p) for p in client_call_kwargs["params"]] == \
               [dict(p) for p in params]
        assert [dict(t) for t in client_call_kwargs["tags"]] == \
               [dict(t) for t in tags]
