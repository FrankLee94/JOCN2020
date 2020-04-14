import os

for i in range(10):
	print('**********************************************cycle: ' + str(i+1))
	os.system("python traffic.py")
	os.system("python grooming.py")
	print('\n')
	print('\n')
	print('\n')
