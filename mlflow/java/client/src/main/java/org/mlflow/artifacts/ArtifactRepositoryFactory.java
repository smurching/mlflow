package org.mlflow.artifacts;

import java.net.URI;

import org.mlflow.tracking.creds.MlflowHostCredsProvider;

import org.apache.hadoop.fs.FileSystem
import org.apache.hadoop.fs.Path


public class ArtifactRepositoryFactory {
  private final MlflowHostCredsProvider hostCredsProvider;

  public ArtifactRepositoryFactory(MlflowHostCredsProvider hostCredsProvider) {
    this.hostCredsProvider = hostCredsProvider;
  }

  public ArtifactRepository getArtifactRepository(URI baseArtifactUri, String runId) {
    if (baseArtifactUri.getScheme() == "dbfs") {
      return new DbfsArtifactRepository(baseArtifactUri.toString(), runId, hostCredsProvider);
    }
    return new CliBasedArtifactRepository(baseArtifactUri.toString(), runId, hostCredsProvider);
  }
}
