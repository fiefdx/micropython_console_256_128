#!/usr/bin/python
# -*- coding: utf-8 -*-
from machine import Pin, I2C, reset
import time
import binascii
from micropython import const

from ntp import get_ntp_time

#    the new version use i2c0,if it dont work,try to uncomment the line 14 and comment line 17
#    it should solder the R3 with 0R resistor if want to use alarm function,please refer to the Sch file on waveshare Pico-RTC-DS3231 wiki
#    https://www.waveshare.net/w/upload/0/08/Pico-RTC-DS3231_Sch.pdf

ALARM_PIN = const(3)


class ds3231(object):
    #            13:45:00 Mon 24 May 2021
    #  the register value is the binary-coded decimal (BCD) format
    #               sec min hour week day month year
    NowTime = const(b'\x00\x45\x13\x02\x24\x05\x21')
    #w  = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
    w  = ("Sun","Mon","Tue","Wed","Thu","Fri","Sat")
    address = const(0x68)
    start_reg = const(0x00)
    alarm1_reg = const(0x07)
    control_reg = const(0x0e)
    status_reg = const(0x0f)
        
    def __init__(self, i2c):
        self.bus = i2c
        
    def set_time(self, new_time):
        # "2020/01/22 21:03:37 Wed"
        hour = new_time[11] + new_time[12]
        minute = new_time[14] + new_time[15]
        second = new_time[17] + new_time[18]
        week = "0" + str(self.w.index(new_time.split(" ", 2)[2])+1)
        year = new_time.split(" ", 2)[0][2] + new_time.split(" ", 2)[0][3]
        month = new_time.split(" ", 2)[0][5] + new_time.split(" ", 2)[0][6]
        day = new_time.split(" ", 2)[0][8] + new_time.split(" ", 2)[0][9]
        now_time = binascii.unhexlify((second + " " + minute + " " + hour + " " + week + " " + day + " " + month + " " + year).replace(' ',''))
        #print(binascii.unhexlify((second + " " + minute + " " + hour + " " + week + " " + day + " " + month + " " + year).replace(' ','')))
        #print(self.NowTime)
        self.bus.writeto_mem(int(self.address), int(self.start_reg), now_time)
        
    def sync_time(self):
        new_time = None
        try:
            new_time = get_ntp_time()
            # print(new_time)
        except Exception as e:
            pass
        if new_time: # (2024, 8, 21, 17, 12, 7, 2, 234)
            # "2020/01/22 21:03:37 Wed"
            hour = "%02d" % new_time[3] 
            minute = "%02d" % new_time[4]
            second = "%02d" % new_time[5]
            week = "%02d" % (new_time[6]+2, )
            year = str(new_time[0])[2] + str(new_time[0])[3]
            month = "%02d" % new_time[1]
            day = "%02d" % new_time[2]
            now_time = binascii.unhexlify((second + " " + minute + " " + hour + " " + week + " " + day + " " + month + " " + year).replace(' ',''))
            self.bus.writeto_mem(int(self.address), int(self.start_reg), now_time)
            return True
        return False
    
    def read_time(self):
        t = self.bus.readfrom_mem(int(self.address),int(self.start_reg),7)
        a = t[0]&0x7F  #second
        b = t[1]&0x7F  #minute
        c = t[2]&0x3F  #hour
        d = t[3]&0x07  #week
        e = t[4]&0x3F  #day
        f = t[5]&0x1F  #month
        #print("20%x/%02x/%02x %02x:%02x:%02x %s" %(t[6],t[5],t[4],t[2],t[1],t[0],self.w[d-1]))
        return "20%x/%02x/%02x %02x:%02x:%02x %s" %(t[6],t[5],t[4],t[2],t[1],t[0],self.w[d-1])

    def read_temp(self):
        return self.bus.readfrom_mem(0x57, 0x04, 1)[0] - 40
    
    def read_power_status(self):
        return int(binascii.hexlify(self.bus.readfrom_mem(0x57, 0x22, 2)), 16) / 1000, self.bus.readfrom_mem(0x57, 0x2A, 1)[0], (self.bus.readfrom_mem(0x57, 0x02, 1)[0] >> 7) & 1
    
    def power_off(self):
        #d = self.bus.readfrom_mem(0x57, 0x02, 1)[0]
        #d |= 1 << 5
        #d |= 1 << 3
        #d &= 0 << 2
        d = const(0b01001000)
        self.bus.writeto_mem(0x57, 0x02, bytearray([d]))

    def reboot(self):
        reset()


if __name__ == '__main__':
    i2c = I2C(1, scl=Pin(27), sda=Pin(26), freq=100000)
    rtc = ds3231(i2c)
    #rtc.set_time('21:59:00,Friday,2024-08-09')
    #rtc.set_time('2024/08/20 19:19:00 Tue')
    print(rtc.read_time())
