#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for traffic generation
# JialongLi 2020/03/09

import random
import math
import pandas as pd

NODE_NUM = 24			#拓扑节点数目
#ARRIVE_RATE = 24 * 150	#到达率，计算出来的爱尔兰是整个系统的爱尔兰
#SERVICE_RATE = 1		#服务率
RATIO_DELAY_SEN = 0.3	#延时敏感业务占比
REQ_NUM = 100000		#请求的总数目

#hot_zone = [6, 11, 20]
hot_zone = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

#读取VM实例的文件
def read_vm_instances(vm_instances_file_path):
	vm_instances_dict = {}
	df = pd.read_excel(vm_instances_file_path)
	for i in range((len(df.index.values))):			#行数，比实际少1
		vm_instances_dict[i] = df.loc[i].values[1:]#读取第2,3列数据，注意cpu是整型，ram是浮点
	return vm_instances_dict

# a event generation
def eventGeneration(arr_rate, ser_rate, vm_instances_dict):
	Probability_Poisson = random.random()
	if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
		Probability_Poisson = 0.5
	interval = -(1e6 / arr_rate) * math.log(1 - Probability_Poisson)   # event interval
	interval = int(round(interval))
	Probability_Poisson = random.random()
	persist_time = -(1e6 / ser_rate) * math.log(1 - Probability_Poisson)  # event service time
	persist_time = int(round(persist_time))
	if interval == 0:		#避免出现两个业务间隔时间为0的情况
		interval = 1
	if persist_time == 0:	#避免出现某个业务持续时间为0的情况
		persist_time = 1

	#node_id = random.randint(0, NODE_NUM - 1)	#从0开始到NODE_NUM - 1
	normal_zone = [i for i in range(NODE_NUM)]
	zone = normal_zone + hot_zone
	node_id = random.choice(zone)
	vm_id = random.randint(0, len(vm_instances_dict) - 1)
	CPU = vm_instances_dict[vm_id][0]
	RAM = vm_instances_dict[vm_id][1]  
	bandwidth = (random.randint(1, 60)) * 50	# 50 - 3000 M, granularity is 50M
	if random.random() > RATIO_DELAY_SEN: 
		delay_sen = 0   #0代表延时不敏感，概率1-RATIO_DELAY_SEN
	else:
		delay_sen = 1   #1代表延时敏感，概率RATIO_DELAY_SEN
	return interval, persist_time, node_id, CPU, RAM, bandwidth, delay_sen 

# traffic generation, raw data
def trafficGeneration(traffic_file_raw_path, arr_rate, ser_rate, vm_instances_dict):
	traffic_file_raw = open(traffic_file_raw_path, 'w')
	traffic_file_raw.write('ReqNo' + '\t' + 'node_id' + '\t' + 'CPU' + '\t' + 'RAM' + \
		'\t' + 'arrive_time' + '\t' + 'leave_time' + '\t' + 'persist_time' + '\t' + 'bandwidth' + '\t' + 'delay_sen' + '\n')
	
	absolute_time = 0
	for i in range(REQ_NUM):
		interval, persist_time, node_id, CPU, RAM, bandwidth, delay_sen = eventGeneration(arr_rate, ser_rate, vm_instances_dict)
		absolute_time += interval
		arrive_time = absolute_time
		leave_time = arrive_time + persist_time
		traffic_file_raw.write(str(i) + '\t' + str(node_id) + '\t' + str(CPU) + '\t' + str(RAM) + '\t' + \
			str(arrive_time) + '\t' + str(leave_time) + '\t' + str(persist_time) + '\t' + str(bandwidth) + '\t' + str(delay_sen) + '\n')
	traffic_file_raw.close()

# sort traffic
def sortTraffic(traffic_file_raw_path, traffic_file_sort_path):
	traffic_file_raw = open(traffic_file_raw_path, 'r')
	traffic_file_sort = open(traffic_file_sort_path, 'w')
	traffic_file_sort.write('ReqNo' + '\t' + 'node_id' + '\t' + 'CPU' + '\t' + 'RAM' + '\t'+ 'timing' + \
		'\t' + 'bandwidth' + '\t' + 'delay_sen' + '\t' + 'status' + '\n')

	event_dict = {}
	for line in traffic_file_raw.readlines():  # a line has two events
		item_list = line.split('\t')
		if item_list[0] == 'ReqNo':
			continue
		#0:ReqNo; 1:node_id; 2:CPU; 3:RAM; 4:arrive_time;
		#5:leave_time; 6:persist_time; 7:bandwidth; 8:delay_sen #持续时间6不用加
		key_0 = (int(item_list[0]), int(item_list[1]), float(item_list[2]), float(item_list[3]), int(item_list[7]), int(item_list[8]), 1)  # arrive
		value_0 = int(item_list[4])  # arrive time
		key_1 = (int(item_list[0]), int(item_list[1]), float(item_list[2]), float(item_list[3]), int(item_list[7]), int(item_list[8]), 0)  # leave
		value_1 = int(item_list[5])  # leave time
		event_dict[key_0] = value_0
		event_dict[key_1] = value_1

	#event_dict_sorted = sorted(event_dict.items(), key=lambda event_dict:event_dict[1], reverse=False)
	event_dict_sorted = sorted(event_dict.items(), key=lambda e:e[1], reverse=False)
	#item顺序：item[1]表示timing,item[0]表示各个字段，如下：
	#0:ReqNo; 1:node_id; 2:CPU; 3:RAM; 4:bandwidth; 5:delay_sen; 6:0或者1,1表示到达
	for item in event_dict_sorted:
		RequeNo = item[0][0]
		node_id = item[0][1]
		CPU = item[0][2]
		RAM = item[0][3]
		timing = item[1]
		bandwidth = item[0][4]
		delay_sen = item[0][5]
		if item[0][6] == 1:
			status = 'arrive'
		else:
			status = 'leave'
		traffic_file_sort.write(str(RequeNo) + '\t' + str(node_id) + '\t' + str(CPU) + '\t' + str(RAM) + '\t' + \
			str(timing) + '\t' + str(bandwidth) + '\t' + str(delay_sen) + '\t' + status + '\n')
	traffic_file_raw.close()
	traffic_file_sort.close()


if __name__ == '__main__':
	for i in range(10, 11):#包前不包后
		arrive_rate = i * NODE_NUM * 2
		serive_rate = 1
		erlang_all = int(float(arrive_rate) / float(serive_rate))
		erlang_single_node = i * 2
		print('single node erlang: ' + str(erlang_single_node))
		vm_instances_file_ph = './topology/ec2_instances.xlsx'
		vm_instan_dict = read_vm_instances(vm_instances_file_ph)
		traffic_file_raw_ph = './traffic_data/traffic_raw_' + str(erlang_single_node) + '.txt'
		traffic_file_sort_ph = './traffic_data/traffic_sort_' + str(erlang_single_node) + '.txt'
		trafficGeneration(traffic_file_raw_ph, arrive_rate, serive_rate, vm_instan_dict)
		sortTraffic(traffic_file_raw_ph, traffic_file_sort_ph)