#!usr/bin/env python
#-*- coding:utf-8 -*-

# this model is for core traffic graph
# JialongLi 2020/05/09


import pickle
import matplotlib.pyplot as plt


# 从pkl文件中读取数据
def loadData(file_path):
	outfile = open(file_path, 'rb')
	[traff, timing] = pickle.load(outfile)
	outfile.close()
	return traff, timing

# 离散事件发生的时刻单位为μs
def normalized(timing):
	for i in range(len(timing)):
		timing[i] = timing[i] / 1e6
	return timing

# draw throughput picture
def drawThroughput(fcfs_path, dsrf_path, hbdf_path, curf_path, combine_path):
	traff_fcfs, timing_fcfs = loadData(fcfs_path)
	traff_dsrf, timing_dsrf = loadData(dsrf_path)
	traff_hbdf, timing_hbdf = loadData(hbdf_path)
	traff_curf, timing_curf = loadData(curf_path)
	traff_combine, timing_combine = loadData(combine_path)

	timing_fcfs = normalized(timing_fcfs)
	timing_dsrf = normalized(timing_dsrf)
	timing_hbdf = normalized(timing_hbdf)
	timing_curf = normalized(timing_curf)
	timing_combine = normalized(timing_combine)

	plt.plot(timing_fcfs, traff_fcfs, color = 'red', label = 'fcfs')
	plt.plot(timing_dsrf, traff_dsrf, color = 'blue', label = 'dsrf')
	plt.plot(timing_hbdf, traff_hbdf, color = 'yellow', label = 'hbdf')
	plt.plot(timing_curf, traff_curf, color = 'green', label = 'curf')
	plt.plot(timing_combine, traff_combine, color = 'black', label = 'combine')
	plt.xlabel('Time(s)', fontsize = 14)
	plt.ylabel('Network Throughput(Gb/s)', fontsize = 14)
	plt.legend(loc = 'lower left', fontsize = 14)
	#plt.ylim(1500, 2800)
	#plt.xlim(10, 20)
	plt.show()

if __name__ == '__main__':
	fcfs_p = './result/core_traffic/fcfs.pkl'
	dsrf_p = './result/core_traffic/dsrf.pkl'
	hbdf_p = './result/core_traffic/hbdf.pkl'
	curf_p = './result/core_traffic/curf.pkl'
	combine_p = './result/core_traffic/combine.pkl'
	drawThroughput(fcfs_p, dsrf_p, hbdf_p, curf_p, combine_p)