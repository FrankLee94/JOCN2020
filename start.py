import os

for i in range(100):
	print('**********************************************cycle: ' + str(i+1))
	os.system("python traffic.py")
	os.system("python main.py")
