import logging as logger
import boto3
import json
import os

logger.getLogger().setLevel(logger.INFO)

CUSTOM_ENDPOINT = os.getenv('FW_ENDPOINT_URL')
if CUSTOM_ENDPOINT is None:
    client=boto3.client('iotfleetwise')
else:
    session = boto3.Session()
    session._loader.search_paths.extend([os.path.dirname(os.path.abspath(__file__)) + "/models"])
    client = session.client("iotfleetwise", endpoint_url=CUSTOM_ENDPOINT)

def on_event(event, context):
    logger.info(event)
    request_type = event['RequestType']
    if request_type == 'Create': 
        return on_create(event)
    if request_type == 'Update': 
        return on_update(event)
    if request_type == 'Delete': 
        return on_delete(event)
    raise Exception("Invalid request type: {request_type}")

def on_create(event):
    props = event["ResourceProperties"]
    logger.info(f"create new resource with props {props}")

    response = client.create_signal_catalog(
      name = props['name'],
      description = props['description'],
      nodes = json.loads(props['nodes'])
    )
    logger.info(f"create signal catalog response: {response}")
    return { 'PhysicalResourceId': props['name'] }

def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    logger.info(f"update resource {physical_id} with props {props}")
    raise Exception("update not implemented yet")
    #return { 'PhysicalResourceId': physical_id }

def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    logger.info(f"delete resource {props['name']} {physical_id}")
    response = client.delete_signal_catalog(
      name = props['name']
    )
    logger.info(f"delete signal catalog response: {response}")
    return { 'PhysicalResourceId': physical_id }
