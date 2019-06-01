package org.mlflow.artifacts;

import java.net.URI;

import org.apache.hadoop.fs.FileSystem;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.mlflow.tracking.creds.MlflowHostCredsProvider;

public class DbfsRestArtifactRepository {
    private static final Logger logger = LoggerFactory.getLogger(DbfsRestArtifactRepository.class);
    private String artifactUri;

    public DbfsRestArtifactRepository(String artifactUri, MlflowHostCredsProvider hostCredsProvider) {
        this.artifactUri = artifactUri;
    }



}