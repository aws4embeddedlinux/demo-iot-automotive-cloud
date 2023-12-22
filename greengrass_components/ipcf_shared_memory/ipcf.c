/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Copyright 2019-2023 NXP
 */
#include "ipcf.h"

int msg_sizes[IPC_SHM_MAX_POOLS] = {MAX_SAMPLE_MSG_LEN};
int msg_sizes_count = 1;
unsigned long successCount = 0;
unsigned long errorCount = 0;
/**
 * struct ipc_sample_app - sample app private data
 * @num_channels:		number of channels configured in this sample
 * @num_msgs:			number of messages to be sent to remote app
 * @ctrl_shm:			control channel local shared memory
 * @last_rx_no_msg:		last number of received message
 * @last_tx_msg:		last transmitted message
 * @last_rx_msg:		last received message
 * @local_virt_shm:		local shared memory virtual address
 * @mem_fd:				MEM device file descriptor
 * @local_shm_offset:	local ShM offset in mapped page
 * @local_shm_map:		local ShM mapped page address
 * @sema:				binary semaphore for sync send_msg func with shm_rx_cb
 * @instance:			instance id
 */
struct ipc_sample_app {
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

/* link with generated variables */
const void *rx_cb_arg = &app;

/* Init IPC shared memory driver (see ipc-shm.h for API) */
int init_ipc_shm(void)
{
	int err;

	err = ipc_shm_init(&ipcf_shm_instances_cfg);
	if (err)
		return err;

	app.num_channels = ipcf_shm_instances_cfg.shm_cfg[0].num_channels;

	/* acquire control channel memory once */
	app.ctrl_shm = ipc_shm_unmanaged_acquire(app.instance, CTRL_CHAN_ID);
	if (!app.ctrl_shm) {
		//sample_err("failed to get memory of control channel");
		return -ENOMEM;
	}

	return 0;
}

/*
 * ipc implementation of memcpy to IO memory space
 */
void ipc_memcpy_toio(void *dst, void *buf, size_t count)
{
	static int bytes_aligned = IPC_MEMCPY_BYTES_ALIGNED;
	/* Cast to char* as memcpy copy each bytes */
	char *dst_casted = (char *)dst;
	char *buf_casted = (char *)buf;

	while (count && !IS_ALIGNED((unsigned long)dst_casted, bytes_aligned)) {
		*dst_casted = *buf_casted;
		dst_casted += 1;
		buf_casted += 1;
		count--;
	}

	while (count >= bytes_aligned) {
		memcpy(dst_casted, buf_casted, bytes_aligned);
		dst_casted += bytes_aligned;
		buf_casted += bytes_aligned;
		count -= bytes_aligned;
	}

	while (count) {
		*dst_casted = *buf_casted;
		dst_casted += 1;
		buf_casted += 1;
		count--;
	}
}

/*
 * ipc implementation of memcpy from IO memory space
 */
void ipc_memcpy_fromio(void *dst, void *buf, size_t count)
{
	static int bytes_aligned = IPC_MEMCPY_BYTES_ALIGNED;
	/* Cast to char* as memcpy copy each bytes */
	char *dst_casted = (char *)dst;
	char *buf_casted = (char *)buf;

	while (count && !IS_ALIGNED((unsigned long)buf_casted, bytes_aligned)) {
		*dst_casted = *buf_casted;
		dst_casted += 1;
		buf_casted += 1;
		count--;
	}

	while (count >= bytes_aligned) {
		memcpy(dst_casted, buf_casted, bytes_aligned);
		dst_casted += bytes_aligned;
		buf_casted += bytes_aligned;
		count -= bytes_aligned;
	}

	while (count) {
		*dst_casted = *buf_casted;
		dst_casted += 1;
		buf_casted += 1;
		count--;
	}
}

/*
 * data channel Rx callback: print message, release buffer and signal the
 * completion variable.
 */
void data_chan_rx_cb(void *arg, const uint8_t instance, int chan_id,
		void *buf, size_t data_size)
{
	int err = 0;
	char *endptr;
	char tmp[MAX_SAMPLE_MSG_LEN];
	char proc[MAX_SAMPLE_MSG_LEN];
	
	assert(data_size <= MAX_SAMPLE_MSG_LEN);
	/* process the received data */
	ipc_memcpy_fromio(tmp, (char *)buf, data_size);
	
	/* send pre GG processing stats over */
	sprintf(proc, "PROC\nDataSize %ld\nSuccess %lu\nError %lu", 
	data_size, successCount, errorCount);
	
	// Spawn two GG sending tasks
	pthread_t ggTask;
	pthread_t procGGTask;
    printf("Before Thread\n");
    
    pthread_create(&ggTask, NULL, sendToGreengrass, (void*) tmp);
	pthread_create(&procGGTask, NULL, sendToGreengrass, (void*) proc);
	
	printf("ch %d << %ld bytes: %s\n", chan_id, data_size, tmp);

	/* consume received data: get number of message */
	/* Note: without being copied locally */
	app.last_rx_no_msg = strtol((char *)buf + strlen("#"), &endptr, 10);

	/* release the buffer */
	err = ipc_shm_release_buf(instance, chan_id, buf);
	
	// wait for threads to finish
	pthread_join(ggTask, NULL);
	pthread_join(procGGTask, NULL);
	
	printf("Threads complete");
	
	/* notify send_msg function a reply was received */
	sem_post(&app.sema);
}

/*
 * control channel Rx callback: print control message
 */
void ctrl_chan_rx_cb(void *arg, const uint8_t instance, int chan_id,
		void *mem)
{
	/* temp buffer for string operations that do unaligned SRAM accesses */
	char tmp[CTRL_CHAN_SIZE];

	assert(chan_id == CTRL_CHAN_ID);
	assert(strlen(mem) <= CTRL_CHAN_SIZE);

	ipc_memcpy_fromio(tmp, (char *)mem, CTRL_CHAN_SIZE);
	printf("ch %d << %ld bytes: %s\n", chan_id, strlen(tmp), tmp);

	/* notify run_demo() the ctrl reply was received and demo can end */
	sem_post(&app.sema);
}

/* send control message with number of data messages to be sent */
int send_ctrl_msg(const uint8_t instance)
{
	/* last channel is control channel */
	const int chan_id = CTRL_CHAN_ID;
	/* temp buffer for string operations that do unaligned SRAM accesses */
	char tmp[CTRL_CHAN_SIZE] = {0};
	int err;

	/* Write number of messages to be sent in control channel memory */
	sprintf(tmp, "SENDING MESSAGES: %d", app.num_msgs);
	ipc_memcpy_toio(app.ctrl_shm, tmp, CTRL_CHAN_SIZE);

	printf("ch %d >> %ld bytes: %s\n", chan_id, strlen(tmp), tmp);

	/* notify remote */
	err = ipc_shm_unmanaged_tx(instance, chan_id);
	if (err) {
		//sample_err("tx failed on control channel");
		return err;
	}

	return 0;
}

/**
 * generate_msg() - generates message with fixed pattern
 * @dest:	destination buffer
 * @len:	destination buffer length
 * @msg_no:	message number
 *
 * Generate message by repeated concatenation of a pattern
 */
void generate_msg(char *dest, int len, int msg_no)
{
	char tmp[MAX_SAMPLE_MSG_LEN];

	/* Write number of messages to be sent in control channel memory.
	 * Use stack temp buffer because snprintf may do unaligned memory writes
	 * in SRAM and A53 will complain about unaligned accesses.
	 */
	int ret = snprintf(tmp, len, "#%d", msg_no);

	ipc_memcpy_toio(dest, tmp, ret);
}

/**
 * send_data_msg() - Send generated data message to remote peer
 * @instance: instance id
 * @msg_len: message length
 * @msg_no: message sequence number to be written in the test message
 * @chan_id: ipc channel to be used for remote CPU communication
 *
 * It uses a completion variable for synchronization with reply callback.
 */
int send_data_msg(const uint8_t instance, int msg_len, int msg_no,
		int chan_id)
{
	int err = 0;
	char *buf = NULL;

	buf = ipc_shm_acquire_buf(instance, chan_id, msg_len);
	if (!buf) {
		return -ENOMEM;
	}

	/* write data to acquired buffer */
	generate_msg(buf, msg_len, msg_no);

	/* save data for comparison with echo reply */
	ipc_memcpy_fromio(app.last_tx_msg, buf, msg_len);
	
	
	printf("ch %d >> %d bytes: %s\n", chan_id, msg_len, app.last_tx_msg);

	/* send data to remote peer */
	err = ipc_shm_tx(instance, chan_id, buf, msg_len);
	if (err) {
		errorCount++;
		return err;
	}
	successCount++;

	/* wait for echo reply from remote (signaled from Rx callback) */
	sem_wait(&app.sema);
	if (errno == EINTR) {
		printf("interrupted...\n");
		return err;
	}

	return 0;
}

/*
 * Send requested number of messages to remote peer, cycling through all data
 * channels and wait for an echo reply after each sent message.
 */
int run_demo(int num_msgs)
{
	int err, msg, ch, i;
	i = 0;
	/* signal number of messages to remote via control channel */
	err = send_ctrl_msg(app.instance);
	if (err)
		return err;

	/* send generated data messages */
	msg = 0;
	ch = 1;

	while (msg < num_msgs) {
		err = send_data_msg(app.instance,
				msg_sizes[i], msg, ch);
		
		if (err)
			return err;
			
		printf("Wait for CTRL");
		/* wait for ctrl msg reply */
		if (++msg == num_msgs) {
		sem_wait(&app.sema);
		return 0;
		}
		
	}

	return 0;
}

/*
 * interrupt signal handler for terminating the sample execution gracefully
 */
void int_handler(int signum)
{
	app.num_msgs = 0;
}
