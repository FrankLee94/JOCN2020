#!usr/bin/env python
#-*- coding:utf-8 -*-

# 各种统计及打印函数
# JialongLi 2020/05/09

import matplotlib.pyplot as plt
import pickle
import random


REQ_NUM = 10000



# 获取latency
# 200km ~ 1ms, 每一跳5ms
def get_latency(vm_locate_idx, row):
	latency = 0
	node = row['area_id'] * 4 + row['node_id'] + 1
	if vm_locate_idx[row['ReqNo']][0] == 'DC':
		if node in [2, 6, 10, 14]:
			latency = 3 * 5 + (5 + 5 + 50) / 200
		else:
			latency = 2 * 5 + (5 + 50) / 200
	if vm_locate_idx[row['ReqNo']][0] == 'neigh':
		if node in [2, 6, 10, 14]:
			latency = 2 * 5 + (5 + 5) / 200
		else:
			latency = 1 * 5 + (5) / 200
	return latency

# 统计核心网流量
def traffic_draw(df, vm_locate_idx, method):
	traff = [0 for i in range(2 *REQ_NUM + 1)]	# 2n+1个位置
	timing = [0]
	idx = 0
	for index, row in df.iterrows():
		if row['status'] == 'arrive':
			idx += 1
			timing.append(row['timing'])
			if vm_locate_idx[row['ReqNo']][0] == 'block' or \
				vm_locate_idx[row['ReqNo']][0] == 'local':
				traff[idx] = traff[idx - 1]
			else:
				traff[idx] = traff[idx - 1]
				traff[idx] += row['bandwidth']
		else:
			idx += 1
			timing.append(row['timing'])
			if vm_locate_idx[row['ReqNo']][0] == 'block' or \
				vm_locate_idx[row['ReqNo']][0] == 'local':
				traff[idx] = traff[idx - 1]
			else:
				traff[idx] = traff[idx - 1]
				traff[idx] -= row['bandwidth']
	# rd = random.randint(10000, 99999)
	save_file_path = './result/core_traffic/' + method + '.pkl'
	infile = open(save_file_path, 'wb')
	pickle.dump([traff, timing], infile)
	infile.close()

# 统计信息
def stastics(df, vm_locate_idx, info, method, total_reward):
	block_num = 0
	traff_DC = 0		# 到达DC的总流量
	traff_neigh = 0		# 到达neigh的总流量
	laten_sen = 0		# 延时敏感业务总延时
	laten_uns = 0		# 延时不敏感业务总延时
	sen_count = 0		# 延时敏感接入业务的总数量
	uns_count = 0		# 延时不敏感接入业务的总数量
	location_count = {'block': 0, 'local': 0, 'neigh': 0, 'DC': 0}
	for index, row in df.iterrows():
		if row['status'] == 'arrive':
			if vm_locate_idx[row['ReqNo']][0] == 'block':
				block_num += 1
			elif vm_locate_idx[row['ReqNo']][0] == 'DC':
				traff_DC += row['bandwidth']
				if row['delay_sen'] == 1:		# 延时敏感业务，DC延时
					laten_sen += get_latency(vm_locate_idx, row)
					sen_count += 1
				else:
					laten_uns += get_latency(vm_locate_idx, row)
					uns_count += 1
			elif vm_locate_idx[row['ReqNo']][0] == 'neigh':
				traff_neigh += row['bandwidth']
				if row['delay_sen'] == 1:		# 延时敏感业务，neigh延时
					laten_sen += get_latency(vm_locate_idx, row)
					sen_count += 1
				else:
					laten_uns += get_latency(vm_locate_idx, row)
					uns_count += 1
			else:		# 'local'
				if row['delay_sen'] == 1:		# 延时敏感业务，local延时0
					laten_sen += 0
					sen_count += 1
				else:
					laten_uns += 0
					uns_count += 1
		else:
			pass
	for key, value in vm_locate_idx.items():
		location_count[value[0]] += 1
	for key, value in location_count.items():
		print(key, value)
	print('blocking rate:  ' + str(round(block_num / REQ_NUM * 100, 2)) + '%')
	print('DC traffic:  ' + str(round(traff_DC, 0)) + 'Gb')
	print('neigh traffic:  ' + str(round(traff_neigh, 0)) + 'Gb')
	print('DC + neigh traffic:  ' + str(round(traff_DC + traff_neigh, 0)) + 'Gb')
	print('average latency for sensitive:  ' + str(round(laten_sen / sen_count, 2)))
	print('average latency for unsensitive:  ' + str(round(laten_uns / uns_count, 2)))
	print('average latency:  ' + str(round((laten_sen + laten_uns) / (sen_count + uns_count), 2)))

	block_rate = round(block_num / REQ_NUM, 4)
	traffic_dc = round(traff_DC, 0)
	traffic_neigh = round(traff_neigh, 0)
	traffic = traffic_dc + traffic_neigh
	latency_uns = round(laten_uns / uns_count, 2)
	latency_sen = round(laten_sen / sen_count, 2)
	latency = round((laten_sen + laten_uns) / (sen_count + uns_count), 2)
	idx = info['baselines'].index(method)
	info['local'][idx] += location_count['local']
	info['neigh'][idx] += location_count['neigh']
	info['DC'][idx] += location_count['DC']
	info['block'][idx] += location_count['block']
	info['traffic'][idx] += traffic
	info['traffic_dc'][idx] += traffic_dc
	info['traffic_neigh'][idx] += traffic_neigh
	info['latency'][idx] += latency
	info['latency_uns'][idx] += latency_uns
	info['latency_sen'][idx] += latency_sen
	info['block_rate'][idx] += block_rate
	info['score'][idx] += total_reward / 1000

	traffic_draw(df, vm_locate_idx, method)