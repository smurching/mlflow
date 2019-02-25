# The data set used in this example is from http://archive.ics.uci.edu/ml/datasets/Wine+Quality
# P. Cortez, A. Cerdeira, F. Almeida, T. Matos and J. Reis.
# Modeling wine preferences by data mining from physicochemical properties. In Decision Support Systems, Elsevier, 47(4):547-553, 2009.

import os
import warnings
import sys

import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import ElasticNet

import mlflow
import mlflow.endpoints
import mlflow.models
import mlflow.sklearn


def eval_metrics(actual, pred):
    rmse = np.sqrt(mean_squared_error(actual, pred))
    mae = mean_absolute_error(actual, pred)
    r2 = r2_score(actual, pred)
    return rmse, mae, r2


def should_rollback_endpoint(endpoint_name):
    return True

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    np.random.seed(40)

    # Read the wine-quality csv file (make sure you're running this from the root of MLflow!)
    wine_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wine-quality.csv")
    data = pd.read_csv(wine_path)

    # Split the data into training and test sets. (0.75, 0.25) split.
    train, test = train_test_split(data)

    # The predicted column is "quality" which is a scalar from [3, 9]
    train_x = train.drop(["quality"], axis=1)
    test_x = test.drop(["quality"], axis=1)
    train_y = train[["quality"]]
    test_y = test[["quality"]]

    alpha = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    l1_ratio = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

    with mlflow.start_run():
        lr = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=42)
        lr.fit(train_x, train_y)

        predicted_qualities = lr.predict(test_x)

        (rmse, mae, r2) = eval_metrics(test_y, predicted_qualities)

        print("Elasticnet model (alpha=%f, l1_ratio=%f):" % (alpha, l1_ratio))
        print("  RMSE: %s" % rmse)
        print("  MAE: %s" % mae)
        print("  R2: %s" % r2)

        mlflow.log_param("alpha", alpha)
        mlflow.log_param("l1_ratio", l1_ratio)
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2", r2)
        mlflow.log_metric("mae", mae)

        mlflow.sklearn.log_model(lr, "model")

        # Register logged model with the tracking server. What's the most natural flow for this?

        # Here model_id is a pointer to all the info needed to deploy the model, like where
        # it's stored in blob storage. The model service will also store a pointer back
        # to the run.
        # Q: does it make sense for the model to have a separate name? Like you could have many
        # endpoints that reference the same model, so maybe our server's notion of a "Model"
        # is a group of MLflow models keyed on a common model name. Endpoints can reference
        model_id, version = mlflow.models.register(run_id=mlflow.active_run().info.run_uuid,
                                                   path="model",
                                                   name="SklearnWineQualityModel")
        # or mlflow.models.endpoints.get_or_create?
        endpoint_id = mlflow.endpoints.get_or_create(name="ChurnPrediction")

        # In V2 we could allow an endpoint to have > 1 models, but for now we just do one
        mlflow.models.deploy(
            endpoint_name="ChurnPrediction", model_id=model_id, deploy_target="databricks",
            deploy_args={"rollout": "incremental"})


        # Q: where does update logic / A/B testing logic go? Such logic may be different depending
        # on the deployment service. We can address this in two ways:
        # a) the user deploys the new endpoint and writes their own custom proxy logic that wraps around
        #    MLflow endpoints, phases in usage of a new endpoint from [all] downstream service[s]
        #    (or basically has a 'wrapper' downstream service that forwards to an MLflow endpoint, to
        #    avoid problem of having to update all downstream services). Such a flow might look like
        #    1) Deploy model to "staging" endpoint
        #    2) Tell proxy service to start its update procedure, generate some predictions from
        #       staging endpoint.
        #    3) Once proxy service switches over entirely to staging endpoint, deploy staging
        #       model to prod endpoint
        #    4) Update proxy service to pull from prod endpoint instead
        # b) for deployment services that support it natively (like SM), allow passing deployment
        #    kwargs directly to the deployment service
        # https://aws.amazon.com/sagemaker/features/ - SageMaker has A/B testing where you specify
        # the percentage of each model that gets served per endpoint. So an endpoint in SageMaker
        # can actually serve multiple models with some percentage per model
        # Lesson: our model registry data model needs to be as general as the most flexible
        #         deployment target, or to restrict the flexibility of a deployment target

        if should_rollback_endpoint("ChurnPrediction"):
            pass
            # List (model_id, deploy_args) that can be passed to deploy() to rollback an endpoint to
            # a previous revision
            # versions = mlflow.endpoints.history(name="WineQualityModel")

