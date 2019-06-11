import os
import posixpath

from mlflow.exceptions import MlflowException
from mlflow.store.artifact_repo import ArtifactRepository
from mlflow.store.rest_store import RestStore
from mlflow.tracking import utils
from mlflow.utils.string_utils import strip_prefix
from mlflow.utils.hadoop_filesystem import _HadoopFileSystem
from mlflow.utils.file_utils import relative_path_to_artifact_path


class DbfsFuseArtifactRepository(ArtifactRepository):
    """
    Stores artifacts on DBFS, leveraging HDFS APIs to read/write from DBFS.

    This repository is used with URIs of the form ``dbfs:/<path>``.
    """

    def __init__(self, artifact_uri):
        cleaned_artifact_uri = artifact_uri.rstrip('/')
        super(DbfsFuseArtifactRepository, self).__init__(cleaned_artifact_uri)
        # NOTE: if we ever need to support databricks profiles different from that set for
        #  tracking, we could pass in the databricks profile name into this class.
        self.get_host_creds = _get_host_creds_from_default_store()
        if not cleaned_artifact_uri.startswith('dbfs:/'):
            raise MlflowException('DbfsArtifactRepository URI must start with dbfs:/')

    def _get_dbfs_path(self, artifact_path):
        return '%s/%s' % (self.artifact_uri, strip_prefix(artifact_path, '/'))

    def log_artifact(self, local_file, artifact_path=None):
        basename = os.path.basename(local_file)
        if artifact_path:
            dst_path = self._get_dbfs_path(
                posixpath.join(artifact_path, basename))
        else:
            dst_path = self._get_dbfs_path(basename)
        _HadoopFileSystem.copy_from_local_file(src=local_file, dst=dst_path, remove_src=False)

    def log_artifacts(self, local_dir, artifact_path=None):
        artifact_path = artifact_path or ''
        for (dirpath, _, filenames) in os.walk(local_dir):
            artifact_subdir = artifact_path
            if dirpath != local_dir:
                rel_path = os.path.relpath(dirpath, local_dir)
                rel_path = relative_path_to_artifact_path(rel_path)
                artifact_subdir = posixpath.join(artifact_path, rel_path)
            for name in filenames:
                file_path = os.path.join(dirpath, name)
                self.log_artifact(file_path, artifact_subdir)

    def list_artifacts(self, path=None):
        if path:
            dbfs_dir = self._get_dbfs_path(path)
        else:
            dbfs_dir = self._get_dbfs_path('')
        list_res = _HadoopFileSystem.listdir(dbfs_dir)
        # If the passed-in path is a file, return an empty list.
        for info in list_res:
            if info.path == path and not info.is_dir:
                return []
        return sorted(list_res, key=lambda f: f.path)

    def _download_file(self, remote_file_path, local_path):
        src_path = self._get_dbfs_path(remote_file_path)
        _HadoopFileSystem.copy_to_local_file(src=src_path, dst=local_path, remove_src=False)


def _get_host_creds_from_default_store():
    store = utils._get_store()
    if not isinstance(store, RestStore):
        raise MlflowException('Failed to get credentials for DBFS; they are read from the ' +
                              'Databricks CLI credentials or MLFLOW_TRACKING* environment ' +
                              'variables.')
    return store.get_host_creds
