"""Settings for the mef_eline NApp."""

# Base URL of the Pathfinder endpoint
PATHFINDER_URL = 'http://localhost:8181/api/kytos/pathfinder/v2/'

# Base URL of the Flow Manager endpoint
MANAGER_URL = 'http://localhost:8181/api/kytos/flow_manager/v2'

# VLAN pool settings

# The VLAN pool settings is a dictionary of datapath id, which contains
# a dictionary of of_port numbers with the respective vlan pool range
# that should be used on this of_port. See the example below, which
# sets the vlan range from 101 to 119 for of_ports 1 and 4:

# vlan_ids should be an iterable of int values between 1 and 4095
# vlan_ids = range(101, 120)
# VLAN_POOL_OVERRIDE = {"00:00:00:00:00:00:00:01": {1: vlan_ids, 4: vlan_ids}}

VLAN_POOL_OVERRIDE = {}
