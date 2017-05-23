#!/usr/bin/python
import sys
import os
import subprocess
import re

import splunk_docker_utils
from collections import defaultdict
from docker import Client

##################
# Routines
##################


##################
# Main
##################

# Global Vars

##################

splunk_docker_utils.do_setup()

# We need to loop running containers, getting stats

hosts = open (splunk_docker_utils.RUN_DIR + '/docker_hosts.dat','r')

for host in hosts:

    host=host.rstrip()
    conn_string="tcp://" + host +":2375"        
    #cli = Client(base_url='tcp://192.168.160.166:2375', version='auto')

    try:
        cli = Client(base_url=conn_string, version='auto')
        containers=cli.containers()
        count=0
        for container in containers:
            #print "container is "+str(container)
            name_attr=re.search( r'\[u\'\/(\w+)\'\]',str(containers[count]['Names']))
            container_name=name_attr.group(1)	
            count +=1
            inspect=cli.inspect_container(container_name)
            # We need hostname, unfortunately we have to inspect container for it
            hostname=inspect['Config']['Hostname']
            stats=cli.stats(container_name,decode=None, stream=False)

            # Memory

            max_usage = stats['memory_stats']['max_usage']
            usage = stats['memory_stats']['usage']
            limit = stats['memory_stats']['limit']
            mem_pct_used = round(float(usage) / float(limit) * 100,2)
            page_faults = stats['memory_stats']['stats']['total_pgmajfault']
            pgin = stats['memory_stats']['stats']['total_pgpgin']
            pgout = stats['memory_stats']['stats']['total_pgpgout']
            
        
            print "Docker Host:"+host + " - Container Name:"+container_name + " - Hostname:"+hostname + " - MaxUsage:"+str(max_usage) + " - Usage:"+str(usage) + " - Limit:"+str(limit) + " - PctUsed:"+str(mem_pct_used) + " - PageFaults:"+str(page_faults) + " - PageIn:"+str(pgin)+ " - PageOut:"+str(pgout)    
                
    except Exception, e:

            # We'll just continue here
            #print str(e)
            continue
            