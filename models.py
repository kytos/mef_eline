"""Classes used in the main application."""
from datetime import datetime
from uuid import uuid4

import requests

from kytos.core import log
from kytos.core.common import GenericEntity
from kytos.core.helpers import get_time, now
from kytos.core.interface import UNI
from napps.kytos.mef_eline import settings


class EVC(GenericEntity):
    """Class that represents a E-Line Virtual Connection."""

    unique_attributes = ['name', 'uni_a', 'uni_z']

    def __init__(self, **kwargs):
        """Create an EVC instance with the provided parameters.

        Args:
            id(str): EVC identifier. Whether it's None an ID will be genereted.
            name: represents an EVC name.(Required)
            uni_a (UNI): Endpoint A for User Network Interface.(Required)
            uni_z (UNI): Endpoint Z for User Network Interface.(Required)
            start_date(datetime|str): Date when the EVC was registred.
                                      Default is now().
            end_date(datetime|str): Final date that the EVC will be fineshed.
                                    Default is None.
            bandwidth(int): Bandwidth used by EVC instance. Default is 0.
            primary_links(list): Primary links used by evc. Default is []
            backup_links(list): Backups links used by evc. Default is []
            current_path(list):circuit being used at the moment if this is an
                                active circuit. Default is [].
            primary_path(list): primary circuit offered to user IF one or more
                                links were provided. Default is [].
            backup_path(list): backup circuit offered to the user IF one or
                               more links were provided. Default is [].
            dynamic_backup_path(bool): Enable computer backup path dynamically.
                                       Dafault is False.
            creation_time(datetime|str): datetime when the circuit should be
                                         activated. default is now().
            enabled(Boolean): attribute to indicate the operational state.
                              default is False.
            active(Boolean): attribute to Administrative state;
                             default is False.
            owner(str): The EVC owner. Default is None.
            priority(int): Service level provided in the request. Default is 0.

        Raises:
            ValueError: raised when object attributes are invalid.

        """
        self._validate(**kwargs)
        super().__init__()

        # required attributes
        self._id = kwargs.get('id', uuid4().hex)
        self.uni_a = kwargs.get('uni_a')
        self.uni_z = kwargs.get('uni_z')
        self.name = kwargs.get('name')

        # optional attributes
        self.start_date = get_time(kwargs.get('start_date')) or now()
        self.end_date = get_time(kwargs.get('end_date')) or None

        self.bandwidth = kwargs.get('bandwidth', 0)
        self.primary_links = kwargs.get('primary_links', [])
        self.backup_links = kwargs.get('backup_links', [])
        self.current_path = kwargs.get('current_path', [])
        self.primary_path = kwargs.get('primary_path', [])
        self.backup_path = kwargs.get('backup_path', [])
        self.dynamic_backup_path = kwargs.get('dynamic_backup_path', False)
        self.creation_time = get_time(kwargs.get('creation_time')) or now()
        self.owner = kwargs.get('owner', None)
        self.priority = kwargs.get('priority', 0)
        self.circuit_scheduler = kwargs.get('circuit_scheduler', [])

        if kwargs.get('active', False):
            self.activate()
        else:
            self.deactivate()

        if kwargs.get('enabled', False):
            self.enable()
        else:
            self.disable()

        # datetime of user request for a EVC (or datetime when object was
        # created)
        self.request_time = kwargs.get('request_time', now())
        # dict with the user original request (input)
        self._requested = kwargs

    def update(self, **kwargs):
        """Update evc attributes.

        This method will raises an error trying to change the following
        attributes: [name, uni_a and uni_z]

        Raises:
            ValueError: message with error detail.

        """
        for attribute, value in kwargs.items():
            if attribute in self.unique_attributes:
                raise ValueError(f'{attribute} can\'t be be updated.')
            if hasattr(self, attribute):
                setattr(self, attribute, value)
            else:
                raise ValueError(f'The attribute "{attribute}" is invalid.')

    def __repr__(self):
        """Repr method."""
        return f"EVC({self._id}, {self.name})"

    def _validate(self, **kwargs):
        """Do Basic validations.

        Verify required attributes: name, uni_a, uni_z
        Verify if the attributes uni_a and uni_z are valid.

        Raises:
            ValueError: message with error detail.

        """
        for attribute in self.unique_attributes:

            if attribute not in kwargs:
                raise ValueError(f'{attribute} is required.')

            if 'uni' in attribute:
                uni = kwargs.get(attribute)
                if not isinstance(uni, UNI):
                    raise ValueError(f'{attribute} is an invalid UNI.')

                elif not uni.is_valid():
                    tag = uni.user_tag.value
                    message = f'VLAN tag {tag} is not available in {attribute}'
                    raise ValueError(message)

    def __eq__(self, other):
        """Override the default implementation."""
        if not isinstance(other, EVC):
            return False

        attrs_to_compare = ['name', 'uni_a', 'uni_z', 'owner', 'bandwidth']
        for attribute in attrs_to_compare:
            if getattr(other, attribute) != getattr(self, attribute):
                return False
        return True

    def as_dict(self):
        """Return a dictionary representing an EVC object."""
        evc_dict = {"id": self.id, "name": self.name,
                    "uni_a": self.uni_a.as_dict(),
                    "uni_z": self.uni_z.as_dict()}

        time_fmt = "%Y-%m-%dT%H:%M:%S"

        def link_as_dict(links):
            """Return list comprehension of links as_dict."""
            return [link.as_dict() for link in links if link]

        evc_dict["start_date"] = self.start_date
        if isinstance(self.start_date, datetime):
            evc_dict["start_date"] = self.start_date.strftime(time_fmt)

        evc_dict["end_date"] = self.end_date
        if isinstance(self.end_date, datetime):
            evc_dict["end_date"] = self.end_date.strftime(time_fmt)

        evc_dict['bandwidth'] = self.bandwidth
        evc_dict['primary_links'] = link_as_dict(self.primary_links)
        evc_dict['backup_links'] = link_as_dict(self.backup_links)
        evc_dict['current_path'] = link_as_dict(self.current_path)
        evc_dict['primary_path'] = link_as_dict(self.primary_path)
        evc_dict['backup_path'] = link_as_dict(self.backup_path)
        evc_dict['dynamic_backup_path'] = self.dynamic_backup_path

        if self._requested:
            request_dict = self._requested.copy()
            request_dict['uni_a'] = request_dict['uni_a'].as_dict()
            request_dict['uni_z'] = request_dict['uni_z'].as_dict()
            evc_dict['_requested'] = request_dict

        evc_dict["request_time"] = self.request_time
        if isinstance(self.request_time, datetime):
            evc_dict["end_date"] = self.request_time.strftime(time_fmt)

        time = self.creation_time.strftime(time_fmt)
        evc_dict['creation_time'] = time

        evc_dict['owner'] = self.owner
        evc_dict['circuit_scheduler'] = self.circuit_scheduler
        evc_dict['active'] = self.is_active()
        evc_dict['enabled'] = self.is_enabled()
        evc_dict['priority'] = self.priority

        return evc_dict

    def create(self):
        """Create a EVC."""
        pass

    def discover_new_path(self):
        """Discover a new path for EVC."""
        pass

    def change_path(self, path):
        """Change EVC path."""
        pass

    def reprovision(self):
        """Force the EVC (re-)provisioning."""
        pass

    def remove(self):
        """Remove EVC path."""
        pass

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return this EVC's ID."""
        return self._id

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

    def should_deploy(self):
        """Verify if the circuit should be deployed."""
        if not self.primary_links:
            log.debug("Primary links are empty.")
            return False

        if not self.is_enabled():
            log.debug(f'{self} is disabled.')
            return False

        if not self.is_active():
            log.debug(f'{self} will be deployed.')
            return True

        return False

    def deploy(self):
        """Install the flows for this circuit."""
        if not self.should_deploy():
            return

        self._chose_vlans()
        self.install_nni_flows()
        self.install_uni_flows()
        self.activate()
        log.info(f"{self} was deployed.")

    def install_nni_flows(self):
        """Install NNI flows."""
        for incoming, outcoming in self.primary_links_zipped():
            in_vlan = incoming.get_metadata('s_vlan').value
            out_vlan = outcoming.get_metadata('s_vlan').value

            flows = []
            # Flow for one direction
            flows.append(self.prepare_nni_flow(incoming.endpoint_b,
                                               outcoming.endpoint_a,
                                               in_vlan, out_vlan))

            # Flow for the other direction
            flows.append(self.prepare_nni_flow(outcoming.endpoint_a,
                                               incoming.endpoint_b,
                                               out_vlan, in_vlan))
            self.send_flow_mods(incoming.endpoint_b.switch, flows)

    def install_uni_flows(self):
        """Install UNI flows."""
        # Install UNI flows
        # Determine VLANs
        in_vlan_a = self.uni_a.user_tag.value if self.uni_a.user_tag else None
        out_vlan_a = self.primary_links[0].get_metadata('s_vlan').value

        in_vlan_z = self.uni_z.user_tag.value if self.uni_z.user_tag else None
        out_vlan_z = self.primary_links[-1].get_metadata('s_vlan').value

        # Flows for the first UNI
        flows_a = []

        # Flow for one direction, pushing the service tag
        push_flow = self.prepare_push_flow(self.uni_a.interface,
                                           self.primary_links[0].endpoint_a,
                                           in_vlan_a, out_vlan_a, in_vlan_z)
        flows_a.append(push_flow)

        # Flow for the other direction, popping the service tag
        pop_flow = self.prepare_pop_flow(self.primary_links[0].endpoint_a,
                                         self.uni_a.interface, out_vlan_a)
        flows_a.append(pop_flow)

        self.send_flow_mods(self.uni_a.interface.switch, flows_a)

        # Flows for the second UNI
        flows_z = []

        # Flow for one direction, pushing the service tag
        push_flow = self.prepare_push_flow(self.uni_z.interface,
                                           self.primary_links[-1].endpoint_b,
                                           in_vlan_z, out_vlan_z, in_vlan_a)
        flows_z.append(push_flow)

        # Flow for the other direction, popping the service tag
        pop_flow = self.prepare_pop_flow(self.primary_links[-1].endpoint_b,
                                         self.uni_z.interface, out_vlan_z)
        flows_z.append(pop_flow)

        self.send_flow_mods(self.uni_z.interface.switch, flows_z)

    @staticmethod
    def send_flow_mods(switch, flow_mods):
        """Send a flow_mod list to a specific switch."""
        endpoint = "%s/flows/%s" % (settings.MANAGER_URL, switch.id)

        data = {"flows": flow_mods}
        requests.post(endpoint, json=data)

    @staticmethod
    def prepare_flow_mod(in_interface, out_interface):
        """Prepare a common flow mod."""
        default_action = {"action_type": "output",
                          "port": out_interface.port_number}

        flow_mod = {"match": {"in_port": in_interface.port_number},
                    "actions": [default_action]}

        return flow_mod

    def prepare_nni_flow(self, in_interface, out_interface, in_vlan, out_vlan):
        """Create NNI flows."""
        flow_mod = self.prepare_flow_mod(in_interface, out_interface)
        flow_mod['match']['dl_vlan'] = in_vlan

        new_action = {"action_type": "set_vlan",
                      "vlan_id": out_vlan}
        flow_mod["actions"].insert(0, new_action)

        return flow_mod

    def prepare_push_flow(self, *args):
        """Prepare push flow.

        Arguments:
            in_interface(str): Interface input.
            out_interface(str): Interface output.
            in_vlan(str): Vlan input.
            out_vlan(str): Vlan output.
            new_in_vlan(str): Interface input.

        Return:
            dict: An python dictionary representing a FlowMod

        """
        # assign all arguments
        in_interface, out_interface, in_vlan, out_vlan, new_in_vlan = args

        flow_mod = self.prepare_flow_mod(in_interface, out_interface)
        flow_mod['match']['dl_vlan'] = in_vlan

        new_action = {"action_type": "set_vlan",
                      "vlan_id": out_vlan}
        flow_mod["actions"].insert(0, new_action)

        new_action = {"action_type": "push_vlan",
                      "tag_type": "s"}
        flow_mod["actions"].insert(0, new_action)

        new_action = {"action_type": "set_vlan",
                      "vlan_id": new_in_vlan}
        flow_mod["actions"].insert(0, new_action)

        return flow_mod

    def prepare_pop_flow(self, in_interface, out_interface, in_vlan):
        """Prepare pop flow."""
        flow_mod = self.prepare_flow_mod(in_interface, out_interface)
        flow_mod['match']['dl_vlan'] = in_vlan
        new_action = {"action_type": "pop_vlan"}
        flow_mod["actions"].insert(0, new_action)
        return flow_mod
