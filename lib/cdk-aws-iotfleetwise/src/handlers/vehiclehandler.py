import json
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

client_iot = boto3.client("iot")

def on_event(event, context):
    logger.info(f"on_event {event} {context}")
    request_type = event["RequestType"]
    if request_type == "Create":
        return on_create(event, context)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)
    raise Exception("Invalid request type: {request_type}")


def on_create(event, context):
    props = event["ResourceProperties"]
    logger.info(f"create new resource with props {props}")
    ret = {"PhysicalResourceId": props["vehicle_name"]}

    if props["create_iot_thing"] == "true":
        logger.info("creating certificate for iot thing")
        response_iot = client_iot.create_keys_and_certificate(setAsActive=True)
        logger.info(f"create_keys_and_certificate response {response_iot}")
        ret["Data"] = {
            "certificateId": response_iot["certificateId"],
            "certificateArn": response_iot["certificateArn"],
            "certificatePem": response_iot["certificatePem"],
            "privateKey": response_iot["keyPair"]["PrivateKey"],
        }
        response = client_iot.describe_endpoint(endpointType="iot:Data-ATS")
        logger.info(f"describe_endpoint response {response}")
        ret["Data"]["endpointAddress"] = response["endpointAddress"]

    response = client.create_vehicle(
        associationBehavior="CreateIotThing" if (props["create_iot_thing"] == "true") else "ValidateIotThingExists",
        vehicleName=props["vehicle_name"],
        modelManifestArn=props["model_manifest_arn"],
        decoderManifestArn=props["decoder_manifest_arn"],
        #attributes=props["attributes"],
    )
    logger.info(f"create_vehicle response {response}")
    return ret


def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    logger.info(f"update resource {physical_id} with props {props}")
    raise Exception("update not implemented yet")
    # return { 'PhysicalResourceId': physical_id }


def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    logger.info(f"delete resource {props['vehicle_name']} {physical_id}")

    response = client.delete_vehicle(vehicleName=props["vehicle_name"])
    logger.info(f"delete_vehicle response {response}")

    if props["create_iot_thing"] == "true":
        response_iot = client_iot.list_thing_principals(thingName=props["vehicle_name"])
        logger.info(f"list_thing_principals response {response_iot}")

        for cert in response_iot["principals"]:
            logger.info(f"delete_certificate {cert}")
            response_delete = client_iot.delete_certificate(certificateId=cert, forceDelete=True)
            logger.info(f"delete_certificate response {response_delete}")

        logger.info(f"delete_thing")
        response_delete_thing = client_iot.delete_thing(thingName=props["vehicle_name"])
        logger.info(f"delete_thing response {response_delete_thing}")
    return {"PhysicalResourceId": physical_id}