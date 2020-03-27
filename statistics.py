#!usr/bin/env python
#-*- coding:utf-8 -*-

# 各种统计及打印函数
# JialongLi 2020/03/26

#打印输出函数
#打印输出函数
def display(core_traff, locate_count):
	print('delay-sensitive traffic origin:  ' + str(int(core_traff[0]/1000)) + ' Gb')
	print('delay-nonsensitive traffic origin:  ' + str(int(core_traff[1]/1000)) + ' Gb')
	print('delay-sensitive traffic weight:  ' + str(int(core_traff[2]/1000)) + ' Gb')
	print('delay-nonsensitive traffic weight:  ' + str(int(core_traff[3]/1000)) + ' Gb')
	print('traffic origin:  ' + str(int((core_traff[0] + core_traff[1])/1000)) + ' Gb')
	print('traffic weight:  ' + str(int((core_traff[2] + core_traff[3])/1000)) + ' Gb')
	print('location count:  ' + str(locate_count[0] + locate_count[1] + locate_count[2]))
	print('local:  ' + str(locate_count[0]))
	print('neigh:  ' + str(locate_count[1]))
	print('DC   :  ' + str(locate_count[2]))