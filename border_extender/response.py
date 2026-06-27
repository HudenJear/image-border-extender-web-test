import json

from flask import Response
import logging


def _is_empty(value):
    """Helper to determine if a response data payload is empty."""
    if value is None:
        return True
    if isinstance(value, (dict, list, tuple, set, str)):
        return len(value) == 0
    return False


def make_succ_empty_response():
    payload = {'code': 0, 'data': {}}
    # Log success with empty data explicitly
    logging.info("Response success | code=0 | data_empty=True")
    data = json.dumps(payload)
    return Response(data, mimetype='application/json')


def make_succ_response(data):
    is_empty = _is_empty(data)
    # Log success and whether data is empty
    logging.info(f"Response success | code=0 | data_empty={is_empty}")
    data = json.dumps({'code': 0, 'data': data})
    return Response(data, mimetype='application/json')


def make_err_response(err_msg):
    # Log error text content
    logging.error(f"Response error | code=-1 | errorMsg={err_msg}")
    data = json.dumps({'code': -1, 'errorMsg': err_msg})
    return Response(data, mimetype='application/json')
