"""Main module of kytos/mef_eline Kytos Network Application.

NApp to provision circuits from user request.
"""
import time

import requests
from flask import jsonify, request

from kytos.core import KytosNApp, log, rest
from kytos.core.events import KytosEvent
from kytos.core.helpers import listen_to
from kytos.core.interface import TAG, UNI
from kytos.core.link import Link
from napps.kytos.mef_eline import settings
from napps.kytos.mef_eline.models import EVC
from napps.kytos.mef_eline.schedule import Schedule


class Main(KytosNApp):
    """Main class of amlight/mef_eline NApp.

    This class is the entry point for this napp.
    """

    def setup(self):
        """Replace the '__init__' method for the KytosNApp subclass.

        The setup method is automatically called by the controller when your
        application is loaded.

        So, if you have any setup routine, insert it here.
        """
        self.execute_as_loop(1)
        self.schedule = Schedule()
        self.namespace = 'kytos.mef_eline.circuits'
        self.box = None
        self.list_stored_boxes()

    def execute(self):
        """This method is executed right after the setup method execution.

        You can also use this method in loop mode if you add to the above setup
        method a line like the following example:

            self.execute_as_loop(30)  # 30-second interval.
        """
        self.schedule.run_pending()

    def shutdown(self):
        """This method is executed when your napp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
        pass

    @staticmethod
    def _clear_path(path):
        """Remove switches from a path, returning only interfaeces."""
        return [endpoint for endpoint in path if len(endpoint) > 23]

    @staticmethod
    def get_paths(circuit):
        """Get a valid path for the circuit from the Pathfinder."""
        endpoint = settings.PATHFINDER_URL
        request_data = {"source": circuit.uni_a.interface.id,
                        "destination": circuit.uni_z.interface.id}
        api_reply = requests.post(endpoint, json=request_data)
        if api_reply.status_code != requests.codes.ok:
            log.error("Failed to get paths at %s. Returned %s",
                      endpoint, api_reply.status_code)
            return None
        reply_data = api_reply.json()
        return reply_data.get('paths')

    def get_best_path(self, circuit):
        """Return the best path available for a circuit, if exists."""
        paths = self.get_paths(circuit)
        if paths:
            return self.create_path(self.get_paths(circuit)[0]['hops'])
        return None

    def create_path(self, path):
        """Return the path containing only the interfaces."""
        new_path = []
        clean_path = self._clear_path(path)

        if len(clean_path) % 2:
            return None

        for link in zip(clean_path[1:-1:2], clean_path[2::2]):
            interface_a = self._find_interface_by_id(link[0])
            interface_b = self._find_interface_by_id(link[1])
            if interface_a is None or interface_b is None:
                return None
            new_path.append(Link(interface_a, interface_b))

        return new_path

    def _find_interface_by_id(self, interface_id):
        """Find a Interface on controller with interface_id."""
        if interface_id is None:
            return None

        switch_id = ":".join(interface_id.split(":")[:-1])
        interface_number = int(interface_id.split(":")[-1])
        try:
            switch = self.controller.switches[switch_id]
        except KeyError:
            return None

        try:
            interface = switch.interfaces[interface_number]
        except KeyError:
            return None

        return interface

    @rest('/v2/evc/', methods=['GET'])
    def list_circuits(self):
        """Endpoint to return all circuits stored."""
        return jsonify(self.box.data), 200

    @rest('/v2/evc/<circuit_id>', methods=['GET'])
    def get_circuit(self, circuit_id):
        """Endpoint to return a circuit based on id."""
        circuits = self.box.data
        if circuit_id in circuits:
            result = circuits[circuit_id]
            status = 200
        else:
            result = {'response': f'circuit_id {circuit_id} not found'}
            status = 400

        return jsonify(result), status

    @rest('/v2/evc/', methods=['POST'])
    def create_circuit(self):
        """Try to create a new circuit.

        Firstly, for EVPL: E-Line NApp verifies if UNI_A's requested C-VID and
        UNI_Z's requested C-VID are available from the interfaces' pools. This
        is checked when creating the UNI object.

        Then, E-Line NApp requests a primary and a backup path to the
        Pathfinder NApp using the attributes primary_links and backup_links
        submitted via REST

        # For each link composing paths in #3:
        #  - E-Line NApp requests a S-VID available from the link VLAN pool.
        #  - Using the S-VID obtained, generate abstract flow entries to be
        #    sent to FlowManager

        Push abstract flow entries to FlowManager and FlowManager pushes
        OpenFlow entries to datapaths

        E-Line NApp generates an event to notify all Kytos NApps of a new EVC
        creation

        Finnaly, notify user of the status of its request.
        """
        # Try to create the circuit object
        data = request.get_json()

        try:
            evc = self.evc_from_dict(data)
        except ValueError as exception:
            return jsonify("Bad request: {}".format(exception)), 400

        # save circuit
        self.save_evc(evc)

        # Request paths to Pathfinder
        evc.primary_links = self.get_best_path(evc)

        # Schedule the circuit deploy
        self.schedule.circuit_deploy(evc)

        # Notify users

        return jsonify({"circuit_id": evc.id}), 201


    # METHODS TO HANDLE STOREHOUSE
    def create_box(self):
        """Create a new box."""
        content = {'namespace': self.namespace,
                   'callback': self._create_box_callback,
                   'data': {}}
        event = KytosEvent(name='kytos.storehouse.create', content=content)
        self.controller.buffers.app.put(event)
        log.info('Create box from storehouse.')

    def _create_box_callback(self, event, data, error):
        """Callback to handle create_box."""
        if error:
            log.error(f'Can\'t create box with namespace {self.namespace}')

        self.box = data
        log.info(f'Box {self.box.box_id} was created in {self.namespace}.')

    def list_stored_boxes(self):
        """List all boxes using the current namespace."""
        name = 'kytos.storehouse.list'
        content = {'namespace': self.namespace,
                   'callback': self._get_or_create_a_box_from_list_of_boxes}

        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.info(f'Bootstraping storehouse box for {self.namespace}.')

    def _get_or_create_a_box_from_list_of_boxes(self, event, data, error):
        """Create a new box or retrieve the stored box."""
        if len(data) == 0:
            self.create_box()
        else:
            self.get_stored_box(data[0])

    def get_stored_box(self, box_id):
        """Get box from storehouse"""
        content = {'namespace': self.namespace,
                   'callback': self._get_box_callback,
                   'box_id': box_id,
                   'data': {}}
        name = 'kytos.storehouse.retrieve'
        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.info(f'Retrieve box with {box_id} from {self.namespace}.')

    def _get_box_callback(self, event, data, error):
        """Handle get_box method saving the box or logging with the error."""
        if error:
            log.error(f'Box {data.box_id} not found in {data.namespace}.')

        self.box = data
        log.info(f'Box {self.box.box_id} was load from storehouse.')

    def save_evc(self, evc):
        """Save a EVC using the storehouse."""
        self.box.data[evc.id] = evc.as_dict()

        content = {'namespace': self.namespace,
                   'box_id': self.box.box_id,
                   'data': self.box.data,
                   'callback': self._save_evc_callback}

        event = KytosEvent(name='kytos.storehouse.update', content=content)
        self.controller.buffers.app.put(event)

    def _save_evc_callback(self, event, data, error):
        """Callback to handle save EVC."""
        if error:
            log.error(f'Can\'t update the {self.box.box_id}')

        log.info(f'Box {data.box_id} was updated.')

    @listen_to('kytos/topology.updated')
    def trigger_evc_reprovisioning(self, event):
        """Listen to topology update to trigger EVCs (re)provisioning.

        Schedule all Circuits with valid UNIs.
        """
        for data in self.box.data.values():
            try:
                evc = self.evc_from_dict(data)
                self.schedule.circuit_deploy(evc)
            except ValueError as exception:
                log.debug(f'{data.get("id")} can not be provisioning yet.')

    def evc_from_dict(self, evc_dict):
        """Convert some dict values to instance of EVC classes.

        This method will convert: [UNI, Link]
        """
        data = evc_dict.copy()  # Do not modify the original dict

        for attribute, value in data.items():

            if 'uni' in attribute:
                data[attribute] = self.uni_from_dict(value)

            if ('path' in attribute or 'link' in attribute) and \
               ('dynamic_backup_path' != attribute):
                if len(value) != 0:
                    link = Link(value.get('endpoint_a'),
                                value.get('endpoint_b'))
                    link.extend_metadata(value.get('metadata'))
                    data[attribute] = link

        return EVC(**data)

    def uni_from_dict(self, uni_dict):
        if uni_dict is None:
            return False

        interface_id = uni_dict.get("interface_id")

        interface = self._find_interface_by_id(interface_id)
        if interface is None:
            return False

        tag = TAG.from_dict(uni_dict.get("tag"))

        if tag is False:
            return False

        try:
            uni = UNI(interface, tag)
        except TypeError:
            return False

        return uni
