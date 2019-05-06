package org.mlflow.artifacts;

import java.net.URI;

public class DbfsArtifactRepository {
    private static final Logger logger = LoggerFactory.getLogger(CliBasedArtifactRepository.class);

    /**
     * Temporary method - to be pulled out into DbfsArtifactRepository, which should then handle
     * delegation to a CliBasedArtifactRpeository (or REST based repo, if we want to stay pure-Java),
     * when we do Java plugins to keep code changes minimal for now. Actually, since we probably
     * need to implement the REST repo in Java, we might as well refactor this.
     */
    private boolean isDbfsRegisteredWithHdfs() {
        path = new Path("dbfs:/");
        try {
            FileSystem.get(conf).makeQualified(path);
        } catch (Exception e) {
            return false;
        }
        return true;
    }

}