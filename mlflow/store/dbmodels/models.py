import time
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column, String, Float, ForeignKey, Integer, CheckConstraint,
    BigInteger, PrimaryKeyConstraint)
from sqlalchemy.ext.declarative import declarative_base
from mlflow.entities import (
    Experiment, RunTag, Metric, Param, RunData, RunInfo,
    SourceType, RunStatus, Run, ViewType, Model, Endpoint)
from mlflow.entities.lifecycle_stage import LifecycleStage

Base = declarative_base()


SourceTypes = [
    SourceType.to_string(SourceType.NOTEBOOK),
    SourceType.to_string(SourceType.JOB),
    SourceType.to_string(SourceType.LOCAL),
    SourceType.to_string(SourceType.UNKNOWN),
    SourceType.to_string(SourceType.PROJECT)
]

RunStatusTypes = [
    RunStatus.to_string(RunStatus.SCHEDULED),
    RunStatus.to_string(RunStatus.FAILED),
    RunStatus.to_string(RunStatus.FINISHED),
    RunStatus.to_string(RunStatus.RUNNING)
]


def _create_entity(base, model):

    # create dict of kwargs properties for entity and return the initialized entity
    config = {}
    for k in base._properties():
        # check if its mlflow entity and build it
        obj = getattr(model, k)

        if isinstance(model, SqlRun):
            if base is RunData:
                # Run data contains list for metrics, params and tags
                # so obj will be a list so we need to convert those items
                if k == 'metrics':
                    # only get latest recorded metrics per key
                    metrics = {}
                    for o in obj:
                        if o.key not in metrics or o.timestamp > metrics.get(o.key).timestamp:
                            metrics[o.key] = Metric(o.key, o.value, o.timestamp)
                    obj = metrics.values()
                elif k == 'params':
                    obj = [Param(o.key, o.value) for o in obj]
                elif k == 'tags':
                    obj = [RunTag(o.key, o.value) for o in obj]
            elif base is RunInfo:
                if k == 'source_type':
                    obj = SourceType.from_string(obj)
                elif k == "status":
                    obj = RunStatus.from_string(obj)

        config[k] = obj
    return base(**config)


class SqlExperiment(Base):
    __tablename__ = 'experiments'

    experiment_id = Column(Integer, autoincrement=True)
    name = Column(String(256), unique=True, nullable=False)
    artifact_location = Column(String(256), nullable=True)
    lifecycle_stage = Column(String(32), default=LifecycleStage.ACTIVE)

    __table_args__ = (
        CheckConstraint(
            lifecycle_stage.in_(LifecycleStage.view_type_to_stages(ViewType.ALL)),
            name='lifecycle_stage'),
        PrimaryKeyConstraint('experiment_id', name='experiment_pk')
    )

    def __repr__(self):
        return '<SqlExperiment ({}, {})>'.format(self.experiment_id, self.name)

    def to_mlflow_entity(self):
        return _create_entity(Experiment, self)


class SqlRun(Base):
    __tablename__ = 'runs'

    run_uuid = Column(String(32), nullable=False)
    name = Column(String(250))
    source_type = Column(String(20), default=SourceType.to_string(SourceType.LOCAL))
    source_name = Column(String(500))
    entry_point_name = Column(String(50))
    user_id = Column(String(256), nullable=True, default=None)
    status = Column(String(20), default=RunStatus.to_string(RunStatus.SCHEDULED))
    start_time = Column(BigInteger, default=int(time.time()))
    end_time = Column(BigInteger, nullable=True, default=None)
    source_version = Column(String(50))
    lifecycle_stage = Column(String(20), default=LifecycleStage.ACTIVE)
    artifact_uri = Column(String(200), default=None)
    experiment_id = Column(Integer, ForeignKey('experiments.experiment_id'))
    experiment = relationship('SqlExperiment', backref=backref('runs', cascade='all'))

    __table_args__ = (
        CheckConstraint(source_type.in_(SourceTypes), name='source_type'),
        CheckConstraint(status.in_(RunStatusTypes), name='status'),
        CheckConstraint(lifecycle_stage.in_(LifecycleStage.view_type_to_stages(ViewType.ALL)),
                        name='lifecycle_stage'),
        PrimaryKeyConstraint('run_uuid', name='run_pk')
    )

    def to_mlflow_entity(self):
        # run has diff parameter names in __init__ than in properties_ so we do this manually
        info = _create_entity(RunInfo, self)
        data = _create_entity(RunData, self)
        return Run(run_info=info, run_data=data)


class SqlTag(Base):
    __tablename__ = 'tags'

    key = Column(String(250))
    value = Column(String(250), nullable=True)
    run_uuid = Column(String(32), ForeignKey('runs.run_uuid'))
    run = relationship('SqlRun', backref=backref('tags', cascade='all'))

    __table_args__ = (
        PrimaryKeyConstraint('key', 'run_uuid', name='tag_pk'),
    )

    def __repr__(self):
        return '<SqlRunTag({}, {})>'.format(self.key, self.value)

    def to_mlflow_entity(self):
        return _create_entity(RunTag, self)


class SqlMetric(Base):
    __tablename__ = 'metrics'

    key = Column(String(250))
    value = Column(Float, nullable=False)
    timestamp = Column(BigInteger, default=int(time.time()))
    run_uuid = Column(String(32), ForeignKey('runs.run_uuid'))
    run = relationship('SqlRun', backref=backref('metrics', cascade='all'))

    __table_args__ = (
        PrimaryKeyConstraint('key', 'timestamp', 'run_uuid', name='metric_pk'),
    )

    def __repr__(self):
        return '<SqlMetric({}, {}, {})>'.format(self.key, self.value, self.timestamp)

    def to_mlflow_entity(self):
        return _create_entity(Metric, self)


class SqlParam(Base):
    __tablename__ = 'params'

    key = Column(String(250))
    value = Column(String(250), nullable=False)
    run_uuid = Column(String(32), ForeignKey('runs.run_uuid'))
    run = relationship('SqlRun', backref=backref('params', cascade='all'))

    __table_args__ = (
        PrimaryKeyConstraint('key', 'run_uuid', name='param_pk'),
    )

    def __repr__(self):
        return '<SqlParam({}, {})>'.format(self.key, self.value)

    def to_mlflow_entity(self):
        return _create_entity(Param, self)


class SqlModel(Base):
    __tablename__ = 'models'

    run_uuid = Column(String(32), ForeignKey('runs.run_uuid'))
    path = Column(String(250), nullable=False)
    model_id = Column(String(32))
    name = Column(String(250))
    version = Column(BigInteger)


    run = relationship('SqlRun', backref=backref('models', cascade='all'))

    __table_args__ = (
        PrimaryKeyConstraint('model_id', name='model_pk'),
    )

    def __repr__(self):
        return '<SqlModel({}, {}, {}, {}, {})>'.format(
            self.run_uuid, self.path, self.model_id, self.name, self.version)

    def to_mlflow_entity(self):
        return _create_entity(Model, self)


class SqlEndpoint(Base):
    __tablename__ = 'endpoints'

    name = Column(String(250))
    deployment_target = Column(String(250))
    status = Column(String(32))
    model_id = Column(String(32), ForeignKey('models.model_id'))


    __table_args__ = (
        PrimaryKeyConstraint('name', name='endpoint_pk'),
    )

    def __repr__(self):
        return '<SqlEndpoint({}, {}, {}, {})>'.format(
            self.name, self.deployment_target, self.status, self.model_id)

    def to_mlflow_entity(self):
        return _create_entity(Endpoint, self)


"""
message Model {
  // Data about where the model is stored
  optional string run_id = 1;
  optional string path = 2;
  // Data stored by server
  // UUID of model, assigned by server. Can be used to reference model
  optional string model_id = 3;
  // Model name & version (autoincrementing int). (name, version) can be used to reference model
  // as well
  optional string name = 4;
  optional int64 version = 5;
}

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

message GetModel {
  optional string model_id = 1;
  message Response {
    // Model entity
    optional Model model = 1;
    // List of endpoints with which the current model is associated
    repeated Endpoint endpoints = 2;
  }
}

// Describe a single endpoint
message GetEndpoint {
  optional string name = 1;
  message Response {
    optional Endpoint endpoint = 1;
  }
}
"""