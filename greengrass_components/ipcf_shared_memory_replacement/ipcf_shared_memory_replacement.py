#!/usr/bin/python3

import can
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import (
    PublishMessage,
    BinaryMessage
)
from time import sleep
import time
import traceback

# global CAN read success counter
successCount = 0

def processCan(can):
            # this will consumed by the greengrass_stats_publisher
            topic= 'topic/localGGProc'

            # must be <= 256
            dataSize = 256

            # we assume there is no read error
            errorCount = 0

            # processCAN is called for every single CAN message
            global successCount
            successCount += 1

            # epoch in seconds
            epoch_time = int(time.time())

            payload = "PROC\nDataSize " + str(dataSize) + "\nSuccess " + str(successCount) + "\nError " + str(errorCount)+"\nPreTS "+ str(epoch_time)
            print (payload)
            try:
                publish_message = PublishMessage(binary_message=BinaryMessage(message=bytes(payload, 'utf-8')))
                ipc_client.publish_to_topic(topic=topic, publish_message=publish_message)
                print('Successfully published to topic: ' + topic)
            except Exception:
                print('Exception occurred')
                traceback.print_exc()

try:
    sleep(15)
    ipc_client = GreengrassCoreIPCClientV2()
    bus = can.interface.Bus(channel='can0', bustype='socketcan')
    notifier = can.Notifier(bus,[processCan])
except:
    print("Failed to connect to CAN, should retry \n")
while True:
    sleep(1)
