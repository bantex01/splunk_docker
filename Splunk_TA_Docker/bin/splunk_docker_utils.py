import os
import filecmp
import re
import subprocess
import sys

from collections import defaultdict

#######################

RUN_DIR = os.path.dirname(os.path.join(os.getcwd(), __file__))
DOCKER_CFG = dict()
CACHE_DIR = RUN_DIR + "/cache/"
CONTAINER_DIR = CACHE_DIR + "container/"
CONTAINER_DEAD_DIR = CONTAINER_DIR + "dead/"
IMAGE_DIR = CACHE_DIR + "images/"
date_attr=re.search(r'(.*)',subprocess.check_output(["date"]))
RUN_DATE = date_attr.group(1)
FILES = defaultdict(dict)
EPOCH = subprocess.check_output(["date","+%s"]).rstrip()

#######################

def do_setup():

	#print "in do setup"
	if (not os.path.exists(CACHE_DIR)):

	#print "cache dir does not exist"
		try:
			os.mkdir(CACHE_DIR, 0755)
		except Exception, e:
			print "Exiting - unable to create cache directory "+str(e)
			sys.exit(2)

	if (not os.path.exists(CONTAINER_DIR)):
		#print "container dir does not exist"
		try:
			os.mkdir(CONTAINER_DIR, 0755)
		except Exception, e:
			print "Exiting - unable to create container directory "+str(e)
			sys.exit(2)

	if (not os.path.exists(CONTAINER_DEAD_DIR)):
		#print "dead container dir does not exist"
		try:
			os.mkdir(CONTAINER_DEAD_DIR, 0755)
		except Exception, e:
			print "Exiting - unable to create dead container directory "+str(e)
			sys.exit(2)

	if (not os.path.exists(IMAGE_DIR)):
		#print "image dir does not exist"
		try:
			os.mkdir(IMAGE_DIR, 0755)
		except Exception, e:
			print "Exiting - unable to create image directory "+str(e)
			sys.exit(2)


def clear_directory(dir):

	#print "in clear dir, dir is "+dir
	for f in os.listdir(dir):
		#print "file is "+f
		os.remove(dir +f)


def compare_files(file1,file2):

	#print "in compare files" + attribute + " " +file1 + " " +file2

	if (filecmp.cmp(file1,file2)):
		# files the same
		return "NO_DIFF"
	else:
		return "DIFF"


def gather_attributes_from_file(attribute,file):

	with open(file,'r') as data_file:
		data=data_file.read().replace('\n','')

	if (attribute == "container"):
		container_attr=re.search(r'.*:(.*) - .*:(.*) - .*:(.*) - .*:(.*) - .*:(.*) - .*:(.*)',data)
		string=container_attr.group(1) + "," + container_attr.group(2) + "," + container_attr.group(3) + "," + container_attr.group(4) +"," + container_attr.group(5) + "," + container_attr.group(6)
		#print "string is "+string
		return string


def create_data_file(file,string):

	#print "in create data file"
	data_file = open(file,'w')
	data_file.write(string)
	data_file.close()

	
def parse_conf(conf_file):

	conf_file = RUN_DIR + "/" + conf_file
	if (os.path.exists(conf_file)):
		#print "file exists"
		conf_file = open(conf_file,'r')
		for conf_line in conf_file:
			#print "conf line is "+conf_line
			if (re.match(r'\w+.*=.?\w+',conf_line)):
				#print "line matches "+conf_line
				cfg_items=re.search(r'(\w+).*=.?(\w+)',conf_line)
				#print "cfg is "+cfg_items.group(1)
				#print "item is "+cfg_items.group(2)
				DOCKER_CFG[cfg_items.group(1)] = cfg_items.group(2)

	else:
		# Set all default config here
		#print "File does not exist setting default cfg items"
		DOCKER_CFG['cache_timoeut'] = CACHE_TIMEOUT


def remove_file(file):

	if (os.path.exists(file)):
		os.remove(file)


def get_file_details(dir):

	for file in os.listdir(dir):
		#print "file is " +file
		file = dir + file
		if (os.path.isdir(file)):
			continue

		cksum_attr=re.search(r'(\w+)\s(\w+)\s+.+',subprocess.check_output(["cksum",file]))
		#print "FUNC: cksum is "+cksum_attr.group(1)
		#print "FUNC: file size is "+cksum_attr.group(2)

		file_epoch=re.search(r'(.*)\n',subprocess.check_output(["stat","-c","%Y",file]))
		#print "file epoch is "+file_epoch.group(1)

		FILES[file]['cksum'] = cksum_attr.group(1)
		FILES[file]['size'] = cksum_attr.group(2)
		FILES[file]['epoch'] = file_epoch.group(1)


def read_lines_from_file(file):

	f=open(file,'r')
	for line in f.readlines():
		line=line.rstrip()
		print line
	f.close()


def create_stats_file(file):

	f=open(file,'w')
	for file in FILES:
		f.write(file + "," + FILES[file]['epoch'] + "," + FILES[file]['cksum'] + "," + FILES[file]['size'] + "\n")
	f.close()


def touch_file(file):

	with open(file,'a'):
		os.utime(file,None)
