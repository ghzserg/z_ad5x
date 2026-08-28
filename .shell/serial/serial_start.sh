#!/bin/sh

cd /usr/data/zmod/zmod/.shell/serial/

insmod usbserial.ko
insmod usb-serial-simple.ko
insmod ch341.ko
insmod cp210x.ko
insmod pl2303.ko
insmod cdc-acm.ko
