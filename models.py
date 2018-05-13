"""Classes used in the main application."""
from uuid import uuid4

import json
import requests
from datetime import datetime

from kytos.core import log
from kytos.core.helpers import now, get_time
from kytos.core.interface import UNI, TAG
from napps.kytos.mef_eline import settings


class EVC:
    """Class that represents a E-Line Virtual Connection."""

    def __init__(self, name, uni_a, uni_z, start_date=None, end_date=None,
                 bandwidth=0, primary_links=None, backup_links=None,
                 dynamic_backup_path=False, creation_time=None):
        """Create an EVC instance with the provided parameters.

        Do some basic validations to attributes.
        """
        self.validate(name, uni_a, uni_z)

        self._id = uuid4().hex
        self.uni_a = uni_a
        self.uni_z = uni_z
        self.name = name
        self.start_date = start_date if start_date else now()
        self.end_date = end_date
        # Bandwidth profile
        self.bandwidth = bandwidth
        self.primary_links = primary_links if primary_links else []
        self.backup_links = backup_links if backup_links else []
        self.dynamic_backup_path = dynamic_backup_path
        # dict with the user original request (input)
        self._requested = {}
        # circuit being used at the moment if this is an active circuit
        self.current_path = []
        # primary circuit offered to user IF one or more links were provided in
        # the request
        self.primary_path = []
        # backup circuit offered to the user IF one or more links were provided
        # in the request
        self.backup_path = []
        # datetime of user request for a EVC (or datetime when object was
        # created)
        self.request_time = now()
        # datetime when the circuit should be activated. now() || schedule()
        self.creation_time = get_time(creation_time) or now()
        self.owner = None
        # Operational State
        self.active = False
        # Administrative State
        self.enabled = False
        # Service level provided in the request. "Gold", "Silver", ...
        self.priority = 0

    def validate(self, name=None, uni_a=None, uni_z=None):
        """Validate the EVC arguments.

        Raises:
            ValueError: raised when object attributes are invalid.
        """
        # Verify required attributes
        if name is None:
            raise ValueError("name is required.")

        if uni_a is None:
            raise ValueError("uni_a is required")

        if uni_z is None:
            raise ValueError('uni_z is required')

        # Verify UNIs instances
        if not isinstance(uni_a, UNI):
            raise ValueError("Invalid uni_a.")

        if not isinstance(uni_z, UNI):
            raise ValueError("Invalid uni_z.")

        # Verify if UNIs is valid
        if not uni_a.is_valid():
            tag = uni_a.user_tag.value
            raise ValueError(f"VLAN tag {tag} is not available on uni_a.")

        if not uni_z.is_valid():
            tag = uni_z.user_tag.value
            raise ValueError(f"VLAN tag {tag} is not available on uni_z.")

    def as_dict(self):
        """A dictionary representing an EVC object."""
        evc_dict = {"id": self.id, "name": self.name,
                    "uni_a": self.uni_a.as_dict(),
                    "uni_z": self.uni_z.as_dict()}

        time_fmt = "%Y-%m-%dT%H:%M:%S"

        date = self.start_date.strftime(time_fmt)
        evc_dict["start_date"] = date

        date = self.end_date
        if date:
            date = self.end_date.strftime(time_fmt)
        evc_dict['end_date'] = date

        evc_dict['bandwidth'] = self.bandwidth

        evc_dict['primary_links'] = [link.as_dict() for link in
                                     self.primary_links if link]

        evc_dict['backup_links'] = [link.as_dict() for link in
                                    self.backup_links if link]

        evc_dict['dynamic_backup_path'] = self.dynamic_backup_path

        if self._requested:
            evc_dict['_requested'] = self._requested

        evc_dict['current_path'] = self.current_path
        evc_dict['primary_path'] = self.primary_path
        evc_dict['backup_path'] = self.backup_path

        time = self.request_time.strftime(time_fmt)
        evc_dict['request_time'] = time

        time = self.creation_time.strftime(time_fmt)
        evc_dict['creation_time'] = time

        evc_dict['owner'] = self.owner
        evc_dict['active'] = self.active
        evc_dict['enabled'] = self.enabled
        evc_dict['priority'] = self.priority

        return evc_dict

    def as_json(self):
        """Json representation for the EVC object."""
        return json.dumps(self.as_dict())

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return this EVC's ID."""
        return self._id

    def create(self):
        pass

    def discover_new_path(self):
        pass

    def change_path(self, path):
        pass

    def reprovision(self):
        """Force the EVC (re-)provisioning"""
        pass

    def remove(self):
        pass

    @staticmethod
    def send_flow_mods(switch, flow_mods):
        """Send a flow_mod list to a specific switch."""
        endpoint = "%s/flows/%s" % (settings.MANAGER_URL, switch.id)

        data = {"flows": flow_mods}
        requests.post(endpoint, json=data)

    @staticmethod
    def prepare_flow_mod(in_interface, out_interface, in_vlan=None,
                         out_vlan=None, push=False, pop=False, change=False):
        """Create a flow_mod dictionary with the correct parameters."""
        default_action = {"action_type": "output",
                          "port": out_interface.port_number}

        flow_mod = {"match": {"in_port": in_interface.port_number},
                    "actions": [default_action]}
        if in_vlan:
            flow_mod['match']['dl_vlan'] = in_vlan
        if out_vlan and not pop:
            new_action = {"action_type": "set_vlan",
                          "vlan_id": out_vlan}
            flow_mod["actions"].insert(0, new_action)
        if pop:
            new_action = {"action_type": "pop_vlan"}
            flow_mod["actions"].insert(0, new_action)
        if push:
            new_action = {"action_type": "push_vlan",
                          "tag_type": "s"}
            flow_mod["actions"].insert(0, new_action)
        if change:
            new_action = {"action_type": "set_vlan",
                          "vlan_id": change}
            flow_mod["actions"].insert(0, new_action)
        return flow_mod

    def _chose_vlans(self):
        """Chose the VLANs to be used for the circuit."""
        for link in self.primary_links:
            tag = link.get_next_available_tag()
            link.use_tag(tag)
            link.add_metadata('s_vlan', tag)

    def primary_links_zipped(self):
        """Return an iterator which yields pairs of links in order."""
        return zip(self.primary_links[:-1],
                   self.primary_links[1:])

    def deploy(self):
        """Install the flows for this circuit."""
        if self.primary_links is None:
            log.info("Primary links are empty.")
            return False

        self._chose_vlans()

        # Install NNI flows
        for incoming, outcoming in self.primary_links_zipped():
            in_vlan = incoming.get_metadata('s_vlan').value
            out_vlan = outcoming.get_metadata('s_vlan').value

            flows = []
            # Flow for one direction
            flows.append(self.prepare_flow_mod(incoming.endpoint_b,
                                               outcoming.endpoint_a,
                                               in_vlan, out_vlan))

            # Flow for the other direction
            flows.append(self.prepare_flow_mod(outcoming.endpoint_a,
                                               incoming.endpoint_b,
                                               out_vlan, in_vlan))

            self.send_flow_mods(incoming.endpoint_b.switch, flows)

        # Install UNI flows
        # Determine VLANs
        in_vlan_a = self.uni_a.user_tag.value if self.uni_a.user_tag else None
        out_vlan_a = self.primary_links[0].get_metadata('s_vlan').value

        in_vlan_z = self.uni_z.user_tag.value if self.uni_z.user_tag else None
        out_vlan_z = self.primary_links[-1].get_metadata('s_vlan').value

        # Flows for the first UNI
        flows_a = []

        # Flow for one direction, pushing the service tag
        flows_a.append(self.prepare_flow_mod(self.uni_a.interface,
                                             self.primary_links[0].endpoint_a,
                                             in_vlan_a, out_vlan_a, True,
                                             change=in_vlan_z))

        # Flow for the other direction, popping the service tag
        flows_a.append(self.prepare_flow_mod(self.primary_links[0].endpoint_a,
                                             self.uni_a.interface,
                                             out_vlan_a, in_vlan_a, pop=True))

        self.send_flow_mods(self.uni_a.interface.switch, flows_a)

        # Flows for the second UNI
        flows_z = []

        # Flow for one direction, pushing the service tag
        flows_z.append(self.prepare_flow_mod(self.uni_z.interface,
                                             self.primary_links[-1].endpoint_b,
                                             in_vlan_z, out_vlan_z, True,
                                             change=in_vlan_a))

        # Flow for the other direction, popping the service tag
        flows_z.append(self.prepare_flow_mod(self.primary_links[-1].endpoint_b,
                                             self.uni_z.interface,
                                             out_vlan_z, in_vlan_z, pop=True))

        self.send_flow_mods(self.uni_z.interface.switch, flows_z)

        log.info(f"Deployed EVC id {self.id}, name {self.name}.")
