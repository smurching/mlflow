package org.mlflow.artifacts;

import java.net.URI;

import org.mlflow.tracking.creds.MlflowHostCredsProvider;

import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;


public class ArtifactRepositoryFactory {
  private final MlflowHostCredsProvider hostCredsProvider;

  public ArtifactRepositoryFactory(MlflowHostCredsProvider hostCredsProvider) {
    this.hostCredsProvider = hostCredsProvider;
  }

  public ArtifactRepository getArtifactRepository(URI baseArtifactUri, String runId) {
    System.out.println("Got base artifact URI " + baseArtifactUri.getScheme() == "dbfs");
    if (baseArtifactUri.getScheme() == "dbfs") {
      // TODO(sid) figure out how this translation to a single artifact URI is supposed to work.
      // Probably need the host creds provider for the rest-backed repo
      String artifactUri = baseArtifactUri.toString();
//      return new DbfsArtifactRepository(baseArtifactUri.toString(), runId, hostCredsProvider);
      return new DbfsArtifactRepository(baseArtifactUri.toString(), runId, hostCredsProvider);

    }
    return new CliBasedArtifactRepository(baseArtifactUri.toString(), runId, hostCredsProvider);
  }
}
