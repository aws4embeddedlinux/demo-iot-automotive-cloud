import json
import serial
import awsiot.greengrasscoreipc
import awsiot.greengrasscoreipc.model as model
from time import sleep
from datetime import datetime
import threading
from collections import deque


def collectData(queue):
    id=1
    try:
        ser= serial.Serial('/dev/ttyLF0', 115200)
        # print("connected to serial ")
    except:
        print("Failed to connect to serial, should retry \n")
    while True:
        try:
            # print("trying to read serial \n")
            can_data= ser.readline().decode()
            dictData= json.loads(can_data)
            dictData["ts_component"] = str(datetime.now())
            dictData["id"]= "4" + str(id)
            jsonData= json.dumps(dictData)
            queue.append(jsonData)
            id+=1
        except Exception as se:
            print("Failed to connect to read from serial", se)
            try:
                ser= serial.Serial('/dev/ttyLF0', 115200)
            except:
                print("Serial broken, retry in 2 seconds")
                sleep(2)

def sendData(queue):
    ipc_client = awsiot.greengrasscoreipc.connect()
    while True:
        while len(queue) != 0:
            topic= 'dt/pubCANdataPy/embedded-metrics/Goldbox/can'
            op = ipc_client.new_publish_to_iot_core()
            op.activate(model.PublishToIoTCoreRequest(
                topic_name=topic,
                qos=model.QOS.AT_LEAST_ONCE,
                payload=queue.popleft().encode(),
            ))
            try:
                result = op.get_response().result(timeout=10.0)
                # print("successfully published message:", result)
            except Exception as e:
                print("failed to publish message:", e)

if __name__ == '__main__':
    sleep(15)
    
    data= deque([])
    threading.Thread(target= collectData, args=(data, )).start()
    threading.Thread(target= sendData, args=(data, )).start()

