#!/usr/bin/python3

import can
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import (
    PublishMessage,
    BinaryMessage
)
import time
import traceback
import threading

import argparse

# Global variables for data aggregation
successCount = 0
aggregateData = {
    'successCount': 0,
    'errorCount': 0
}

TOPIC = 'topic/localGGProc'

def processCan(can):
    global aggregateData
    aggregateData['successCount'] += 1

def publish_aggregated_data():
    global ipc_client, aggregateData

    while True:
        time.sleep(int(args.timeout))  # Wait for 10 seconds before publishing
        epoch_time = int(time.time())

        payload = (
            f"PROC\nDataSize 256\nSuccess {aggregateData['successCount']}\n"
            f"Error {aggregateData['errorCount']}\nPreTS {epoch_time}"
        )
        print(payload)

        try:
            publish_message = PublishMessage(binary_message=BinaryMessage(message=bytes(payload, 'utf-8')))
            ipc_client.publish_to_topic(topic=TOPIC, publish_message=publish_message)
            print(f'Successfully published to topic: {TOPIC}')
        except Exception:
            print('Exception occurred')
            traceback.print_exc()

        # Reset aggregated data
        aggregateData = {
            'successCount': 0,
            'errorCount': 0
        }

parser = argparse.ArgumentParser()
parser.add_argument("--timeout", default=10)
args = parser.parse_args()

try:
    ipc_client = GreengrassCoreIPCClientV2()
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    notifier = can.Notifier(bus, [processCan])

    # Start the periodic data publish thread
    threading.Thread(target=publish_aggregated_data, daemon=True).start()

except Exception:
    print("Failed to connect to CAN, should retry \n")
    traceback.print_exc()

# Main loop
while True:
    time.sleep(1)  # To keep the main thread alive
