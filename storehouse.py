"""Module to handle the storehouse."""
from kytos.core import log
from kytos.core.events import KytosEvent


class StoreHouse:
    """Class to handle storehouse."""

    def __init__(self, controller):
        """Method to initialize the storehouse."""
        self.controller = controller
        self.namespace = 'kytos.mef_eline.circuits'
        self.box = None
        self.create_box()
        self.list_stored_boxes()

    def get_data(self):
        """Return the box data."""
        if not self.box:
            return {}
        return self.box.data

    def create_box(self):
        """Create a new box."""
        content = {'namespace': self.namespace,
                   'callback': self._create_box_callback,
                   'data': {}}
        event = KytosEvent(name='kytos.storehouse.create', content=content)
        self.controller.buffers.app.put(event)
        log.info('Create box from storehouse.')

    def _create_box_callback(self, _event, data, error):
        """Execute the callback to handle create_box."""
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

    def _get_or_create_a_box_from_list_of_boxes(self, _event, data, _error):
        """Create a new box or retrieve the stored box."""
        if data:
            self.get_stored_box(data[0])
        else:
            self.create_box()

    def get_stored_box(self, box_id):
        """Get box from storehouse."""
        content = {'namespace': self.namespace,
                   'callback': self._get_box_callback,
                   'box_id': box_id,
                   'data': {}}
        name = 'kytos.storehouse.retrieve'
        event = KytosEvent(name=name, content=content)
        self.controller.buffers.app.put(event)
        log.info(f'Retrieve box with {box_id} from {self.namespace}.')

    def _get_box_callback(self, _event, data, error):
        """Handle get_box method saving the box or logging with the error."""
        if error:
            log.error(f'Box {data.box_id} not found in {self.namespace}.')

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

    def _save_evc_callback(self, _event, data, error):
        """Display the save EVC result in the log."""
        if error:
            log.error(f'Can\'t update the {self.box.box_id}')

        log.info(f'Box {data.box_id} was updated.')
