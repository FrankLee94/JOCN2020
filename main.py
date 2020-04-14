#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for hierarchy resource allocation in mec
# JialongLi 2020/03/07

import networkx as nx
import copy
import grooming as gm
import statistics as st
import pandas as pd
import random


NODE_NUM = 24			#节点数目
WAVE_NUM = 10		#两节点之间的波长数目
REQ_NUM = 100000		#请求的总数目
CPU_TOTAL = 500.0		#单节点CPU总量
RAM_TOTAL = 1000.0		#单节点RAM总量
ONE_HOP_LATENCY = 1.0	#虚拓扑单跳时延1ms
DC_NODE_DIS = 50		#数据中心和所连节点的距离
DC_ID = [7, 10]			#数据中心节点ID集合，和边缘计算节点相同
WAVE_CAPA = 10000		#单波长容量，10000M

#算法初始化
#current_load：每个节点CPU和RAM资源的使用率
#vm_locate_index：存储请求的分类及具体位置，分类有local, neigh, DC, block
#timing_list：存储每个请求或者离开的时刻点，长度为2*REQ_NUM
def initial():
	current_load = [[0.0, 0.0] for i in range(NODE_NUM)]#节点负载
	vm_locate_index = {}
	timing_list = [0 for i in range(2 * REQ_NUM)]
	return current_load, vm_locate_index, timing_list

# 某个请求接入，更新虚拟机所在节点的负载
def fill_current_load(current_load, ReqNo, vm_locate_index, CPU, RAM):
	if vm_locate_index[ReqNo][0] == 'DC':		#DC的CPU及RAM资源无限
		pass
	elif vm_locate_index[ReqNo][0] == 'block':	#被阻塞
		pass
	else:
		vm_locate = vm_locate_index[ReqNo][1]	#虚拟机的具体位置
		current_load[vm_locate][0] += CPU
		current_load[vm_locate][1] += RAM

# 某个请求离开，更新虚拟机所在节点的负载
def rele_current_load(current_load, ReqNo, vm_locate_index, CPU, RAM):
	if vm_locate_index[ReqNo][0] == 'DC':		#DC的CPU及RAM资源无限
		pass
	elif vm_locate_index[ReqNo][0] == 'block':	#被阻塞
		pass
	else:
		vm_locate = vm_locate_index[ReqNo][1]	#虚拟机的具体位置
		current_load[vm_locate][0] -= CPU
		current_load[vm_locate][1] -= RAM

#处理数据中心接入时，有可能出现源宿节点相同的情况，因为数据中心直连宿节点
def source_desti_same():
	lp_mode = 'DC'
	lp_found = []
	lp_new = []
	return lp_mode, lp_found, lp_new


#*****************************对比算法1：先来先服务*******************************

#为某个请求布置一个虚拟机
#locate_flag有四种情况，分别是'local', 'neigh', 'DC', 'block'
def find_locate_fcfs(current_load, node_id, bandwidth, CPU, RAM, G_topo, wave_use_index, exist_lp):
	#尝试使用local节点
	if current_load[node_id][0] + CPU <= CPU_TOTAL and current_load[node_id][1] + RAM <= RAM_TOTAL:
		locate_flag = 'local'
		vm_locate = node_id
		return locate_flag, vm_locate, [], []
	#尝试使用邻居节点
	for adj_node in nx.neighbors(G_topo, node_id): #node_id的所有相邻节点
		if current_load[adj_node][0] + CPU <= CPU_TOTAL and current_load[adj_node][1] + RAM <= RAM_TOTAL:
			lp_mode, lp_found, lp_new = gm.find_lp(G_topo, node_id, adj_node, bandwidth, NODE_NUM, WAVE_CAPA, WAVE_NUM, wave_use_index, exist_lp)
			if lp_mode != 'block':
				locate_flag = 'neigh'  #邻居接纳
				vm_locate = adj_node
				return locate_flag, vm_locate, lp_found, lp_new
	#尝试使用DC
	for dc_node in DC_ID: #DC节点
		if node_id == dc_node:#DC直连的节点请求使用DC资源
			lp_mode, lp_found, lp_new = source_desti_same()
		else:
			lp_mode, lp_found, lp_new = gm.find_lp(G_topo, node_id, dc_node, bandwidth, NODE_NUM, WAVE_CAPA, WAVE_NUM, wave_use_index, exist_lp)
		if lp_mode != 'block':
			locate_flag = 'DC'  #数据中心接纳
			vm_locate = dc_node
			return locate_flag, vm_locate, lp_found, lp_new
	#阻塞，无法接入
	locate_flag = 'block'
	vm_locate = -1
	return locate_flag, vm_locate, [], []

# 先来先服务模型：先使用本节点，接着使用临近节点，最后使用DC。不区分延时敏感与否
def fcfs(traffic_file_sort_path, G_topo, info_dict_fcfs):
	traffic_file_sort = open(traffic_file_sort_path, 'r')
	wave_use_index, exist_lp, max_lp_id, record_path = gm.reso_initial(NODE_NUM, WAVE_NUM, REQ_NUM)
	current_load, vm_locate_index, timing_list = initial()
	core_traff_ori, core_traff_wei, latency_sen, latency_uns, req_sts = st.sts_initial(REQ_NUM)
	block_bd = 0	#阻塞的总带宽

	req_count = 0
	for line in traffic_file_sort.readlines(): 
		item_list = line.strip().split('\t')
		if item_list[0] == 'ReqNo':
			continue
		ReqNo = int(item_list[0])
		node_id = int(item_list[1])
		CPU = float(item_list[2])
		RAM = float(item_list[3])
		timing = int(item_list[4])
		bandwidth = int(item_list[5])
		delay_sen = int(item_list[6])  #1代表延时敏感，0代表不敏感
		status = item_list[7]
		timing_list[req_count] = timing#记录到达和离开的所有时间点
		st.cal_req_sts(req_sts, bandwidth, CPU, RAM)

		if status == 'arrive':
			locate_flag, vm_locate, lp_found, lp_new = find_locate_fcfs(current_load, 
				node_id, bandwidth, CPU, RAM, G_topo, wave_use_index, exist_lp)
			vm_locate_index[ReqNo] = [locate_flag, vm_locate]#位置分类 + 具体位置
			fill_current_load(current_load, ReqNo, vm_locate_index, CPU, RAM)
			gm.reso_add(lp_found, lp_new, bandwidth, max_lp_id, wave_use_index, exist_lp)
			record_path[ReqNo].append(copy.deepcopy(lp_found))#记录下某个请求使用光路的情况
			record_path[ReqNo].append(copy.deepcopy(lp_new))		
			
			#统计信息
			st.rt_core_traff(status, req_count, bandwidth, locate_flag, core_traff_ori, delay_sen)
			latency = st.cal_latency(locate_flag, ONE_HOP_LATENCY, DC_NODE_DIS, lp_found, lp_new, G_topo)
			st.sts_latency(locate_flag, latency, latency_sen, latency_uns, delay_sen)
			block_bd = st.cal_block_bd(locate_flag, block_bd, bandwidth)
		else:    # 'leave'
			lp_found = record_path[ReqNo][0]
			lp_new = record_path[ReqNo][1]
			locate_flag = vm_locate_index[ReqNo][0]
			rele_current_load(current_load, ReqNo, vm_locate_index, CPU, RAM)
			gm.reso_delete(lp_found, lp_new, bandwidth, wave_use_index, exist_lp)
			st.rt_core_traff(status, req_count, bandwidth, locate_flag, core_traff_ori, delay_sen)
		#print(req_count)
		req_count += 1
	traffic_file_sort.close()
	st.display(info_dict_fcfs, req_sts, block_bd, vm_locate_index, REQ_NUM, latency_sen, latency_uns, core_traff_ori, timing_list)



#*****************************对比算法2：延时敏感优先*******************************

#为某个请求布置一个虚拟机
#延时敏感业务：先使用local，然后是neigh，最后是DC
#延时不敏感业务：先使用DC，接着使用neigh，最后是local
#locate_flag有四种情况，分别是'local', 'neigh', 'DC', 'block'
def find_locate_dsrf(current_load, node_id, bandwidth, CPU, RAM, delay_sen, G_topo, wave_use_index, exist_lp):
	if delay_sen == 0:
		#延时不敏感业务,直接尝试使用DC
		for dc_node in DC_ID: #DC节点
			if node_id == dc_node:#DC直连的节点请求使用DC资源
				lp_mode, lp_found, lp_new = source_desti_same()
			else:
				lp_mode, lp_found, lp_new = gm.find_lp(G_topo, 
					node_id, dc_node, bandwidth, NODE_NUM, WAVE_CAPA, WAVE_NUM, wave_use_index, exist_lp)
			if lp_mode != 'block':
				locate_flag = 'DC'  #数据中心接纳
				vm_locate = dc_node
				return locate_flag, vm_locate, lp_found, lp_new
		#尝试使用邻居节点
		for adj_node in nx.neighbors(G_topo, node_id): #node_id的所有相邻节点
			if current_load[adj_node][0] + CPU <= CPU_TOTAL and current_load[adj_node][1] + RAM <= RAM_TOTAL:
				lp_mode, lp_found, lp_new = gm.find_lp(G_topo, node_id, adj_node, bandwidth, NODE_NUM, WAVE_CAPA, WAVE_NUM, wave_use_index, exist_lp)
				if lp_mode != 'block':
					locate_flag = 'neigh'  #邻居接纳
					vm_locate = adj_node
					return locate_flag, vm_locate, lp_found, lp_new
		#尝试使用local节点
		if current_load[node_id][0] + CPU <= CPU_TOTAL and current_load[node_id][1] + RAM <= RAM_TOTAL:
			locate_flag = 'local'
			vm_locate = node_id
			return locate_flag, vm_locate, [], []
		#阻塞, 无法接入
		locate_flag = 'block'
		vm_locate = -1
		return locate_flag, vm_locate, [], []

	#以下为延时敏感业务
	#尝试使用local节点
	if current_load[node_id][0] + CPU <= CPU_TOTAL and current_load[node_id][1] + RAM <= RAM_TOTAL:
		locate_flag = 'local'
		vm_locate = node_id
		return locate_flag, vm_locate, [], []
	#尝试使用邻居节点
	for adj_node in nx.neighbors(G_topo, node_id): #node_id的所有相邻节点
		if current_load[adj_node][0] + CPU <= CPU_TOTAL and current_load[adj_node][1] + RAM <= RAM_TOTAL:
			lp_mode, lp_found, lp_new = gm.find_lp(G_topo, node_id, adj_node, bandwidth, NODE_NUM, WAVE_CAPA, WAVE_NUM, wave_use_index, exist_lp)
			if lp_mode != 'block':
				locate_flag = 'neigh'  #邻居接纳
				vm_locate = adj_node
				return locate_flag, vm_locate, lp_found, lp_new
	#尝试使用DC
	for dc_node in DC_ID: #DC节点
		if node_id == dc_node:#DC直连的节点请求使用DC资源
			lp_mode, lp_found, lp_new = source_desti_same()
		else:
			lp_mode, lp_found, lp_new = gm.find_lp(G_topo, 
				node_id, dc_node, bandwidth, NODE_NUM, WAVE_CAPA, WAVE_NUM, wave_use_index, exist_lp)
		if lp_mode != 'block':
			locate_flag = 'DC'  #数据中心接纳
			vm_locate = dc_node
			return locate_flag, vm_locate, lp_found, lp_new
	#阻塞，无法接入
	locate_flag = 'block'
	vm_locate = -1
	return locate_flag, vm_locate, [], []

#延时敏感优先算法
def dsrf(traffic_file_sort_path, G_topo, info_dict_dsrf):
	traffic_file_sort = open(traffic_file_sort_path, 'r')
	wave_use_index, exist_lp, max_lp_id, record_path = gm.reso_initial(NODE_NUM, WAVE_NUM, REQ_NUM)
	current_load, vm_locate_index, timing_list = initial()
	core_traff_ori, core_traff_wei, latency_sen, latency_uns, req_sts = st.sts_initial(REQ_NUM)
	block_bd = 0	#阻塞的总带宽

	req_count = 0
	for line in traffic_file_sort.readlines(): 
		item_list = line.strip().split('\t')
		if item_list[0] == 'ReqNo':
			continue
		ReqNo = int(item_list[0])
		node_id = int(item_list[1])
		CPU = float(item_list[2])
		RAM = float(item_list[3])
		timing = int(item_list[4])
		bandwidth = int(item_list[5])
		delay_sen = int(item_list[6])  #1代表延时敏感，0代表不敏感
		status = item_list[7]
		timing_list[req_count] = timing#记录到达和离开的所有时间点
		st.cal_req_sts(req_sts, bandwidth, CPU, RAM)

		if status == 'arrive':
			locate_flag, vm_locate, lp_found, lp_new = find_locate_dsrf(current_load, 
				node_id, bandwidth, CPU, RAM, delay_sen, G_topo, wave_use_index, exist_lp)
			vm_locate_index[ReqNo] = [locate_flag, vm_locate]#位置分类 + 具体位置
			fill_current_load(current_load, ReqNo, vm_locate_index, CPU, RAM)
			gm.reso_add(lp_found, lp_new, bandwidth, max_lp_id, wave_use_index, exist_lp)
			record_path[ReqNo].append(copy.deepcopy(lp_found))#记录下某个请求使用光路的情况
			record_path[ReqNo].append(copy.deepcopy(lp_new))		
			
			#统计信息
			st.rt_core_traff(status, req_count, bandwidth, locate_flag, core_traff_ori, delay_sen)
			latency = st.cal_latency(locate_flag, ONE_HOP_LATENCY, DC_NODE_DIS, lp_found, lp_new, G_topo)
			st.sts_latency(locate_flag, latency, latency_sen, latency_uns, delay_sen)
			block_bd = st.cal_block_bd(locate_flag, block_bd, bandwidth)
		else:    # 'leave'
			lp_found = record_path[ReqNo][0]
			lp_new = record_path[ReqNo][1]
			locate_flag = vm_locate_index[ReqNo][0]
			rele_current_load(current_load, ReqNo, vm_locate_index, CPU, RAM)
			gm.reso_delete(lp_found, lp_new, bandwidth, wave_use_index, exist_lp)
			st.rt_core_traff(status, req_count, bandwidth, locate_flag, core_traff_ori, delay_sen)
		#print(req_count)
		req_count += 1
	traffic_file_sort.close()
	st.display(info_dict_dsrf, req_sts, block_bd, vm_locate_index, REQ_NUM, latency_sen, latency_uns, core_traff_ori, timing_list)



if __name__ == '__main__':
	topo_file_ph = './topology/topo_usnet.xlsx'
	G_topology = gm.read_topo_file(topo_file_ph)
	info_fcfs = {'erlang': [], 'local':[], 'neigh':[], 'DC':[], 'block':[],
	'la_sen':[], 'la_ins':[], 'la':[], 'traff_sen':[], 'traff_ins':[], 'traff':[]}
	info_dsrf = copy.deepcopy(info_fcfs)

	for i in range(1, 31):#包前不包后
		erlang = i * 10 * 24
		#traffic_file_sort_ph = './traffic_data/traffic_sort_1200.txt'
		traffic_file_sort_ph = './traffic_data/traffic_sort_' + str(erlang) + '.txt'
		#print('Please check the following files!!!!!!')
		#print('topo_file: ' + topo_file_ph)
		#print('traffic_file: ' + traffic_file_sort_ph)
		#print('\n')

		#先来先服务
		print('first come first serve: erlang ' + str(i * 10))
		fcfs(traffic_file_sort_ph, G_topology, info_fcfs)

		#延时敏感优先
		#print('\n')
		print('delay-sensitive requests first: erlang ' + str(i * 10))
		dsrf(traffic_file_sort_ph, G_topology, info_dsrf)
		#print('\n')

		info_fcfs['erlang'].append(i * 10)
		info_dsrf['erlang'].append(i * 10)

	number = random.randint(0, 100000)
	df_fcfs = pd.DataFrame(info_fcfs)
	df_fcfs.to_excel('./result/cycle_500_1000_10/fcfs_cycle_' + str(number) + '.xlsx', index = False)
	df_dsrf = pd.DataFrame(info_dsrf)
	df_dsrf.to_excel('./result/cycle_500_1000_10/dsrf_cycle_' + str(number) + '.xlsx', index = False)


'''	
	for key, value in info_fcfs.items():
		for i in range(3):
			average = 0.0
			for j in range(NUM_CYCLE):
				average += value[j*3 + i]
			average = average / NUM_CYCLE
			info_fcfs_process[key].append(average)
'''
