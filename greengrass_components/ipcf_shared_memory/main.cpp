// importing C libraries here
extern "C" {
#include "ipcf.h"
}

// import rest of libraries
#include <time.h>
#include <iostream>
#include <thread> 
#include <fstream>
#include <sstream>
#include <aws/crt/Api.h>
#include <aws/greengrass/GreengrassCoreIpcClient.h>
#include <fmt/core.h>

using namespace Aws::Crt;
using namespace Aws::Greengrass;

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

// create global scope ipcClient
static GreengrassCoreIpcClient* ipcClient;
    
// publishes messageStr to MQTT topic, return true if successful, false otherwise
bool publishMessage(String& messageStr, std::string const& topic) {
    String topicStr(topic.c_str());
    // 10 second timeout if no response from GG IoT Core
    int timeout = 10;
    
    PublishToTopicRequest request;
    Vector<uint8_t> messageData({messageStr.begin(), messageStr.end()});
    BinaryMessage binaryMessage;
    binaryMessage.SetMessage(messageData);
    PublishMessage publishMessage;
    publishMessage.SetBinaryMessage(binaryMessage);
    request.SetTopic(topicStr);
    request.SetPublishMessage(publishMessage);

    auto operation = ipcClient->NewPublishToTopic();
    auto activate = operation->Activate(request, nullptr);
    activate.wait();

    auto responseFuture = operation->GetResult();
    if (responseFuture.wait_for(std::chrono::seconds(timeout)) == std::future_status::timeout) {
        std::cerr << "Operation timed out while waiting for response from Greengrass Core." << std::endl;
        return false;
    }

    auto response = responseFuture.get();
    if (response) {
        std::cout << "Successfully published to the topic: " << topic << std::endl;
    } else {
        // An error occurred.
        std::cout << "Failed to publish to topic: " << topic << std::endl;
        auto errorType = response.GetResultType();
        if (errorType == OPERATION_ERROR) {
            auto *error = response.GetOperationError();
            std::cout << "Operation error: " << error->GetMessage().value() << std::endl;
        } else {
            std::cout << "RPC error: " << response.GetRpcError() << std::endl;
        }
        return false;
    }
    
    return true;
}

// IPCF code 
extern struct ipc_sample_app {
	int num_channels;
	int num_msgs;
	char *ctrl_shm;
	volatile int last_rx_no_msg;
	char last_tx_msg[L_BUF_LEN];
	char last_rx_msg[L_BUF_LEN];
	int *local_virt_shm;
	int mem_fd;
	size_t local_shm_offset;
	int *local_shm_map;
	sem_t sema;
	uint8_t instance;
} app;


// function for getting current time (prior to processing)
static std::string getPreprocTime() {
    std::time_t seconds = std::time(0);
    std::stringstream ss;
    ss << "\nPreTS "; // need to prepend newline for newline parsing
    ss << seconds;
    std::string ts = ss.str();
    
    return ts;
}

// called by IPCF function, needs to be of type void* (void*) to
// comply with thread signature convention
void* sendToGreengrass(void *tmp) {
    strcat((char*) tmp, getPreprocTime().c_str()); // append a preprocessing timestamp
    String data((char*) tmp);
	
	// read first line, to see which topic to send to
	std::string ipcStr = std::string(data.begin(), data.end());
	std::istringstream iss(ipcStr);
    std::string line;
    std::getline(iss, line);
    
    if (line == "OS")
        publishMessage(data, "topic/localRTOSOS");
    else if (line == "CAN")
        publishMessage(data, "topic/localCAN");
    else if (line == "PROC")
        publishMessage(data, "topic/localGGProc");
    else
	    publishMessage(data, "topic/localRTOSApp");
	    
	return NULL;
	
}

int main(int argc, char *argv[])
{
    // setup GG IPC client
    ApiHandle apiHandle(g_allocator);
    Io::EventLoopGroup eventLoopGroup(1);
    Io::DefaultHostResolver socketResolver(eventLoopGroup, 64, 30);
    Io::ClientBootstrap bootstrap(eventLoopGroup, socketResolver);
    
    ipcClient = new GreengrassCoreIpcClient(bootstrap);
    IpcClientLifecycleHandler ipcLifecycleHandler;
    auto connectionStatus = ipcClient->Connect(ipcLifecycleHandler).get();
    
    // error if fails connection
    if (!connectionStatus) {
        std::cerr << "Failed to establish IPC connection: " << connectionStatus.StatusToString() << std::endl;
        exit(-1);
    }
    
    // set up IPCF stuff
	int err = 0;
	struct sigaction sig_action;
	app.instance = 0;
	size_t page_size = sysconf(_SC_PAGE_SIZE);
	off_t page_phys_addr;
	uintptr_t local_shm_addr = ipcf_shm_instances_cfg.shm_cfg->local_shm_addr;
	uint32_t shm_size = ipcf_shm_instances_cfg.shm_cfg->shm_size;
	int tmp[IPC_SHM_SIZE] = {0};

	sem_init(&app.sema, 0, 0);

	/* init ipc shm driver */
	err = init_ipc_shm();
	if (err)
		return err;

	/* catch interrupt signals to terminate the execution gracefully */
	sig_action.sa_handler = int_handler;
	sigaction(SIGINT, &sig_action, NULL);

	app.num_msgs = 1;
	while (app.num_msgs) {
		printf("\nReading from M7 Core: ");

		err = run_demo(app.num_msgs);
		
		//std::this_thread::sleep_for(std::chrono::seconds(10));
	}

	ipc_shm_free();

	/* Clear memory to re-init driver */
	page_phys_addr = (local_shm_addr / page_size) * page_size;
	app.local_shm_offset = local_shm_addr - page_phys_addr;
	app.mem_fd = open(IPC_SHM_DEV_MEM_NAME, O_RDWR);

	app.local_shm_map = mmap(NULL, app.local_shm_offset + shm_size,
				  PROT_READ | PROT_WRITE, MAP_SHARED,
				  app.mem_fd, page_phys_addr);

	app.local_virt_shm = app.local_shm_map + app.local_shm_offset;

	memcpy(app.local_virt_shm, tmp, shm_size);
	munmap(app.local_shm_map, app.local_shm_offset + shm_size);
	close(app.mem_fd);

	sem_destroy(&app.sema);

	printf("exit\n");

	return err;
}
