/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Copyright 2019-2023 NXP
 */
#include <errno.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <semaphore.h>
#include <signal.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <pthread.h>

#include "ipc-shm.h"
#include "ipcf_Ip_Cfg.h"

#define IPC_SHM_DEV_MEM_NAME    "/dev/mem"

#ifdef POLLING
#define INTER_CORE_TX_IRQ IPC_IRQ_NONE
#else
#define INTER_CORE_TX_IRQ 2u
#endif /* POLLING */
#define INTER_CORE_RX_IRQ 1u

#define CTRL_CHAN_ID 0
#define CTRL_CHAN_SIZE 64
#define MAX_SAMPLE_MSG_LEN 256
#define L_BUF_LEN 4096
#define IPC_SHM_SIZE 0x100000

#ifndef ARRAY_SIZE
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))
#endif

#ifndef IPC_MEMCPY_BYTES_ALIGNED
#define IPC_MEMCPY_BYTES_ALIGNED 8
#endif

#define IS_ALIGNED(x, a) (((x) & ((typeof(x))(a) - 1)) == 0)

/* Init IPC shared memory driver (see ipc-shm.h for API) */
int init_ipc_shm(void);

/*
 * ipc implementation of memcpy to IO memory space
 */
void ipc_memcpy_toio(void *dst, void *buf, size_t count);

/*
 * ipc implementation of memcpy from IO memory space
 */
void ipc_memcpy_fromio(void *dst, void *buf, size_t count);

/*
 * data channel Rx callback: print message, release buffer and signal the
 * completion variable.
 */
void data_chan_rx_cb(void *arg, const uint8_t instance, int chan_id,
		void *buf, size_t data_size);

/*
 * control channel Rx callback: print control message
 */
void ctrl_chan_rx_cb(void *arg, const uint8_t instance, int chan_id,
		void *mem);

/* send control message with number of data messages to be sent */
int send_ctrl_msg(const uint8_t instance);

/**
 * generate_msg() - generates message with fixed pattern
 * @dest:	destination buffer
 * @len:	destination buffer length
 * @msg_no:	message number
 *
 * Generate message by repeated concatenation of a pattern
 */
void generate_msg(char *dest, int len, int msg_no);

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
		int chan_id);

/*
 * Send requested number of messages to remote peer, cycling through all data
 * channels and wait for an echo reply after each sent message.
 */
int run_demo(int num_msgs);

/*
 * interrupt signal handler for terminating the sample execution gracefully
 */
void int_handler(int signum);


void* sendToGreengrass(void* tmp);
