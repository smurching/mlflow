class EndpointStatus(object):
    """Enum for originating source of a :py:class:`mlflow.entities.Run`."""
    ENDPOINT_STOPPED, ENDPOINT_PENDING, ENDPOINT_RUNNING, ENDPOINT_TERMINATING = range(1, 5)
    _STRING_TO_ENDPOINT_STATUS = {
        "STOPPED": ENDPOINT_STOPPED,
        "PENDING": ENDPOINT_PENDING,
        "RUNNING": ENDPOINT_RUNNING,
        "TERMINATING": ENDPOINT_TERMINATING,
    }
    ENDPOINT_STATUS_TO_STRING = {value: key for key, value in _STRING_TO_ENDPOINT_STATUS.items()}

    @staticmethod
    def from_string(status_str):
        if status_str not in EndpointStatus._STRING_TO_ENDPOINT_STATUS:
            raise Exception(
                "Could not get endpoint status corresponding to string %s. Valid endpoint "
                "status strings: %s" % (status_str, list(EndpointStatus._STRING_TO_ENDPOINT_STATUS.keys())))
        return EndpointStatus._STRING_TO_ENDPOINT_STATUS[status_str]

    @staticmethod
    def to_string(status):
        if status not in EndpointStatus.ENDPOINT_STATUS_TO_STRING:
            raise Exception("Could not get string corresponding to endpoint status %s. Valid endpoint "
                            "statuses: %s" % (status, list(EndpointStatus.ENDPOINT_STATUS_TO_STRING.keys())))
        return EndpointStatus.ENDPOINT_STATUS_TO_STRING[status]
