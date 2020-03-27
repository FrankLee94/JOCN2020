#!usr/bin/env python
#-*- coding:utf-8 -*-

# 各种统计及打印函数
# JialongLi 2020/03/26

import matplotlib.pyplot as plt

#统计变量初始化
#core_traff_ori：延时敏感原始，延时不敏感原始
#core_traff_wei：延时敏感加权，延时不敏感加权
#latency_sen, list,存储延时敏感业务的延时，只存储接入的
#atency_uns, list,存储延时不敏感业务的延时，只存储接入的
#req_sts:请求的统计信息，分别是总带宽，总CPU，总RAM
def sts_initial(req_num):
	core_traff_ori = [[0 for j in range(2 * req_num)] for i in range(2)]
	core_traff_wei = [[0 for j in range(2 * req_num)] for i in range(2)]
	latency_sen = [] 
	latency_uns = []
	req_sts = [0, 0.0, 0.0]
	return core_traff_ori, core_traff_wei, latency_sen, latency_uns, req_sts

#请求的统计信息，分别是总带宽，总CPU，总RAM
def cal_req_sts(req_sts, bandwidth, CPU, RAM):
	req_sts[0] += bandwidth
	req_sts[1] += CPU
	req_sts[2] += RAM

#经过核心网的实时流量
#core_traff_ori：延时敏感原始，延时不敏感原始
#core_traff_wei：延时敏感加权，延时不敏感加权
#core_traff_ori,double list, [[延时敏感], [延时不敏感]]
def rt_core_traff(status, req_count, bandwidth, locate_flag, core_traff_ori, delay_sen):
	if status == 'arrive':		#到达，核心网流量有可能增加
		if locate_flag == 'local' or locate_flag == 'block':#本地或者阻塞不产生流量
			if req_count == 0:
				core_traff_ori[0][req_count] = 0
				core_traff_ori[1][req_count] = 0
			else:
				core_traff_ori[0][req_count] = core_traff_ori[0][req_count-1]
				core_traff_ori[1][req_count] = core_traff_ori[1][req_count-1]
		else:						#neigh或者DC接入，产生流量
			if delay_sen == 1:		#延时敏感
				if req_count == 0:
					core_traff_ori[0][req_count] = bandwidth
					core_traff_ori[1][req_count] = 0
				else:
					core_traff_ori[0][req_count] = core_traff_ori[0][req_count-1] + bandwidth
					core_traff_ori[1][req_count] = core_traff_ori[1][req_count-1]
			else:					#延时不敏感
				if req_count == 0:
					core_traff_ori[0][req_count] = 0
					core_traff_ori[1][req_count] = bandwidth
				else:
					core_traff_ori[0][req_count] = core_traff_ori[0][req_count-1]
					core_traff_ori[1][req_count] = core_traff_ori[1][req_count-1] + bandwidth
	else:						#离开，核心网流量有可能减少
		if locate_flag == 'local' or locate_flag == 'block':#本地或者阻塞不产生流量
			core_traff_ori[0][req_count] = core_traff_ori[0][req_count-1]
			core_traff_ori[1][req_count] = core_traff_ori[1][req_count-1]
		else:
			if delay_sen == 1:		#延时敏感
				core_traff_ori[0][req_count] = core_traff_ori[0][req_count-1] - bandwidth
				core_traff_ori[1][req_count] = core_traff_ori[1][req_count-1]
			else:					#延时不敏感
				core_traff_ori[0][req_count] = core_traff_ori[0][req_count-1]
				core_traff_ori[1][req_count] = core_traff_ori[1][req_count-1] - bandwidth

#计算一条光路经过的物理距离
#lp, list,[lp_id, 源节点，宿节点，波长号，使用带宽0，路径节点集合]
def lp_distance(G_topo, lp):
	dis = 0
	path = lp[5]
	for i in range(len(path) - 1):
		dis += G_topo[path[i]][path[i+1]]['weight']#累加距离
	return dis
		
#计算单个请求的延时
#延时分为两部分，处理延时和传播延时
def cal_latency(locate_flag, one_hop_latency, dc_node_dis, lp_found, lp_new, G_topo):
	latency = 0
	total_dis = 0
	if locate_flag == 'block':#阻塞的请求不计算延时
		latency = -1
		return latency
	if locate_flag == 'local':
		return latency
	
	for lp in lp_found:		#累加已有光路的物理距离
		dis = lp_distance(G_topo, lp)
		total_dis += dis
	for lp in lp_new:		#累加新建光路的物理距离
		dis = lp_distance(G_topo, lp)
		total_dis += dis
	total_dis = float(total_dis) / 100.0#注意，在USNET中，除以100表示公里数，两节点间距离为3-26公里
	
	if locate_flag == 'neigh':
		proce_latency = (len(lp_found) + len(lp_new)) * one_hop_latency#处理时延
		propa_latency = total_dis / 200.0					#传播时延, 200km/ms
		latency = proce_latency + propa_latency
		return latency
	if locate_flag == 'DC':
		proce_latency = (len(lp_found) + len(lp_new) + 1) * one_hop_latency#数据中心加1跳
		propa_latency = (total_dis + dc_node_dis) / 200.0					#传播时延, 200km/ms
		latency = proce_latency + propa_latency
		return latency

#根据返回的单个延时来存储所有的latency
def sts_latency(locate_flag, latency, latency_sen, latency_uns, delay_sen):
	if locate_flag == 'block':#阻塞没有延时
		return
	if delay_sen == 1:#延时敏感
		latency_sen.append(latency)
	else:
		latency_uns.append(latency)

#统计阻塞的总带宽
def cal_block_bd(locate_flag, block_bd, bandwidth):
	if locate_flag == 'block':
		block_bd += bandwidth
	else:
		pass
	return block_bd

#输出带宽阻塞率
def display_blocking(req_sts, block_bd):
	rate = round(float(block_bd) / float(req_sts[0]) * 100, 2)
	print('overall bandwidth:  ' + str(int(req_sts[0]/1000)) + 'Gb')
	print('overall vCPU:  ' + str(req_sts[1]))
	print('overall RAM:  ' + str(round(req_sts[2], 2)) + 'Gb')
	print('blocking rate in bandwidth:  ' + str(rate) + '%')

#输出虚拟机放置的各种信息，以及连接阻塞率
def display_locate_info(vm_locate_index, req_num):
	show = {'local':0, 'neigh':0, 'DC':0, 'block':0}
	for key, value in vm_locate_index.items():
		show[value[0]] += 1
	for key, value in show.items():
		rate = round(float(value) / float(req_num) * 100, 2)
		print(key + ': ' + str(value) + '\t' + str(rate) + '%')

#输出延时信息
def display_latency(latency_sen, latency_uns):
	total_sen = 0.0
	total_uns = 0.0
	for item in latency_sen:
		total_sen += item
	for item in latency_uns:
		total_uns += item
	aver_sen = round(total_sen / len(latency_sen), 2)
	aver_uns = round(total_uns / len(latency_uns), 2)
	aver = round((total_sen + total_uns) / (len(latency_sen) + len(latency_uns)), 2)
	print('average latency for sensitive:  ' + str(aver_sen) + 'ms')
	print('average latency for insensitive:  ' + str(aver_uns) + 'ms')
	print('average latency:  ' + str(aver) + 'ms')

#core_traff_ori,double list, [[延时敏感], [延时不敏感]]
def display_traffic(core_traff_ori, timing_list):
	total_sen = 0.0
	total_uns = 0.0
	core_traff = []
	for i in range(len(timing_list)):
		core_traff_ori[0][i] = core_traff_ori[0][i] / 1000.0
		core_traff_ori[1][i] = core_traff_ori[1][i] / 1000.0
		core_traff.append(core_traff_ori[0][i] + core_traff_ori[1][i])
	for item in core_traff_ori[0]:
		total_sen += item
	for item in core_traff_ori[1]:
		total_uns += item
	aver_sen = round(total_sen / len(timing_list), 2)
	aver_uns = round(total_uns / len(timing_list), 2)
	aver = round(aver_sen + aver_uns, 2)
	print('average core traffic for sensitive:  ' + str(aver_sen) + 'Gb')
	print('average core traffic for insensitive:  ' + str(aver_uns) + 'Gb')
	print('average core traffic:  ' + str(aver) + 'Gb')

	plt.plot(timing_list, core_traff_ori[0], color = 'red', label = 'sensitive')
	plt.plot(timing_list, core_traff_ori[1], color = 'blue', label = 'insensitive')
	plt.plot(timing_list, core_traff, color = 'green', label = 'all traffic')
	plt.xlabel('Time (μs)', fontsize = 14)
	plt.ylabel('Core Traffic (Gb/s)', fontsize = 14)
	plt.legend(loc = 'upper left', fontsize = 14)
	#plt.ylim(0, 250)
	#plt.xlim(100*1e6, 110*1e6)
	plt.show()

#打印输出函数
def display(req_sts, block_bd, vm_locate_index, req_num, latency_sen, latency_uns, core_traff_ori, timing_list):
	display_blocking(req_sts, block_bd)
	display_locate_info(vm_locate_index, req_num)
	display_latency(latency_sen, latency_uns)
	display_traffic(core_traff_ori, timing_list)
