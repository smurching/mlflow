package org.mlflow.artifacts;

import java.net.URI;
import java.io.File;
import java.io.IOException;
import java.util.List;

import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.conf.Configuration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.mlflow.tracking.creds.MlflowHostCredsProvider;
import org.mlflow.api.proto.Service.FileInfo;


public class DbfsArtifactRepository implements ArtifactRepository {
    private static final Logger logger = LoggerFactory.getLogger(DbfsArtifactRepository.class);

    /**
     * Temporary method - to be pulled out into DbfsArtifactRepository, which should then handle
     * delegation to a CliBasedArtifactRpeository (or REST based repo, if we want to stay
     * pure-Java), when we do Java plugins to keep code changes minimal for now. Actually, since we
     * probably need to implement the REST repo in Java, we might as well refactor this.
     */
    public static boolean isDbfsRegisteredWithHdfs() {
        Configuration conf = new Configuration();
        try {
            Path path = new Path("dbfs:/");
            FileSystem.get(conf).makeQualified(path);
        } catch (IOException e) {
            logger.info(e.toString());
            return false;
        }
        return true;
    }

    private ArtifactRepository delegate;

    public DbfsArtifactRepository(String artifactUri, String runId,
                                  MlflowHostCredsProvider hostCredsProvider) {
        if (DbfsArtifactRepository.isDbfsRegisteredWithHdfs()) {
            this.delegate = new DbfsFuseArtifactRepository(artifactUri);
        } else {
            // this.delegate = new DbfsRestArtifactRepository(artifactUri, hostCredsProvider);
            this.delegate = new CliBasedArtifactRepository(artifactUri, runId, hostCredsProvider);
        }
    }

    @Override
    public void logArtifact(File localFile) {
        this.delegate.logArtifact(localFile);
    }

    @Override
    public void logArtifact(File localFile, String artifactPath) {
        this.delegate.logArtifact(localFile, artifactPath);
    }

    @Override
    public void logArtifacts(File localDir) {
        this.delegate.logArtifacts(localDir);
    }


    @Override
    public void logArtifacts(File localDir, String artifactPath) {
        this.delegate.logArtifacts(localDir, artifactPath);
    }

    @Override
    public List<FileInfo> listArtifacts() {
        return this.delegate.listArtifacts();
    }

    @Override
    public List<FileInfo> listArtifacts(String artifactPath) {
        return this.delegate.listArtifacts(artifactPath);
    }

    @Override
    public File downloadArtifacts() {
        return this.delegate.downloadArtifacts();
    }

    @Override
    public File downloadArtifacts(String artifactPath) {
        return this.delegate.downloadArtifacts(artifactPath);
    }



}