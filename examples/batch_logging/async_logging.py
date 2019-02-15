import mlflow

def async_example():
    # In the future, we may implement one or more of the async logging APIs used below, in which
    # data is buffered on the client and eventually flushed to the server (after n seconds, n bytes
    # logged, calls to end_run()). This could be relevant e.g. for MLlib x MLflow integration, where
    # MLlib performance & reliability should be minimally affected by MLflow (e.g. failure to
    # log a metric shouldn't fail or slow model training).
    #
    # TL;DR: This use case seems supported by both a single REST API (LogBatch) and multiple
    # REST APIs (LogMetrics, SetTags, LogParams), although we can provide nicer behavior with
    # a single REST API.
    #
    # It's unclear whether the API should be truly async or simply not validate that network calls
    # succeed (a truly async API would improve performance at the cost of increased complexity,
    # e.g. a background thread(s) that makes requests).
    #
    #
    # Naive/simple solution:
    #
    # Naively, we can implement async logging via a background thread that serially makes REST API
    # requests (one metric or param or tag per request) from a fixed-size ordered queue, cancelling
    # & removing the oldest request in the queue if it's full.
    #
    # Batched-logging-based solution:
    # Here we use a similar approach to the naive solution but batch together requests from our
    # queue.
    #
    # Considerations:
    # The debugging UX becomes complicated if it's possible to have data
    # logged out of order of program execution (i.e. if "accuracy" and "learning_rate" are logged
    # below but the "my_git_diff" tag is not). This can happen with both a single & multiple batched
    # logging endpoints - in both cases, unless we allow the user to specify an order
    # in which to persist elements of their batched logging request & error out on the first failed
    # attempt to persist a metric/param/tag, and additionally if metrics, params, tags, are split
    # up across multiple REST endpoints.
    #
    # However, we propose that the potential for out-of-order logging in this use case
    # isn't a dealbreaker for our REST APIs: in general with async logging, you don't get strong
    # ordering guarantees on when data reaches the server relative to what line of code your program
    # is executing (i.e. data may reach the server later).
    #
    # If we were to make (or implement) stronger guarantees on ordered logging, we might want
    # to modify our REST API to accept an order in which to log entities (i.e. have users
    # specify a single ordered list of metrics/params/tags to log) and modify the error behavior to
    # fail an API request on the first entity that fails to be persisted.
    mlflow.log_metric("accuracy", 0.3, block=False)
    mlflow.log_param("l1_ratio", 0.5, block=False)
    mlflow.log_metric("accuracy", 0.9, block=False)
    mlflow.set_tag("my_git_diff", "a_very_long_string" * 9999999, block=False)
    mlflow.log_param("learning_rate", 1e-4, block=False)
    # Batch-fluent APIs: convenience wrapper over log_metric, etc that uses a dict
    mlflow.log_metrics({"accuracy": 0.5, "loss": 0.3}, block=False)
    mlflow.log_params({"another_param": "value"}, block=False)


if __name__ == "__main__":
    async_example()
