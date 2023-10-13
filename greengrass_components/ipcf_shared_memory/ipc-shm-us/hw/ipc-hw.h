/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Copyright 2019,2021 NXP
 */
#ifndef IPC_HW_H
#define IPC_HW_H

int ipc_hw_init(const uint8_t instance, const struct ipc_shm_cfg *cfg);
void ipc_hw_free(const uint8_t instance);
void ipc_hw_irq_enable(const uint8_t instance);
void ipc_hw_irq_disable(const uint8_t instance);
void ipc_hw_irq_notify(const uint8_t instance);

#endif /* IPC_HW_H */
