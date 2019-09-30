.. _registry:

=====================
MLflow Model Registry
=====================

The MLflow Model Registry component is a centralized model store, set of APIs, and UI, to collaboratively manage the full lifecycle of an MLflow Model. It provides model lineage (which MLflow Experiment and Run produced the model), model versioning, stage transitions (e.g. from staging to production), annotations (e.g. with comments, tags), and deployment management (e.g. which production jobs have requested a specific model version).

.. contents:: Table of Contents
  :local:
  :depth: 1

Concepts
========

The MLflow Model Registry provides a standalone component that introduces several concepts to collaboratively manage the full lifecycle of an MLflow Model. 

Model
    A model is an MLflow Model logged with one of the model flavor’s ``log_model`` methods.

Registered Model
    A registered model is an MLflow Model registered with the MLflow Model Registry. A registered model has a unique name, version, stage, and other metadata.

Model Version
    Each registered model can have one or many versions. When a new model is added to the Model Registry, it is added as version 1. Each new model registered to the same model name will increment the version number.

Model Stage
    Each model version can be assigned one or many stages. Stages represent the lifecycle of a model and can be user-defined. MLflow provides predefined stages for common use-cases such as *Staging* and *Production*.

Stage Transitions
    When a model is added to the Model Registry it is added with the stage *None*. Each stage transition will be recorded as an activity on the model version. Stage transitions can be requested and approved, allowing for CI/CD workflow integration.

Model Activities
    Activities are new registration events or changes in the stage of a model version. Each activity logs the user, the activity, and additional metadata such as comments.

Adding an MLflow Model to the Model Registry
============================================

Before a model can be added to the Model Registry it has to be logged using the ``log_model`` methods of the corresponding model flavors. Given a logged model, it can be added to the registry either through a UI workflow or through APIs.

UI Workflow
-----------

From the MLflow Runs detail page, select a logged MLflow Model in the Artifact section. Click the **Register Model** button. 

.. figure:: _static/images/registry_1_register.png

If you are adding a new model, pick a unique name to identify the model. If you are registering a new version to an existing model, pick the existing model’s name from the dropdown.

.. figure:: _static/images/registry_2_dialog.png

Once the model is added to the Model Registry you can either navigate to the **Models** page to find the model in the overview, or click directly on the link provided in the Artifact section of the runs detail page to go to the version you just created.

.. figure:: _static/images/registry_3_overview.png

Each model has an overview page that shows the active versions, as well as model activity. Click on a version to navigate to the version detail page.

.. figure:: _static/images/registry_4_version.png

On the version detail page you can see comments, activites, and the current stage of this particular model version. If you click on the stage in the top right, you can request a stage transition.

.. figure:: _static/images/registry_5_transition.png

If you have the appropriate access controls, you can approve transition requests, changing the state of the current version.

.. figure:: _static/images/registry_6_approve.png

API Workflow
------------

Once a model is logged using the ``log_model`` methods, you can use the model URI to add it to the registry.

Call the ``registed_model`` API to add it to the registry:

.. code-block:: py

   mlflow.register_model("runs:/e148278107274..832/artifacts/model",
                         "EmailMarketingCampaign")

Alternatively, you can use the send in registered model name to ``log_model`` method.

.. code-block:: py

   mlflow.tensorflow.log_model(tf_saved_model_dir=saved_estimator_path,
                               tf_meta_graph_tags=[tag_constants.SERVING],
                               tf_signature_def_key="predict",
                               artifact_path="model",
                               registered_model="EmailMarketingCampaign")

.. note:: If a registered model does not already exist, registry will create one before creating a new model version.

With the ``get_model_version`` API you can confirm that the model has successfully been registered:

.. code-block:: py

   mlflow.registry.get_model_version(registered_model = "EmailMarketingCampaign", 
                                     version = 12)

Or you can ask for the latest registered model by stage

.. code-block:: py

   mlflow.registry.get_latest_version(registered_model = "EmailMarketingCampaign", 
                                      stage = "None")


The model is added to the registry with the stage **None**, indicating that it is new. You can use the REST API to create a stage transition request:


.. code-block:: bash

  curl                                                \
    -X POST                                           \
    -d '{"model_version": {
           "registered_model" : {
             "name" : "EmailMarketingCampaign"
           },
           "version" : 12},
         "stage" : "Production",
         "comment" : "Reduces error rate by 3.2%."
        }'                                            \
  https://...databricks.com/api/2.0/preview/mlflow/transition-requests/create


If you have the appropriate access controls, you can use the following API to approve the stage transition request, changing the state of the current version:

.. code-block:: bash

  curl                                            \
     -X PATCH                                      \
     -d '{"action": 1,
         "transition_request": {
         "model_version": {
           "registered_model": {
             "name": "EmailMarketingCampaign"
           },
           "version": 2
          },
          "request_activity": {
           "model_registry_data": {
             "transition": {
               "to_stage": "Production"
              }
           }
         }
       }'                                       \
  https://...databricks.com/api/2.0/preview/mlflow/transition-requests/update

