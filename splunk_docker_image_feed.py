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
		
def create_image_status_hash():

	if (os.path.exists(splunk_docker_utils.CACHE_DIR+"image_status.out")):
		f=open(splunk_docker_utils.CACHE_DIR+"image_status.out",'r')
		for line in f.readlines():
			line=line.rstrip()
			line_attr=line.split(',')
			PREVIOUS_IMAGES[line_attr[0]][line_attr[1]]={'size': line_attr[2], 'epoch': line_attr[3]}				
            
            
def create_current_image_hash():

    for file in os.listdir(splunk_docker_utils.IMAGE_DIR):
        if (os.path.isdir(file)):
            continue
		
        #print "processing file "+file
        docker_host_attr=file.split('_')
        docker_host=docker_host_attr[0]
        f=open(splunk_docker_utils.IMAGE_DIR+file,'r')
        for line in f.readlines():
            line=line.rstrip()
            line_attr=line.split(',')
            CURRENT_IMAGES[docker_host][line_attr[0]]={'size': line_attr[1]}	
        f.close()	
        
        
def create_new_stats_file():

    f=open(splunk_docker_utils.CACHE_DIR+"image_status.out",'w')
    for key in CURRENT_IMAGES:
        for image in CURRENT_IMAGES[key]:
            f.write(key + "," + image + "," + CURRENT_IMAGES[key][image]['size'] + "," + CURRENT_IMAGES[key][image]['epoch']+"\n")
    f.close()

    
##################
# Main
##################

# Global Vars

CACHE_TIMEOUT=86400 # 24 hours
CURRENT_IMAGES = defaultdict(dict)
PREVIOUS_IMAGES = defaultdict(dict)

##################

splunk_docker_utils.do_setup()
splunk_docker_utils.parse_conf('splunk_docker_image_feed.conf')

try:

	# A hash will be created from the status file, a hash will be taken of the image files
	# The image file hash will be looped. The following logic will be applied:
	#
	# 1. If the image is in the status hash, continue unless cache has expired
	# 2. If the image is not present in the status hash, it is new and an event will be
	#    sent to the index
	# 3. If the image is no longer in the image hash but was in the status hash, a removal
	#    event will be send to the index

	if (os.path.exists(splunk_docker_utils.CACHE_DIR+"image_status.out")):

        	# Create a hash of the status file
		create_image_status_hash()
		# Now let's create a hash of the current images
		create_current_image_hash()
		
		for docker_host in CURRENT_IMAGES:
			#print "host is "+docker_host
			#print "processing "+str(CURRENT_IMAGES[docker_host])
			for image in CURRENT_IMAGES[docker_host]:
				#print "image is "+image
				current_image_size=CURRENT_IMAGES[docker_host][image]['size']
				#print "size is "+current_image_size	

				if (image in PREVIOUS_IMAGES[docker_host]):
					#print "Image "+image +"found in previous stats file"
					if (current_image_size == PREVIOUS_IMAGES[docker_host][image]['size']):
						#print "previous image size matches too"
						#print "need to leave this unless epoch expired"
						check_epoch=int(PREVIOUS_IMAGES[docker_host][image]['epoch']) + int(splunk_docker_utils.DOCKER_CFG['cache_timeout'])
						#print "check epoch is "+str(check_epoch)
						#print "epoch is "+splunk_docker_utils.EPOCH
						if (int(splunk_docker_utils.EPOCH) > int(check_epoch)):
							#print "epoch expired, this needs to go up"
							print "Docker Host:"+docker_host + " - Image Name:"+image + " - Image Size:"+CURRENT_IMAGES[docker_host][image]['size'] + " - Status:CACHE_EXPIRE"
							# Let's update the CURRENT_IMAGES hash with the epoch
							CURRENT_IMAGES[docker_host][image]['epoch']=splunk_docker_utils.EPOCH	
							PREVIOUS_IMAGES[docker_host][image]['processed']="yes"
						else:
							# Just need to update the hash to say we've processed this file
							CURRENT_IMAGES[docker_host][image]['epoch']=PREVIOUS_IMAGES[docker_host][image]['epoch']
							PREVIOUS_IMAGES[docker_host][image]['processed']="yes"
					else:
						# Image size appears to have changed, we need to send this change up
						print "Docker Host:"+docker_host + " - Image Name:"+image + " - Image Size:"+CURRENT_IMAGES[docker_host][image]['size'] + " - Status:SIZE_CHANGE"
						PREVIOUS_IMAGES[docker_host][image]['processed']="yes"
						CURRENT_IMAGES[docker_host][image]['epoch']=splunk_docker_utils.EPOCH

				else:
					# Image isn't even in previous status hash, this is new and needs to go up
					print "Docker Host:"+docker_host + " - Image Name:"+image + " - Image Size:"+CURRENT_IMAGES[docker_host][image]['size'] + " - Status:NEW"
					CURRENT_IMAGES[docker_host][image]['epoch']=splunk_docker_utils.EPOCH
					
							
        	# Now we've looped the current images, the image should either be processed or not. If not, it's gone and we need to send a remove
        	# event up to the index
        
        	for docker_host in PREVIOUS_IMAGES:
            		#print "host is "+docker_host
            		for image in PREVIOUS_IMAGES[docker_host]:
                		#print "image is "+image
                		if ("processed" not in PREVIOUS_IMAGES[docker_host][image]):
                    			#print docker_host + " " + image + " has not been processed"
                    			print "Docker Host:"+docker_host + " - Image Name:"+image + " - Image Size:"+PREVIOUS_IMAGES[docker_host][image]['size'] + " - Status:REMOVE"
                    
        	# Finally, let's create our new stats file
        	create_new_stats_file()

	else:
        
		# Nothing to compare, everything must go up to index
		create_current_image_hash() 

		# Let's push the image info to the index and create the stats file for next run
		for key in CURRENT_IMAGES:
			for image in CURRENT_IMAGES[key]:
				print "Docker Host:"+key + " - Image Name:"+image + " - Image Size:"+CURRENT_IMAGES[key][image]['size'] + " - Status:NEW"
				CURRENT_IMAGES[key][image]['epoch']=splunk_docker_utils.EPOCH
                
		create_new_stats_file()


	#print CURRENT_IMAGES
	#print "******************* woo"
	#print PREVIOUS_IMAGES
    
		
except Exception, e:
	print "Exiting - unable to complete main loop: "+str(e)	
	sys.exit(2)


