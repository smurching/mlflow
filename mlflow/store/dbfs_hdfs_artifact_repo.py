import os
import json

from mlflow.entities import FileInfo
from mlflow.exceptions import MlflowException
from mlflow.store.artifact_repo import ArtifactRepository
from mlflow.store.rest_store import RestStore
from mlflow.tracking import utils
from mlflow.utils.rest_utils import http_request, http_request_safe, RESOURCE_DOES_NOT_EXIST
from mlflow.utils.string_utils import strip_prefix
from mlflow.spark import _HadoopFileSystem

LIST_API_ENDPOINT = '/api/2.0/dbfs/list'
GET_STATUS_ENDPOINT = '/api/2.0/dbfs/get-status'
DOWNLOAD_CHUNK_SIZE = 1024


class DbfsHdfsArtifactRepository(ArtifactRepository):
    """
    Stores artifacts on DBFS, leveraging HDFS APIs to read/write from DBFS.

    This repository is used with URIs of the form ``dbfs:/<path>``.
    """

    def __init__(self, artifact_uri):
        cleaned_artifact_uri = artifact_uri.rstrip('/')
        super(DbfsHdfsArtifactRepository, self).__init__(cleaned_artifact_uri)
        # NOTE: if we ever need to support databricks profiles different from that set for
        #  tracking, we could pass in the databricks profile name into this class.
        self.get_host_creds = _get_host_creds_from_default_store()
        if not cleaned_artifact_uri.startswith('dbfs:/'):
            raise MlflowException('DbfsArtifactRepository URI must start with dbfs:/')

    def _get_dbfs_path(self, artifact_path):
        return '%s/%s' % (self.artifact_uri, strip_prefix(artifact_path, '/'))

    def get_path_module(self):
        import posixpath
        return posixpath

    def log_artifact(self, local_file, artifact_path=None):
        basename = self.get_path_module().basename(local_file)
        if artifact_path:
            dst_path = self._get_dbfs_path(
                self.get_path_module().join(artifact_path, basename))
        else:
            dst_path = self._get_dbfs_path(basename)
        _HadoopFileSystem.copy_from_local_file(src=local_file, dst=dst_path)

    def log_artifacts(self, local_dir, artifact_path=None):
        artifact_path = artifact_path or ''
        for (dirpath, _, filenames) in os.walk(local_dir):
            artifact_subdir = artifact_path
            if dirpath != local_dir:
                rel_path = self.get_path_module().relpath(dirpath, local_dir)
                artifact_subdir = self.get_path_module().join(artifact_path, rel_path)
            for name in filenames:
                file_path = self.get_path_module().join(dirpath, name)
                self.log_artifact(file_path, artifact_subdir)

    def list_artifacts(self, path=None):
        if path:
            dbfs_dir = self._get_dbfs_path(path)
        else:
            dbfs_dir = self._get_dbfs_path('')
        dbfs_files = _HadoopFileSystem.listdir(dbfs_dir)
        artifact_prefix = strip_prefix(self.artifact_uri, 'dbfs:')
        infos = []
        for dbfs_file in dbfs_files:
            stripped_path = strip_prefix(dbfs_file['path'], artifact_prefix + '/')
            # If `path` is a file, the DBFS list API returns a single list element with the
            # same name as `path`. The list_artifacts API expects us to return an empty list in this
            # case, so we do so here.
            if stripped_path == path:
                return []
            is_dir = dbfs_file['is_dir']
            artifact_size = None if is_dir else dbfs_file['file_size']
            infos.append(FileInfo(stripped_path, is_dir, artifact_size))
        return sorted(infos, key=lambda f: f.path)

    def _download_file(self, remote_file_path, local_path):
        src_path = self._get_dbfs_path(remote_file_path)
        _HadoopFileSystem.copy_to_local_file(src=src_path, dst=local_path)


def _get_host_creds_from_default_store():
    store = utils._get_store()
    if not isinstance(store, RestStore):
        raise MlflowException('Failed to get credentials for DBFS; they are read from the ' +
                              'Databricks CLI credentials or MLFLOW_TRACKING* environment ' +
                              'variables.')
    return store.get_host_creds
