from mlflow.entities._mlflow_object import _MLflowObject
from mlflow.protos.service_pb2 import Model as ProtoModel


class Model(_MLflowObject):
    """
    Model object.
    """
    def __init__(self, run_id, path, model_id, name, version):
        self._run_id = run_id
        self._path = path
        self._model_id = model_id
        self._name = name
        self._version = version

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
        model = ProtoModel()
        model.run_id = self.run_id
        model.path = self.path
        model.model_id = self.model_id
        model.name = self.name
        model.version = self.version
        return model

    @classmethod
    def from_proto(cls, proto):
        return cls(run_id=proto.run_id, path=proto.path, model_id=proto.model_id, name=proto.name,
                   version= proto.version)
