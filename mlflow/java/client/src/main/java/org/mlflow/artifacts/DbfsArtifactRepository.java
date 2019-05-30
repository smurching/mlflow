package org.mlflow.artifacts;

import java.net.URI;

import org.apache.hadoop.fs.FileSystem;

public class DbfsArtifactRepository implements ArtifactRepository {
    private static final Logger logger = LoggerFactory.getLogger(DbfsArtifactRepository.class);

    /**
     * Temporary method - to be pulled out into DbfsArtifactRepository, which should then handle
     * delegation to a CliBasedArtifactRpeository (or REST based repo, if we want to stay pure-Java),
     * when we do Java plugins to keep code changes minimal for now. Actually, since we probably
     * need to implement the REST repo in Java, we might as well refactor this.
     */
    static boolean isDbfsRegisteredWithHdfs() {
        path = new Path("dbfs:/");
        try {
            FileSystem.get(conf).makeQualified(path);
        } catch (Exception e) {
            return false;
        }
        return true;
    }

    private ArtifactRepository delegate;

    public DbfsArtifactRepository(String artifactUri) {
        if (DbfsArtifactRepository.isRegisteredWithHdfs()) {
            this.delegate = DbfsHdfsArtifactRepository(artifactUri);
        } else {
            this.delegate = DbfsRestArtifactRepository(artifactUri);
        }
    }



}