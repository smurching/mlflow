from mlflow.tracking.utils import _get_store

def create(name):
    return _get_store().create_endpoint(endpoint_name=name)


def list():
    return _get_store().list_endpoints()

def get(name):
    return _get_store().get_endpoint(endpoint_name=name)


def get_or_create(name):
    try:
        return get(name)
    except Exception:
        return create(name)
