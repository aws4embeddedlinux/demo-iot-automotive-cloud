import json
import time
import logging as logger
import boto3
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
    logger.info(f"on_event {event} {context}")
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

    if props['useS3'] == 'true':
        campaignS3arn = props['campaign_s3_arn']
        data_format = props.get('data_format', 'JSON')
        prefix = props.get('prefix', '')

        response = client.create_campaign(
            name=props['name'],
            signalCatalogArn=props['signal_catalog_arn'],
            targetArn=props['target_arn'],
            collectionScheme=json.loads(props['collection_scheme']),
            compression=props['compression'],
            postTriggerCollectionDuration=int(props.get('post_trigger_collection_duration', 0)),
            signalsToCollect=json.loads(props['signals_to_collect']),
            spoolingMode=props['spooling_mode'],
            dataDestinationConfigs=[
                {
                    's3Config': {
                        'bucketArn': campaignS3arn,
                        'dataFormat': data_format,
                        'prefix': prefix
                    }
                }
            ]
        )
        logger.info(f"create_campaign response {response}")

    if props['useS3'] == 'false':
        timestream_arn = props['timestream_arn']
        fw_timestream_role = props['fw_timestream_role']

        response = client.create_campaign(
            name=props['name'],
            signalCatalogArn=props['signal_catalog_arn'],
            spoolingMode=props['spooling_mode'],
            targetArn=props['target_arn'],
            compression=props['compression'],
            postTriggerCollectionDuration=int(props.get('post_trigger_collection_duration', 0)),
            collectionScheme=json.loads(props['collection_scheme']),
            signalsToCollect=json.loads(props['signals_to_collect']),
            dataDestinationConfigs=[
                {
                    'timestreamConfig': {
                        'timestreamTableArn': timestream_arn,
                        'executionRoleArn': fw_timestream_role,
                    }
                }
            ]
        )
        logger.info(f"create_campaign response {response}")

    if props['auto_approve'] == 'true':
        retry_count = 10;
        delay = 2;
        while retry_count > 1:
            print(f"waiting for campaign {props['name']} to be created")
            response = client.get_campaign(name=props['name'])
            print(f"get_campaign response {response}")
            if response['status'] == "WAITING_FOR_APPROVAL":
                break
            time.sleep(delay)
            retry_count = retry_count - 1
        print(f"approving the campaign {props['name']}")
        response = client.update_campaign(
            name=props['name'],
            action='APPROVE'
        )
        logger.info(f"update_campaign response {response}")
    return {'PhysicalResourceId': props['name']}


def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    logger.info(f"update resource {physical_id} with props {props}")
    response = client.update_campaign(
        name=props['name'],
        action=props.get('action', 'UPDATE')
    )
    logger.info(f"update_campaign response {response}")
    # raise Exception("update not implemented yet")
    return {'PhysicalResourceId': physical_id}


def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    print(f"delete resource {props['name']} {physical_id}")

    response = client.delete_campaign(
        name=props['name'],
    )
    logger.info(f"delete_campaign response {response}")

    return {'PhysicalResourceId': physical_id}
