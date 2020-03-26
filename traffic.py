#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for traffic generation
# JialongLi 2020/03/09

import random
import math

NODE_NUM = 6			#拓扑节点数目
ARRIVE_RATE = 100		#计算出来的爱尔兰是整个系统的爱尔兰
SERVICE_RATE = 1          
REQUEST_NUM = 100000
CPU_TOTAL = 100
RAM_TOTAL = 100
STO_TOTAL = 100
CPU_MAX = 10
RAM_MAX = 10
STO_MAX = 10

# a event generation
def eventGeneration():
	Probability_Poisson = random.random()
	if Probability_Poisson == 0.0 or Probability_Poisson == 1.0:
		Probability_Poisson = 0.5
	interval = -(1e6 / ARRIVE_RATE) * math.log(1 - Probability_Poisson)   # event interval
	interval = int(round(interval))
	Probability_Poisson = random.random()
	persist_time = -(1e6 / SERVICE_RATE) * math.log(1 - Probability_Poisson)  # event service time
	persist_time = int(round(persist_time))
	if interval == 0:  # ensure that after sorting, 'arrive' is ALWAYS ahead of 'leave' for the same RequestNo
		interval = 1
	if persist_time == 0:
		persist_time = 1
	node_id = random.randint(0, NODE_NUM - 1)
	CPU = random.randint(1, CPU_MAX)  # generate random integer from 0 to PON_NUM - 1
	RAM = random.randint(1, RAM_MAX)  
	STO = random.randint(1, STO_MAX)
	bandwidth = (random.randint(1, 60)) * 50        # 50 - 3000 M, granularity is 50M
	if random.random() > 0.3: 
		delay_sen = 0   #0代表延时不敏感，概率0.7
	else:
		delay_sen = 1   #1代表延时敏感，概率0.3
	return interval, persist_time, node_id, CPU, RAM, STO, bandwidth, delay_sen 

# traffic generation, raw data
def trafficGeneration(traffic_file_raw_path):
	traffic_file_raw = open(traffic_file_raw_path, 'w')
	traffic_file_raw.write('ReqNo' + '\t' + 'node_id' + '\t' + 'CPU' + '\t' + 'RAM' + '\t'+ \
		'STO' + '\t' + 'arrive_time' + '\t' + 'leave_time' + '\t' + 'persist_time' + '\t' + 'bandwidth' + '\t' + 'delay_sen' + '\n')
	
	absolute_time = 0
	for i in range(REQUEST_NUM):
		interval, persist_time, node_id, CPU, RAM, STO, bandwidth, delay_sen = eventGeneration()
		absolute_time += interval
		arrive_time = absolute_time
		leave_time = arrive_time + persist_time
		traffic_file_raw.write(str(i) + '\t' + str(node_id) + '\t' + str(CPU) + '\t' + str(RAM) + '\t' + str(STO) + '\t' + \
			str(arrive_time) + '\t' + str(leave_time) + '\t' + str(persist_time) + '\t' + str(bandwidth) + '\t' + str(delay_sen) + '\n')
	traffic_file_raw.close()

# sort traffic
def sortTraffic(traffic_file_raw_path, traffic_file_sort_path):
	traffic_file_raw = open(traffic_file_raw_path, 'r')
	traffic_file_sort = open(traffic_file_sort_path, 'w')
	traffic_file_sort.write('ReqNo' + '\t' + 'node_id' + '\t' + 'CPU' + '\t' + 'RAM' + '\t'+ 'STO' + '\t'+ 'timing' + \
		'\t' + 'bandwidth' + '\t' + 'delay_sen' + '\t' + 'status' + '\n')

	event_dict = {}
	for line in traffic_file_raw.readlines():  # a line has two events
		item_list = line.split('\t')
		if item_list[0] == 'ReqNo':
			continue
		#0:ReqNo; 1:node_id; 2:CPU; 3:RAM; 4:STO; 5:arrive_time;
		#6:leave_time; 7:persist_time; 8:bandwidth; 9:delay_sen
		key_0 = (int(item_list[0]), int(item_list[1]), int(item_list[2]), int(item_list[3]), int(item_list[4]), int(item_list[8]), int(item_list[9]), 1)  # arrive
		value_0 = int(item_list[5])  # arrive time
		key_1 = (int(item_list[0]), int(item_list[1]), int(item_list[2]), int(item_list[3]), int(item_list[4]), int(item_list[8]), int(item_list[9]), 0)  # leave
		value_1 = int(item_list[6])  # leave time
		event_dict[key_0] = value_0
		event_dict[key_1] = value_1

	event_dict_sorted = sorted(event_dict.items(), key=lambda event_dict:event_dict[1], reverse=False)
	for item in event_dict_sorted:
		RequeNo = item[0][0]
		node_id = item[0][1]
		CPU = item[0][2]
		RAM = item[0][3]
		STO = item[0][4]
		timing = item[1]
		bandwidth = item[0][5]
		delay_sen = item[0][6]
		if item[0][7] == 1:
			status = 'arrive'
		else:
			status = 'leave'
		traffic_file_sort.write(str(RequeNo) + '\t' + str(node_id) + '\t' + str(CPU) + '\t' + str(RAM) + '\t' + str(STO) + '\t' + \
			str(timing) + '\t' + str(bandwidth) + '\t' + str(delay_sen) + '\t' + status + '\n')
	traffic_file_raw.close()
	traffic_file_sort.close()


if __name__ == '__main__':
	Erlang = int(float(ARRIVE_RATE) / float(SERVICE_RATE))
	traffic_file_raw_path = './traffic_data/traffic_raw_' + str(Erlang) + '.txt'
	traffic_file_sort_path = './traffic_data/traffic_sort_' + str(Erlang) + '.txt'
	trafficGeneration(traffic_file_raw_path)
	sortTraffic(traffic_file_raw_path, traffic_file_sort_path)