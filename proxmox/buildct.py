#!/usr/bin/env python
#
# Prototype for handle containers into the Proxmox cluster
#
# Author Simone Roselli <simoneroselli78@gmail.com>

from pyproxmox import *
from glob import *
import json, sys, time, os.path

# Import configuration
execfile('buildct.conf')

# Define a connection to the cluster
auth = prox_auth(CLUSTER_IP, USER_AUTH, PASS_AUTH)

# Instance a new PyProxmox object
p = pyproxmox(auth)

NEW_CT_HOSTNAME = sys.argv[1]
NEW_CT_MACADDRESS = ""

# Retrieve the next reusable CT id 
NEXT_CT_ID = p.getClusterVmNextId()

def cluster_nodes(nodes):
  """ Easily define how many nodes are running on the cluster. Return
  a hostname list """
  cluster = []
  for i in nodes['data']:
    for k, v in i.items():
      if k == 'node':
        cluster.append(v)
  
  return cluster

def ct_per_node(nodes):
  """ Count how many containers are currently running on each node.
  Return a dictionary like 'nodename: <number_of_ct>' """
  ct_values = {}
  for i in nodes: 
    ct_index = p.getNodeContainerIndex(i)
    cts = len(ct_index['data'])
    ct_values[i] = cts

  return ct_values

def check_tasks(tasks, upid):
  """ Check if the ran task is into the 'finished tasks' list """
  for i in tasks:
    for k, v in i.items():
      if k == 'upid':
        if v == upid:
          return True

if __name__=='__main__':

  # Check if a BuildCt instance is already running, in the case wait until the
  # lock file will release. Thi lockfile is created on the clinet machine (jenkins) itself
  if os.path.isfile(LOCKFILE) == True:
    while os.path.isfile(LOCKFILE) == True:
      print "BuildCt is already running .. please wait "
      time.sleep(5)
  
  open(LOCKFILE, 'a').close()
  
  # Node to deploy 
  if len(sys.argv) == 1:
    print "Usage buildct.py hostname <node>"
    exit()
  elif  len(sys.argv) == 2:
    NODE_TO_DEPLOY = min(nodes_occupation, key=nodes_occupation.get)
  elif len(sys.argv) == 3:
    NODE_TO_DEPLOY = sys.argv[2]
  elif len(sys.argv) == 4:
    NODE_TO_DEPLOY = sys.argv[2]
    NEW_CT_MACADDRESS = sys.argv[3]
  
  CLUSTER_NODES = cluster_nodes(p.getNodes())
  nodes_occupation = ct_per_node(CLUSTER_NODES)

  # Dump template CT
  print 'Starting "%s" dump ..' % (TEMPL_ID)
  dump_upid = p.dumpOpenvzContainer(NODE_TO_DEPLOY, dump_data)

  count = 0
  
  while (count < 30):
    state = p.getNodeFinishedTasks(NODE_TO_DEPLOY)
    task = check_tasks(state['data'], dump_upid['data'])
    if task != None:
      print 'Done!'
      break
    else:
      time.sleep(5)
      count = count + 1
  else:
      print 'Dumping timeout or couldn\'t be accomplished'
      exit()


  STORAGE_CONTENT = p.getStorageVolumeData(NODE_TO_DEPLOY, STORAGE_ID, '/')
  TEMPL_DUMP = STORAGE_CONTENT['data'][0]['volid']

  # Dump CT configuration
  dump_data = {
  'vmid': TEMPL_ID,
  'storage': STORAGE_ID,
  'quiet': 1,
  }

  # Restore CT configuration
  if NEW_CT_MACADDRESS != "":
    clone_data = {
    'ostemplate': TEMPL_DUMP,
    'vmid': NEXT_CT_ID['data'],
    'storage': STORAGE_ID,
    'cpus': CPUS,
    'hostname': NEW_CT_HOSTNAME + '.local',
    'memory': MEMORY,
    'swap': SWAP,
    'netif': NETIF + ',host_ifname=veth' + NEXT_CT_ID['data'] + '.0,mac=' + NEW_CT_MACADDRESS,
    'nameserver': NAMESERVER,
    }
  else:
    clone_data = {
    'ostemplate': TEMPL_DUMP,
    'vmid': NEXT_CT_ID['data'],
    'storage': STORAGE_ID,
    'cpus': CPUS,
    'hostname': NEW_CT_HOSTNAME + '.local',
    'memory': MEMORY,
    'swap': SWAP,
    'netif': NETIF + ',host_ifname=veth' + NEXT_CT_ID['data'] + '.0',
    'nameserver': NAMESERVER,
    }

  # Validate dump template     
  if not 'vzdump-openvz-' + TEMPL_ID in TEMPL_DUMP:
    print 'Dump template "%s" not valid' % (TEMPL_DUMP)
    exit()
  else:
    # Clone the new CT from the dump
    print 'Cloning CT "%s" on node \'"%s"\'' % (TEMPL_ID, NODE_TO_DEPLOY)
    clone_upid = p.createOpenvzContainer(NODE_TO_DEPLOY, clone_data)


