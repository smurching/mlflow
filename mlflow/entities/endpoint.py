from mlflow.entities._mlflow_object import _MLflowObject
from mlflow.protos.service_pb2 import Endpoint as ProtoEndpoint, EndpointStatus, Model


class Endpoint(_MLflowObject):
    """
    Endpoint object.

    Proto definition:
    enum EndpointStatus {
      ENDPOINT_STOPPED = 1;
      ENDPOINT_PENDING = 2;
      ENDPOINT_RUNNING = 3;
      ENDPOINT_TERMINATING = 4;
    }

    message Endpoint {
      // Public URL of the endpoint
      optional string url = 1;
      // Name of the endpoint, e.g. "churn prediction". Acts as a unique identifier across all endpoints
      optional string name = 2;
      // The model currently associated with the endpoint
      optional Model model = 3;
      // Status of the endpoint (running, stopped)
      optional EndpointStatus status = 4;
    }
    """

    def __init__(self, url, name, model, status):
        self._url = url
        self._name = name
        self._model = model
        self._status = status

    @property
    def run_id(self):
        return self._run_id

    @property
    def path(self):
        return self._path

    @property
    def model_id(self):
        return self._model_id

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    def to_proto(self):
        endpoint = ProtoEndpoint()
        endpoint.url = self.url
        endpoint.name = self.name
        endpoint.model = Model.to_proto(self.model)
        endpoint.status = self.status
        return endpoint

    @classmethod
    def from_proto(cls, proto):
        return cls(proto.url, proto.name, proto.model, proto.status)
