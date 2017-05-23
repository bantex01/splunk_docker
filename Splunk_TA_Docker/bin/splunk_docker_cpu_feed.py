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
            name_attr=re.search( r'\[u\'\/(\w+)\'\]',str(containers[count]['Names']))
            container_name=name_attr.group(1)	
            count +=1
            inspect=cli.inspect_container(container_name)
            # We need hostname, unfortunately we have to inspect container for it
            hostname=inspect['Config']['Hostname']
            stats=cli.stats(container_name,decode=None, stream=False)

            # Perentage of CPU used by the container

            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] -  stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_usage = round(float(cpu_delta) / float(system_delta) * 100,2)
            
            print "Docker Host:"+host + " - Container Name:"+container_name + " - Hostname:"+hostname + " - CPUPct:"+str(cpu_usage)
                
    except Exception, e:

            # We'll just continue here
            continue
            