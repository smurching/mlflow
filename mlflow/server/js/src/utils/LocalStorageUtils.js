import localForage from "localforage";

/**
 * Utils for working with local storage.
 */
export default class LocalStorageUtils {
  static version = "0.8.0";

  static getStore(name) {
    return localForage.createInstance({
      version: LocalStorageUtils.version,
      name: name,
    });
  }

  // Interface to local storage for the current experiment. We use the key
  // (experiment_id, creation_time) to try to ensure we don't accidentally reuse settings e.g. if
  // an experiment is deleted & another with the same ID is created
  static getStoreForExperiment(experimentId) {
    return LocalStorageUtils.getStore("experiment-" + experimentId);
  }
}
