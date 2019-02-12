import mlflow

def main():
    # Async APIs: data is buffered on the client and eventually flushed to the server
    # (after n seconds, n bytes, end_run()). Another question here is if the API should be
    # truly async or just not validate the response (probably truly async?) but I don't think
    # it matters too much right now.
    #
    # Complicates debugging UX to have data logged out of order of program execution (i.e.
    # if "accuracy" and "learning_rate" are logged below.
    #
    # We can avoid out-of-order logging by trying to reject the whole request if any individual
    # values are invalid, but then we have issues when partial data is persisted & the remaining
    # fails due to e.g. S3 or database issues. But maybe we can assume that to be unlikely (i.e.
    # use a DB transaction), so enforce a guarantee that data is written all-or-nothing (atomic)
    #
    # If we feel that having atomicity is too difficult, we can alternatively say that if a
    # request contains invalid data, our response will specify which input metrics/params/tags
    # were invalid and that the remaining ones may or may not have been written (usually not
    # written i.e. in the invalid data case, but might be written e.g. in the database failure
    # case).
    #
    # Conclusion: if you log things asynchronously, you don't get any guarantees on when
    # they're actually uploaded relative to the state of your program. For example it's ok
    # if data gets to the server later than you expect (i.e. while your main thread is doing
    # something else)
    mlflow.log_metric("accuracy", 0.3, block=False)
    mlflow.log_param("asdf", "Asdf")
    mlflow.log_metric("accuracy", 0.5, block=False)
    mlflow.set_tag("my_git_diff", "some_string_thats_too_long" * 9999999, block=False)
    mlflow.log_param("learning_rate", 0.5, block=False)
    # Batch-fluent APIs: convenience wrapper over log_metric, etc that uses a dict
    mlflow.log_metrics({"accuracy": 0.5, "loss": 0.3}, block=False)
    mlflow.log_params({"another_param": "value"}, block=False)



if __name__ == "__main__":
    main()