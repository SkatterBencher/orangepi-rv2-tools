// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * spm8821_vr.c - Voltage Regulator Control for SPM8821 PMIC
 *
 * Allows userspace to read/write regulator voltages via ioctl
 * Uses direct I2C access to bypass cpufreq constraints
 */

#include <linux/module.h>
#include <linux/miscdevice.h>
#include <linux/i2c.h>
#include <linux/uaccess.h>
#include <linux/delay.h>

struct vr_arg {
    char name[32];
    int value;
};

struct vr_set {
    struct vr_arg info;
    int min;
    int max;
};

#define VR_IOCTL_MAGIC ('v')
#define VR_GET_VOLTAGE _IOWR(VR_IOCTL_MAGIC, 0, struct vr_arg)
#define VR_SET_VOLTAGE _IOWR(VR_IOCTL_MAGIC, 1, struct vr_set)
#define VR_SET_VOLTAGE_DIRECT _IOWR(VR_IOCTL_MAGIC, 2, struct vr_set)
#define VR_READ_REGISTER   _IOWR(VR_IOCTL_MAGIC, 3, struct vr_arg)
#define VR_WRITE_REGISTER  _IOWR(VR_IOCTL_MAGIC, 4, struct vr_arg)

/* SPM8821 I2C address and register map */
#define SPM8821_I2C_BUS 8
#define SPM8821_I2C_ADDR 0x41

/* Register addresses from datasheet */
#define BUCK_VOLT_BASE 0x48   /* BUCK1-6: 0x48 + 3*N, N=0-5 */
#define ALDO_VOLT_BASE 0x5C   /* ALDO1-4 (ldo1-4): 0x5C + 3*N, N=0-3 */
#define DLDO_VOLT_BASE 0x68   /* DLDO1-7 (ldo5-11): 0x68 + 3*N, N=0-6 */
#define REG_VOLT_OFFSET 3

static struct i2c_client *spm8821_client = NULL;

/* Voltage to register value conversion */
static u8 voltage_to_reg(int uv, int is_buck)
{
    int mv = uv / 1000;
    
    if (mv < 500)
        return 0x00;
    
    if (is_buck) {
        /* BUCK: 0.5V-1.35V (5mV steps), 1.375V-3.45V (25mV steps) */
        if (mv <= 1350) {
            return (mv - 500) / 5;
        } else if (mv <= 3450) {
            return 170 + (mv - 1375) / 25;
        }
        return 0xFE;
    } else {
        /* LDO (ALDO/DLDO): 0.5V-3.4V (25mV steps)
         * Register encoding: 0x0B=500mV, 0x0C=525mV, etc.
         * Formula: reg = (mv - 500) / 25 + 0x0B
         */
        if (mv >= 500 && mv <= 3400) {
            int val = ((mv - 500) / 25) + 0x0B;
            return (val > 0x7F) ? 0x7F : (u8)val;
        }
        /* Values below 0x0B default to 500mV per datasheet */
        return 0x0B;
    }
}

/* Register value to voltage conversion */
static int reg_to_voltage(u8 reg, int is_buck)
{
    if (is_buck) {
        /* BUCK voltage table */
        if (reg <= 170) {
            return (500 + reg * 5) * 1000;
        } else if (reg <= 254) {
            return (1375 + (reg - 170) * 25) * 1000;
        }
        return 3450000;
    } else {
        /* LDO voltage table (7-bit, 25mV steps from 500mV)
         * Register: 0x0B=500mV, 0x0C=525mV, etc.
         */
        reg &= 0x7F;  /* Mask to 7 bits */
        if (reg < 0x0B)
            return 500000;  /* Below 0x0B defaults to 500mV */
        return (500 + (reg - 0x0B) * 25) * 1000;
    }
}

/* Get regulator register address */
static int get_regulator_addr(const char *name, int *is_buck)
{
    int num;
    
    if (strncmp(name, "dcdc", 4) == 0) {
        /* dcdc1-6 -> BUCK0-5 */
        *is_buck = 1;
        num = name[4] - '1';
        if (num >= 0 && num <= 5)
            return BUCK_VOLT_BASE + (num * REG_VOLT_OFFSET);
    } else if (strncmp(name, "ldo", 3) == 0) {
        *is_buck = 0;
        
        /* Parse ldo number (ldo1-11) */
        if (name[4] >= '0' && name[4] <= '9') {
            /* ldo10 or ldo11 */
            num = (name[3] - '0') * 10 + (name[4] - '0');
        } else {
            /* ldo1-9 */
            num = name[3] - '0';
        }
        
        if (num >= 1 && num <= 4) {
            /* ldo1-4 = ALDO1-4 */
            return ALDO_VOLT_BASE + ((num - 1) * REG_VOLT_OFFSET);
        } else if (num >= 5 && num <= 11) {
            /* ldo5-11 = DLDO1-7 */
            return DLDO_VOLT_BASE + ((num - 5) * REG_VOLT_OFFSET);
        }
    }
    
    return -1;
}

/* Direct I2C read/write for regulator voltage */
static int spm8821_read_voltage(u8 reg_addr, int is_buck)
{
    int ret;
    
    if (!spm8821_client)
        return -ENODEV;
    
    ret = i2c_smbus_read_byte_data(spm8821_client, reg_addr);
    if (ret < 0)
        return ret;
    
    return reg_to_voltage((u8)ret, is_buck);
}

static int spm8821_write_voltage(u8 reg_addr, int is_buck, int uv)
{
    u8 reg_val = voltage_to_reg(uv, is_buck);
    int ret;
    
    if (!spm8821_client)
        return -ENODEV;
    
    ret = i2c_smbus_write_byte_data(spm8821_client, reg_addr, reg_val);
    if (ret < 0)
        return ret;
    
    /* Small delay for voltage to settle */
    usleep_range(100, 200);
    
    return spm8821_read_voltage(reg_addr, is_buck);
}

static long spm8821_vr_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
    void __user *argp = (void __user *)arg;
    int ret = 0;
    
    if (cmd == VR_GET_VOLTAGE) {
        struct vr_arg vr_info;
        int reg_addr, is_buck;
        
        if (copy_from_user(&vr_info, argp, sizeof(struct vr_arg)))
            return -EFAULT;
        
        reg_addr = get_regulator_addr(vr_info.name, &is_buck);
        if (reg_addr < 0)
            return -EINVAL;
        
        ret = spm8821_read_voltage((u8)reg_addr, is_buck);
        if (ret < 0)
            return ret;
        
        vr_info.value = ret;
        
        if (copy_to_user(argp, &vr_info, sizeof(struct vr_arg)))
            return -EFAULT;
        
    } else if (cmd == VR_SET_VOLTAGE_DIRECT) {
        struct vr_set vr_setinfo;
        int reg_addr, is_buck;
        
        if (copy_from_user(&vr_setinfo, argp, sizeof(struct vr_set)))
            return -EFAULT;
        
        reg_addr = get_regulator_addr(vr_setinfo.info.name, &is_buck);
        if (reg_addr < 0)
            return -EINVAL;
        
        ret = spm8821_write_voltage((u8)reg_addr, is_buck, vr_setinfo.min);
        if (ret < 0)
            return ret;
        
        vr_setinfo.info.value = ret;
        
        if (copy_to_user(argp, &vr_setinfo, sizeof(struct vr_set)))
            return -EFAULT;
    } else {
        return -EINVAL;
    }
    
    return 0;
}

static const struct file_operations spm8821_vr_fops = {
    .owner = THIS_MODULE,
    .unlocked_ioctl = spm8821_vr_ioctl,
};

static struct miscdevice spm8821_vr_dev = {
    .minor = MISC_DYNAMIC_MINOR,
    .name = "spm8821_vr",
    .fops = &spm8821_vr_fops,
};

static int __init spm8821_vr_init(void)
{
    struct i2c_adapter *adapter;
    struct device *dev;
    int ret;
    
    /* Get I2C adapter */
    adapter = i2c_get_adapter(SPM8821_I2C_BUS);
    if (!adapter) {
        pr_err("spm8821_vr: Failed to get I2C adapter %d\n", SPM8821_I2C_BUS);
        return -ENODEV;
    }
    
    /* Find existing SPM8821 device on the bus */
    dev = bus_find_device_by_name(&i2c_bus_type, NULL, "8-0041");
    if (dev) {
        spm8821_client = to_i2c_client(dev);
        pr_info("spm8821_vr: Found existing I2C device at 8-0041\n");
    } else {
        pr_err("spm8821_vr: SPM8821 device not found at 8-0041\n");
        i2c_put_adapter(adapter);
        return -ENODEV;
    }
    
    i2c_put_adapter(adapter);
    
    ret = misc_register(&spm8821_vr_dev);
    if (ret) {
        pr_err("spm8821_vr: Failed to register misc device: %d\n", ret);
        put_device(dev);
        return ret;
    }
    
    pr_info("spm8821_vr: Device registered with direct I2C access\n");
    return 0;
}

static void __exit spm8821_vr_exit(void)
{
    misc_deregister(&spm8821_vr_dev);
    if (spm8821_client) {
        put_device(&spm8821_client->dev);
        spm8821_client = NULL;
    }
    pr_info("spm8821_vr: Device unregistered\n");
}

module_init(spm8821_vr_init);
module_exit(spm8821_vr_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("SPM8821 PMIC Direct I2C Voltage Control");
MODULE_VERSION("2.0");