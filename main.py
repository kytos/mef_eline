"""Main module of kytos/mef_eline Kytos Network Application.

NApp to provision circuits from user request.
"""
import requests
from flask import jsonify, request

from kytos.core import KytosNApp, log, rest
from kytos.core.events import KytosEvent
from kytos.core.helpers import listen_to
from kytos.core.interface import TAG, UNI
from kytos.core.link import Link
from napps.kytos.mef_eline import settings
from napps.kytos.mef_eline.models import EVC
from napps.kytos.mef_eline.scheduler import CircuitSchedule, Scheduler
from napps.kytos.mef_eline.storehouse import StoreHouse


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
        self.sched = Scheduler()
        self.storehouse = StoreHouse(self.controller)

    def execute(self):
        """Execute once when the napp is running."""
        pass

    def shutdown(self):
        """Execute when your napp is unloaded.

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

        if api_reply.status_code != getattr(requests.codes, 'ok'):
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
            interface_a = self.controller.get_interface_by_id(link[0])
            interface_b = self.controller.get_interface_by_id(link[1])
            if interface_a is None or interface_b is None:
                return None
            new_path.append(Link(interface_a, interface_b))

        return new_path

    @rest('/v2/evc/', methods=['GET'])
    def list_circuits(self):
        """Endpoint to return all circuits stored."""
        circuits = self.storehouse.get_data()
        if not circuits:
            return jsonify({"response": "No circuit stored."}), 200

        return jsonify(circuits), 200

    @rest('/v2/evc/<circuit_id>', methods=['GET'])
    def get_circuit(self, circuit_id):
        """Endpoint to return a circuit based on id."""
        circuits = self.storehouse.get_data()

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

        # verify duplicated evc
        if self.is_duplicated_evc(evc):
            return jsonify("Not Acceptable: This evc already exists."), 409

        # save circuit
        self.storehouse.save_evc(evc)

        # Request paths to Pathfinder
        evc.primary_links = self.get_best_path(evc) or []

        # Schedule the circuit deploy
        self.sched.add(evc)

        # Notify users
        event = KytosEvent(name='kytos.mef_eline.created',
                           content=evc.as_dict())
        self.controller.buffers.app.put(event)

        return jsonify({"circuit_id": evc.id}), 201

    @rest('/v2/evc/<circuit_id>', methods=['PATCH'])
    def update(self, circuit_id):
        """Update a circuit based on payload.

        The EVC required attributes can't be updated.
        """
        data = request.get_json()
        circuits = self.storehouse.get_data()

        if circuit_id not in circuits:
            result = {'response': f'circuit_id {circuit_id} not found'}
            return jsonify(result), 404

        try:
            evc = self.evc_from_dict(circuits.get(circuit_id))
            evc.update(**data)
            self.storehouse.save_evc(evc)
            result = {evc.id: evc.as_dict()}
            status = 200
        except ValueError as exception:
            result = "Bad request: {}".format(exception)
            status = 400

        return jsonify(result), status

    def is_duplicated_evc(self, evc):
        """Verify if the circuit given is duplicated with the stored evcs.

        Args:
            evc (EVC): circuit to be analysed.

        Returns:
            boolean: True if the circuit is duplicated, otherwise False.

        """
        for circuit_dict in self.storehouse.get_data().values():
            try:
                circuit = self.evc_from_dict(circuit_dict)
            except ValueError:
                continue

            if circuit == evc:
                return True

        return False

    @listen_to('kytos/topology.updated')
    def trigger_evc_reprovisioning(self, *_):
        """Listen to topology update to trigger EVCs (re)provisioning.

        Schedule all Circuits with valid UNIs.
        """
        stored_data = self.storehouse.get_data().values() or []
        for data in stored_data:
            try:
                evc = self.evc_from_dict(data)
                self.sched.add(evc)
            except ValueError as _exception:
                log.debug(f'{data.get("id")} can not be provisioning yet.')

    def evc_from_dict(self, evc_dict):
        """Convert some dict values to instance of EVC classes.

        This method will convert: [UNI, Link]
        """
        data = evc_dict.copy()  # Do not modify the original dict

        for attribute, value in data.items():

            if 'uni' in attribute:
                data[attribute] = self.uni_from_dict(value)

            if attribute == 'circuit_schedule':
                data[attribute] = []
                for schedule in value:
                    data[attribute].append(CircuitSchedule.from_dict(schedule))

            if ('path' in attribute or 'link' in attribute) and \
               (attribute != 'dynamic_backup_path'):
                if value:
                    data[attribute] = self.link_from_dict(value)

        return EVC(**data)

    def uni_from_dict(self, uni_dict):
        """Return a UNI object from python dict."""
        if uni_dict is None:
            return False

        interface_id = uni_dict.get("interface_id")
        interface = self.controller.get_interface_by_id(interface_id)
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

    def link_from_dict(self, link_dict):
        """Return a Link object from python dict."""
        id_a = link_dict.get('endpoint_a')
        id_b = link_dict.get('endpoint_b')

        endpoint_a = self.controller.get_interface_by_id(id_b)
        endpoint_b = self.controller.get_interface_by_id(id_a)

        link = Link(endpoint_a, endpoint_b)
        link.extend_metadata(link_dict.get('metadata'))

        return link
