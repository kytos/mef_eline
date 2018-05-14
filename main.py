"""Main module of kytos/mef_eline Kytos Network Application.

NApp to provision circuits from user request.
"""
from datetime import datetime
from datetime import timezone
import json
import requests
import time
from flask import jsonify, request

from kytos.core.events import KytosEvent
from kytos.core import KytosNApp, log, rest
from kytos.core.interface import TAG, UNI
from kytos.core.helpers import listen_to
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
        self.namespace = settings.NAMESPACE
        self.namespace_evcs = self.namespace.split('.')[-1]  # 'circuits' str
        self.box_id = None
        self.pending_evcs = []  # it'll be used for evcs that have failed.
        self.load_callback_executed = True  # to retrieve data synchronously
        self._bootstrap_box()

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
        log.info('Shutting down kytos/mef_eline.')
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
            log.debug('interface is None')
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
        """Rest endpoint to display all circuit information."""
        self._load_box()
        circuits = self.store_items.get(self.namespace_evcs, {})
        if circuits:
            return jsonify(circuits.data), 200
        return jsonify(circuits), 200

    @rest('/v2/evc/<circuit_id>', methods=['GET'])
    def get_circuit(self, circuit_id):
        """Rest endpoint to display a specific circuit information."""
        self._load_box()
        circuits = self.store_items.get(self.namespace_evcs, {})
        if circuits.data:
            if circuits.data.get(circuit_id):
                return jsonify(circuits.data.get(circuit_id)), 200
        return jsonify({'response': f'circuit_id {circuit_id} not found'}), 400

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

        Finally, notify user of the status of its request.
        """
        try:
            # Try to create the circuit object
            data = request.get_json()
            for uni in ['uni_a', 'uni_z']:
                data[uni] = self._get_uni_from_request(data.get(uni))
            circuit = EVC(**data, mef_eline=self)
            if circuit:
                self._save_evc(circuit)
                self._schedule_circuit(circuit)
        except (AttributeError, ValueError) as exception:
            return jsonify("Bad request: {}".format(exception)), 400
        return jsonify({"circuit_id": circuit.id}), 201

    @listen_to('.*kytos/of_core.handshake.completed')
    def handle_handshake(self, event):
        """Listen to switches handshake to trigger EVCs (re)provisioning.

        """
        # In practice, it takes a few seconds before we can send flowmods.
        # Once we have retries on EVC scheduler funcs, get rid of this sleep.
        time.sleep(5)
        self.schedule_all_circuits()

    def _bootstrap_box(self):
        """Bootstrap a box for mef_eline.namespace.

        To bootstrap, a list of boxes of this namespace will be
        requested. Then, if a box exists, it'll be loaded. Otherwise,
        a new box will be created.

        """
        name = 'kytos.storehouse.list'
        content = {'namespace': self.namespace,
                   'callback': self._bootstrap_box_callback}
        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.info(f'Bootstraping storehouse box for {self.namespace}.')

    def _bootstrap_box_callback(self, event, box, error):
        """Callback of _bootstrap_box."""
        if len(box) == 0:
            self._create_box()
        else:
            self.box_id = box[0]
        log.debug(f'box_id {self.box_id}')
        self._load_box()

    def _load_box(self, sync=True):
        """Load the data retrieved from storehouse.

        Args:
            sync (bool): True to retrieve synchronously
        """
        content = {'namespace': self.namespace,
                   'callback': self._load_box_callback,
                   'data': {}}
        name = 'kytos.storehouse.retrieve'
        content['box_id'] = self.box_id
        msg = 'Retrieving data from storehouse.'

        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)

        if sync:
            self.load_callback_executed = False
            while not self.load_callback_executed:
                time.sleep(0.1)

    def _load_box_callback(self, event, box, error):
        """Callback of _load_box."""
        if error:
            log.error(f'Box {box.box_id} not found in {box.namespace}.')
        else:
            self.store_items[self.namespace_evcs] = box
            log.debug(f'Box {box.box_id} loaded from {box.namespace}.')
        self.load_callback_executed = True

    def _create_box(self):
        """Create store box for mef_eline self.namespace."""
        content = {'namespace': self.namespace,
                   'callback': self._create_box_callback,
                   'data': {}}
        name = 'kytos.storehouse.create'
        msg = 'Creating new box in storehouse'
        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)

    def _create_box_callback(self, event, box, error):
        """Callback of _create_box."""
        if error:
            log.error(f'Box {box.box_id} not created in {box.namespace}.')
        else:
            self.box_id = box.box_id
            log.info(f'Box {box.box_id} was created in {box.namespace}.')

    def _schedule_circuit(self, circuit, sched_func='circuit_enable',
                          **kwargs):
        """Schedule a function generically for a specific circuit.

        Args:
            circuit (EVC): mef_eline.models.EVC object.
            sched_func (str): mef_eline.schedule.Schedule's function to be run.
            kwargs (dict): kwargs of sched_func.
        """
        res = getattr(self.schedule, sched_func)(circuit, **kwargs)
        return res

    def schedule_all_circuits(self, sched_func='circuit_enable', **kwargs):
        """Schedule a function generically for all circuits.

        Args:
            sched_func (str): mef_eline.schedule.Schedule's function to be run
            kwargs (dict): kwargs of sched_func.
        """
        store = self.store_items.get(self.namespace_evcs)
        func = getattr(self.schedule, sched_func)

        if store and func:
            for data in store.data.values():
                try:
                    evc_dict = {
                        'name': data['name'],
                        'uni_a': data['uni_a'],
                        'uni_z': data['uni_z'],
                        'start_date': data['start_date'],
                        'end_date': data['end_date'],
                        'bandwidth': data['bandwidth'],
                        'primary_links': data['primary_links'],
                        'backup_links': data['backup_links'],
                        'dynamic_backup_path': data['dynamic_backup_path'],
                        'creation_time': data['creation_time'],
                        '_id': data['id'],
                        'enabled': data['enabled'],
                        'active': data['active'],
                        'owner': data['owner'],
                        'priority': data['priority'],
                        'mef_eline': self
                    }
                    circuit = EVC(**evc_dict)
                    log.debug(circuit.__dict__)
                    if circuit:
                        self._save_evc(circuit)
                        # 'func' should update storehouse with mef_eline obj
                        # in order to update the actual status of the EVC
                        func(circuit=circuit, **kwargs)
                except (ValueError, TypeError):
                    pass  # issu-e #25

    def _save_evc(self, circuit):
        """Save the circuit async."""
        store = self.store_items.get(self.namespace_evcs)
        name = 'kytos.storehouse.update'
        content = {'namespace': self.namespace,
                   'box_id': store.box_id,
                   'data': {circuit.id: circuit.as_dict()},
                   'method': 'PATCH',
                   'callback': self._save_evc_callback,
                   'evc': circuit}

        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.debug(f"{event!r}")

    def _save_evc_callback(self, event, box, error):
        """Callback of _save_evc."""
        evc = event.content['evc']
        evc_id = evc.id
        evc_name = evc.name
        if error:
            log.error(f"Couldn't save {evc!r}.")
        else:
            log.info(f'Saved {evc!r}.')
