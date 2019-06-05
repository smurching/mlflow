//package org.mlflow.artifacts;
//
//import java.net.URI;
//import java.nio.file.Path;
//import java.nio.file.Paths;
//import java.util.List;
//import java.util.ArrayList;
//
//import org.apache.commons.io.FileUtils;
//import org.apache.hadoop.fs.FileSystem;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import org.mlflow.tracking.creds.MlflowHostCredsProvider;
//import org.mlflow.tracking.MlflowHttpCaller;
//
//public class DbfsRestArtifactRepository implements ArtifactRepository {
//    private static final Logger logger = LoggerFactory.getLogger(
//      DbfsRestArtifactRepository.class);
//    private String baseDbfsEndpoint;
//    private MlflowHostCredsProvider hostCredsProvider;
//    private MlflowHttpCaller httpCaller;
//
//    public DbfsRestArtifactRepository(String artifactUri,
//                                      MlflowHostCredsProvider hostCredsProvider) {
//        this.baseDbfsEndpoint = "/dbfs/" + artifactUri.substr("dbfs:/".length());
//        this.hostCredsProvider = hostCredsProvider;
//        this.httpCaller = new MlflowHttpCaller(hostCredsProvider);
//    }
//
//    /**
//     * Resolve an artifact path into a DBFS endpoint that can be used for streaming reads/writes.
//     */
//    private String getDbfsPath(String artifactPath) {
//        if (artifactPath == null) {
//            return this.baseDbfsEndpoint;
//        } else  {
//            // TODO handle leading "/" in artifact path?
//            return this.baseDbfsEndpoint + "/" + artifactPath;
//        }
//    }
//
//    @Override
//    public void logArtifact(File localFile, String artifactPath) {
//        String path = getDbfsPath(artifactPath) + "/" + localFile.getName();
//        httpCaller.post(path, FileUtils.readFileToString(localFile, StandardCharsets.UTF_8));
//    }
//
//    @Override
//    public void logArtifact(File localFile) {
//        logArtifact(localFile, null);
//    }
//
//    @Override
//    public void logArtifacts(File localDir, String artifactPath) {
//        if (!localDir.exists()) {
//            throw new MlflowClientException("Local file does not exist: " + localDir);
//        }
//        if (localDir.isFile()) {
//            throw new MlflowClientException("Local path points to a file. Use logArtifact" +
//                    " instead: " + localDir);
//        }
//        for (File child: localDir.listFiles()) {
//            if (child.isFile()) {
//                logArtifact(child, artifactPath);
//            } else {
//                logArtifacts(child, artifactPath);
//            }
//        }
//    }
//
//    @Override
//    public void logArtifacts(File localDir) {
//        logArtifacts(localDir, null);
//    }
//
//    /**
//     * Download a single artifact into the specified directory, returning a File corresponding
//     * to the downloaded artifact. The file is downloaded with the same basename into the
//     * specified directory.
//     * @param remotePath Path of the file to download in the form /dbfs/path/to/file
//     * @param localDestDir Destination directory
//     */
//    private File downloadArtifact(String remotePath, String localDestDir) {
//        String basename = new File(remotePath).getName();
//        File dstFile = new File(localDestDir + "/" + basename);
//        String fileContents;
//        try {
//            fileContents = httpCaller.get(basename);
//        } catch (IOException e) {
//            throw new MlflowClientException(getUnexpectedErrorSuffix(
//                    "Failed to download artifact from " + remotePath.toString()), e);
//        }
//        FileUtils.writeStringToFile(dstFile, fileContents, StandardCharsets.UTF_8);
//        return dstFile;
//    }
//
//    @Override
//    public File downloadArtifacts(String artifactPath) {
//        String path = getDbfsPath(artifactPath);
//        try {
//            Path localDestDir = new Path(Files.createTempDirectory(null).toUri());
//            if (!fs.isDirectory(remotePath))  {
//                return downloadArtifact(remotePath, localDestDir);
//            }
//            RemoteIterator<LocatedFileStatus> iter = fs.listFiles(remotePath, true);
//            while (iter.hasNext()) {
//                LocatedFileStatus fileStatus = iter.next();
//                if (!fileStatus.isDirectory()) {
//                    // TODO: kinda jank to do HDFS relpath computations using java.nio.file.Paths
//                    // Get the path of the file relative to the target artifact dir
//                    java.nio.file.Path parentPath =
//                            Paths.get(fileStatus.getPath().toString()).getParent();
//                    String relPath =
//                            Paths.get(remotePath.toString()).relativize(parentPath).toString();
//                    Path localDestPath = localDestDir;
//                    if (relPath.length() > 0) {
//                        localDestPath = new Path(localDestDir, relPath);
//                    }
//                    downloadArtifact(fileStatus.getPath(), localDestPath);
//                }
//            }
//            return new File(localDestDir.toUri());
//        } catch (IOException e) {
//            throw new MlflowClientException(getUnexpectedErrorSuffix(
//                    "Failed to download artifacts from " + remotePath.toString()), e);
//        }
//    }
//
//    @Override
//    public File downloadArtifacts() {
//        return downloadArtifacts(null);
//    }
//
//    @Override
//    public List<Service.FileInfo> listArtifacts(String artifactPath) {
////                if path:
////            dbfs_path = self._get_dbfs_path(path)
////        else:
////            dbfs_path = self._get_dbfs_path('')
////        dbfs_list_json = {'path': dbfs_path}
////        response = self._dbfs_list_api(dbfs_list_json)
////        try:
////            json_response = json.loads(response.text)
////        except ValueError:
////            raise MlflowException(
////                "API request to list files under DBFS path %s failed with status code %s. "
////                "Response body: %s" % (dbfs_path, response.status_code, response.text))
////        # /api/2.0/dbfs/list will not have the 'files' key in the response for empty directories
////        infos = []
////        artifact_prefix = strip_prefix(self.artifact_uri, 'dbfs:')
////        if json_response.get('error_code', None) == RESOURCE_DOES_NOT_EXIST:
////            return []
////        dbfs_files = json_response.get('files', [])
////        for dbfs_file in dbfs_files:
////            stripped_path = strip_prefix(dbfs_file['path'], artifact_prefix + '/')
////            # If `path` is a file, the DBFS list API returns a single list element with the
////            # same name as `path`. The list_artifacts API expects us to return an empty list
////            # in this
////            # case, so we do so here.
////            if stripped_path == path:
////                return []
////            is_dir = dbfs_file['is_dir']
////            artifact_size = None if is_dir else dbfs_file['file_size']
////            infos.append(FileInfo(stripped_path, is_dir, artifact_size))
////        return sorted(infos, key=lambda f: f.path)
//          String listEndpoint = getDbfsPath(artifactPath);
//          String response = httpCaller.get(listEndpoint);
//
////        // TODO also handle leading slash like in logArtifact?
////        Path remotePath = new Path(this.artifactUri);
////        if (artifactPath != null) {
////            remotePath = new Path(remotePath, artifactPath);
////        }
//        List<Service.FileInfo> fileInfos = new ArrayList<>();
////        FileStatus[] statuses;
////        try {
////            statuses = fs.listStatus(remotePath);
////        } catch (IOException e) {
////            throw new MlflowClientException(getUnexpectedErrorSuffix(
////                    "Failed to list artifacts in " + artifactPath), e);
////        }
////        for (FileStatus fileStatus: statuses) {
////            Service.FileInfo.Builder builder = Service.FileInfo.newBuilder();
////            // TODO: kinda jank to do HDFS relpath computations using java.nio.file.Paths
////            String relPath = Paths.get(this.artifactUri).relativize(
////                    Paths.get(fileStatus.getPath().toString())).toString();
////            builder.setPath(relPath);
////            builder.setIsDir(fileStatus.isDirectory());
////            builder.setFileSize(fileStatus.getLen());
////            fileInfos.add(builder.build());
////        }
//        return fileInfos;
//    }
//
//    @Override
//    public List<Service.FileInfo> listArtifacts() {
//        return listArtifacts(null);
//    }
//
//}