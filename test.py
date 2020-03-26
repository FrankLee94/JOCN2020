#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for test
# JialongLi 2020/03/13


import networkx as nx
import matplotlib.pyplot as plt
import xlrd
import copy
import random


NODE_NUM = 6			#节点数目

# 从xlsx文件里面读取拓扑数据。
def read_topo_file(topo_file_path):
	G = nx.DiGraph()
	workbook = xlrd.open_workbook(topo_file_path)
	booksheet = workbook.sheet_by_index(0)   #读取第一页的全部内容
	nrows = booksheet.nrows    #一共有多少行数据
	G.add_nodes_from([i for i in range(NODE_NUM)])
	for i in range(1, nrows):  #第0行不要
		row = booksheet.row_values(i)  #每一行里面的数据
		for j in range(1, nrows): #第0列不要
			if i == j:       #避免出现环
				continue
			else:
				if int(row[j]) != 0:    #有边
					G.add_edge(i-1, j-1, weight = int(row[j]))
				else:
					continue            #无边
	return G


# 画出topo
def drwa_topo(G):
	#pos = nx.spring_layout(G)
	pos = nx.kamada_kawai_layout(G)
	nx.draw(G, pos, with_labels = True)
	#edge_labels = nx.get_edge_attributes(G, 'weight')
	#nx.draw_networkx_edge_labels(G, pos, labels=edge_labels)
	plt.show()

# 两点之间最短路径算法
def shortest_path(G):
	#两点之间的一条最短路径
	print(nx.shortest_path(G, source=0, target=5, weight='weight'))

	#两点之间的所有最短路径
	print([p for p in nx.all_shortest_paths(G, source=0, target=5, weight='weight')])

	#两点之间是否有路
	print(nx.has_path(G, 0, 3))  #返回True或者False
	print(nx.ancestors(G, 5))  #有向图，某个节点的祖先
	print(nx.descendants(G, 0)) #有向图，某个节点的后代
	print(list(nx.simple_cycles(G)))

def test(a):
	a.pop(0) 

if __name__ == '__main__':
	topo_file_path = './topology/topo_single_node.xlsx'
	#G = read_topo_file(topo_file_path)
	#drwa_topo(G)
	#print(nx.has_path(G, 0, 3))
	#print(nx.shortest_path(G, source=1, target=5, weight='weight'))

	a = {(1,2):{0:66, 1:666}, (2,3):{0:6666, 1:6666}}
	a[(1,3)][2] = 3
	print(a)