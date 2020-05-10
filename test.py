#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for test
# JialongLi 2020/03/13

from itertools import islice
import networkx as nx
import matplotlib.pyplot as plt
import xlrd
import copy
import random

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

def k_shortest_paths(G, source, target, k, weight=None):
	return list(islice(nx.shortest_simple_paths(G, source, target,weight=weight), k))

if __name__ == '__main__':
	for i in range(10):
		if i > -1:
			continue
		for j in range(10):
			print('yes')