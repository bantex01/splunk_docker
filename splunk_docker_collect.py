#!/usr/bin/python

import sys
import os
import re
import splunk_docker_utils

from collections import defaultdict
from docker import Client

##################
# Routines
##################

def get_current_container_files():

	# Get a list of container files, we'll need this to clean up the dir
	# to ensure we only have existing container files

	for f in os.listdir(splunk_docker_utils.CONTAINER_DIR):
		#print "file is "+f
		if (os.path.isdir(f)):
			continue

		f = f.rstrip()
		f = splunk_docker_utils.CONTAINER_DIR + f
		CURRENT_CONTAINER_FILES[f]='1'


def get_container_info():

	containers=cli.containers(all='true')
	count=0

	for container in containers:

		name_attr=re.search( r'\[u\'\/(\w+)\'\]',str(containers[count]['Names']))
		container_name=name_attr.group(1)
		status=containers[count]['Status']

		if ("Up" in status):
			status="Up"
		else:
			status="Down"

		id=containers[count]['Id'][:12]
		image=containers[count]['Image']
		command=containers[count]['Command']
		inspect=cli.inspect_container(container_name)
		hostname=inspect['Config']['Hostname']

		CONTAINERS.append(hostname) # We'll use this array later to gather stats

		count += 1

		# Create string to be checked against old container file if it exists
		attr_string=host + "," + container_name + "," + hostname + "," + status + "," + image + "," +command

		# This is the name we need to say we've processed (matches name in current_container_files)
		container_file_name = splunk_docker_utils.CONTAINER_DIR + hostname + ".out"

		# Let's compare the built string from the new data to the data held in the cache directory

		if (os.path.exists(container_file_name)):

			container_file_attr_string=splunk_docker_utils.gather_attributes_from_file("container",container_file_name)
			if (attr_string != container_file_attr_string):
				splunk_docker_utils.create_data_file(container_file_name,"Docker Host:" +host + " - Container Name:"+container_name  + " - Host Name:"+hostname +" - Status:"+status + " - Image:" +image + " - Command:" + command + "\n")

		else:
			splunk_docker_utils.create_data_file(container_file_name,"Docker Host:" +host + " - Container Name:"+container_name  + " - Host Name:"+hostname +" - Status:"+status + " - Image:" +image + " - Command:" + command + "\n")


		# Let's update the current_container_files has to say we've processed this file
		# At the end we'll loop this hash and any file that hasn't been processed will be
		# removed from the directory

		CURRENT_CONTAINER_FILES[container_file_name]='2'
			
	
def clean_up_container_files():

	# move to temp deletion area

	for key in CURRENT_CONTAINER_FILES:
		if (CURRENT_CONTAINER_FILES[key] == "1"):
			if (os.path.isdir(key)):
				continue
			else:
				os.rename(key,splunk_docker_utils.CONTAINER_DEAD_DIR+os.path.basename(key))	
		

def get_current_image_files():

	# Let's get a list of docker image files, we'll need this to clean up the dir
	# to ensure we only have existing image files

	for f in os.listdir(splunk_docker_utils.IMAGE_DIR):
		#print "file is "+f
		if (os.path.isdir(f)):
			continue

		f = f.rstrip()
		f = splunk_docker_utils.IMAGE_DIR + f
		CURRENT_IMAGE_FILES[f]='1'


def get_image_info():

	images=cli.images(all='true')	
	#print images
	count=0

	f=open(splunk_docker_utils.IMAGE_DIR +host +"_images.out",'w')
	
	for image in images:

		#print "image is "+str(image)
		name_attr=re.search(r'\[u\'(.*)\'\]',str(images[count]['RepoTags']))
		image_name=name_attr.group(1)
		#IMAGES[host][image_name]={"size": str(images[count]['Size'])}
		f.write(image_name +"," +str(images[count]['Size']) + "\n")
		count +=1

	f.close()
	CURRENT_IMAGE_FILES[splunk_docker_utils.IMAGE_DIR + host + "_images.out"]='2'


def clean_up_image_files():

	for key in CURRENT_IMAGE_FILES:
		if (CURRENT_IMAGE_FILES[key] == "1"):
			if (os.path.isdir(key)):
				continue
			else:
				os.remove(key)


#def get_stats():

	#for container in CONTAINERS:
		#print "in array, container is "+container
		#stats=cli.stats(container, decode=None, stream=False)
		#print "*********************"
		#print "\n"
		#print stats


def check_timeout():

	splunk_docker_utils.get_file_details(splunk_docker_utils.CACHE_DIR)
	if (splunk_docker_utils.CACHE_DIR + "docker_collect.out" in splunk_docker_utils.FILES):
		# compare previous file epoch with current epoch + cache_timeout
		check_epoch = int(splunk_docker_utils.FILES[splunk_docker_utils.CACHE_DIR + 'docker_collect.out']['epoch']) + int(splunk_docker_utils.DOCKER_CFG['cache_timeout'])
		if (int(splunk_docker_utils.EPOCH) >= int(check_epoch)):
			splunk_docker_utils.create_data_file(splunk_docker_utils.CACHE_DIR + 'docker_collect.out',splunk_docker_utils.EPOCH + "," + splunk_docker_utils.FILES[splunk_docker_utils.CACHE_DIR + 'docker_collect.out']['cksum'] + "," + splunk_docker_utils.FILES[splunk_docker_utils.CACHE_DIR + 'docker_collect.out']['size'])
			return "cache_expired"
		else:
			return "ok"
	else:
		# file does not exist, need to create
		splunk_docker_utils.create_data_file(splunk_docker_utils.CACHE_DIR + 'docker_collect.out',splunk_docker_utils.EPOCH + ',0,0')
		return "cache_expired"


def get_last_collection_status(file):

	if (os.path.exists(file)):
		f=open(file,'r')
		line=f.read()
		line=line.rstrip()
		f.close()
		return line
	else:
		return "NO_STATUS,NA"
		

##################
# Main
##################

# Global Vars

CURRENT_CONTAINER_FILES = dict()
CURRENT_IMAGE_FILES = dict()
CONTAINERS = [] 
IMAGES = defaultdict(dict)
CACHE_TIMEOUT = 3600

##################


#cli = Client(base_url='unix://var/run/docker.sock',version='auto')
#cli = Client(base_url='tcp://192.168.160.166:2375', version='auto')

splunk_docker_utils.do_setup()
splunk_docker_utils.parse_conf('splunk_docker_collect.conf')
cache_expire = check_timeout()

hosts = open (splunk_docker_utils.RUN_DIR + '/docker_hosts.dat','r')

# Let's get a list of container files before the run so we can clean up after
get_current_container_files()
# Let's get a list of image file before the run so we can clean up after
get_current_image_files()

for host in hosts:

	host = host.rstrip()
	last_status_file=splunk_docker_utils.CACHE_DIR + host +"_status.out" 
	last_status_attr=get_last_collection_status(last_status_file).split(',')
	last_status=last_status_attr[0]
	last_status_string=last_status_attr[1]

	# Let's first create our connection string
	host=host.rstrip()
	conn_string="tcp://" + host +":2375"

	# Let's create the bulk of our output msg string
	output_string = splunk_docker_utils.RUN_DATE + " - Docker Host:" + host + " - Message:"

	# Now let's create the client and gather our data

	try:
		cli = Client(base_url=conn_string, version='auto')

		# Let's gather container information first
		get_container_info()
		
		# Let's gather image info now
		get_image_info()

		# Let's gather stats for the hosts
		#get_stats()

		# Let's check to see if the collection status has changed, if so, we send to index immediately so dashboard
		# can be updated quicker than the cache_timeout expiry

		if (last_status == "UP"):
			if (cache_expire == 'cache_expired'):
				print output_string + "splunk_docker_collect.py completed successfully"
		else:
			print output_string + "splunk_docker_collect.py completed successfully"
			splunk_docker_utils.create_data_file(last_status_file,"UP" + ",splunk_docker_collect.py completed successfully")

	except Exception, e:

		if (last_status == "DOWN"):
			if (cache_expire == 'cache_expired'):
				print output_string + "splunk_docker_collect.py failed~"+str(e)

			# Would like to have checked that it's the same error, but even error's of the same
			# type have a different obj reference. New error (would be rare) would get sent up on
			# cache_expire anyway 

		else:
			print output_string + "splunk_docker_collect.py failed~"+str(e)
			splunk_docker_utils.create_data_file(last_status_file,"DOWN"+ "," + str(e))


# Clean up container files
clean_up_container_files()
# Clean up image files
clean_up_image_files()
