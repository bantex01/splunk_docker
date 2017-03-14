#!/usr/bin/python
import sys
import os
import subprocess
import re

import splunk_docker_utils
from collections import defaultdict

##################
# Routines
##################

def parse_status_file(file):

	#print "in parse status "+file

	f=open(file,'r')
	for line in f.readlines():
		line=line.rstrip()
		line_attr=re.search(r'(.*),(.*),(.*),(.*)',line)	 
		CONTAINER_STATUS[line_attr.group(1)]['epoch'] = line_attr.group(2)
		CONTAINER_STATUS[line_attr.group(1)]['cksum'] = line_attr.group(3)
		CONTAINER_STATUS[line_attr.group(1)]['size'] = line_attr.group(4)

	f.close()
		

##################
# Main
##################

# Global Vars

CACHE_TIMEOUT=86400 # 24 hours
CONTAINER_STATUS = defaultdict(dict)
OUTPUT = []

##################

splunk_docker_utils.do_setup()
splunk_docker_utils.parse_conf('splunk_docker_container_feed.conf')

try:

	# See if there's a records file, if not, let's just loop through all 	
	# container files taking details, creating the records file and finally 
	# sending data to index 

	if (os.path.exists(splunk_docker_utils.CACHE_DIR + "container_status.out")):
		#print "container status file exists"

		# We need to get a list of the files, then compare them with what's
		# in our status file. If there's a container file in our stats file and
		# no longer appears to exist, that will be removed from the next stats file.
		#
		# If container file exists and is in status file, the following will occur
		#
		# 1. If the cksum has changed, the file detail will be sent to the index
		# 2. If the epoch of last update has breached the config item
		#    cache_timeout, then data will be sent to index

		splunk_docker_utils.get_file_details(splunk_docker_utils.CONTAINER_DIR)	
		parse_status_file(splunk_docker_utils.CACHE_DIR + "container_status.out")

		# We now have a hash of the file details (FILES) from the container files and a
		# hash of file details from status file (CONTAINER_STATUS)

		# Let's loop the container file hash - we'll create a new status file
		# at the end of this

		for container in splunk_docker_utils.FILES:
			#print "working with "+container
			if (container in CONTAINER_STATUS):
				#print container + " found in status file"
				next_update_epoch=int(CONTAINER_STATUS[container]['epoch']) + int(splunk_docker_utils.DOCKER_CFG['cache_timeout']) 	
				#print "next epoch is " + str(next_update_epoch)	
				if (int(splunk_docker_utils.EPOCH) > int(next_update_epoch)):
					#print "epoch passed timeout, need to send data up" 
					OUTPUT.append(container)
					splunk_docker_utils.FILES[container]['epoch'] = splunk_docker_utils.EPOCH
					# Need to update the actual files epoch here to ensure the stats file and file match
					splunk_docker_utils.touch_file(container)	
				else:
					# epoch OK, let's check cksum
					if (splunk_docker_utils.FILES[container]['cksum'] != CONTAINER_STATUS[container]['cksum']):
						#print "cksum differences found, need to update"
						OUTPUT.append(container)
					#else:
						#print "no cksum differences found, leaving as-is"

			else:
				# No previous status found, must be new container
				#print "New container found "+container
				OUTPUT.append(container)			

		# Here, we should have an updated FILES dictionary that will be used to create the new stats file
		# and output array that we will loop to create the data feed
		
		for file in OUTPUT:
			#print file
			splunk_docker_utils.read_lines_from_file(file)
		
		splunk_docker_utils.create_stats_file(splunk_docker_utils.CACHE_DIR + "container_status.out")

	else:

		# No stats file, nothing to compare against, let's get the data in
		# the index and create our stats file for next run

		splunk_docker_utils.get_file_details(splunk_docker_utils.CONTAINER_DIR)

		# we now need to loop the files dictionary, cat'ing out the files
		# and making our stats file for next run

		for key in splunk_docker_utils.FILES:

			# Read lines to STDOUT to be sent to index
			splunk_docker_utils.read_lines_from_file(key)
			
			# Create stats file for next run
			splunk_docker_utils.create_stats_file(splunk_docker_utils.CACHE_DIR + "container_status.out")	


	# Finally, let's send up removed events to index for containers no longer found between runs

	for file in os.listdir(splunk_docker_utils.CONTAINER_DEAD_DIR):
		if (os.path.isdir(file)):
			continue
		else:
			container_string=splunk_docker_utils.gather_attributes_from_file("container",splunk_docker_utils.CONTAINER_DEAD_DIR+file)
			attr=container_string.split(",")
			print "Docker Host:"+attr[0] +" - Container Name:"+attr[1] +" - Host Name:"+attr[2] +" - Status:Removed - Image:"+attr[4] +" - Command:"+attr[5]+"\n"
			os.remove(splunk_docker_utils.CONTAINER_DEAD_DIR+file)

		
except Exception, e:
	print "Exiting - unable to complete main loop: "+str(e)	
	sys.exit(2)


#for key in splunk_docker_utils.DOCKER_CFG:
        #print key + " = " +str(splunk_docker_utils.DOCKER_CFG[key])

#print "*********************"

#print "Files from status file"
#for key in CONTAINER_STATUS:
#	print key + " = " +str(CONTAINER_STATUS[key])

#print "Files in status file after run"
#for key in splunk_docker_utils.FILES:
#        print key + " = " +str(splunk_docker_utils.FILES[key])

