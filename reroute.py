#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for reroute
# JialongLi 2020/04/13

from itertools import islice
import networkx as nx
import matplotlib.pyplot as plt
import xlrd
import copy
import random

KSP_K = 4	#ksp中的k取值

# 从xlsx文件里面读取拓扑数据。
def read_topo_file(topo_file_p):
	G_topo = nx.Graph()
	workbook = xlrd.open_workbook(topo_file_p)
	booksheet = workbook.sheet_by_index(0)   #读取第一页的全部内容
	nrows = booksheet.nrows			#一共有多少行数据
	for i in range(1, nrows):		#第0行不要
		row = booksheet.row_values(i)  #每一行里面的数据
		for j in range(1, nrows):	#第0列不要
			if i == j:       		#避免出现环
				continue
			else:
				if int(row[j]) != 0:#有边
					G_topo.add_edge(i-1, j-1, weight = int(row[j]))
					#G_topo.add_edge(i, j, weight = int(row[j]))
				else:
					continue		#无边
	return G_topo		#返回一个无向图


#初始化函数
#wave_use_index：key为源宿节点组成的元组，value为固定长度为波长数的list，只有1或者0
#exist_lp：key为源宿节点组成的元组,value是dict，里面包含多个lp的信息，每个lp是一个list
#exist_lp：double dict结构 {(1,2):{0:lp, 1:lp}, (2,3):{0:lp, 1:lp}}
#lp的list结构：[lp编号，源节点，宿节点，使用的波长编号，已使用带宽，路径上包含的所有节点]
#0：lp编号，从0开始，只在源宿节点之间唯一
#1：源节点
#2：宿节点
#3：使用的波长编号
#4：已使用带宽，不大于单波长容量
#5：路径上包含的所有节点，是一个list，包括源宿节点
#max_lp_id：从0开始，当前值加1表示存在过的最多光路数目
def reso_initial(node_num, wave_num, req_num):
	wave_use_index = {}	#两两节点间的波长是否被使用，1为可用，0为不可用
	exist_lp = {}		#两节点间已经存在的光路。注意：只保存一跳光路！
	record_path = {}	#记录下每个到达请求所使用的路径,[[lp_found],[lp_new]]
	max_lp_id = {}		#记录下两节点间lp_id的最大值。新建光路的lp_id在此基础上累加
	for i in range(node_num):
		for j in range(node_num):
			if i == j:
				continue 		#一个节点内部没有波长资源
			else:
				key = (i, j)
				value = [1 for k in range(wave_num)]
				wave_use_index[key] = value
	for i in range(req_num):
		record_path[i] = []
	return wave_use_index, exist_lp, max_lp_id, record_path

#增加已有光路的负载,仅一条
def exist_lp_add_bd(bandwidth, lp, exist_lp):
	lp_id = lp[0]
	key = (lp[1], lp[2])
	exist_lp[key][lp_id][4] += bandwidth

#减少已有光路的负载,仅一条
#需要返回值，确认该光路是否需要删除
def exist_lp_minus_bd(bandwidth, lp, exist_lp):
	is_delete = False
	lp_id = lp[0]
	key = (lp[1], lp[2])
	exist_lp[key][lp_id][4] -= bandwidth
	if exist_lp[key][lp_id][4] == 0:
		is_delete = True
	return is_delete

#新增一条光路，增加该光路信息，并加上该请求带宽
#lp_new，list,[待确定lp_id, 源节点，宿节点，波长号，使用带宽0，路径节点集合]
def add_lp(bandwidth, lp, max_lp_id, wave_use_index, exist_lp):
	key = (lp[1], lp[2])
	if key in exist_lp.keys():		#两节点间已有光路
		max_lp_id[key] += 1			#增加一条光路
	else:							#两节点间没有光路
		max_lp_id[key] = 0			#从0开始计起
		exist_lp[key] = {}
	lp[0] = max_lp_id[key]			#修改lp的lp_id，原来为字符串tbd
	lp[4] = bandwidth				#增加当前请求带宽
	lp_id = lp[0]					#当前lp_id即为max_lp_id的最大值
	exist_lp[key][lp_id] = copy.deepcopy(lp)#增加光路索引

	wave = lp[3]					#使用波长
	path = lp[5]					#增加当前请求带宽
	for i in range(len(path) - 1):
		wave_use_index[(path[i], path[i+1])][wave] = 0	#该波长不再可用

#拆除一条光路，删除该光路信息
#lp，list,[lp_id, 源节点，宿节点，波长号，使用带宽0，路径节点集合]
def delete_lp(lp, wave_use_index, exist_lp):
	lp_id = lp[0]
	key = (lp[1], lp[2])
	wave = lp[3]
	path = lp[5]
	exist_lp[key].pop(lp_id)							#删除光路索引
	for i in range(len(path) - 1):
		wave_use_index[(path[i], path[i+1])][wave] = 1	#该波长重新可用

#接入一条请求，在资源中增加带宽及所使用波长
#lp_found:list,[已确定lp_id,源节点，宿节点，波长号，使用带宽0，路径节点集合]
#lp_new，list, [待确定lp_id,源节点，宿节点，波长号，使用带宽0，路径节点集合]
def reso_add(lp_found, lp_new, bandwidth, max_lp_id, wave_use_index, exist_lp):
	for lp in lp_found:
		exist_lp_add_bd(bandwidth, lp, exist_lp)
	for lp in lp_new:
		add_lp(bandwidth, lp, max_lp_id, wave_use_index, exist_lp)

#删除一条请求，在资源中减少带宽及更新所使用波长
#注意：对于删除请求，都是减少带宽。当且仅当某条光路负载为0时，需要拆除
def reso_delete(lp_found, lp_new, bandwidth, wave_use_index, exist_lp):
	for lp in lp_found:
		is_delete = exist_lp_minus_bd(bandwidth, lp, exist_lp)
		if is_delete:
			delete_lp(lp, wave_use_index, exist_lp)
	for lp in lp_new:
		is_delete = exist_lp_minus_bd(bandwidth, lp, exist_lp)
		if is_delete:
			delete_lp(lp, wave_use_index, exist_lp)	

#使用已有且符合条件的lp构建有向图
def build_lp_graph(node_num, wave_capa, bandwidth, exist_lp):
	G_lp = nx.DiGraph()
	G_lp.add_nodes_from([i for i in range(node_num)])#所有节点都加入
	select_lp_index = {}		#记录构建有向图所使用的光路,key=(s, d), value = lp_id
	for key, value in exist_lp.items():	#value是一个dict
		for lp_id, lp in value.items(): #value为两个节点间的所有lp
			if lp[4] + bandwidth <= wave_capa:
				select_lp_index[key] = lp[0]  #lp_id
				G_lp.add_edge(key[0], key[1])
				break
	return G_lp, select_lp_index

#根据之前构建的有向图，输出已有可用光路
def get_lp_found(s_id, d_id, G_lp, select_lp_index, exist_lp):
	lp_found = []
	path = nx.shortest_path(G_lp, source = s_id, target = d_id)#使用其中一条最短路径
	for i in range(len(path) - 1):
		key = (path[i], path[i+1])
		lp_id = select_lp_index[key]
		lp = exist_lp[key][lp_id]
		lp_found.append(copy.deepcopy(lp))
	return lp_found

#KSP算法
def k_shortest_paths(G, source, target, k, weight=None):
	return list(islice(nx.shortest_simple_paths(G, source, target,weight=weight), k))

#1.查找可否在电层上被一个光路一跳接入
#lp_found:list,[lp_id，源节点，宿节点]
def find_lp_onehop(s_id, d_id, wave_capa, bandwidth, exist_lp):
	is_lp_onehop = False
	lp_found = []
	lp_new = []
	if (s_id, d_id) in exist_lp.keys():		#两节点间已有光路
		for lp_id, lp in exist_lp[(s_id, d_id)].items():
			if lp[4] + bandwidth <= wave_capa:
				is_lp_onehop = True
				lp_found.append(copy.deepcopy(lp))#深拷贝lp
				break
	else:
		pass
	return is_lp_onehop, lp_found, lp_new

#2.查找可否在两个节点之间建立一条透明的光路
#lp_new，list,[待确定lp_id,源节点，宿节点，波长号，使用带宽0，路径节点集合]
def find_lp_new(G_topo, s_id, d_id, wave_num, wave_use_index):
	is_lp_new = False
	flag = False
	lp_found = []
	lp_new = []
	wave = -1
	#两节点间的全部的最短路径，是一个双重list
	#注意此时计算最短路径不用路径距离。用跳数衡量
	if not nx.has_path(G_topo, source = s_id, target = d_id):
		print('topo error! no physical link between two nodes!')
		return 
	#all_st_paths = [p for p in nx.all_shortest_paths(G_topo, source=s_id, target=d_id)]
	all_st_paths = k_shortest_paths(G_topo, s_id, d_id, KSP_K)	#ksp算法
	for st_path in all_st_paths:
		for wave in range(wave_num):	#逐条波长检查
			flag = True
			for i in range(len(st_path) - 1):			#逐段链路检查
				if wave_use_index[(i, i+1)][wave] == 0:	#该波长不可用
					flag = False
					break
			if flag:
				break
		if flag:
			is_lp_new  = True
			lp_new.append(['tbd', s_id, d_id, wave, 0, st_path])#lp编号待确定，新建光路负载为0
			break
	return is_lp_new, lp_found, lp_new

#3.查找可否使用已经存在的多个光路多跳接入，采用Dij算法寻找最短路径
#select_lp_index:构建有向图中使用的已存在lp，字典格式，key=(s,d), value=lp_id
#lp_found:list,[lp_id，源节点，宿节点]
def find_lp_multihop(s_id, d_id, node_num, wave_capa, bandwidth, exist_lp):
	is_lp_multihop = False
	lp_found = []
	lp_new = []
	#使用已有且符合条件的lp构建有向图
	G_lp, select_lp_index = build_lp_graph(node_num, wave_capa, bandwidth, exist_lp)
	if not nx.has_path(G_lp, source = s_id, target = d_id): #不可达，直接返回
		return is_lp_multihop, lp_found, lp_new
	else:
		is_lp_multihop = True
		lp_found = get_lp_found(s_id, d_id, G_lp, select_lp_index, exist_lp)
	return is_lp_multihop, lp_found, lp_new

#4.查找可否新建光路和已经存在的光路一同接入。原有光路可能有多条，新建光路最多一条。
#可以把构建的图分为两个子图，分别包含源宿节点。
#源节点连通的点s_children，宿节点连通的点d_parents,集合set()形式
#i:  新建光路：源节点连通的点 -> 宿节点，否则：
#ii：新建光路：源节点 -> 宿节点连通的点；否则：
#iii:新建光路：源节点连通的点 -> 宿节点连通的点。
def find_lp_mix(G_topo, s_id, d_id, node_num, wave_capa, wave_num, bandwidth, wave_use_index, exist_lp):
	is_lp_mix = False
	lp_found = []
	lp_new = []
	G_lp, select_lp_index = build_lp_graph(node_num, wave_capa, bandwidth, exist_lp)
	s_children = nx.descendants(G_lp, s_id)
	d_parents = nx.ancestors(G_lp, d_id)

	#新建光路：源节点连通的点 -> 宿节点
	for s_child in s_children:
		is_lp_new, lp_found, lp_new = find_lp_new(G_topo, s_child, d_id, wave_num, wave_use_index)
		if is_lp_new:
			is_lp_mix = True
			#已有光路：源节点 -> 源节点连通的某点
			lp_found = get_lp_found(s_id, s_child, G_lp, select_lp_index, exist_lp)
			return is_lp_mix, lp_found, lp_new

	#新建光路：源节点 -> 宿节点连通的点
	for d_parent in d_parents:
		is_lp_new, lp_found, lp_new = find_lp_new(G_topo, s_id, d_id, wave_num, wave_use_index)
		if is_lp_new:
			is_lp_mix = True
			#已有光路：宿节点连通的某点 -> 宿节点
			lp_found = get_lp_found(d_parent, d_id, G_lp, select_lp_index, exist_lp)
			return is_lp_mix, lp_found, lp_new

	#新建光路：源节点连通的点 -> 宿节点连通的点
	for s_child in s_children:
		for d_parent in d_parents:
			is_lp_new, lp_found, lp_new = find_lp_new(G_topo, s_id, d_id, wave_num, wave_use_index)
			if is_lp_new:
				is_lp_mix = True
				#已有光路：源节点 -> 源节点连通的某点； 宿节点连通的某点 -> 宿节点
				lp_found_1 = get_lp_found(s_id, s_child, G_lp, select_lp_index, exist_lp)
				lp_found_2 = get_lp_found(d_parent, d_id, G_lp, select_lp_index, exist_lp)
				lp_found = lp_found_1 + lp_found_2
				return is_lp_mix, lp_found, lp_new
	return is_lp_mix, lp_found, lp_new

#为某两个节点间的请求寻找可用光路
#1.在电层上被一个光路一跳接入；否则：
#2.在两个节点之间建立一条透明的光路；否则：
#3.使用已经存在的多个光路多跳接入，采用Dij算法寻找最短路径；否则：
#4.新建光路和已经存在的光路一同接入；否则：阻塞
#lp_found，list,[已有的lp_id,源节点，宿节点，波长号，使用带宽0，路径节点集合]
#lp_new，  list,[待确定lp_id,源节点，宿节点，波长号，使用带宽0，路径节点集合]
def find_lp(G_topo, s_id, d_id, bandwidth, node_num, wave_capa, wave_num, wave_use_index, exist_lp):
	if s_id == d_id:
		print('the source node is the same as destination node!!')
		return

	lp_mode = 'block' 	#五种模式，分别是onehop，new, multihop, mix, block

	#一跳接入
	#is_lp_onehop, lp_found, lp_new = find_lp_onehop(s_id, d_id, wave_capa, bandwidth, exist_lp)
	#if is_lp_onehop:
	#	lp_mode = 'onehop'
	#	return lp_mode, lp_found, lp_new
	
	#新建光路接入
	is_lp_new, lp_found, lp_new = find_lp_new(G_topo, s_id, d_id, wave_num, wave_use_index)
	if is_lp_new:
		lp_mode = 'new'
		return lp_mode, lp_found, lp_new

	#多跳光路接入
	#is_lp_multihop, lp_found, lp_new = find_lp_multihop(s_id, d_id, node_num, wave_capa, bandwidth, exist_lp)
	#if is_lp_multihop:
	#	lp_mode = 'multihop'
	#	return lp_mode, lp_found, lp_new

	#混合光路接入
	#is_lp_mix, lp_found, lp_new = find_lp_mix(G_topo, s_id, d_id, node_num, wave_capa, wave_num, bandwidth, wave_use_index, exist_lp)
	#if is_lp_mix:
	#	lp_mode = 'mix'
	#	return lp_mode, lp_found, lp_new

	#无法接入，阻塞
	lp_found = []
	lp_new = []
	return lp_mode, lp_found, lp_new


#**********************************在此处截断，下面为测试函数

#产生随机的目的节点，在实际仿真中不需要
def gen_d(s_id, node_num):
	d_id = -1
	for i in range(1000):
		d_id = random.randint(0, node_num - 1)
		if d_id != s_id:
			break
	return d_id

#更新阻塞带宽和总带宽
def bd_info_count(bandwidth_info, bd, lp_md):
	bandwidth_info[1] += bd
	if lp_md == 'block':
		bandwidth_info[0] += bd

#统计输出函数
def display(show, exist_lp, req_num, bandwidth_info):
	print('number block rate')
	print(str(round(show['block'] / req_num * 100, 2)) + '%')
	#print('bandwidth block rate')
	#print(str(round(bandwidth_info[0] / bandwidth_info[1] * 100, 2)) + '%')
	#print('access mode')
	#for key, value in show.items():
	#	print(key, value)
	#print('wave use index')
	#for key, value in wave_use_index.items():
	#	print(key, value)
	#print('exist lp')
	#for key, value in exist_lp.items():
	#	print(key, value)
	#print('num of direct lp, maximum is 30:  ' + str(len(exist_lp)))#应该为30

# 画出topo
def draw_topo(G_topo):
	pos = nx.spring_layout(G_topo)
	#pos = nx.kamada_kawai_layout(G_topo)
	nx.draw(G_topo, pos, with_labels = True)
	#edge_labels = nx.get_edge_attributes(G_topo, 'weight')
	#nx.draw_networkx_edge_labels(G_topo, pos, labels=edge_labels)
	plt.show()

#测试函数
def test(topo_file_p, traffic_file_sort_p, node_num, wave_capa, wave_num, req_num):
	show = {'onehop': 0, 'new': 0, 'multihop': 0, 'mix': 0, 'block': 0}
	wave_use_index, exist_lp, max_lp_id, record_path = reso_initial(node_num, wave_num, req_num)
	G_topo = read_topo_file(topo_file_p)

	count = 0
	bd_info = [0, 0]#采用带宽阻塞率，左边为阻塞带宽总和，右边为所有业务带宽之和
	traffic_file_sort = open(traffic_file_sort_p, 'r')
	for line in traffic_file_sort.readlines(): 
		item_list = line.strip().split('\t')
		if item_list[0] == 'ReqNo':
			continue					#第0行，全为说明文字，跳过当前循环
		ReqNo = int(item_list[0])		#请求编号，同一个请求有到达和离开两个编号
		node_id = int(item_list[1])		#请求产生的节点
		bandwidth = int(item_list[5])	#请求的带宽
		status = item_list[7]			#到达或者离开，arrive or leave

		s_id = node_id
		d_id = gen_d(s_id, node_num)	#产生一个随机的目的节点
		#d_id = random.randint(0, node_num - 1)#源宿节点可能相同
		count += 1
		#print(str(count) + ':  ' + status)
		if status == 'arrive':
			lp_mode, lp_found, lp_new = find_lp(G_topo, s_id, d_id, bandwidth, node_num, wave_capa, wave_num, wave_use_index, exist_lp)
			reso_add(lp_found, lp_new, bandwidth, max_lp_id, wave_use_index, exist_lp)
			record_path[ReqNo].append(copy.deepcopy(lp_found))#记录下某个请求使用光路的情况
			record_path[ReqNo].append(copy.deepcopy(lp_new))
			show[lp_mode] += 1
			bd_info_count(bd_info, bandwidth, lp_mode)
		else:		#业务离开
			lp_found = record_path[ReqNo][0]
			lp_new = record_path[ReqNo][1]
			reso_delete(lp_found, lp_new, bandwidth, wave_use_index, exist_lp)
	display(show, exist_lp, req_num, bd_info)


#主函数
if __name__ == '__main__':
	n_num = 24			#节点数目		
	w_capa = 10000		#单波长容量，10000M
	w_num = 36			#两节点之间的波长数目
	r_num = 100000		#请求数目
	topo_file_path = './topology/topo_usnet.xlsx'

	for i in range(10, 11):#包前不包后
		erlang_single_node = i * 2
		traffic_file_sort_ph = './traffic_data/traffic_sort_' + str(erlang_single_node) + '.txt'
		print('***************single node erlang: ' + str(erlang_single_node))
		test(topo_file_path, traffic_file_sort_ph, n_num, w_capa, w_num, r_num)

