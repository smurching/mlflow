package org.mlflow.artifacts;

import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.nio.file.Paths;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

import org.apache.hadoop.fs.Path;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.LocatedFileStatus;
import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.RemoteIterator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.mlflow.api.proto.Service;
import org.mlflow.tracking.MlflowClientException;


public class DbfsHdfsArtifactRepository implements ArtifactRepository {
    private static final Logger logger = LoggerFactory.getLogger(DbfsHdfsArtifactRepository.class);
    private FileSystem fs;
    private String artifactUri;

    private String getUnexpectedErrorSuffix(String msg) {
        return msg + ". This error should not arise during normal operation; please file a " +
                "GitHub issue at https://github.com/mlflow/mlflow/issues";
    }

    public DbfsHdfsArtifactRepository(String artifactUri) {
        this.artifactUri = artifactUri;
        Configuration conf = new Configuration();
        try {
            this.fs = FileSystem.get(conf);
        } catch (IOException e) {
            throw new MlflowClientException(getUnexpectedErrorSuffix(
                    "Failed to initialize DBFS artifact repository"), e);
        }
    }

    private Path getLocalPath(File localFile) {
        return new Path("file:/" + localFile.getPath());
    }

    private Path getRemotePath(String artifactPath) {
        return new Path(this.artifactUri);
    }

    @Override
    public void logArtifact(File localFile, String artifactPath) {
        if (!localFile.exists()) {
            throw new MlflowClientException("Local file does not exist: " + localFile);
        }
        if (localFile.isDirectory()) {
            throw new MlflowClientException("Local path points to a directory. Use logArtifacts" +
                    " instead: " + localFile);
        }
        // TODO(sid) write file to DBFS using HDFS APIs
        String strippedArtifactPath;
        if (artifactPath != null && artifactPath.charAt(0) == '/') {
            strippedArtifactPath = artifactPath.substring(1);
        } else {
            strippedArtifactPath = artifactPath;
        }
        String destPath;
        if (strippedArtifactPath != null) {
            destPath = artifactPath + "/" + localFile.getName();
        } else {
            destPath = localFile.getName();
        }
        Path localPath = new Path(localFile.toURI());
        Path remotePath = new Path(new Path(this.artifactUri), destPath);
        try {
            fs.copyFromLocalFile(false, localPath, remotePath);
        } catch (IOException e) {
            throw new MlflowClientException(getUnexpectedErrorSuffix(
                    "Failed to log artifact to path " + artifactPath), e);
        }
    }

    @Override
    public void logArtifact(File localFile) {
        logArtifact(localFile, null);
    }

    @Override
    public void logArtifacts(File localDir, String artifactPath) {
        if (!localDir.exists()) {
            throw new MlflowClientException("Local file does not exist: " + localDir);
        }
        if (localDir.isFile()) {
            throw new MlflowClientException("Local path points to a file. Use logArtifact" +
                    " instead: " + localDir);
        }
        for (File child: localDir.listFiles()) {
            if (child.isFile()) {
                logArtifact(child, artifactPath);
            } else {
                logArtifacts(child, artifactPath);
            }
        }
    }

    @Override
    public void logArtifacts(File localDir) {
        logArtifacts(localDir, null);
    }

    /**
     * Download a single artifact into the specified directory, returning a File corresponding
     * to the downloaded artifact. The file is downloaded with the same basename into the
     * specified directory.
     * @param remotePath Path of the file to download
     * @param localDestDir Destination directory
     */
    private File downloadArtifact(Path remotePath, Path localDestDir) {
        String basename = new File(remotePath.toString()).getName();
        Path dstPath = new Path(localDestDir, basename);
        try {
            fs.copyToLocalFile(false, remotePath, dstPath, true);
        } catch (IOException e) {
            throw new MlflowClientException(getUnexpectedErrorSuffix(
                    "Failed to download artifact from " + remotePath.toString()), e);
        }
        return new File(dstPath.toUri());
    }

    @Override
    public File downloadArtifacts(String artifactPath) {
        Path remotePath = new Path(this.artifactUri);
        if (artifactPath != null) {
            remotePath = new Path(remotePath, artifactPath);
        }
        try {
            Path localDestDir = new Path(Files.createTempDirectory(null).toUri());
            if (!fs.isDirectory(remotePath))  {
                return downloadArtifact(remotePath, localDestDir);
            }
            RemoteIterator<LocatedFileStatus> iter = fs.listFiles(remotePath, true);
            while (iter.hasNext()) {
                LocatedFileStatus fileStatus = iter.next();
                if (!fileStatus.isDirectory()) {
                    // TODO: kinda jank to do HDFS relpath computations using java.nio.file.Paths
                    // Get the path of the file relative to the target artifact dir
                    java.nio.file.Path parentPath =
                            Paths.get(fileStatus.getPath().toString()).getParent();
                    String relPath =
                            Paths.get(remotePath.toString()).relativize(parentPath).toString();
                    Path localDestPath = localDestDir;
                    if (relPath.length() > 0) {
                        localDestPath = new Path(localDestDir, relPath);
                    }
                    downloadArtifact(fileStatus.getPath(), localDestPath);
                }
            }
            return new File(localDestDir.toUri());
        } catch (IOException e) {
            throw new MlflowClientException(getUnexpectedErrorSuffix(
                    "Failed to download artifacts from " + remotePath.toString()), e);
        }
    }

    @Override
    public File downloadArtifacts() {
        return downloadArtifacts(null);
    }

    @Override
    public List<Service.FileInfo> listArtifacts(String artifactPath) {
        // TODO also handle leading slash like in logArtifact?
        Path remotePath = new Path(this.artifactUri);
        if (artifactPath != null) {
            remotePath = new Path(remotePath, artifactPath);
        }
        List<Service.FileInfo> fileInfos = new ArrayList<>();
        FileStatus[] statuses;
        try {
            statuses = fs.listStatus(remotePath);
        } catch (IOException e) {
            throw new MlflowClientException(getUnexpectedErrorSuffix(
                    "Failed to list artifacts in " + artifactPath), e);
        }
        for (FileStatus fileStatus: statuses) {
            Service.FileInfo.Builder builder = Service.FileInfo.newBuilder();
            // TODO: kinda jank to do HDFS relpath computations using java.nio.file.Paths
            String relPath = Paths.get(this.artifactUri).relativize(
                    Paths.get(fileStatus.getPath().toString())).toString();
            builder.setPath(relPath);
            builder.setIsDir(fileStatus.isDirectory());
            builder.setFileSize(fileStatus.getLen());
            fileInfos.add(builder.build());
        }
        return fileInfos;
    }

    @Override
    public List<Service.FileInfo> listArtifacts() {
        return listArtifacts(null);
    }

}