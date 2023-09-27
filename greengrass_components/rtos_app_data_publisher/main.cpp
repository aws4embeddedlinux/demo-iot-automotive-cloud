#include <iostream>
#include <thread>
#include <fstream>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <aws/crt/Api.h>
#include <aws/greengrass/GreengrassCoreIpcClient.h>
#include <fmt/core.h>
#include <time.h>

using namespace Aws::Crt;
using namespace Aws::Greengrass;

#ifdef DEBUG
bool publishFake = true;
#else
bool publishFake = false;
#endif

// global scope client publishing to IoT Core
static GreengrassCoreIpcClient* mqttPub;

// maintain unique ID of device
static std::string deviceId = "1-";
static unsigned long messageNo = 0;

// structs to represent data to be sent as payload
struct RTOSAppData {
    std::string deviceTS;
    std::string runtimeName;
    std::string priority;
    std::string absTime;
    std::string percentage;
    std::string idle;
    int usage;
    std::string reads;
    std::string response;
    std::string statusName;
    std::string status;
    std::string success;
    std::string error;
};

// function for getting current time
static std::string getCurrentTime () {
    std::time_t seconds = std::time(0);
    std::stringstream ss;
    ss << seconds;
    std::string ts = ss.str();
    
    return ts;
}

// function to create fake RTOS App stats, for testing ingestion pipeline
std::string createAppStats(RTOSAppData& data) {
    
    // retrieve current time for timestamp
    std::string timeStr = getCurrentTime();
    
    // JSON formatted string as payload
    std::string json(fmt::format("\
    {{ \
    \"name\": \"FreeRTOSApp\",\n\
    \"id\": \"{0}\",\n\
    \"ts_component\": \"{1}\",\n\
    \"ts_device\": \"{2}\",\n\
    \"TaskRuntimeStats\": \n{{\
        \"RuntimeName\": \"{3}\",\n\
        \"Priority\": {4},\n\
        \"AbsTime\": {5},\n\
        \"PercentageTime\": {6},\n\
        \"IdleTime\": {7},\n\
        \"ResourceUsage\": {8},\n\
        \"CANReadCount\": {9},\n\
        \"ResponseTime\": {10}\n\
        \n}},\
    \"TaskCurrentStatus\": \n{{\
        \"CurrentStatusName\": \"{11}\",\n\
        \"Status\": \"{12}\"\n\
        \n}},\
    \"ProcessingStats\": \n{{\
        \"MailboxWriteSuccessCount\": {13},\n\
        \"MailboxWriteErrorCount\": {14}\n\
        \n}}\
    }}\
    ", deviceId + std::to_string(messageNo), timeStr, data.deviceTS, data.runtimeName, data.priority, data.absTime, 
    data.percentage, data.idle, data.usage, data.reads, data.response, 
    data.statusName, data.status, data.success, data.error));
    
    return json;
}

// publishes messageStr to rtos-app MQTT topic
void publishMessage(String& messageStr) {
    
    //String messageStr((char*) message);
    std::cout << "Publishing message " << messageStr << std::endl;
    String topicStr("dt/pubRTOSAppData/embedded-metrics/Goldbox/rtos-app");
    
    QOS qos = QOS_AT_LEAST_ONCE;
    // 10 second timeout if no response from GG IoT Core
    int timeout = 10;
    
    PublishToIoTCoreRequest request;
    Vector<uint8_t> messageData({messageStr.begin(), messageStr.end()});
    request.SetTopicName(topicStr);
    request.SetPayload(messageData);
    request.SetQos(qos);
    
    auto operation = mqttPub->NewPublishToIoTCore();
    auto activate = operation->Activate(request, nullptr);
    activate.wait();
    
    auto responseFuture = operation->GetResult();
    if (responseFuture.wait_for(std::chrono::seconds(timeout)) == std::future_status::timeout) {
        std::cerr << "Operation timed out while waiting for response from Greengrass Core." << std::endl;
    }

    auto response = responseFuture.get();
    if (response) {
        std::cout << "Successfully published to the topic: " << topicStr << std::endl;
    } else {
        // An error occurred.
        std::cout << "Failed to publish to topic: " << topicStr << std::endl;
        auto errorType = response.GetResultType();
        if (errorType == OPERATION_ERROR) {
            auto *error = response.GetOperationError();
            std::cout << "Operation error: " << error->GetMessage().value() << std::endl;
        } else {
            std::cout << "RPC error: " << response.GetRpcError() << std::endl;
        }
    }
}

// helper class for string parsing
class ReadData {
    public:
        std::string absTime;
        std::string percentageTime;
        std::string priority;
        
        static std::string getNumeric(std::string str) {
            std::string numericOnly;
            for (int i = 0; i < str.size(); i++) {
                if (isdigit(str[i]))
                    numericOnly += str[i];
            }
            
            return numericOnly;
        }
        
        ReadData(std::string at, std::string pt) {
            absTime = at;
            percentageTime = getNumeric(pt); // parse ex <1%
            priority = "0";
        }
};

// Creates a list of stats strings (each representing a different task) to be published
std::vector<String> produceJSON(std::string str) {
    std::vector<String> ret;
    std::unordered_map<std::string, ReadData*> appData;
    
    std::istringstream iss(str);
    std::string idleTime;
    std::string readCount;
    std::string successCount;
    std::string errorCount;
    std::string responseTime;
    std::string deviceTS;
    
    std::string line;
    while (std::getline(iss, line)) {
        std::istringstream rmWhiteSpace(line);
        std::vector<std::string> words;
        std::string word;
        
        while (rmWhiteSpace >> word) {
            words.push_back(word);
        }
        
        if (words.size() == 0 || words[0] == "Tmr" || words[0] == "softirq" || words[0] == "T" || words[0] == "") {
            continue;
        } else if (words[0] == "IDLE") {
            if (words.size() == 3) 
                idleTime = words[1];
        } else if (words[0] == "S") {
            successCount = words[1];
        } else if (words[0] == "E") {
            errorCount = words[1];
        } else if (words[0] == "P") {
            readCount = words[1];
        } else if (words[0] == "R") {
            responseTime = words[1];
        } else if (words[0] == "PreTS") {
            deviceTS = words[1];
        } else {
            auto it = appData.find(words[0]);
            // if missing in hashmap, then must be newly reading stats table data:
            if (it == appData.end()) {
                appData[words[0]] = new ReadData(words[1], words[2]);
            } else {
                ReadData* rtosApp = appData[words[0]];
                rtosApp->priority = words[1];
            }
        }
        
    }
    
    for (auto& it: appData) {
        std::string key = it.first;
        ReadData* value = it.second;
        
        RTOSAppData data = {
            deviceTS,
            key, // runtime name
            value->priority, // priority
            value->absTime, // absTime
            value->percentageTime, // percentageTime
            idleTime, // idle time
            -1, // resource usage 
            readCount, // CAN read count
            responseTime, // response time
            "N/A", // status name
            "N/A", // status
            successCount, // success count
            errorCount // error cont
        };
        
        String messageRTOS(createAppStats(data).c_str());
        ret.push_back(messageRTOS);
    }

    return ret;
}

// subscriber handler
class SubscribeResponseHandler : public SubscribeToTopicStreamHandler {
    public:
        virtual ~SubscribeResponseHandler() {}
    private:
        void OnStreamEvent(SubscriptionResponseMessage *response) override {
            auto jsonMessage = response->GetJsonMessage();
            std::vector<String> msgs;
            if (jsonMessage.has_value() && jsonMessage.value().GetMessage().has_value()) {
                String messageString = jsonMessage.value().GetMessage().value().View().WriteReadable();
                msgs = produceJSON(std::string(messageString.begin(), messageString.end()));
                std::cout << "Received new message: " << messageString << std::endl;
                //publishMessage(msg);
            } else {
                auto binaryMessage = response->GetBinaryMessage();
                if (binaryMessage.has_value() && binaryMessage.value().GetMessage().has_value()) {
                    auto messageBytes = binaryMessage.value().GetMessage().value();
                    std::string messageString(messageBytes.begin(), messageBytes.end());
                    std::cout << "Received new message: " << messageString << std::endl;
                    msgs = produceJSON(messageString);
                    //publishMessage(msg);
                }
            }
            
            for (String msg : msgs) {
                publishMessage(msg);
            }
            
            messageNo++;
        }

        bool OnStreamError(OperationError *error) override {
            std::cout << "Received an operation error: ";
            if (error->GetMessage().has_value()) {
                std::cout << error->GetMessage().value();
            }
            std::cout << std::endl;
            return false; // Return true to close stream, false to keep stream open.
        }

        void OnStreamClosed() override {
            std::cout << "Subscribe to topic stream closed." << std::endl;
        }
};

class IpcClientLifecycleHandler : public ConnectionLifecycleHandler {
    void OnConnectCallback() override {
        std::cout << "OnConnectCallback" << std::endl;
    }

    void OnDisconnectCallback(RpcError error) override {
        std::cout << "OnDisconnectCallback: " << error.StatusToString() << std::endl;
        exit(-1);
    }

    bool OnErrorCallback(RpcError error) override {
        std::cout << "OnErrorCallback: " << error.StatusToString() << std::endl;
        return true;
    }
};

int main() {
    
    String topic("topic/localRTOSApp");
    
    int timeout = 10;

    ApiHandle apiHandle(g_allocator);
    Io::EventLoopGroup eventLoopGroup(1);
    Io::DefaultHostResolver socketResolver(eventLoopGroup, 64, 30);
    Io::ClientBootstrap bootstrap(eventLoopGroup, socketResolver);
    IpcClientLifecycleHandler ipcLifecycleHandler;
    GreengrassCoreIpcClient ipcClient(bootstrap);
    
    auto connectionStatus = ipcClient.Connect(ipcLifecycleHandler).get();
    if (!connectionStatus) {
        std::cerr << "Failed to establish IPC connection: " << connectionStatus.StatusToString() << std::endl;
        exit(-1);
    }
    
    // connect to MQTT here
    Io::EventLoopGroup eventLoopGroup2(1);
    Io::DefaultHostResolver socketResolver2(eventLoopGroup2, 64, 30);
    Io::ClientBootstrap bootstrap2(eventLoopGroup2, socketResolver2);
    IpcClientLifecycleHandler ipcLifecycleHandler2;
    mqttPub = new GreengrassCoreIpcClient(bootstrap2);
    
    auto connectionStatus2 = mqttPub->Connect(ipcLifecycleHandler2).get();
    if (!connectionStatus2) {
        std::cerr << "Failed to establish MQTT connection: " << connectionStatus2.StatusToString() << std::endl;
        exit(-1);
    }
    
    SubscribeToTopicRequest request;
    request.SetTopic(topic);
    auto streamHandler = MakeShared<SubscribeResponseHandler>(DefaultAllocator());
    auto operation = ipcClient.NewSubscribeToTopic(streamHandler);
    auto activate = operation->Activate(request, nullptr);
    activate.wait();

    auto responseFuture = operation->GetResult();
    if (responseFuture.wait_for(std::chrono::seconds(timeout)) == std::future_status::timeout) {
        std::cerr << "Operation timed out while waiting for response from Greengrass Core." << std::endl;
        exit(-1);
    }
    
    auto response = responseFuture.get();
    if (response) {
        std::cout << "Successfully subscribed to topic: " << topic << std::endl;
    } else {
        // An error occurred.
        std::cout << "Failed to subscribe to topic: " << topic << std::endl;
        auto errorType = response.GetResultType();
        if (errorType == OPERATION_ERROR) {
            auto *error = response.GetOperationError();
            std::cout << "Operation error: " << error->GetMessage().value() << std::endl;
        } else {
            std::cout << "RPC error: " << response.GetRpcError() << std::endl;
        }
        exit(-1);
    }
    
    
    // Keep the main thread alive, or the process will exit.
    while (true) {
        
        if (publishFake) {
            RTOSAppData fakeData = {
                "1-1", // device-ID
                "SampleRTName", // runtime name
                std::to_string(std::rand()), // priority
                std::to_string(std::rand()), // absTime
                std::to_string(std::rand()), // percentageTime
                std::to_string(std::rand()), // idle time
                std::rand(), // resource usage 
                std::to_string(std::rand()), // CAN read count
                std::to_string(std::rand()), // response time
                "SampleName", // status name
                "SampleStatus", // status
                std::to_string(std::rand()), // success count
                std::to_string(std::rand()) // error cont
            };
            
            String messageRTOS(createAppStats(fakeData).c_str());
            publishMessage(messageRTOS);
        }
        
        std::this_thread::sleep_for(std::chrono::seconds(10));
        
    }

    operation->Close();

    return 0;
}