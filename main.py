"""Main module of kytos/mef_eline Kytos Network Application.

NApp to provision circuits from user request.
"""
from datetime import datetime
from datetime import timezone
import json

import requests
from flask import jsonify, request

from kytos.core.events import KytosEvent
from kytos.core import KytosNApp, log, rest
from kytos.core.interface import TAG, UNI
from kytos.core.link import Link
from napps.kytos.mef_eline import settings
from napps.kytos.mef_eline.schedule import Schedule

from napps.kytos.mef_eline.models import EVC

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
        self.store_items = {}
        self.verify_storehouse('circuits')

        self.execute_as_loop(1)
        self.schedule = Schedule()

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

    @staticmethod
    def _get_tag_from_request(requested_tag):
        """Return a tag object from a json request.

        If there is no tag inside the request, return None
        """
        if requested_tag is None:
            return None
        try:
            return TAG(requested_tag.get("tag_type"),
                       requested_tag.get("value"))
        except AttributeError:
            return False

    def _get_uni_from_request(self, requested_uni):
        if requested_uni is None:
            return False

        interface_id = requested_uni.get("interface_id")
        interface = self._find_interface_by_id(interface_id)
        if interface is None:
            return False

        tag = self._get_tag_from_request(requested_uni.get("tag"))

        if tag is False:
            return False

        try:
            uni = UNI(interface, tag)
        except TypeError:
            return False

        return uni

    @rest('/v2/evc/', methods=['GET'])
    def list_circuits(self):
        """Rest endpoint to display all circuit informations."""
        circuits = self.store_items.get('circuits').data
        return jsonify(circuits), 200

    @rest('/v2/evc/<circuit_id>', methods=['GET'])
    def get_circuit(self, circuit_id):
        """Rest endpoint to display a specific circuit informations."""
        circuits = self.store_items.get('circuits').data
        return jsonify(circuits.get(circuit_id,{})), 200

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

        name = data.get('name', None)
        uni_a = self._get_uni_from_request(data.get('uni_a'))
        uni_z = self._get_uni_from_request(data.get('uni_z'))
        start_date = data.get('start_date', None)
        end_date = data.get('end_date', None)
        creation_time = data.get('creation_time', None)

        try:
            circuit = EVC(name, uni_a, uni_z, start_date=start_date,
                          end_date=end_date, creation_time=creation_time)
        except ValueError as exception:
            return jsonify("Bad request: {}".format(exception)), 400

        # Request paths to Pathfinder
        circuit.primary_links = self.get_best_path(circuit)

        # Schedule the circuit deploy
        self.schedule.circuit_deploy(circuit)

        # Save evc
        self.save_evc(circuit)

        # Notify users
        return jsonify({"circuit_id": circuit.id}), 201

    def verify_storehouse(self, entities):
        """Request a list of box saved by specific entity."""
        name = 'kytos.storehouse.list'
        content = {'namespace': f'kytos.mef_eline.{entities}',
                   'callback': self.request_retrieve_entities}
        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.info(f'verify data in storehouse for {entities}.')

    def request_retrieve_entities(self, event, data, error):
        """Retrieve the stored box or create a new box."""
        msg = ''
        content = {'namespace': event.content.get('namespace'),
                   'callback': self.load_from_store,
                   'data': {}}

        if len(data) == 0:
            name = 'kytos.storehouse.create'
            msg = 'Create new box in storehouse'
        else:
            name = 'kytos.storehouse.retrieve'
            content['box_id'] = data[0]
            msg = 'Retrieve data from storeohouse.'

        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.debug(msg)

    def load_from_store(self, event, box, error):
        """Save the data retrived from storehouse."""
        entities = event.content.get('namespace', '').split('.')[-1]
        if error:
            log.error('Error while get a box from storehouse.')
        else:
            self.store_items[entities] = box
            log.info('Data updated')

    def schedule_all_stored_circuits(self):
        """Schedule all stored circuits"""
        store = self.store_items.get('circuits')

        for data in store.data.values():
            # get the evc attributes
            name = data.get('name', None)
            uni_a = self._get_uni_from_request(data.get('uni_a'))
            uni_z = self._get_uni_from_request(data.get('uni_z'))
            start_date = data.get('start_date', None)
            end_date = data.get('end_date', None)
            creation_time = data.get('creation_time', None)

            # we no need try catch , because the data is already validated
            circuit = EVC(name, uni_a, uni_z, start_date=start_date,
                          end_date=end_date, creation_time=creation_time)

            # schedule a circuit deploy event if the event is not deployed yet
            self.schedule.circuit_deploy(circuit, execute_elapsed_time=False)
            log.info(f'{circuit.id} loadded.')

    def save_evc(self, circuit):
        """Save the circuit."""
        store = self.store_items.get('circuits')
        store.data[circuit.id] = circuit.as_dict()

        name = 'kytos.storehouse.update'
        content = {'namespace': 'kytos.mef_eline.circuits',
                   'box_id': store.box_id,
                   'data': store.data,
                   'callback': self.update_instance}

        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)

    def update_instance(self, event, data, error):
        """Display in Kytos console if the data was updated."""
        entities = event.content.get('namespace', '').split('.')[-1]
        if error:
            log.error(f'Error trying to update storehouse {entities}.')
        else:
            log.debug(f'Storehouse update to entities: {entities}.')
