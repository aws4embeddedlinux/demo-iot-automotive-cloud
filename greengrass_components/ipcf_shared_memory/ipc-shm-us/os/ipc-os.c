/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Copyright 2019-2023 NXP
 */
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <pthread.h>
#include <stdlib.h>
#include <dirent.h>

#include "ipc-os.h"
#include "ipc-hw.h"
#include "ipc-shm.h"
#include "ipc-uio.h"

#define IPC_SHM_DEV_MEM_NAME    "/dev/mem"
#define IPC_SHM_UIO_BUF_LEN     255
#define IPC_SHM_UIO_DIR         "/sys/class/uio"
#define IPC_UIO_PARAMS_LEN      130
#define UIO_DRIVER_NAME         "ipc-shm-uio"
#define DRIVER_VERSION          "0.1"

#define RX_SOFTIRQ_POLICY	SCHED_FIFO

/*
 * Maximum number of instances
 */
#define IPC_SHM_MAX_INSTANCES	4u

/* system call wrappers for loading and unloading kernel modules */
#define finit_module(fd, param_values, flags) \
	syscall(__NR_finit_module, fd, param_values, flags)
#define delete_module(name, flags) \
	syscall(__NR_delete_module, name, flags)

/**
 * struct ipc_os_priv_instance - OS specific private data each instance
 * @shm_size:		local/remote ShM size
 * @local_virt_shm:	local ShM virtual address
 * @remote_virt_shm:	remote ShM virtual address
 * @local_shm_map:	local ShM mapped page address
 * @remote_shm_map:	remote ShM mapped page address
 * @local_shm_offset:	local ShM offset in mapped page
 * @remote_shm_offset:	remote ShM offset in mapped page
 * @rx_cb:		upper layer Rx callback function
 * @irq_thread_id:	Rx interrupt thread id
 * @uio_fd:		UIO device file descriptor
 * @mem_fd:		MEM device file descriptor
 */
struct ipc_os_priv_instance {
	size_t shm_size;
	void *local_virt_shm;
	void *remote_virt_shm;
	void *local_shm_map;
	void *remote_shm_map;
	size_t local_shm_offset;
	size_t remote_shm_offset;
	int (*rx_cb)(const uint8_t instance, int budget);
	pthread_t irq_thread_id;
	int uio_fd;
	int mem_fd;
};

/**
 * struct ipc_os_priv - OS specific private data
 * @id:             private data per instance
 * @rx_cb:          upper layer rx callback function
 */
static struct ipc_os_priv {
	struct ipc_os_priv_instance id[IPC_SHM_MAX_INSTANCES];
	int (*rx_cb)(const uint8_t instance, int budget);
} priv;

/** read first line from file */
static int line_from_file(char *filename, char *buf)
{
	char *s;
	int i;
	FILE *file = fopen(filename, "r");

	memset(buf, 0, IPC_UIO_PARAMS_LEN);
	if (!file)
		return -ENONET;

	s = fgets(buf, IPC_SHM_UIO_BUF_LEN, file);
	if (!s)
		return -EIO;

	/* read first line only */
	for (i = 0; (*s) && (i < IPC_SHM_UIO_BUF_LEN); i++) {
		if (*s == '\n') {
			*s = 0;
			break;
		}
		s++;
	}

	fclose(file);
	return 0;
}

/** check whether first line from filename matched filter string */
static int line_match(char *filename, char *filter)
{
	int err;
	char linebuf[IPC_SHM_UIO_BUF_LEN];

	err = line_from_file(filename, linebuf);

	if (err != 0)
		return err;

	err = strncmp(linebuf, filter, IPC_SHM_UIO_BUF_LEN);
	if (err != 0)
		return EINVAL;

	return 0;
}

/** find the first UIO device that matched the kernel counterpart*/
static int get_uio_dev_name(char *dev_name)
{
	struct dirent **name_list;
	int nentries, count, i, err;
	char filename[IPC_SHM_UIO_BUF_LEN];

	nentries = scandir(IPC_SHM_UIO_DIR, &name_list, NULL, alphasort);
	if (nentries < 0)
		return -EIO;

	count = nentries;
	while (count--) {

		/*match name*/
		err = snprintf(filename, sizeof(filename),
			IPC_SHM_UIO_DIR "/%s/name", name_list[count]->d_name);
		if (err <= 0)
			return -EIO;
		if (line_match(filename, UIO_DRIVER_NAME) != 0)
			continue;

		/*match version*/
		err = snprintf(filename, sizeof(filename),
			IPC_SHM_UIO_DIR "/%s/version", name_list[count]->d_name);
		if (err <= 0)
			return -EIO;
		if (line_match(filename, DRIVER_VERSION) != 0)
			continue;

		break;
	}
	if (count >= 0) {
		strncpy(dev_name, name_list[count]->d_name, IPC_SHM_UIO_BUF_LEN);
	}
	/* free memory allocated by scandir */
	for (i = 0; i < nentries; i++)
		free(name_list[i]);
	free(name_list);

	return count >= 0 ? 0 : -ENONET;
}

/* Rx sotfirq thread */
static void *ipc_shm_softirq(void *arg)
{
	const int budget = IPC_SOFTIRQ_BUDGET;
	int irq_count;
	int work;
	uint8_t i = 0;

	while (1) {
		/* block(sleep) until notified from kernel IRQ handler */
		for (i = 0; i < IPC_SHM_MAX_INSTANCES; i++) {
			if (priv.id[i].uio_fd != 0)
				read(priv.id[i].uio_fd, &irq_count, sizeof(irq_count));

			do {
				work = priv.rx_cb(i, budget);
				/* work not done, yield and wait for reschedule */
				sched_yield();
			} while (work >= budget);

			/* re-enable irq */
			ipc_hw_irq_enable(i);
		}
	}

	return 0;
}

/**
 * ipc_shm_os_init() - OS specific initialization code
 * @instance:	instance id
 * @cfg:	configuration parameters
 * @rx_cb:	Rx callback to be called from Rx softirq
 *
 * Return: 0 on success, error code otherwise
 */
int ipc_os_init(const uint8_t instance, const struct ipc_shm_cfg *cfg,
		int (*rx_cb)(const uint8_t, int))
{
	size_t page_size = sysconf(_SC_PAGE_SIZE);
	off_t page_phys_addr;
	int err;
	int ipc_uio_module_fd;
	char ipc_uio_params[IPC_UIO_PARAMS_LEN];
	struct sched_param irq_thread_param;
	pthread_attr_t irq_thread_attr;

	if (!rx_cb)
		return -EINVAL;

	/* save params */
	priv.id[instance].shm_size = cfg->shm_size;
	priv.rx_cb = rx_cb;

	/* open ipc-uio kernel module */
	ipc_uio_module_fd = open(IPC_UIO_MODULE_PATH, O_RDONLY);
	if (ipc_uio_module_fd == -1) {
		shm_err("Can't open %s module\n", IPC_UIO_MODULE_PATH);
		return -ENODEV;
	}

	/* load ipc-uio kernel module passing down hw initialization params */
	snprintf(ipc_uio_params, IPC_UIO_PARAMS_LEN,
		"inter_core_tx_irq=%d inter_core_rx_irq=%d "
		"remote_core=%d,%d local_core=%d,%d,%d",
		cfg->inter_core_tx_irq, cfg->inter_core_rx_irq,
		cfg->remote_core.type, cfg->remote_core.index,
		cfg->local_core.type, cfg->local_core.index,
		cfg->local_core.trusted);
	shm_dbg("Loading %s with params: %s\n",
		IPC_UIO_MODULE_PATH, ipc_uio_params);

	if (finit_module(ipc_uio_module_fd, ipc_uio_params, 0) != 0) {
		shm_err("Can't load %s module\n", IPC_UIO_MODULE_PATH);
		err = -ENODEV;
		goto err_close_ipc_shm_uio;
	}

	/* open MEM device for interrupt support */
	priv.id[instance].mem_fd = open(IPC_SHM_DEV_MEM_NAME, O_RDWR);
	if (priv.id[instance].mem_fd == -1) {
		shm_err("Can't open %s device\n", IPC_SHM_DEV_MEM_NAME);
		err = -ENODEV;
		goto err_close_ipc_shm_uio;
	}

	/* map local physical shared memory */
	/* truncate address to a multiple of page size, or mmap will fail */
	page_phys_addr = (cfg->local_shm_addr / page_size) * page_size;
	priv.id[instance].local_shm_offset = cfg->local_shm_addr - page_phys_addr;

	priv.id[instance].local_shm_map = mmap(NULL, priv.id[instance].local_shm_offset
					+ cfg->shm_size,
					PROT_READ | PROT_WRITE, MAP_SHARED,
					priv.id[instance].mem_fd, page_phys_addr);
	if (priv.id[instance].local_shm_map == MAP_FAILED) {
		shm_err("Can't map memory: %lx\n", cfg->local_shm_addr);
		err = -ENOMEM;
		goto err_close_mem_dev;
	}

	priv.id[instance].local_virt_shm = priv.id[instance].local_shm_map
						+ priv.id[instance].local_shm_offset;

	/* map remote physical shared memory */
	page_phys_addr = (cfg->remote_shm_addr / page_size) * page_size;
	priv.id[instance].remote_shm_offset = cfg->remote_shm_addr - page_phys_addr;

	priv.id[instance].remote_shm_map = mmap(NULL, priv.id[instance].remote_shm_offset
					+ cfg->shm_size,
					PROT_READ | PROT_WRITE, MAP_SHARED,
					priv.id[instance].mem_fd, page_phys_addr);
	if (priv.id[instance].remote_shm_map == MAP_FAILED) {
		shm_err("Can't map memory: %lx\n", cfg->remote_shm_addr);
		err = -ENOMEM;
		goto err_unmap_local_shm;
	}

	priv.id[instance].remote_virt_shm = priv.id[instance].remote_shm_map
						+ priv.id[instance].remote_shm_offset;

	/* search for UIO device name */
	char uio_dev_name[IPC_SHM_UIO_BUF_LEN];
	char dev_uio[IPC_SHM_UIO_BUF_LEN*2];

	err = get_uio_dev_name(uio_dev_name);
	if (err != 0) {
		err = -ENOENT;
		goto err_unmap_remote_shm;
	}
	snprintf(dev_uio, sizeof(dev_uio), "/dev/%s", uio_dev_name);

	/* open UIO device for interrupt support */
	priv.id[instance].uio_fd = open(dev_uio, O_RDWR);
	if (priv.id[instance].uio_fd == -1) {
		shm_err("Can't open %s device\n", dev_uio);
		err = -ENODEV;
		goto err_unmap_remote_shm;
	}

	/* start Rx softirq thread with the highest priority for its policy */
	err = pthread_attr_init(&irq_thread_attr);
	if (err != 0) {
		goto err_close_uio_dev;
		shm_err("Can't initialize Rx softirq attributes\n");
	}

	err = pthread_attr_setschedpolicy(&irq_thread_attr, RX_SOFTIRQ_POLICY);
	if (err != 0) {
		goto err_close_uio_dev;
		shm_err("Can't set Rx softirq policy\n");
	}

	irq_thread_param.sched_priority = sched_get_priority_max(
		RX_SOFTIRQ_POLICY);
	err = pthread_attr_setschedparam(&irq_thread_attr, &irq_thread_param);
	if (err != 0) {
		goto err_close_uio_dev;
		shm_err("Can't set Rx softirq scheduler parameters\n");
	}

	err = pthread_create(&priv.id[instance].irq_thread_id, &irq_thread_attr,
			     ipc_shm_softirq, &priv);
	if (err == -1) {
		shm_err("Can't start Rx softirq thread\n");
		goto err_close_uio_dev;
	}
	shm_dbg("Created Rx softirq thread with priority=%d\n",
		irq_thread_param.sched_priority);
	shm_dbg("done\n");

	return 0;

err_close_uio_dev:
	close(priv.id[instance].uio_fd);
err_unmap_remote_shm:
	munmap(priv.id[instance].remote_shm_map,
			priv.id[instance].remote_shm_offset + priv.id[instance].shm_size);
err_unmap_local_shm:
	munmap(priv.id[instance].local_shm_map,
			priv.id[instance].local_shm_offset + priv.id[instance].shm_size);
err_close_mem_dev:
	close(priv.id[instance].mem_fd);
err_close_ipc_shm_uio:
	close(ipc_uio_module_fd);

	return err;
}

/**
 * ipc_os_free() - free OS specific resources
 */
void ipc_os_free(const uint8_t instance)
{
	void *res;

	/* disable hardirq */
	ipc_hw_irq_disable(instance);

	shm_dbg("stopping irq thread\n");

	/* stop irq thread */
	pthread_cancel(priv.id[instance].irq_thread_id);
	pthread_join(priv.id[instance].irq_thread_id, &res);

	close(priv.id[instance].uio_fd);

	/* unmap remote/local shm */
	munmap(priv.id[instance].remote_shm_map,
			priv.id[instance].remote_shm_offset + priv.id[instance].shm_size);
	munmap(priv.id[instance].local_shm_map,
			priv.id[instance].local_shm_offset + priv.id[instance].shm_size);

	close(priv.id[instance].mem_fd);

	/* unload ipc-uio kernel module */
	if (delete_module(IPC_UIO_MODULE_NAME, O_NONBLOCK) != 0) {
		shm_err("Can't unload %s module\n", IPC_UIO_MODULE_NAME);
	}
}

/**
 * ipc_os_get_local_shm() - get local shared mem address
 */
uintptr_t ipc_os_get_local_shm(const uint8_t instance)
{
	return (uintptr_t)priv.id[instance].local_virt_shm;
}

/**
 * ipc_os_get_remote_shm() - get remote shared mem address
 */
uintptr_t ipc_os_get_remote_shm(const uint8_t instance)
{
	return (uintptr_t)priv.id[instance].remote_virt_shm;
}

/**
 * ipc_os_poll_channels() - invoke rx callback configured at initialization
 *
 * Not implemented for Linux.
 *
 * Return: work done, error code otherwise
 */
int ipc_os_poll_channels(const uint8_t instance)
{
	return -EOPNOTSUPP;
}

static void ipc_send_uio_cmd(uint32_t uio_fd, int32_t cmd)
{
	int ret;

	ret = write(uio_fd, &cmd, sizeof(int));
	if (ret != sizeof(int)) {
		shm_dbg("Failed to execute UIO command %d", cmd);
	}
}

/**
 * ipc_hw_irq_enable() - enable notifications from remote
 */
void ipc_hw_irq_enable(const uint8_t instance)
{
	ipc_send_uio_cmd(priv.id[instance].uio_fd, IPC_UIO_ENABLE_RX_IRQ_CMD);
}

/**
 * ipc_hw_irq_disable() - disable notifications from remote
 */
void ipc_hw_irq_disable(const uint8_t instance)
{
	ipc_send_uio_cmd(priv.id[instance].uio_fd, IPC_UIO_DISABLE_RX_IRQ_CMD);
}

/**
 * ipc_hw_irq_notify() - notify remote that data is available
 */
void ipc_hw_irq_notify(const uint8_t instance)
{
	ipc_send_uio_cmd(priv.id[instance].uio_fd, IPC_UIO_TRIGGER_TX_IRQ_CMD);
}

int ipc_hw_init(const uint8_t instance, const struct ipc_shm_cfg *cfg)
{
	/* dummy implementation: ipc-hw init is handled by kernel UIO module */
	return 0;
}

void ipc_hw_free(const uint8_t instance)
{
	/* dummy implementation: ipc-hw free is handled by kernel UIO module */
}
