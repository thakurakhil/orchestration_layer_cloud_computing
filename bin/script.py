import os
import sys
if __name__ == '__main__':
	if len(sys.argv) < 4:
			print "please enter : python script.py pm_file image_file flavor_file"
			exit(1)
	os.system("sudo apt-get install flask")
	os.chdir("../src")
	os.system("sudo python main.py " + sys.argv[1] + " " +sys.argv[2] + " " +sys.argv[3])
