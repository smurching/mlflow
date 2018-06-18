"""
Scoring server for python model format.
The passed int model is expected to have function:
   predict(pandas.Dataframe) -> pandas.DataFrame

Input, expected intext/csv or application/json format,
is parsed into pandas.DataFrame and passed to the model.

Defines two endpoints:
    /ping used for health check
    /invocations used for scoring
"""
from __future__ import print_function

import pandas as pd
import flask

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def init(model):
    """
    Initialize the server. Loads pyfunc model from the path.
    """
    app = flask.Flask(__name__)

    @app.route('/ping', methods=['GET'])
    def ping():  # pylint: disable=unused-variable
        """
        Determine if the container is working and healthy.
        We declare it healthy if we can load the model successfully.
        """
        health = model is not None
        status = 200 if health else 404
        return flask.Response(response='\n', status=status, mimetype='application/json')

    @app.route('/invocations', methods=['POST'])
    def transformation():  # pylint: disable=unused-variable
        """
        Do an inference on a single batch of data. In this sample server,
        we take data as CSV or json, convert it to a pandas data frame,
        generate predictions and convert them back to CSV.
        """
        # Convert from CSV to pandas
        if flask.request.content_type == 'text/csv':
            data = flask.request.data.decode('utf-8')
            s = StringIO(data)
            data = pd.read_csv(s)
        elif flask.request.content_type == 'application/json':
            data = flask.request.data.decode('utf-8')
            s = StringIO(data)
            data = pd.read_json(s, orient="records")
        else:
            return flask.Response(
                response='This predictor only supports CSV of josn  data, got %s' % str(
                    flask.request.content_type), status=415, mimetype='text/plain')

        print('Invoked with {} records'.format(data.shape[0]))
        # Do the prediction
        predictions = model.predict(data)
        # Convert from numpy back to CSV
        out = StringIO()
        pd.DataFrame({'results': predictions}).to_csv(out, header=True, index=False)
        result = out.getvalue()
        # TODO: do we always return csv or do we return the same type as the
        # input? or do we add parameter?
        return flask.Response(response=result, status=200, mimetype='text/csv')
    return app
