package org.mlflow.artifacts;

import java.net.URI;

import org.apache.hadoop.fs.FileSystem;

public class DbfsHdfsArtifactRepository {
    private static final Logger logger = LoggerFactory.getLogger(DbfsHdfsArtifactRepository.class);

    public DbfsHdfsArtifactRepository(String artifactUri) {
        this.artifactUri = artifactUri;
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
        // TODO(sid) write directory to DBFS using HDFS APIs
//        List<String> baseCommand = Lists.newArrayList(
//                "artifacts", "log-artifacts", "--local-dir", localDir.toString());
//        List<String> command = appendRunIdArtifactPath(baseCommand, runId, artifactPath);
//        String tag = "log dir " + localDir + " to " + getTargetIdentifier(artifactPath);
//        forkMlflowProcess(command, tag);
    }

    @Override
    public void logArtifacts(File localDir) {
        logArtifacts(localDir, null);
    }

    @Override
    public File downloadArtifacts(String artifactPath) {
        checkMlflowAccessible();
        String tag = "download artifacts for " + getTargetIdentifier(artifactPath);
        List<String> command = appendRunIdArtifactPath(
                Lists.newArrayList("artifacts", "download"), runId, artifactPath);
        String localPath = forkMlflowProcess(command, tag).trim();
        return new File(localPath);
    }

    @Override
    public File downloadArtifacts() {
        return downloadArtifacts(null);
    }

    @Override
    public List<Service.FileInfo> listArtifacts(String artifactPath) {
        checkMlflowAccessible();
        String tag = "list artifacts in " + getTargetIdentifier(artifactPath);
        List<String> command = appendRunIdArtifactPath(
                Lists.newArrayList("artifacts", "list"), runId, artifactPath);
        String jsonOutput = forkMlflowProcess(command, tag);
        return parseFileInfos(jsonOutput);
    }

    @Override
    public List<Service.FileInfo> listArtifacts() {
        return listArtifacts(null);
    }

    public DbfsHdfsArtifactRepository() {

    }

}