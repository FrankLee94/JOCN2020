# !usr/bin/env python
# -*- coding:utf-8 -*-

# this model is for hierarchy resource allocation in mec
# JialongLi 2020/03/07

import networkx as nx
import traffic
import statistics as st
import pandas as pd
import copy

class Baselines:
	def __init__(self):
		self.REQ_NUM = 10000		# 请求的总数目
		self.CPU_ONE = 150.0		# 本地节点CPU总量
		self.CPU_TWO = 500.0		# 二级节点CPU总量
		self.RAM_ONE = 150.0		# 本地节点RAM总量
		self.RAM_TWO = 500.0		# 二级节点RAM总量
		self.WAVE_NUM = 4			# 双向波长数目
		self.CAPACITY = 100			# 单波长容量
		# 边的连接关系，16条边
		self.route_edges = [
			(0, 1), (1, 2), (3, 0),					# 区域1
			(4, 5), (5, 6), (7, 4),					# 区域2
			(8, 9), (9, 10), (11, 8),				# 区域3
			(12, 13), (13, 14), (15, 12),			# 区域4
			(0, 4), (12, 8), (0, 16), (12, 17)]		# 环及数据中心
		self.df = None 				# dataframe, 读取的excel
		self.G = None 				# 用来做拓扑
		self.vm_locate_idx = None 	# 用来画图
		self.curr_load = None
		self.e_width = None
		self.info = None

	# 图形初始化
	def graph_init(self):
		G = nx.Graph()
		G.add_nodes_from([i for i in range(18)])
		G.add_edges_from(self.route_edges)
		return G

	# 初始化各条边的最大带宽，注意双向带宽合为单向带宽
	def edge_init(self):
		self.e_width = {}
		for item in self.route_edges:
			reverse_item = (item[1], item[0])
			self.e_width[item] = [0 for i in range(self.WAVE_NUM)]		# 储存每条边的负载
			self.e_width[reverse_item] = [0 for i in range(self.WAVE_NUM)]

	# 算法初始化, curr_load：每个节点CPU的使用率
	# vm_locate_idx：存储请求的分类及具体位置，分类有local, neigh, DC，具体位置为本节点id
	def initial(self):
		# 节点负载, [0, 0]分别表示cpu 和 ram
		self.curr_load = [[0, 0] for i in range(16)]
		self.vm_locate_idx = {}					# 部署位置,具体位置，及使用的路径
		self.G = self.graph_init()
		self.edge_init()

	# info初始化，只初始化一次
	def info_init(self):
		self.info = {'baselines': [], 'local': [], 'neigh': [], 'DC': [], 
		'block': [], 'traffic': [], 'traffic_dc': [], 'traffic_neigh': [], 'latency': [], 
		'latency_uns': [], 'latency_sen': [], 'block_rate': [], 'score': []}
		for key, value in self.info.items():
			if key == 'baselines':
				self.info[key] = ['fcfs', 'dsrf', 'hbdf', 'curf', 'reserve', 'res_class']
			else:
				self.info[key] = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

	# 某个请求接入，更新虚拟机所在节点的负载
	def fill_current_load(self, row):
		if self.vm_locate_idx[row['ReqNo']][0] == 'DC':			# DC的CPU资源无限
			pass
		elif self.vm_locate_idx[row['ReqNo']][0] == 'block':	# 阻塞
			pass
		else:
			vm_locate = self.vm_locate_idx[row['ReqNo']][1]		# 虚拟机的具体位置
			self.curr_load[vm_locate][0] += row['cpu']
			self.curr_load[vm_locate][1] += row['ram']

	# 某个请求离开，更新虚拟机所在节点的负载
	def rele_current_load(self, row):
		if self.vm_locate_idx[row['ReqNo']][0] == 'DC':			# DC的CPU资源无限
			pass
		elif self.vm_locate_idx[row['ReqNo']][0] == 'block':	# 阻塞
			pass
		else:
			vm_locate = self.vm_locate_idx[row['ReqNo']][1]		# 虚拟机的具体位置
			self.curr_load[vm_locate][0] -= row['cpu']
			self.curr_load[vm_locate][1] -= row['ram']

	# 某个请求接入，更新路径负载
	def fill_edge_width(self, row):
		shortest_path = self.vm_locate_idx[row['ReqNo']][2]
		waves = self.vm_locate_idx[row['ReqNo']][3]
		if len(shortest_path) == 0:		# DC接入或者block, 不用更新
			pass
		else:
			for i in range(len(shortest_path) - 1):
				edge = (shortest_path[i], shortest_path[i + 1])
				wave = waves[i]
				self.e_width[edge][wave] += row['bandwidth']

	# 某个请求离开，更新路径负载
	def rele_edge_width(self, row):
		shortest_path = self.vm_locate_idx[row['ReqNo']][2]
		waves = self.vm_locate_idx[row['ReqNo']][3]
		if len(shortest_path) == 0:		# DC接入或者block, 不用更新
			pass
		else:
			for i in range(len(shortest_path) - 1):
				edge = (shortest_path[i], shortest_path[i + 1])
				wave = waves[i]
				self.e_width[edge][wave] -= row['bandwidth']

	# 为当前的链路查找可以接入的波长
	def first_fit(self, row, edge):
		wave = -1
		is_wave_ac = False
		for i in range(self.WAVE_NUM):
			if self.e_width[edge][i] + row['bandwidth'] <= self.CAPACITY:
				wave = i
				is_wave_ac = True
				break
		return is_wave_ac, wave

	# 判断链路上是否有足够带宽接入
	def is_enough_bd(self, row, shortest_path):
		is_enough = True
		waves = []
		for i in range(len(shortest_path) - 1):			# 逐段链路检查
			edge = (shortest_path[i], shortest_path[i+1])
			is_wave_ac, wave = self.first_fit(row, edge)
			if is_wave_ac:
				waves.append(wave)
			else:
				is_enough = False
				waves = []
				break
		return is_enough, waves

	# 先使用local，然后是neigh，最后是DC
	def local_first(self, row):
		node = row['area_id'] * 4 + row['node_id'] + 1
		# 尝试使用local节点
		shortest_path = []
		if self.curr_load[node][0] + row['cpu'] <= self.CPU_ONE and \
			self.curr_load[node][1] + row['ram'] <= self.RAM_ONE:
			locate_flag = 'local'
			vm_locate = node
			waves = []
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 尝试使用邻居节点
		neigh_node = row['area_id'] * 4
		shortest_path = nx.shortest_path(self.G, source=node, target=neigh_node)
		is_enough, waves = self.is_enough_bd(row, shortest_path)
		if self.curr_load[neigh_node][0] + row['cpu'] <= self.CPU_TWO and \
			self.curr_load[neigh_node][1] + row['ram'] <= self.RAM_TWO and is_enough:
			locate_flag = 'neigh'
			vm_locate = neigh_node
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 使用数据中心
		if row['area_id'] < 2:			# 区域0和1使用数据中心‘16’
			DC_node = 16
		else:
			DC_node = 17
		shortest_path = nx.shortest_path(self.G, source=node, target=DC_node)
		is_enough, waves = self.is_enough_bd(row, shortest_path)
		if is_enough:
			locate_flag = 'DC'
			vm_locate = DC_node
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 阻塞
		locate_flag = 'block'
		vm_locate = 999
		shortest_path = []
		waves = []
		self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
			copy.deepcopy(shortest_path), copy.deepcopy(waves)]

	# 先使用DC，接着使用neigh，最后是local
	def dc_first(self, row):
		node = row['area_id'] * 4 + row['node_id'] + 1
		# 使用数据中心
		if row['area_id'] < 2:			# 区域0和1使用数据中心‘16’
			DC_node = 16
		else:
			DC_node = 17
		shortest_path = nx.shortest_path(self.G, source=node, target=DC_node)
		is_enough, waves = self.is_enough_bd(row, shortest_path)
		if is_enough:
			locate_flag = 'DC'
			vm_locate = DC_node
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 尝试使用邻居节点
		neigh_node = row['area_id'] * 4
		shortest_path = nx.shortest_path(self.G, source=node, target=neigh_node)
		is_enough, waves = self.is_enough_bd(row, shortest_path)
		if self.curr_load[neigh_node][0] + row['cpu'] <= self.CPU_TWO and \
			self.curr_load[neigh_node][1] + row['ram'] <= self.RAM_TWO and is_enough:
			locate_flag = 'neigh'
			vm_locate = neigh_node
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 尝试使用local节点
		shortest_path = []
		if self.curr_load[node][0] + row['cpu'] <= self.CPU_ONE and \
			self.curr_load[node][1] + row['ram'] <= self.RAM_ONE:
			locate_flag = 'local'
			vm_locate = node
			waves = []
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 阻塞
		locate_flag = 'block'
		vm_locate = 999
		shortest_path = []
		waves = []
		self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
			copy.deepcopy(shortest_path), copy.deepcopy(waves)]

	# 先使用neigh，接着使用local，最后是dc
	def neigh_first(self, row):
		node = row['area_id'] * 4 + row['node_id'] + 1
		
		# 尝试使用邻居节点
		neigh_node = row['area_id'] * 4
		shortest_path = nx.shortest_path(self.G, source=node, target=neigh_node)
		is_enough, waves = self.is_enough_bd(row, shortest_path)
		if self.curr_load[neigh_node][0] + row['cpu'] <= self.CPU_TWO and \
			self.curr_load[neigh_node][1] + row['ram'] <= self.RAM_TWO and is_enough:
			locate_flag = 'neigh'
			vm_locate = neigh_node
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return
		
		# 尝试使用local节点
		shortest_path = []
		if self.curr_load[node][0] + row['cpu'] <= self.CPU_ONE and \
			self.curr_load[node][1] + row['ram'] <= self.RAM_ONE:
			locate_flag = 'local'
			vm_locate = node
			waves = []
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return

		# 使用数据中心
		if row['area_id'] < 2:			# 区域0和1使用数据中心‘16’
			DC_node = 16
		else:
			DC_node = 17
		shortest_path = nx.shortest_path(self.G, source=node, target=DC_node)
		is_enough, waves = self.is_enough_bd(row, shortest_path)
		if is_enough:
			locate_flag = 'DC'
			vm_locate = DC_node
			self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
				copy.deepcopy(shortest_path), copy.deepcopy(waves)]
			return

		# 阻塞
		locate_flag = 'block'
		vm_locate = 999
		shortest_path = []
		waves = []
		self.vm_locate_idx[row['ReqNo']] = [locate_flag, vm_locate, 
			copy.deepcopy(shortest_path), copy.deepcopy(waves)]

# *****************************对比算法1：先来先服务*******************************

	# 先来先服务模型：先使用本节点，接着使用临近节点，最后使用DC。不区分延时敏感与否
	def fcfs(self):
		self.initial()
		total_reward = 0
		for index, row in self.df.iterrows(): 
			if row['status'] == 'arrive':
				self.local_first(row)				# 执行部署
				self.fill_current_load(row)
				self.fill_edge_width(row)
			else:		# 'leave'
				self.rele_current_load(row)
				self.rele_edge_width(row)
		print('firs-come first-serve: ')
		st.stastics(self.df, self.vm_locate_idx, self.info, 'fcfs', total_reward)

# *****************************对比算法2：延时敏感优先*******************************

	# 延时敏感业务：先使用local，然后是neigh，最后是DC
	# 延时不敏感业务：先使用DC，接着使用neigh，最后是local
	def dsrf(self):
		self.initial()
		total_reward = 0
		for index, row in self.df.iterrows(): 
			if row['status'] == 'arrive':			
				if row['delay_sen'] == 1:
					self.local_first(row)			# 延时敏感优先使用local
				else:
					self.dc_first(row)
				self.fill_current_load(row)
				self.fill_edge_width(row)
			else:		# 'leave'
				self.rele_current_load(row)
				self.rele_edge_width(row)
		print('\n')
		print('delay-sensitive request first: ')
		st.stastics(self.df, self.vm_locate_idx, self.info, 'dsrf', total_reward)

# *****************************对比算法3：大带宽优先*******************************

	# 大带宽业务：> 20G为大带宽业务，优先使用本地，
	# 小带宽业务优先使用数据中心
	def hbdf(self):
		self.initial()
		total_reward = 0
		for index, row in self.df.iterrows(): 
			if row['status'] == 'arrive':
				if row['bandwidth'] > 20:			# 大带宽定义：大于20G
					self.local_first(row)			# 大带宽优先使用local
				else:
					self.dc_first(row)
				self.fill_current_load(row)
				self.fill_edge_width(row)
			else:		# 'leave'
				self.rele_current_load(row)
				self.rele_edge_width(row)
		print('\n')
		print('huge bandwidth first: ')
		st.stastics(self.df, self.vm_locate_idx, self.info, 'hbdf', total_reward)

# *****************************对比算法4：计算不密集优先*******************************

	# 对于计算密集任务，优先使用数据中心
	# 计算密集：cpu 或者 ram 大于25即为计算密集任务
	# 计算不密集：cpu和ram均小于10
	def curf(self):
		self.initial()
		total_reward = 0
		for index, row in self.df.iterrows(): 
			if row['status'] == 'arrive':	
				if row['cpu'] > 25 or row['ram'] > 25:
					self.dc_first(row)		# 计算密集优先使用DC
				else:
					self.local_first(row)
				self.fill_current_load(row)
				self.fill_edge_width(row)
			else:		# 'leave'
				self.rele_current_load(row)
				self.rele_edge_width(row)
		print('\n')
		print('computing-unintensive request first: ')
		st.stastics(self.df, self.vm_locate_idx, self.info, 'curf', total_reward)

# *****************************对比算法5：资源预留算法*******************************

	# 阻塞率：大带宽优先
	# 延时敏感业务延时：延时敏感优先
	# 平均延时：fcfs
	def reserve_algo(self, row, alfa):
		node = row['area_id'] * 4 + row['node_id'] + 1
		# 只要小于阈值，统一使用fcfs
		if self.curr_load[node][0] <= alfa * self.CPU_ONE and self.curr_load[node][1] <= alfa * self.RAM_ONE:
			self.local_first(row)
		else:
			# 本地节点重负载以后，延时敏感或者大带宽业务，或者小计算任务，才能使用本地优先
			# 其余使用数据中心
			# 小计算任务: cpu < 10 and ram < 10
			if row['delay_sen'] == 1 or row['bandwidth'] > 20 or (row['cpu'] < 10 and row['ram'] < 10):
				self.local_first(row)
			else:
				self.dc_first(row)

	# 资源预留算法
	# alfa表示预留的多少，1表示全部预留，0表示不预留
	def reserve(self, alfa):
		self.initial()
		total_reward = 0
		for index, row in self.df.iterrows(): 
			if row['status'] == 'arrive':
				self.reserve_algo(row, alfa)
				self.fill_current_load(row)
				self.fill_edge_width(row)
			else:		# 'leave'
				self.rele_current_load(row)
				self.rele_edge_width(row)
		print('\n')
		print('reserve: ')
		st.stastics(self.df, self.vm_locate_idx, self.info, 'reserve', total_reward)

# *****************************对比算法6：资源分级算法*******************************

	# 对资源进行分级，方法1：只要local_attr >= dc_attr，就使用local_first
	def res_class_I(self, row):
		local_attr = 0
		dc_attr = 0
		if row['delay_sen'] == 1:		# 延时敏感，使用local
			local_attr += 1
		else:
			dc_attr += 1
		if row['bandwidth'] > 20:		# 大带宽，使用local
			local_attr += 1
		if row['bandwidth'] < 10:
			dc_attr += 1
		if row['cpu'] > 25 or row['ram'] > 25:	# 计算密集，使用dc
			dc_attr += 1
		if row['cpu'] < 10 and row['ram'] < 10:	# 计算不密集，使用local
			local_attr += 1
		if local_attr >= dc_attr:		# 只要local的属性大于等于dc的属性，使用local
			self.local_first(row)
		else:
			self.dc_first(row)

	# 对资源进行分级，方法2
	# local_attr及dc_attr可能的值对比，3-0, 2-1, 2-0, 1-2, 1-1, 1-0, 0-1, 0-2, 0-3
	def res_class_II(self, row):
		local_attr = 0
		dc_attr = 0
		if row['delay_sen'] == 1:		# 延时敏感，使用local
			local_attr += 1
		else:
			dc_attr += 1
		if row['bandwidth'] > 20:		# 大带宽，使用local
			local_attr += 1
		if row['bandwidth'] < 10:
			dc_attr += 1
		if row['cpu'] > 25 or row['ram'] > 25:	# 计算密集，使用dc
			dc_attr += 1
		if row['cpu'] < 10 and row['ram'] < 10:	# 计算不密集，使用local
			local_attr += 1
		if (local_attr - dc_attr) >= 2:	# 只要local的属性大于等于dc的属性1以上，使用local
			self.local_first(row)
		elif (dc_attr - local_attr) >= 2: 
			self.dc_first(row)
		else:
			self.neigh_first(row)

	# 对资源进行分级，方法3
	# 只要local的属性大于等于dc的属性1以上，使用local
	def res_class_III(self, row):
		local_attr = 0
		dc_attr = 0
		if row['delay_sen'] == 1:		# 延时敏感，使用local
			local_attr += 1
		else:
			dc_attr += 1
		if row['bandwidth'] > 20:		# 大带宽，使用local
			local_attr += 1
		if row['bandwidth'] < 10:
			dc_attr += 1
		if row['cpu'] > 25 or row['ram'] > 25:	# 计算密集，使用dc
			dc_attr += 1
		if row['cpu'] < 10 and row['ram'] < 10:	# 计算不密集，使用local
			local_attr += 1
		if (local_attr - dc_attr) >= 1:	# 只要local的属性大于等于dc的属性1以上，使用local
			self.local_first(row)
		elif (dc_attr - local_attr) >= 1: 
			self.dc_first(row)
		else:
			self.neigh_first(row)

	# 结合各个baseline算法的优势进行组合
	def res_class(self):
		self.initial()
		total_reward = 0
		for index, row in self.df.iterrows(): 
			if row['status'] == 'arrive':
				self.res_class_III(row)
				self.fill_current_load(row)
				self.fill_edge_width(row)
			else:		# 'leave'
				self.rele_current_load(row)
				self.rele_edge_width(row)
		print('\n')
		print('res_class: ')
		st.stastics(self.df, self.vm_locate_idx, self.info, 'res_class', total_reward)


# main函数
if __name__ == '__main__':
	
	n = 10
	baseline = Baselines()
	baseline.info_init()
	for i in range(n):
		print(i)
		baseline.df = traffic.get_new_df()		# 读取新的随机事件，一轮循环中大家都相同
		baseline.fcfs()
		baseline.dsrf()
		baseline.hbdf()
		baseline.curf()
		# baseline.res_class()
	df = pd.DataFrame(baseline.info)
	for key, value in baseline.info.items():
		if key == 'baselines':
			pass
		elif key == 'block_rate':
			df[key] = df[key].apply(lambda x: x / n)
		else:
			df[key] = df[key].apply(lambda x: round(x / n, 2))
	df.to_excel('./result/result_baselines_erlang15.xlsx', index = False)
	
	'''
	for j in range(11):
		alf = float(j / 10)
		print('alfa:' + str(j))
		n = 10
		baseline = Baselines()
		baseline.info_init()
		for i in range(n):
			print(i)
			baseline.df = traffic.get_new_df()		# 读取新的随机事件，一轮循环中大家都相同
			baseline.reserve(alf)
		df = pd.DataFrame(baseline.info)
		for key, value in baseline.info.items():
			if key == 'baselines':
				pass
			elif key == 'block_rate':
				df[key] = df[key].apply(lambda x: x / n)
			else:
				df[key] = df[key].apply(lambda x: round(x / n, 2))
		path = './result/result_reserve_erlang15_' + str(alf) + '.xlsx'
		df.to_excel(path, index = False)
	'''
