import os
import filecmp
import itertools
import subprocess
import tempfile
import time

import mock
import pytest

import mlflow
from mlflow.entities.run_status import RunStatus
from mlflow.projects import ExecutionException
from mlflow.store.file_store import FileStore
from mlflow import tracking
from mlflow.utils.file_utils import TempDir
from mlflow.utils import env

from tests.projects.utils import TEST_PROJECT_DIR, GIT_PROJECT_URI


def test_fetch_project():
    """ Test fetching a project to be run locally. """
    with TempDir() as tmp:
        dst_dir = tmp.path()
        mlflow.projects._fetch_project(uri=TEST_PROJECT_DIR, version=None, dst_dir=dst_dir,
                                       git_username=None, git_password=None)
        dir_comparison = filecmp.dircmp(TEST_PROJECT_DIR, dst_dir)
        assert len(dir_comparison.left_only) == 0
        assert len(dir_comparison.right_only) == 0
        assert len(dir_comparison.diff_files) == 0
        assert len(dir_comparison.funny_files) == 0
    # Passing `version` raises an exception for local projects
    with TempDir() as dst_dir:
        with pytest.raises(ExecutionException):
            mlflow.projects._fetch_project(uri=TEST_PROJECT_DIR, version="some-version",
                                           dst_dir=dst_dir, git_username=None, git_password=None)
    # Passing only one of git_username, git_password results in an error
    for username, password in [(None, "hi"), ("hi", None)]:
        with TempDir() as dst_dir:
            with pytest.raises(ExecutionException):
                mlflow.projects._fetch_project(uri=TEST_PROJECT_DIR, version="some-version",
                                               dst_dir=dst_dir, git_username=username,
                                               git_password=password)


def test_run_mode():
    """ Verify that we pick the right run helper given an execution mode """
    with TempDir() as tmp, mock.patch("mlflow.tracking.get_tracking_uri") as get_tracking_uri_mock:
        get_tracking_uri_mock.return_value = tmp.path()
        for local_mode in ["local", None]:
            with mock.patch("mlflow.projects._run_local") as run_local_mock:
                mlflow.projects.run(uri=TEST_PROJECT_DIR, mode=local_mode)
                assert run_local_mock.call_count == 1
        with mock.patch("mlflow.projects._run_databricks") as run_databricks_mock:
            mlflow.projects.run(uri=TEST_PROJECT_DIR, mode="databricks")
            assert run_databricks_mock.call_count == 1
        with pytest.raises(ExecutionException):
            mlflow.projects.run(uri=TEST_PROJECT_DIR, mode="some unsupported mode")


def test_use_conda():
    with TempDir() as tmp, mock.patch("mlflow.tracking.get_tracking_uri") as get_tracking_uri_mock:
        get_tracking_uri_mock.return_value = tmp.path()
        # Verify we throw an exception when conda is unavailable
        old_path = os.environ["PATH"]
        env.unset_variable("PATH")
        try:
            with pytest.raises(ExecutionException):
                mlflow.projects.run(TEST_PROJECT_DIR, use_conda=True)
        finally:
            os.environ["PATH"] = old_path


def test_run():
    start_run_opts = [True, False]
    mlflow_run_opts = [True, False]
    for use_start_run, use_mlflow_run in itertools.product(start_run_opts, mlflow_run_opts):
        with TempDir() as tmp, mock.patch("mlflow.tracking.get_tracking_uri")\
                as get_tracking_uri_mock:
            tmp_dir = tmp.path()
            get_tracking_uri_mock.return_value = tmp_dir
            if use_mlflow_run:
                run_uuid = mlflow.projects.run(
                    TEST_PROJECT_DIR, entry_point="test_tracking",
                    parameters={"use_start_run": use_start_run},
                    use_conda=False, experiment_id=0)
            else:
                cmd = ["python", os.path.join(TEST_PROJECT_DIR, "tracking_test.py"),
                       str(use_start_run)]
                subprocess.call(cmd)
                run_uuid = os.listdir(os.path.join(tmp_dir, "mlruns", "0"))[0]
            store = FileStore(tmp_dir)
            run_infos = store.list_run_infos(experiment_id=0)
            assert len(run_infos) == 1
            store_run_uuid = run_infos[0].run_uuid
            assert run_uuid == store_run_uuid
            run = store.get_run(run_uuid)
            expected_params = {"use_start_run": str(use_start_run)}
            assert run.info.status == RunStatus.FINISHED
            assert len(run.data.params) == len(expected_params)
            for param in run.data.params:
                assert param.value == expected_params[param.key]
            expected_metrics = {"some_key": 3}
            for metric in run.data.metrics:
                assert metric.value == expected_metrics[metric.key]


def test_run_exception():
    """ Test that we raise an exception when running a project fails in blocking mode """
    with TempDir() as tmp, mock.patch("mlflow.tracking.get_tracking_uri") as get_tracking_uri_mock:
        tmp_dir = tmp.path()
        get_tracking_uri_mock.return_value = tmp_dir
        # Run with bad parameters, expect an exception
        with pytest.raises(ExecutionException):
            mlflow.projects.run(
                TEST_PROJECT_DIR, entry_point="cat",
                parameters={"line_count": os.path.join(tmp_dir, "some/nonexistent/path")},
                use_conda=False, experiment_id=0)


def test_run_async():
    with TempDir() as tmp, mock.patch("mlflow.tracking.get_tracking_uri") as get_tracking_uri_mock:
        tmp_dir = tmp.path()
        get_tracking_uri_mock.return_value = tmp_dir
        run_uuid0 = mlflow.projects.run(
            TEST_PROJECT_DIR, entry_point="sleep", parameters={"duration": 1},
            use_conda=False, experiment_id=0, block=False)
        assert tracking.get_run(run_uuid0).info.status == RunStatus.RUNNING
        time.sleep(2)
        assert tracking.get_run(run_uuid0).info.status == RunStatus.FINISHED
        run_uuid1 = mlflow.projects.run(
            TEST_PROJECT_DIR, entry_point="sleep", parameters={"duration": -1, "invalid-param": 30},
            use_conda=False, experiment_id=0, block=False)
        time.sleep(1)
        assert tracking.get_run(run_uuid1).info.status == RunStatus.FAILED


def test_get_work_dir():
    """ Test that we correctly determine the working directory to use when running a project. """
    for use_temp_cwd, uri in [(True, TEST_PROJECT_DIR), (False, GIT_PROJECT_URI)]:
        work_dir = mlflow.projects._get_work_dir(uri=uri, use_temp_cwd=use_temp_cwd)
        assert work_dir != uri
        assert os.path.exists(work_dir)
    for use_temp_cwd, uri in [(None, TEST_PROJECT_DIR), (False, TEST_PROJECT_DIR)]:
        assert mlflow.projects._get_work_dir(uri=uri, use_temp_cwd=use_temp_cwd) ==\
               os.path.abspath(TEST_PROJECT_DIR)


def test_storage_dir():
    """
    Test that we correctly handle the `storage_dir` argument, which specifies where to download
    distributed artifacts passed to arguments of type `path`.
    """
    with TempDir() as tmp_dir:
        assert os.path.dirname(mlflow.projects._get_storage_dir(tmp_dir.path())) == tmp_dir.path()
    assert os.path.dirname(mlflow.projects._get_storage_dir(None)) == tempfile.gettempdir()
