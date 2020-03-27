#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for hierarchy resource allocation in mec
# JialongLi 2020/03/07

import networkx as nx
import matplotlib.pyplot as plt
import xlrd
import copy

NODE_NUM = 24			#节点数目
CPU_TOTAL = 100			#单节点CPU总量
RAM_TOTAL = 100			#单节点RAM总量
STO_TOTAL = 100			#单节点STO总量
CPU_MAX = 10			#单个请求最大的CPU
RAM_MAX = 10			#单个请求最大的RAM
STO_MAX = 10			#单个请求最大的STO
WAVE_CAPA = 1000		#单波长容量，1000M
WAVE_NUM = 2			#两节点之间的波长数目


one_hop_node = {0:[1,3], 1:[0,2,3], 2:[1,4,5], 3:[0,1,4], 4:[2,3,5], 5:[2,4]}
DC_hop = {0:2, 1:1, 2:2, 3:2, 4:3, 5:3}


# 为某个请求布置一个虚拟机
def find_locate_fcfs(current_load, node_id, CPU, RAM, STO):
	is_local_ac = False
	is_neigh_ac = False
	if current_load[node_id][0] + CPU <= CPU_TOTAL and current_load[node_id][1] + RAM <= RAM_TOTAL and \
		current_load[node_id][2] + STO <= STO_TOTAL:
		is_local_ac = True
		locate_flag = 'local'
		vm_locate = node_id
	else:
		for adj_node in one_hop_node[node_id]: #node_id的所有相邻节点
			if current_load[adj_node][0] + CPU <= CPU_TOTAL and current_load[adj_node][1] + RAM <= RAM_TOTAL and \
			current_load[adj_node][2] + STO <= STO_TOTAL:
				is_neigh_ac = True
				vm_locate = adj_node
				locate_flag = 'neigh'  #邻居接纳
				break
	if not is_local_ac and not is_neigh_ac:   #未被本地且邻居接纳，则被数据中心接纳
		locate_flag = 'DC'
		vm_locate = -1
	return locate_flag, vm_locate

# 某个请求接入，更新虚拟机所在节点的负载
def fill_current_load(current_load, vm_locate, CPU, RAM, STO):
	current_load[vm_locate][0] += CPU
	current_load[vm_locate][1] += RAM
	current_load[vm_locate][2] += STO

# 某个请求离开，更新虚拟机所在节点的负载
def rele_current_load(current_load, vm_locate, CPU, RAM, STO):
	current_load[vm_locate][0] -= CPU
	current_load[vm_locate][1] -= RAM
	current_load[vm_locate][2] -= STO

# 统计经过核心网的流量
#四种流量，分别是延时敏感原始，延时不敏感原始；延时敏感加权，延时不敏感加权
# core_traff格式：list，[0, 0, 0, 0]
def cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag):
	if locate_flag == 'local':
		pass
	elif locate_flag == 'neigh':
		if delay_sen == 1:  # 延时敏感
			core_traff[0] += bandwidth
			core_traff[2] += bandwidth * 1
		else:				# 延时不敏感
			core_traff[1] += bandwidth
			core_traff[3] += bandwidth * 1
	else:
		if delay_sen == 1:  # 延时敏感
			core_traff[0] += bandwidth
			core_traff[2] += bandwidth * DC_hop[node_id]
		else:				# 延时不敏感
			core_traff[1] += bandwidth
			core_traff[3] += bandwidth * DC_hop[node_id]		

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


# 先来先服务模型：先使用本节点，接着使用临近节点，最后使用DC。不区分延时敏感与否
def fcfs(traffic_file_sort_path):
	traffic_file_sort = open(traffic_file_sort_path, 'r')
	current_load = [[0, 0, 0] for i in range(NODE_NUM)]
	DC_req = set()
	vm_locate_index = {}
	#四种流量，分别是延时敏感原始，延时不敏感原始；延时敏感加权，延时不敏感加权
	core_traff = [0, 0, 0, 0]
	locate_count = [0, 0, 0]  #三种位置，分别对应local, neigh, DC

	for line in traffic_file_sort.readlines(): 
		item_list = line.strip().split('\t')
		if item_list[0] == 'ReqNo':
			continue
		ReqNo = int(item_list[0])
		node_id = int(item_list[1])
		CPU = int(item_list[2])
		RAM = int(item_list[3])
		STO = int(item_list[4])
		timing = int(item_list[5])
		bandwidth = int(item_list[6])
		delay_sen = int(item_list[7])  #1代表延时敏感，0代表不敏感
		status = item_list[8]

		if status == 'arrive':
			locate_flag, vm_locate = find_locate_fcfs(current_load, node_id, CPU, RAM, STO)
			if locate_flag == 'local': 
				vm_locate_index[ReqNo] = vm_locate
				fill_current_load(current_load, vm_locate, CPU, RAM, STO)
				cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag)
				locate_count[0] += 1
			elif locate_flag == 'neigh':
				vm_locate_index[ReqNo] = vm_locate
				fill_current_load(current_load, vm_locate, CPU, RAM, STO) 
				cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag)
				locate_count[1] += 1
			else: # DC接纳
				vm_locate_index[ReqNo] = vm_locate
				cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag)
				locate_count[2] += 1
		else:    # 'leave'
			vm_locate = vm_locate_index[ReqNo]
			if vm_locate == -1:  # DC接纳,不用做操作
				pass
			else:  #该离开请求前面已接入，结束并释放虚拟机资源
				rele_current_load(current_load, vm_locate, CPU, RAM, STO)
	traffic_file_sort.close()

	display(core_traff, locate_count)

# 为某个请求布置一个虚拟机
def find_locate_dsrf(current_load, node_id, CPU, RAM, STO, delay_sen):
	if delay_sen == 0: #延时不敏感业务,直接使用DC
		locate_flag = 'DC'
		vm_locate = -1
		return locate_flag, vm_locate
	
	is_local_ac = False
	is_neigh_ac = False
	if current_load[node_id][0] + CPU <= CPU_TOTAL and current_load[node_id][1] + RAM <= RAM_TOTAL and \
		current_load[node_id][2] + STO <= STO_TOTAL:
		is_local_ac = True
		locate_flag = 'local'
		vm_locate = node_id
	else:
		for adj_node in one_hop_node[node_id]: #node_id的所有相邻节点
			if current_load[adj_node][0] + CPU <= CPU_TOTAL and current_load[adj_node][1] + RAM <= RAM_TOTAL and \
			current_load[adj_node][2] + STO <= STO_TOTAL:
				is_neigh_ac = True
				vm_locate = adj_node
				locate_flag = 'neigh'  #邻居接纳
				break
	if not is_local_ac and not is_neigh_ac:   #未被本地且邻居接纳，则被数据中心接纳
		locate_flag = 'DC'
		vm_locate = -1
	return locate_flag, vm_locate

# 延时敏感业务优先
# 延时敏感业务：先使用local，然后是neigh，最后是DC
# 延时不敏感业务：直接使用DC
def dsrf(traffic_file_sort_path):
	traffic_file_sort = open(traffic_file_sort_path, 'r')
	current_load = [[0, 0, 0] for i in range(NODE_NUM)]
	DC_req = set()
	vm_locate_index = {}
	#四种流量，分别是延时敏感原始，延时不敏感原始；延时敏感加权，延时不敏感加权
	core_traff = [0, 0, 0, 0]
	locate_count = [0, 0, 0]  #三种位置，分别对应local, neigh, DC

	for line in traffic_file_sort.readlines(): 
		item_list = line.strip().split('\t')
		if item_list[0] == 'ReqNo':
			continue					#第0行，全为说明文字，跳过当前循环
		ReqNo = int(item_list[0])		#请求编号，同一个请求有到达和离开两个编号
		node_id = int(item_list[1])		#请求产生的节点
		CPU = int(item_list[2])			#请求的CPU
		RAM = int(item_list[3])			#请求的RAM
		STO = int(item_list[4])			#请求的STO
		timing = int(item_list[5])		#到达或者离开的时刻
		bandwidth = int(item_list[6])	#请求的带宽
		delay_sen = int(item_list[7])	#1代表延时敏感，0代表不敏感
		status = item_list[8]			#到达或者离开，arrive or leave

		if status == 'arrive':
			locate_flag, vm_locate = find_locate_dsrf(current_load, node_id, CPU, RAM, STO, delay_sen)
			if locate_flag == 'local': 
				vm_locate_index[ReqNo] = vm_locate
				fill_current_load(current_load, vm_locate, CPU, RAM, STO)
				cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag)
				locate_count[0] += 1
			elif locate_flag == 'neigh':
				vm_locate_index[ReqNo] = vm_locate
				fill_current_load(current_load, vm_locate, CPU, RAM, STO) 
				cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag)
				locate_count[1] += 1
			else: # DC接纳
				vm_locate_index[ReqNo] = vm_locate
				cal_core_traff(core_traff, node_id, vm_locate, bandwidth, delay_sen, locate_flag)
				locate_count[2] += 1
		else:    # 'leave'
			vm_locate = vm_locate_index[ReqNo]
			if vm_locate == -1:  # DC接纳,不用做操作
				pass
			else:  #该离开请求前面已接入，结束并释放虚拟机资源
				rele_current_load(current_load, vm_locate, CPU, RAM, STO)
	traffic_file_sort.close()

	display(core_traff, locate_count)


if __name__ == '__main__':
	traffic_file_sort_path = './traffic_data/traffic_sort_100.txt'
	
	print('fcfs')
	fcfs(traffic_file_sort_path)

	print('dsrf')
	dsrf(traffic_file_sort_path)