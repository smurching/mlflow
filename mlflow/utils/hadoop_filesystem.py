import os

from mlflow.exceptions import MlflowException
from mlflow.entities import FileInfo
from pyspark import SparkContext


class _HadoopFileSystem:
    """
    Interface to org.apache.hadoop.fs.FileSystem.

    Spark ML models expect to read from and write to Hadoop FileSystem when running on a cluster.
    Since MLflow works on local directories, we need this interface to copy the files between
    the current DFS and local dir.
    """

    def __init__(self):
        raise Exception("This class should not be instantiated")

    _filesystem = None
    _conf = None

    @classmethod
    def _jvm(cls):
        if not SparkContext._gateway:
            raise MlflowException(
                "No JVM associated with a SparkContext was found. This error should not arise "
                "during normal operation; please file a GitHub issue at "
                "https://github.com/mlflow/mlflow/issues")
        return SparkContext._gateway.jvm

    @classmethod
    def _fs(cls):
        if not cls._filesystem:
            cls._filesystem = cls._jvm().org.apache.hadoop.fs.FileSystem.get(cls._conf())
        return cls._filesystem

    @classmethod
    def _conf(cls):
        sc = SparkContext.getOrCreate()
        return sc._jsc.hadoopConfiguration()

    @classmethod
    def _local_path(cls, path):
        return cls._jvm().org.apache.hadoop.fs.Path(os.path.abspath(path))

    @classmethod
    def _remote_path(cls, path):
        return cls._jvm().org.apache.hadoop.fs.Path(path)

    @classmethod
    def listdir(cls, directory):
        """
        Return a list of FileInfos describing files or directories within the passed in
        directory.
        """
        # Call the https://hadoop.apache.org/docs/current/api/org/apache/hadoop/
        # fs/FileSystem.html#listStatus(org.apache.hadoop.fs.Path) API.
        # TODO add slash to end of dirs to indicate that they're dirs and not files? I don't think
        # other artifact repos do this
        return [FileInfo(path=file_status.getPath().getName(), is_dir=file_status.isDirectory(),
                         file_size=file_status.getLen())
                for file_status in cls._fs().listStatus(cls._remote_path(directory))]

    @classmethod
    def copy_to_local_file(cls, src, dst, remove_src):
        cls._fs().copyToLocalFile(remove_src, cls._remote_path(src), cls._local_path(dst))

    @classmethod
    def copy_from_local_file(cls, src, dst, remove_src):
        cls._fs().copyFromLocalFile(remove_src, cls._local_path(src), cls._remote_path(dst))

    @classmethod
    def qualified_local_path(cls, path):
        return cls._fs().makeQualified(cls._local_path(path)).toString()

    @classmethod
    def maybe_copy_from_local_file(cls, src, dst):
        """
        Conditionally copy the file to the Hadoop DFS.
        The file is copied iff the configuration has distributed filesystem.

        :return: If copied, return new target location, otherwise return (absolute) source path.
        """
        local_path = cls._local_path(src)
        qualified_local_path = cls._fs().makeQualified(local_path).toString()
        if qualified_local_path == "file:" + local_path.toString():
            return local_path.toString()
        cls.copy_from_local_file(src, dst, remove_src=False)
        return dst

    @classmethod
    def delete(cls, path):
        cls._fs().delete(cls._remote_path(path), True)


def is_hdfs_available():
    """Returns true if HDFS utilities are available via PySpark, false otherwise"""
    try:
        _HadoopFileSystem._jvm()
        return True
    except MlflowException:
        return False
