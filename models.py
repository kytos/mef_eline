"""Classes used in the main application."""
from datetime import datetime
from uuid import uuid4

import requests

from kytos.core import log
from kytos.core.common import EntityStatus, GenericEntity
from kytos.core.helpers import get_time, now
from kytos.core.interface import UNI
from kytos.core.link import Link
from napps.kytos.mef_eline import settings
from napps.kytos.mef_eline.storehouse import StoreHouse


class Path(list, GenericEntity):
    """Class to represent a Path."""

    def __eq__(self, other=None):
        """Compare paths."""
        if not other or not isinstance(other, Path):
            return False
        return super().__eq__(other)

    def is_affected_by_link(self, link=None):
        """Verify if the current path is affected by link."""
        if not link:
            return False
        return link in self

    def link_affected_by_interface(self, interface=None):
        """Return the link using this interface, if any, or None otherwise."""
        if not interface:
            return None
        for link in self:
            if interface in (link.endpoint_a, link.endpoint_b):
                return link
        return None

    def choose_vlans(self):
        """Choose the VLANs to be used for the circuit."""
        for link in self:
            tag = link.get_next_available_tag()
            link.use_tag(tag)
            link.add_metadata('s_vlan', tag)

    def make_vlans_available(self):
        """Make the VLANs used in a path available when undeployed."""
        for link in self:
            link.make_tag_available(link.get_metadata('s_vlan'))
            link.remove_metadata('s_vlan')

    @property
    def status(self):
        """Check for the  status of a path.

        If any link in this path is down, the path is considered down.
        """
        if not self:
            return EntityStatus.DISABLED

        endpoint = '%s/%s' % (settings.TOPOLOGY_URL, 'links')
        api_reply = requests.get(endpoint)
        if api_reply.status_code != getattr(requests.codes, 'ok'):
            log.error('Failed to get links at %s. Returned %s',
                      endpoint, api_reply.status_code)
            return None
        links = api_reply.json()['links']
        for path_link in self:
            try:
                link = links[path_link.id]
            except KeyError:
                return EntityStatus.DOWN
            if link['active'] is False:
                return EntityStatus.DOWN
        return EntityStatus.UP

    def as_dict(self):
        """Return list comprehension of links as_dict."""
        return [link.as_dict() for link in self if link]


class DynamicPathManager:
    """Class to handle and create paths."""

    controller = None

    @classmethod
    def set_controller(cls, controller=None):
        """Set the controller to discovery news paths."""
        cls.controller = controller

    @staticmethod
    def get_paths(circuit):
        """Get a valid path for the circuit from the Pathfinder."""
        endpoint = settings.PATHFINDER_URL
        request_data = {"source": circuit.uni_a.interface.id,
                        "destination": circuit.uni_z.interface.id}
        api_reply = requests.post(endpoint, json=request_data)

        if api_reply.status_code != getattr(requests.codes, 'ok'):
            log.error("Failed to get paths at %s. Returned %s",
                      endpoint, api_reply.status_code)
            return None
        reply_data = api_reply.json()
        return reply_data.get('paths')

    @staticmethod
    def _clear_path(path):
        """Remove switches from a path, returning only interfaces."""
        return [endpoint for endpoint in path if len(endpoint) > 23]

    @classmethod
    def get_best_path(cls, circuit):
        """Return the best path available for a circuit, if exists."""
        paths = cls.get_paths(circuit)
        if paths:
            return cls.create_path(cls.get_paths(circuit)[0]['hops'])
        return None

    @classmethod
    def create_path(cls, path):
        """Return the path containing only the interfaces."""
        new_path = Path()
        clean_path = cls._clear_path(path)

        if len(clean_path) % 2:
            return None

        for link in zip(clean_path[1:-1:2], clean_path[2::2]):
            interface_a = cls.controller.get_interface_by_id(link[0])
            interface_b = cls.controller.get_interface_by_id(link[1])
            if interface_a is None or interface_b is None:
                return None
            new_path.append(Link(interface_a, interface_b))

        return new_path


class EVCBase(GenericEntity):
    """Class to represent a circuit."""

    unique_attributes = ['name', 'uni_a', 'uni_z']

    def __init__(self, controller, **kwargs):
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
            current_path(list): Circuit being used at the moment if this is an
                                active circuit. Default is [].
            primary_path(list): primary circuit offered to user IF one or more
                                links were provided. Default is [].
            backup_path(list): backup circuit offered to the user IF one or
                               more links were provided. Default is [].
            dynamic_backup_path(bool): Enable computer backup path dynamically.
                                       Dafault is False.
            creation_time(datetime|str): datetime when the circuit should be
                                         activated. default is now().
            enabled(Boolean): attribute to indicate the administrative state;
                              default is False.
            active(Boolean): attribute to indicate the operational state;
                             default is False.
            archived(Boolean): indicate the EVC has been deleted and is
                               archived; default is False.
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
        self.primary_links = Path(kwargs.get('primary_links', []))
        self.backup_links = Path(kwargs.get('backup_links', []))
        self.current_path = Path(kwargs.get('current_path', []))
        self.primary_path = Path(kwargs.get('primary_path', []))
        self.backup_path = Path(kwargs.get('backup_path', []))
        self.dynamic_backup_path = kwargs.get('dynamic_backup_path', False)
        self.creation_time = get_time(kwargs.get('creation_time')) or now()
        self.owner = kwargs.get('owner', None)
        self.priority = kwargs.get('priority', 0)
        self.circuit_scheduler = kwargs.get('circuit_scheduler', [])

        self.current_links_cache = set()
        self.primary_links_cache = set()
        self.backup_links_cache = set()

        self.archived = kwargs.get('archived', False)

        self._storehouse = StoreHouse(controller)

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

    def sync(self):
        """Sync this EVC in the storehouse."""
        self._storehouse.save_evc(self)
        log.info(f'EVC {self.id} was synced to the storehouse.')

    def update(self, **kwargs):
        """Update evc attributes.

        This method will raises an error trying to change the following
        attributes: [name, uni_a and uni_z]

        Returns:
            the values for enable and a path attribute, if exists and None
            otherwise
        Raises:
            ValueError: message with error detail.

        """
        enable, path = (None, None)
        for attribute, value in kwargs.items():
            if attribute in self.unique_attributes:
                raise ValueError(f'{attribute} can\'t be be updated.')
            if hasattr(self, attribute):
                setattr(self, attribute, value)
                if 'enable' in attribute:
                    enable = value
                elif 'path' in attribute:
                    path = value
            else:
                raise ValueError(f'The attribute "{attribute}" is invalid.')
        self.sync()
        return enable, path

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

                if not uni.is_valid():
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

        evc_dict["start_date"] = self.start_date
        if isinstance(self.start_date, datetime):
            evc_dict["start_date"] = self.start_date.strftime(time_fmt)

        evc_dict["end_date"] = self.end_date
        if isinstance(self.end_date, datetime):
            evc_dict["end_date"] = self.end_date.strftime(time_fmt)

        evc_dict['bandwidth'] = self.bandwidth
        evc_dict['primary_links'] = self.primary_links.as_dict()
        evc_dict['backup_links'] = self.backup_links.as_dict()
        evc_dict['current_path'] = self.current_path.as_dict()
        evc_dict['primary_path'] = self.primary_path.as_dict()
        evc_dict['backup_path'] = self.backup_path.as_dict()
        evc_dict['dynamic_backup_path'] = self.dynamic_backup_path

        # if self._requested:
        #     request_dict = self._requested.copy()
        #     request_dict['uni_a'] = request_dict['uni_a'].as_dict()
        #     request_dict['uni_z'] = request_dict['uni_z'].as_dict()
        #     request_dict['circuit_scheduler'] = self.circuit_scheduler
        #     evc_dict['_requested'] = request_dict

        evc_dict["request_time"] = self.request_time
        if isinstance(self.request_time, datetime):
            evc_dict["request_time"] = self.request_time.strftime(time_fmt)

        time = self.creation_time.strftime(time_fmt)
        evc_dict['creation_time'] = time

        evc_dict['owner'] = self.owner
        evc_dict['circuit_scheduler'] = [sc.as_dict()
                                         for sc in self.circuit_scheduler]

        evc_dict['active'] = self.is_active()
        evc_dict['enabled'] = self.is_enabled()
        evc_dict['archived'] = self.archived
        evc_dict['priority'] = self.priority

        return evc_dict

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return this EVC's ID."""
        return self._id

    def archive(self):
        """Archive this EVC on deletion."""
        self.archived = True


# pylint: disable=fixme, too-many-public-methods
class EVCDeploy(EVCBase):
    """Class to handle the deploy procedures."""

    def create(self):
        """Create a EVC."""

    def discover_new_path(self):
        """Discover a new path to satisfy this circuit and deploy."""
        return DynamicPathManager.get_best_path(self)

    def change_path(self):
        """Change EVC path."""

    def reprovision(self):
        """Force the EVC (re-)provisioning."""

    def is_affected_by_link(self, link):
        """Return True if this EVC has the given link on its current path."""
        return link in self.current_path

    def link_affected_by_interface(self, interface):
        """Return True if this EVC has the given link on its current path."""
        return self.current_path.link_affected_by_interface(interface)

    def is_backup_path_affected_by_link(self, link):
        """Return True if the backup path of this EVC uses the given link."""
        return link in self.backup_path

    # pylint: disable=invalid-name
    def is_primary_path_affected_by_link(self, link):
        """Return True if the primary path of this EVC uses the given link."""
        return link in self.primary_path

    def is_using_primary_path(self):
        """Verify if the current deployed path is self.primary_path."""
        return self.primary_path and (self.current_path == self.primary_path)

    def is_using_backup_path(self):
        """Verify if the current deployed path is self.backup_path."""
        return self.backup_path and (self.current_path == self.backup_path)

    def is_using_dynamic_path(self):
        """Verify if the current deployed path is a dynamic path."""
        if self.current_path and \
           not self.is_using_primary_path() and \
           not self.is_using_backup_path() and \
           self.current_path.status == EntityStatus.UP:
            return True
        return False

    def deploy_to_backup_path(self):
        """Deploy the backup path into the datapaths of this circuit.

        If the backup_path attribute is valid and up, this method will try to
        deploy this backup_path.

        If everything fails and dynamic_backup_path is True, then tries to
        deploy a dynamic path.
        """
        # TODO: Remove flows from current (cookies)
        if self.is_using_backup_path():
            # TODO: Log to say that cannot move backup to backup
            return True

        success = False
        if self.backup_path.status is EntityStatus.UP:
            success = self.deploy_to_path(self.backup_path)

        if success:
            return True

        if self.dynamic_backup_path:
            return self.deploy_to_path()

        return False

    def deploy_to_primary_path(self):
        """Deploy the primary path into the datapaths of this circuit.

        If the primary_path attribute is valid and up, this method will try to
        deploy this primary_path.
        """
        # TODO: Remove flows from current (cookies)
        if self.is_using_primary_path():
            # TODO: Log to say that cannot move primary to primary
            return True

        if self.primary_path.status is EntityStatus.UP:
            return self.deploy_to_path(self.primary_path)
        return False

    def deploy(self):
        """Deploy EVC to best path.

        Best path can be the primary path, if available. If not, the backup
        path, and, if it is also not available, a dynamic path.
        """
        if self.archived:
            return False
        self.enable()
        success = self.deploy_to_primary_path()
        if not success:
            success = self.deploy_to_backup_path()

        return success

    @staticmethod
    def get_path_status(path):
        """Check for the current status of a path.

        If any link in this path is down, the path is considered down.
        """
        if not path:
            return EntityStatus.DISABLED

        for link in path:
            if link.status is not EntityStatus.UP:
                return link.status
        return EntityStatus.UP

#    def discover_new_path(self):
#        # TODO: discover a new path to satisfy this circuit and deploy

    def remove(self):
        """Remove EVC path and disable it."""
        self.remove_current_flows()
        self.disable()
        self.sync()

    def remove_current_flows(self):
        """Remove all flows from current path."""
        switches = set()

        switches.add(self.uni_a.interface.switch)
        switches.add(self.uni_z.interface.switch)
        for link in self.current_path:
            switches.add(link.endpoint_a.switch)
            switches.add(link.endpoint_b.switch)

        match = {'cookie': self.get_cookie(),
                 'cookie_mask': 18446744073709551615}

        for switch in switches:
            self._send_flow_mods(switch, [match], 'delete')

        self.current_path.make_vlans_available()
        self.current_path = Path([])
        self.deactivate()
        self.sync()

    @staticmethod
    def links_zipped(path=None):
        """Return an iterator which yields pairs of links in order."""
        if not path:
            return []
        return zip(path[:-1], path[1:])

    def should_deploy(self, path=None):
        """Verify if the circuit should be deployed."""
        if not path:
            log.debug("Path is empty.")
            return False

        if not self.is_enabled():
            log.debug(f'{self} is disabled.')
            return False

        if not self.is_active():
            log.debug(f'{self} will be deployed.')
            return True

        return False

    def deploy_to_path(self, path=None):
        """Install the flows for this circuit.

        Procedures to deploy:

        0. Remove current flows installed
        1. Decide if will deploy "path" or discover a new path
        2. Choose vlan
        3. Install NNI flows
        4. Install UNI flows
        5. Activate
        6. Update current_path
        7. Update links caches(primary, current, backup)

        """
        self.remove_current_flows()
        if not self.should_deploy(path):
            path = self.discover_new_path()
            if path is None:
                return False

        if not path:
            # This means that the discovered path does not leave the
            # switch, so there is no NNI, and the flows must "link" the
            # UNIs directly.
            self._install_direct_uni_flows()
        else:
            path.choose_vlans()
            self._install_nni_flows(path)
            self._install_uni_flows(path)
        self.activate()
        self.current_path = path
        self.sync()
        log.info(f"{self} was deployed.")
        return True

    def _install_direct_uni_flows(self):
        """Install flows connecting two UNIs.

        This case happens when the circuit is between UNIs in the
        same switch.
        """
        vlan_a = self.uni_a.user_tag.value if self.uni_a.user_tag else None
        vlan_z = self.uni_z.user_tag.value if self.uni_z.user_tag else None

        flow_mod_az = self._prepare_flow_mod(self.uni_a.interface,
                                             self.uni_z.interface)
        flow_mod_za = self._prepare_flow_mod(self.uni_z.interface,
                                             self.uni_a.interface)

        if vlan_a and vlan_z:
            flow_mod_az['match']['dl_vlan'] = vlan_a
            flow_mod_za['match']['dl_vlan'] = vlan_z
            flow_mod_az['actions'].insert(0, {'action_type': 'set_vlan',
                                              'vlan_id': vlan_z})
            flow_mod_za['actions'].insert(0, {'action_type': 'set_vlan',
                                              'vlan_id': vlan_a})
        elif vlan_a:
            flow_mod_az['match']['dl_vlan'] = vlan_a
            flow_mod_az['actions'].insert(0, {'action_type': 'pop_vlan'})
            flow_mod_za['actions'].insert(0, {'action_type': 'set_vlan',
                                              'vlan_id': vlan_a})
        elif vlan_z:
            flow_mod_za['match']['dl_vlan'] = vlan_z
            flow_mod_za['actions'].insert(0, {'action_type': 'pop_vlan'})
            flow_mod_az['actions'].insert(0, {'action_type': 'set_vlan',
                                              'vlan_id': vlan_z})
        self._send_flow_mods(self.uni_a.interface.switch,
                             [flow_mod_az, flow_mod_za])

    def _install_nni_flows(self, path=None):
        """Install NNI flows."""
        for incoming, outcoming in self.links_zipped(path):
            in_vlan = incoming.get_metadata('s_vlan').value
            out_vlan = outcoming.get_metadata('s_vlan').value

            flows = []
            # Flow for one direction
            flows.append(self._prepare_nni_flow(incoming.endpoint_b,
                                                outcoming.endpoint_a,
                                                in_vlan, out_vlan))

            # Flow for the other direction
            flows.append(self._prepare_nni_flow(outcoming.endpoint_a,
                                                incoming.endpoint_b,
                                                out_vlan, in_vlan))
            self._send_flow_mods(incoming.endpoint_b.switch, flows)

    def _install_uni_flows(self, path=None):
        """Install UNI flows."""
        if not path:
            log.info('install uni flows without path.')
            return

        # Determine VLANs
        in_vlan_a = self.uni_a.user_tag.value if self.uni_a.user_tag else None
        out_vlan_a = path[0].get_metadata('s_vlan').value

        in_vlan_z = self.uni_z.user_tag.value if self.uni_z.user_tag else None
        out_vlan_z = path[-1].get_metadata('s_vlan').value

        # Flows for the first UNI
        flows_a = []

        # Flow for one direction, pushing the service tag
        push_flow = self._prepare_push_flow(self.uni_a.interface,
                                            path[0].endpoint_a,
                                            in_vlan_a, out_vlan_a, in_vlan_z)
        flows_a.append(push_flow)

        # Flow for the other direction, popping the service tag
        pop_flow = self._prepare_pop_flow(path[0].endpoint_a,
                                          self.uni_a.interface, out_vlan_a)
        flows_a.append(pop_flow)

        self._send_flow_mods(self.uni_a.interface.switch, flows_a)

        # Flows for the second UNI
        flows_z = []

        # Flow for one direction, pushing the service tag
        push_flow = self._prepare_push_flow(self.uni_z.interface,
                                            path[-1].endpoint_b,
                                            in_vlan_z, out_vlan_z, in_vlan_a)
        flows_z.append(push_flow)

        # Flow for the other direction, popping the service tag
        pop_flow = self._prepare_pop_flow(path[-1].endpoint_b,
                                          self.uni_z.interface, out_vlan_z)
        flows_z.append(pop_flow)

        self._send_flow_mods(self.uni_z.interface.switch, flows_z)

    @staticmethod
    def _send_flow_mods(switch, flow_mods, command='flows'):
        """Send a flow_mod list to a specific switch.

        Args:
            switch(Switch): The target of flows.
            flow_mods(dict): Python dictionary with flow_mods.
            command(str): By default is 'flows'. To remove a flow is 'remove'.

        """
        endpoint = f'{settings.MANAGER_URL}/{command}/{switch.id}'

        data = {"flows": flow_mods}
        requests.post(endpoint, json=data)

    def get_cookie(self):
        """Return the cookie integer from evc id."""
        value = self.id[len(self.id)//2:]
        return int(value, 16)

    def _prepare_flow_mod(self, in_interface, out_interface):
        """Prepare a common flow mod."""
        default_action = {"action_type": "output",
                          "port": out_interface.port_number}

        flow_mod = {"match": {"in_port": in_interface.port_number},
                    "cookie": self.get_cookie(),
                    "actions": [default_action]}

        return flow_mod

    def _prepare_nni_flow(self,
                          in_interface, out_interface, in_vlan, out_vlan):
        """Create NNI flows."""
        flow_mod = self._prepare_flow_mod(in_interface, out_interface)
        flow_mod['match']['dl_vlan'] = in_vlan

        new_action = {"action_type": "set_vlan",
                      "vlan_id": out_vlan}
        flow_mod["actions"].insert(0, new_action)

        return flow_mod

    def _prepare_push_flow(self, *args):
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

        flow_mod = self._prepare_flow_mod(in_interface, out_interface)
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

    def _prepare_pop_flow(self, in_interface, out_interface, in_vlan):
        """Prepare pop flow."""
        flow_mod = self._prepare_flow_mod(in_interface, out_interface)
        flow_mod['match']['dl_vlan'] = in_vlan
        new_action = {"action_type": "pop_vlan"}
        flow_mod["actions"].insert(0, new_action)
        return flow_mod


class LinkProtection(EVCDeploy):
    """Class to handle link protection."""

    def is_affected_by_link(self, link=None):
        """Verify if the current path is affected by link down event."""
        return self.current_path.is_affected_by_link(link)

    def is_using_primary_path(self):
        """Verify if the current deployed path is self.primary_path."""
        return self.current_path == self.primary_path

    def is_using_backup_path(self):
        """Verify if the current deployed path is self.backup_path."""
        return self.current_path == self.backup_path

    def is_using_dynamic_path(self):
        """Verify if the current deployed path is dynamic."""
        if self.current_path and \
           not self.is_using_primary_path() and \
           not self.is_using_backup_path() and \
           self.current_path.status is EntityStatus.UP:
            return True
        return False

    def deploy_to(self, path_name=None, path=None):
        """Create a deploy to path."""
        if self.current_path == path:
            log.debug(f'{path_name} is equal to current_path.')
            return True

        if path.status is EntityStatus.UP:
            return self.deploy_to_path(path)

        return False

    def handle_link_up(self, link):
        """Handle circuit when link down.

        Args:
            link(Link): Link affected by link.down event.

        """
        if self.is_using_primary_path():
            return True

        success = False
        if self.primary_path.is_affected_by_link(link):
            success = self.deploy_to_primary_path()

        if success:
            return True

        # We tried to deploy(primary_path) without success.
        # And in this case is up by some how. Nothing to do.
        if self.is_using_backup_path() or self.is_using_dynamic_path():
            return True

        # In this case, probably the circuit is not being used and
        # we can move to backup
        if self.backup_path.is_affected_by_link(link):
            success = self.deploy_to_backup_path()

        if success:
            return True

        # In this case, the circuit is not being used and we should
        # try a dynamic path
        if self.dynamic_backup_path:
            return self.deploy_to_path()

        return True

    def handle_link_down(self):
        """Handle circuit when link down.

        Returns:
            bool: True if the re-deploy was successly otherwise False.

        """
        success = False
        if self.is_using_primary_path():
            success = self.deploy_to_backup_path()
        elif self.is_using_backup_path():
            success = self.deploy_to_primary_path()

        if not success and self.dynamic_backup_path:
            success = self.deploy_to_path()

        if success:
            log.debug(f"{self} deployed after link down.")
        else:
            self.deactivate()
            self.current_path = Path([])
            self.sync()
            log.debug(f'Failed to re-deploy {self} after link down.')

        return success


class EVC(LinkProtection):
    """Class that represents a E-Line Virtual Connection."""
