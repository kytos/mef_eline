"""Module to test the schedule.py file."""
from unittest import TestCase
from unittest.mock import Mock, patch

from kytos.core.interface import TAG, UNI, Interface
from kytos.core.switch import Switch
from kytos.core.link import Link

from napps.kytos.mef_eline.models import EVC
from napps.kytos.mef_eline.settings import MANAGER_URL


class TestEVC(TestCase):  # pylint: disable=too-many-public-methods
    """Tests to verify EVC class."""

    def test_attributes_empty(self):
        """Test if the EVC raises an error with name is required."""
        attributes = {}
        error_message = "name is required."
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_without_uni_a(self):
        """Test if the EVC raises and error with UNI A is required."""
        attributes = {"name": "circuit_name"}
        error_message = "uni_a is required."
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_with_invalid_uni_a(self):
        """Test if the EVC raises and error with invalid UNI A."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(tag_value=82)
        }
        error_message = "VLAN tag 82 is not available in uni_a"
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_without_uni_z(self):
        """Test if the EVC raises and error with UNI Z is required."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True)
        }
        error_message = "uni_z is required."
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_with_invalid_uni_z(self):
        """Test if the EVC raises and error with UNI Z is required."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(tag_value=83)
        }
        error_message = "VLAN tag 83 is not available in uni_z"
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    @staticmethod
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

    @staticmethod
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

        metadata = kwargs.get("metadata", {})

        def side_effect(key):
            return Mock(value=metadata.get(key))

        link.get_metadata = Mock(side_effect=side_effect)

        return link

    def test_update_name(self):
        """Test if raises and error when trying to update the name."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        update_dict = {
            "name": "circuit_name_2"
        }
        error_message = "name can't be be updated."
        with self.assertRaises(ValueError) as handle_error:
            evc = EVC(**attributes)
            evc.update(**update_dict)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_update_uni_a(self):
        """Test if raises and error when trying to update the uni_a."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        update_dict = {
            "uni_a": self.get_uni_mocked(is_valid=True)
        }
        error_message = "uni_a can't be be updated."
        with self.assertRaises(ValueError) as handle_error:
            evc = EVC(**attributes)
            evc.update(**update_dict)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_update_uni_z(self):
        """Test if raises and error when trying to update the uni_z."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        update_dict = {
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        error_message = "uni_z can't be be updated."
        with self.assertRaises(ValueError) as handle_error:
            evc = EVC(**attributes)
            evc.update(**update_dict)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_circuit_representation(self):
        """Test the method __repr__."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        evc = EVC(**attributes)
        expected_value = f'EVC({evc.id}, {evc.name})'
        self.assertEqual(str(evc), expected_value)

    def test_comparison_method(self):
        """Test the method __eq__."""
        attributes = {
            "name": "circuit_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        evc1 = EVC(**attributes)
        evc2 = EVC(**attributes)

        attributes = {
            "name": "circuit_name_2",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }
        evc3 = EVC(**attributes)
        evc4 = EVC(**attributes)

        self.assertEqual(evc1 == evc2, True)
        self.assertEqual(evc1 == evc3, False)
        self.assertEqual(evc2 == evc3, False)
        self.assertEqual(evc3 == evc4, True)

    def test_as_dict_method(self):
        """Test the method as_dict."""
        attributes = {
            "id": "custom_id",
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True),
            "start_date": '2018-08-21T18:44:54',
            "end_date": '2018-08-21T18:44:55',
            'primary_links': [],
            'request_time': '2018-08-21T19:10:41',
            'creation_time': '2018-08-21T18:44:54',
            'owner': "my_name",
            'circuit_scheduler': [],
            'enabled': True,
            'priority': 2
        }
        evc = EVC(**attributes)

        expected_dict = {
            'id': 'custom_id',
            'name': 'custom_name',
            'uni_a': attributes['uni_a'].as_dict(),
            'uni_z': attributes['uni_z'].as_dict(),
            'start_date': '2018-08-21T18:44:54',
            'end_date': '2018-08-21T18:44:55',
            'bandwidth': 0,
            'primary_links': [],
            'backup_links': [],
            'current_path': [],
            'primary_path': [],
            'backup_path': [],
            'dynamic_backup_path': False,
            '_requested': {
                           "id": "custom_id",
                           "name": "custom_name",
                           "uni_a": attributes['uni_a'].as_dict(),
                           "uni_z": attributes['uni_z'].as_dict(),
                           "start_date": '2018-08-21T18:44:54',
                           "end_date": '2018-08-21T18:44:55',
                           'primary_links': [],
                           'request_time': '2018-08-21T19:10:41',
                           'creation_time': '2018-08-21T18:44:54',
                           'owner': "my_name",
                           'circuit_scheduler': [],
                           'enabled': True,
                           'priority': 2
            },
            'request_time': '2018-08-21T19:10:41',
            'creation_time': '2018-08-21T18:44:54',
            'owner': 'my_name',
            'circuit_scheduler': [],
            'active': False,
            'enabled': True,
            'priority': 2
        }
        actual_dict = evc.as_dict()
        for name, value in expected_dict.items():
            actual = actual_dict.get(name)
            if name == '_requested':
                for requested_name, requested_value in value.items():
                    if isinstance(requested_value, UNI):
                        value[requested_name] = requested_value.as_dict()
            self.assertEqual(value, actual)

    def test_primary_links_zipped(self):
        """Test primary links zipped method."""
        pass

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case1(self, log_mock):
        """Test should deploy method without primary links."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True)
        }

        evc = EVC(**attributes)
        evc.should_deploy()
        log_mock.debug.assert_called_with('Primary links are empty.')

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case2(self, log_mock):
        """Test should deploy method with disable circuit."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True),
            "primary_links": [self.get_link_mocked(), self.get_link_mocked()]
        }
        evc = EVC(**attributes)

        self.assertFalse(evc.should_deploy())
        log_mock.debug.assert_called_with(f'{evc} is disabled.')

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case3(self, log_mock):
        """Test should deploy method with enabled and not active circuit."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True),
            "primary_links": [self.get_link_mocked(), self.get_link_mocked()],
            "enabled": True
        }
        evc = EVC(**attributes)
        self.assertTrue(evc.should_deploy())
        log_mock.debug.assert_called_with(f'{evc} will be deployed.')

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case4(self, log_mock):
        """Test should deploy method with enabled and active circuit."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(is_valid=True),
            "uni_z": self.get_uni_mocked(is_valid=True),
            "primary_links": [self.get_link_mocked(), self.get_link_mocked()],
            "enabled": True,
            "active": True
        }
        evc = EVC(**attributes)
        self.assertFalse(evc.should_deploy())

    @patch('napps.kytos.mef_eline.models.requests')
    def test_send_flow_mods(self, requests_mock):
        """Test if you are sending flow_mods."""
        flow_mods = {"id": 20}
        switch = Mock(spec=Switch, id=1)
        EVC.send_flow_mods(switch, flow_mods)
        expected_endpoint = f"{MANAGER_URL}/flows/{switch.id}"
        expected_data = {"flows": flow_mods}
        self.assertEqual(requests_mock.post.call_count, 1)
        requests_mock.post.assert_called_once_with(expected_endpoint,
                                                   json=expected_data)

    def test_prepare_flow_mod(self):
        """Test prepare flow_mod method."""
        interface_a = Interface('eth0', 1, Mock(spec=Switch))
        interface_z = Interface('eth1', 3, Mock(spec=Switch))
        flow_mod = EVC.prepare_flow_mod(interface_a, interface_z)
        expected_flow_mod = {
                           'match': {'in_port': interface_a.port_number},
                           'actions': [
                                       {'action_type': 'output',
                                        'port': interface_z.port_number}
                           ]
        }
        self.assertEqual(expected_flow_mod, flow_mod)

    def test_prepare_pop_flow(self):
        """Test prepare pop flow  method."""
        attributes = {
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(interface_port=1, is_valid=True),
            "uni_z": self.get_uni_mocked(interface_port=2, is_valid=True),
        }
        evc = EVC(**attributes)
        interface_a = evc.uni_a.interface
        interface_z = evc.uni_z.interface
        in_vlan = 10
        flow_mod = evc.prepare_pop_flow(interface_a, interface_z, in_vlan)
        expected_flow_mod = {
            'match': {'in_port': interface_a.port_number, 'dl_vlan': in_vlan},
            'actions': [
                        {'action_type': 'pop_vlan'},
                        {'action_type': 'output',
                         'port': interface_z.port_number
                         }
            ]
        }
        self.assertEqual(expected_flow_mod, flow_mod)

    def test_prepare_push_flow(self):
        """Test prepare push flow method."""
        attributes = {
            "name": "custom_name",
            "uni_a": self.get_uni_mocked(interface_port=1, is_valid=True),
            "uni_z": self.get_uni_mocked(interface_port=2, is_valid=True),
        }
        evc = EVC(**attributes)
        interface_a = evc.uni_a.interface
        interface_z = evc.uni_z.interface
        in_vlan_a = 10
        out_vlan_a = 20
        in_vlan_z = 3
        flow_mod = evc.prepare_push_flow(interface_a, interface_z,
                                         in_vlan_a, out_vlan_a, in_vlan_z)
        expected_flow_mod = {
            'match': {'in_port': interface_a.port_number,
                      'dl_vlan': in_vlan_a
                      },
            'actions': [
                        {'action_type': 'set_vlan', 'vlan_id': in_vlan_z},
                        {'action_type': 'push_vlan', 'tag_type': 's'},
                        {'action_type': 'set_vlan', 'vlan_id': out_vlan_a},
                        {'action_type': 'output',
                         'port': interface_z.port_number
                         }
            ]
        }
        self.assertEqual(expected_flow_mod, flow_mod)

    @patch('napps.kytos.mef_eline.models.EVC.send_flow_mods')
    def test_install_uni_flows(self, send_flow_mods_mock):
        """Test install uni flows method.

        This test will verify the flows send to the send_flows_mods method.
        """
        uni_a = self.get_uni_mocked(interface_port=2, tag_value=82,
                                    switch_id="switch_uni_a", is_valid=True)
        uni_z = self.get_uni_mocked(interface_port=3, tag_value=83,
                                    switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                self.get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                     metadata={"s_vlan": 5}),
                self.get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                     metadata={"s_vlan": 6})
            ]
        }
        evc = EVC(**attributes)
        evc.install_uni_flows()

        expected_flow_mod_a = [
            {'match': {'in_port': uni_a.interface.port_number,
                       'dl_vlan': uni_a.user_tag.value},
             'actions': [
                {'action_type': 'set_vlan', 'vlan_id': uni_z.user_tag.value},
                {'action_type': 'push_vlan', 'tag_type': 's'},
                {'action_type': 'set_vlan',
                 'vlan_id': evc.primary_links[0].get_metadata('s_vlan').value},
                {'action_type': 'output',
                 'port': evc.primary_links[0].endpoint_a.port_number}
             ]},
            {'match': {
                'in_port': evc.primary_links[0].endpoint_a.port_number,
                'dl_vlan': evc.primary_links[0].get_metadata('s_vlan').value
             },
             'actions': [
                {'action_type': 'pop_vlan'},
                {'action_type': 'output', 'port': uni_a.interface.port_number}
             ]
             }
        ]
        send_flow_mods_mock.assert_any_call(uni_a.interface.switch,
                                            expected_flow_mod_a)

        expected_flow_mod_z = [
            {'match': {'in_port': uni_z.interface.port_number,
                       'dl_vlan': uni_z.user_tag.value},
             'actions': [
                {'action_type': 'set_vlan', 'vlan_id': uni_a.user_tag.value},
                {'action_type': 'push_vlan', 'tag_type': 's'},
                {'action_type': 'set_vlan',
                 'vlan_id': evc.primary_links[-1].get_metadata('s_vlan').value
                 },
                {'action_type': 'output',
                 'port': evc.primary_links[-1].endpoint_b.port_number}
              ]
             },
            {'match': {
                 'in_port': evc.primary_links[-1].endpoint_b.port_number,
                 'dl_vlan': evc.primary_links[-1].get_metadata('s_vlan').value
             },
             'actions': [
                {'action_type': 'pop_vlan'},
                {'action_type': 'output', 'port': uni_z.interface.port_number}
              ]
             }
        ]

        send_flow_mods_mock.assert_any_call(uni_z.interface.switch,
                                            expected_flow_mod_z)

    @patch('napps.kytos.mef_eline.models.EVC.send_flow_mods')
    def test_install_nni_flows(self, send_flow_mods_mock):
        """Test install nni flows method.

        This test will verify the flows send to the send_flows_mods method.
        """
        uni_a = self.get_uni_mocked(interface_port=2, tag_value=82,
                                    switch_id="switch_uni_a", is_valid=True)
        uni_z = self.get_uni_mocked(interface_port=3, tag_value=83,
                                    switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                self.get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                     metadata={"s_vlan": 5}),
                self.get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                     metadata={"s_vlan": 6})
            ]
        }
        evc = EVC(**attributes)
        evc.install_nni_flows()

        in_vlan = evc.primary_links[0].get_metadata('s_vlan').value
        out_vlan = evc.primary_links[-1].get_metadata('s_vlan').value

        in_port = evc.primary_links[0].endpoint_b.port_number
        out_port = evc.primary_links[-1].endpoint_a.port_number

        expected_flow_mods = [
            {'match': {
                'in_port': in_port,
                'dl_vlan': in_vlan},
                'actions': [
                    {'action_type': 'set_vlan', 'vlan_id': out_vlan},
                    {'action_type': 'output', 'port': out_port}
                ]
             },
            {'match': {'in_port': out_port, 'dl_vlan': out_vlan},
             'actions': [
                {'action_type': 'set_vlan', 'vlan_id': in_vlan},
                {'action_type': 'output', 'port': in_port}
              ]
             }
        ]

        switch = evc.primary_links[0].endpoint_b.switch
        send_flow_mods_mock.assert_called_once_with(switch, expected_flow_mods)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVC._chose_vlans')
    @patch('napps.kytos.mef_eline.models.EVC.install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.install_uni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.activate')
    @patch('napps.kytos.mef_eline.models.EVC.should_deploy')
    def test_deploy_successfully(self, *args):
        """Test if all methods to deploy are called."""
        (should_deploy_mock, activate_mock, install_uni_flows_mock,
         install_nni_flows, chose_vlans_mock, log_mock) = args

        should_deploy_mock.return_value = True
        uni_a = self.get_uni_mocked(interface_port=2, tag_value=82,
                                    switch_id="switch_uni_a", is_valid=True)
        uni_z = self.get_uni_mocked(interface_port=3, tag_value=83,
                                    switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                self.get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                     metadata={"s_vlan": 5}),
                self.get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                     metadata={"s_vlan": 6})
            ]
        }

        evc = EVC(**attributes)
        evc.deploy()

        self.assertEqual(should_deploy_mock.call_count, 1)
        self.assertEqual(activate_mock.call_count, 1)
        self.assertEqual(install_uni_flows_mock.call_count, 1)
        self.assertEqual(install_nni_flows.call_count, 1)
        self.assertEqual(chose_vlans_mock.call_count, 1)
        log_mock.info.assert_called_once_with(f"{evc} was deployed.")

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVC._chose_vlans')
    @patch('napps.kytos.mef_eline.models.EVC.install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.install_uni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.activate')
    @patch('napps.kytos.mef_eline.models.EVC.should_deploy')
    def test_deploy_fail(self, *args):
        """Test if all methods is ignored when the should_deploy is false."""
        (should_deploy_mock, activate_mock, install_uni_flows_mock,
         install_nni_flows, chose_vlans_mock, log_mock) = args

        should_deploy_mock.return_value = False
        uni_a = self.get_uni_mocked(interface_port=2, tag_value=82,
                                    switch_id="switch_uni_a", is_valid=True)
        uni_z = self.get_uni_mocked(interface_port=3, tag_value=83,
                                    switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                self.get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                     metadata={"s_vlan": 5}),
                self.get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                     metadata={"s_vlan": 6})
            ]
        }

        evc = EVC(**attributes)
        evc.deploy()

        self.assertEqual(should_deploy_mock.call_count, 1)
        self.assertEqual(activate_mock.call_count, 0)
        self.assertEqual(install_uni_flows_mock.call_count, 0)
        self.assertEqual(install_nni_flows.call_count, 0)
        self.assertEqual(chose_vlans_mock.call_count, 0)
        self.assertEqual(log_mock.info.call_count, 0)
