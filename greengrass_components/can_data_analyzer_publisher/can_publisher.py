#!/usr/bin/env python3

import json
import serial
import awsiot.greengrasscoreipc
import awsiot.greengrasscoreipc.model as model
from time import sleep
from datetime import datetime
import threading
from collections import deque
import os
import argparse  # Import the argparse module

THING_NAME = os.getenv('AWS_IOT_THING_NAME', '')

def collectData(queue, serial_port):
    id=1
    print("collectData")
    try:
        print("connecting to serial")
        ser = serial.Serial(serial_port, 115200)  # Use the serial_port argument
        print("connected to serial ")
    except:
        print("Failed to connect to serial, should retry \n")
    while True:
        try:
            can_data = ser.readline().decode()
            dictData = json.loads(can_data)
            dictData["ts_component"] = str(datetime.now())
            dictData["id"] = "4" + str(id)
            jsonData = json.dumps(dictData)
            queue.append(jsonData)
            id += 1
        except Exception as se:
            print("Failed to connect to read from serial", se)
            try:
                ser = serial.Serial(serial_port, 115200)  # Use the serial_port argument
            except:
                print("Serial broken, retry in 2 seconds")
                sleep(2)

def sendData(queue):
    ipc_client = awsiot.greengrasscoreipc.connect()
    while True:
        while len(queue) != 0:
            topic= f'dt/pubCANdataPy/embedded-metrics/{THING_NAME}/can'
            op = ipc_client.new_publish_to_iot_core()
            msg = queue.popleft().encode()
            op.activate(model.PublishToIoTCoreRequest(
                topic_name=topic,
                qos=model.QOS.AT_LEAST_ONCE,
                payload=msg,
            ))
            try:
                result = op.get_response().result(timeout=10.0)
                # print("successfully published message:", result)
            except Exception as e:
                print("failed to publish message:", e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Serial port reader.')
    parser.add_argument('serial_port', type=str, help='Serial port to connect to (e.g., /dev/ttyLF1)')
    args = parser.parse_args()

    sleep(15)
    
    data = deque([])
    print("starting")
    threading.Thread(target=collectData, args=(data, args.serial_port)).start()  # Pass the serial port argument
    threading.Thread(target=sendData, args=(data, )).start()
