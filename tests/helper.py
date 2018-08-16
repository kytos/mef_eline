"""Module to help create tests."""
import sys
from unittest.mock import Mock

# import the controller
from kytos.core import Controller
from kytos.core.config import KytosConfig
# import the napps path
sys.path.insert(0, '/var/lib/kytos/napps/..')


def get_controller_mock():
    """Return a controller mock."""
    options = KytosConfig().options['daemon']
    controller = Controller(options)
    controller.log = Mock()
    return controller

def get_napp_urls(napp):
    """Return the kytos/mef_eline urls.

    The urls will be like:

    urls = [
        (options, methods, url)
    ]

    """
    controller = napp.controller
    controller.api_server.register_napp_endpoints(napp)

    urls = []
    for rule in controller.api_server.app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        if f'{napp.username}/{napp.name}' in str(rule):
            urls.append((options, rule.methods, f'{str(rule)}'))

    return urls


def get_app_test_client(napp):
    """Return a flask api test client."""
    napp.controller.api_server.register_napp_endpoints(napp)
    return napp.controller.api_server.app.test_client()


def get_event_listeners(napp):
    """Return the event listeners name.

    Returns:
        list: list with all events listeners registered.

    """
    return napp.listeners()
