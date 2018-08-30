"""Module to help to create tests."""
import sys
from unittest import TestCase
from unittest.mock import Mock, patch

from kytos.core.interface import TAG, UNI, Interface
from kytos.core.switch import Switch
from kytos.core.link import Link
from kytos.core.common import EntityStatus


def get_link_mocked(**kwargs):
    """Return a link mocked.

    Args:
        link_dict: Python dict returned after call link.as_dict()
    """
    switch = Mock(spec=Switch)
    endpoint_a = Interface(kwargs.get('endpoint_a_name', 'eth0'),
                           kwargs.get('endpoint_a_port', 1), switch)
    endpoint_b = Interface(kwargs.get('endpoint_b_name', 'eth1'),
                           kwargs.get('endpoint_b_port', 2), switch)
    link = Mock(spec=Link, endpoint_a=endpoint_a, endpoint_b=endpoint_b)
    link.as_dict.return_value = kwargs.get('link_dict', {"id": "link_id"})
    link.status = kwargs.get('status', EntityStatus.DOWN)

    metadata = kwargs.get("metadata", {})

    def side_effect(key):
        return Mock(value=metadata.get(key))

    link.get_metadata = Mock(side_effect=side_effect)

    return link

def get_uni_mocked(**kwargs):
    """Create an uni mocked.

    Args:
        interface_name(str): Interface name. Defaults to "eth1".
        interface_port(int): Interface pror. Defaults to 1.
        tag_type(int): Type of a tag. Defaults to 1.
        tag_value(int): Value of a tag. Defaults to 81
        is_valid(bool): Value returned by is_valid method.
                        Defaults to False.
    """
    interface_name = kwargs.get("interface_name", "eth1")
    interface_port = kwargs.get("interface_port", 1)
    tag_type = kwargs.get("tag_type", 1)
    tag_value = kwargs.get("tag_value", 81)
    is_valid = kwargs.get("is_valid", False)
    switch = Mock(spec=Switch)
    switch.id = kwargs.get("switch_id", "custom_switch_id")
    interface = Interface(interface_name, interface_port, switch)
    tag = TAG(tag_type, tag_value)
    uni = Mock(spec=UNI, interface=interface, user_tag=tag)
    uni.is_valid.return_value = is_valid
    uni.as_dict.return_value = {
        "interface_id": f'switch_mock:{interface_port}',
        "tag": tag.as_dict()
    }
    return uni
