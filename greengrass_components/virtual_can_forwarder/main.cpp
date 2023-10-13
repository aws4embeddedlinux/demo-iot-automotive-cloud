#include <iostream>
#include <thread>
#include <fstream>
#include <aws/crt/Api.h>
#include <aws/greengrass/GreengrassCoreIpcClient.h>
#include <fmt/core.h>
#include <time.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <net/if.h>

using namespace Aws::Crt;
using namespace Aws::Greengrass;

static unsigned long messageNo = 0;

int socket_fd;

// Function to send CAN frames via SocketCAN
void sendCANFrame(int socket_fd, int can_id, unsigned char* frame_data, int length) {
    struct can_frame frame;

    // Prepare CAN frame
    frame.can_id = can_id;
    frame.can_dlc = length;
    memcpy(frame.data, frame_data, length);

    // Send CAN frame
    write(socket_fd, &frame, sizeof(struct can_frame));

}

// subscriber handler
class SubscribeResponseHandler : public SubscribeToTopicStreamHandler {
    public:
        virtual ~SubscribeResponseHandler() {}
    private:
        void OnStreamEvent(SubscriptionResponseMessage *response) override {
            // Assuming the payload contains CAN ID and CAN frame
            auto jsonMessage = response->GetJsonMessage();
            
            if (jsonMessage.has_value() && jsonMessage.value().GetMessage().has_value()) {
                auto messageString = jsonMessage.value().GetMessage().value().View().WriteReadable();
                std::string msg = std::string(messageString.begin(), messageString.end());

                // Parse CAN ID and CAN frame from msg
                int can_id;
                unsigned char frame_data[8];
                // Implement parsing logic here

                // Send CAN frame via SocketCAN
                sendCANFrame(socket_fd, can_id, frame_data, 8);
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


    struct sockaddr_can addr;
    struct ifreq ifr;

    // Create socket
    socket_fd = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    strcpy(ifr.ifr_name, "vcan0");
    ioctl(socket_fd, SIOCGIFINDEX, &ifr);

    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    bind(socket_fd, (struct sockaddr *)&addr, sizeof(addr));
    
    String topic("topic/localCAN");
    
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
        
        std::this_thread::sleep_for(std::chrono::seconds(10));
    }

    operation->Close();
    close(socket_fd);

    return 0;
}