#include <iostream>
#include <cstdlib>
#include <thread>
#include <fstream>
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

std::string thing_name;

// global scope client publishing to IoT Core
static GreengrassCoreIpcClient* mqttPub;

// maintain unique ID of device
static std::string deviceId = "3-";
static unsigned long messageNo = 0;

// function to create fake GG processing stats, for testing ingestion pipeline
std::string createGGProcessingStats(std::string preprocTS, std::string bitsSent, std::string success, std::string error) {
    // retrieve current time for timestamp
    std::time_t seconds = std::time(0);
    std::stringstream ss;
    ss << seconds;
    std::string timeStr = ss.str();
    
    // JSON formatted string as payload
    std::string json(fmt::format("\
    {{ \
    \"name\": \"GreengrassProcessing\",\n\
    \"id\": \"{0}\",\n\
    \"ts_component\": \"{1}\",\n\
    \"ts_device\": \"{2}\",\n\
    \"IPCProcessingStats\": \n{{\
        \"BitsSent\": {3}\n\
    \n}},\
    \"MailboxProcessingStats\": \n{{\
        \"MailboxReadSuccessCount\": {4},\n\
        \"MailboxReadErrorCount\": {5}\n\
    \n}}\
    }}\
    ", deviceId + std::to_string(messageNo), timeStr, preprocTS, bitsSent, success, error));
    
    return json;
}


// produce the JSON from ipc fed string
String produceJSON(std::string procStr) {
    std::istringstream iss(procStr);
    std::string line;
    
    std::string bitsSent;
    std::string success;
    std::string error;
    std::string preprocTS;
    
    std::getline(iss, line);
    assert(line == "PROC");
    
    while (std::getline(iss, line)) {
        std::istringstream rmWhiteSpace(line);
        std::vector<std::string> words;
        std::string word;
        
        while (rmWhiteSpace >> word) {
            words.push_back(word);
        }
        
        // convention is using "DataSize"
        if (words[0] == "DataSize")
            bitsSent = words[1];
        else if (words[0] == "Success")
            success = words[1];
        else if (words[0] == "Error")
            error = words[1];
        else if (words[0] == "PreTS")
            preprocTS = words[1];
    }
    
    std::string stats = createGGProcessingStats(preprocTS, bitsSent, success, error);
    String msg(stats.c_str());
    return msg;
}

// publishes messageStr to MQTT topic
void publishMessage(String& messageStr) {
    
    //String messageStr((char*) message);
    std::cout << "Publishing message " << messageStr << std::endl;

    std::string topicStrStd = "dt/pubRTOSAppData/embedded-metrics/" + thing_name + "/gg-processing";

    String topicStr(topicStrStd.c_str());
    
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

// subscriber handler
class SubscribeResponseHandler : public SubscribeToTopicStreamHandler {
    public:
        virtual ~SubscribeResponseHandler() {}
    private:
        void OnStreamEvent(SubscriptionResponseMessage *response) override {
            auto jsonMessage = response->GetJsonMessage();
            
            if (jsonMessage.has_value() && jsonMessage.value().GetMessage().has_value()) {
                auto messageString = jsonMessage.value().GetMessage().value().View().WriteReadable();
                std::string msg = std::string(messageString.begin(), messageString.end());
                std::cout << "Received new message: " << msg << std::endl;
                String msgString = produceJSON(msg);
                publishMessage(msgString);
            } else {
                auto binaryMessage = response->GetBinaryMessage();
                if (binaryMessage.has_value() && binaryMessage.value().GetMessage().has_value()) {
                    auto messageBytes = binaryMessage.value().GetMessage().value();
                    std::string msg(messageBytes.begin(), messageBytes.end());
                    std::cout << "Received new message: " << msg << std::endl;
                    String msgString = produceJSON(msg);
                    publishMessage(msgString);
                }
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
    
    String topic("topic/localGGProc");
    
    int timeout = 10;
    // Get a thing name from the env variable set by GG
    thing_name = std::getenv("AWS_IOT_THING_NAME") ? std::getenv("AWS_IOT_THING_NAME") : "";

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
            std::string fakeData = createGGProcessingStats(std::to_string(std::rand()),
            std::to_string(std::rand()), std::to_string(std::rand()), std::to_string(std::rand()));
            
            String messageRTOS(fakeData.c_str());
            publishMessage(messageRTOS);
        }
        
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }

    operation->Close();

    return 0;
}