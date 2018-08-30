"""Method to thest EVCDeploy class."""
import sys
from unittest import TestCase
from unittest.mock import Mock, patch

from kytos.core.interface import UNI, Interface
from kytos.core.switch import Switch
from kytos.core.common import EntityStatus

# pylint: disable=wrong-import-position
sys.path.insert(0, '/var/lib/kytos/napps/..')
# pylint: enable=wrong-import-position

from napps.kytos.mef_eline.models import EVC, Path  # NOQA
from napps.kytos.mef_eline.settings import MANAGER_URL  # NOQA
from napps.kytos.mef_eline.tests.helpers import get_link_mocked, get_uni_mocked  # NOQA


class TestEVC(TestCase):  # pylint: disable=too-many-public-methods
    """Tests to verify EVC class."""

    def test_primary_links_zipped(self):
        """Test primary links zipped method."""
        pass

    @staticmethod
    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case1(log_mock):
        """Test should deploy method without primary links."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }

        evc = EVC(**attributes)
        evc.should_deploy()
        log_mock.debug.assert_called_with('Path is empty.')

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case2(self, log_mock):
        """Test should deploy method with disable circuit."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_links": [get_link_mocked(), get_link_mocked()]
        }
        evc = EVC(**attributes)

        self.assertFalse(evc.should_deploy(attributes['primary_links']))
        log_mock.debug.assert_called_with(f'{evc} is disabled.')

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case3(self, log_mock):
        """Test should deploy method with enabled and not active circuit."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_links": [get_link_mocked(), get_link_mocked()],
            "enabled": True
        }
        evc = EVC(**attributes)
        self.assertTrue(evc.should_deploy(attributes['primary_links']))
        log_mock.debug.assert_called_with(f'{evc} will be deployed.')

    @patch('napps.kytos.mef_eline.models.log')
    def test_should_deploy_case4(self, log_mock):
        """Test should deploy method with enabled and active circuit."""
        log_mock.debug.return_value = True
        attributes = {
            "name": "custom_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_links": [get_link_mocked(), get_link_mocked()],
            "enabled": True,
            "active": True
        }
        evc = EVC(**attributes)
        self.assertFalse(evc.should_deploy(attributes['primary_links']))

    @patch('napps.kytos.mef_eline.models.requests')
    def test_send_flow_mods_case1(self, requests_mock):
        """Test if you are sending flow_mods."""
        flow_mods = {"id": 20}
        switch = Mock(spec=Switch, id=1)
        EVC.send_flow_mods(switch, flow_mods)
        expected_endpoint = f"{MANAGER_URL}/flows/{switch.id}"
        expected_data = {"flows": flow_mods}
        self.assertEqual(requests_mock.post.call_count, 1)
        requests_mock.post.assert_called_once_with(expected_endpoint,
                                                   json=expected_data)

    @patch('napps.kytos.mef_eline.models.requests')
    def test_send_flow_mods_case2(self, requests_mock):
        """Test if you are sending flow_mods."""
        flow_mods = {"id": 20}
        switch = Mock(spec=Switch, id=1)
        EVC.send_flow_mods(switch, flow_mods, command='delete')
        expected_endpoint = f"{MANAGER_URL}/delete/{switch.id}"
        expected_data = {"flows": flow_mods}
        self.assertEqual(requests_mock.post.call_count, 1)
        requests_mock.post.assert_called_once_with(expected_endpoint,
                                                   json=expected_data)

    def test_prepare_flow_mod(self):
        """Test prepare flow_mod method."""
        interface_a = Interface('eth0', 1, Mock(spec=Switch))
        interface_z = Interface('eth1', 3, Mock(spec=Switch))
        attributes = {
            "name": "custom_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_links": [get_link_mocked(), get_link_mocked()],
            "enabled": True,
            "active": True
        }
        evc = EVC(**attributes)
        flow_mod = evc.prepare_flow_mod(interface_a, interface_z)
        expected_flow_mod = {
                           'match': {'in_port': interface_a.port_number},
                           'cookie': evc.get_cookie(),
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
            "uni_a": get_uni_mocked(interface_port=1, is_valid=True),
            "uni_z": get_uni_mocked(interface_port=2, is_valid=True),
        }
        evc = EVC(**attributes)
        interface_a = evc.uni_a.interface
        interface_z = evc.uni_z.interface
        in_vlan = 10
        flow_mod = evc.prepare_pop_flow(interface_a, interface_z, in_vlan)
        expected_flow_mod = {
            'match': {'in_port': interface_a.port_number, 'dl_vlan': in_vlan},
            'cookie': evc.get_cookie(),
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
            "uni_a": get_uni_mocked(interface_port=1, is_valid=True),
            "uni_z": get_uni_mocked(interface_port=2, is_valid=True),
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
            'cookie': evc.get_cookie(),
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

    @staticmethod
    @patch('napps.kytos.mef_eline.models.EVC.send_flow_mods')
    def test_install_uni_flows(send_flow_mods_mock):
        """Test install uni flows method.

        This test will verify the flows send to the send_flow_mods method.
        """
        uni_a = get_uni_mocked(interface_port=2, tag_value=82,
                               switch_id="switch_uni_a", is_valid=True)
        uni_z = get_uni_mocked(interface_port=3, tag_value=83,
                               switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]
        }
        evc = EVC(**attributes)
        evc.install_uni_flows(attributes['primary_links'])

        expected_flow_mod_a = [
            {'match': {'in_port': uni_a.interface.port_number,
                       'dl_vlan': uni_a.user_tag.value},
             'cookie': evc.get_cookie(),
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
             'cookie': evc.get_cookie(),
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
             'cookie': evc.get_cookie(),
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
             'cookie': evc.get_cookie(),
             'actions': [
                {'action_type': 'pop_vlan'},
                {'action_type': 'output', 'port': uni_z.interface.port_number}
              ]
             }
        ]

        send_flow_mods_mock.assert_any_call(uni_z.interface.switch,
                                            expected_flow_mod_z)

    @staticmethod
    @patch('napps.kytos.mef_eline.models.EVC.send_flow_mods')
    def test_install_nni_flows(send_flow_mods_mock):
        """Test install nni flows method.

        This test will verify the flows send to the send_flow_mods method.
        """
        uni_a = get_uni_mocked(interface_port=2, tag_value=82,
                               switch_id="switch_uni_a", is_valid=True)
        uni_z = get_uni_mocked(interface_port=3, tag_value=83,
                               switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]
        }
        evc = EVC(**attributes)
        evc.install_nni_flows(attributes['primary_links'])

        in_vlan = evc.primary_links[0].get_metadata('s_vlan').value
        out_vlan = evc.primary_links[-1].get_metadata('s_vlan').value

        in_port = evc.primary_links[0].endpoint_b.port_number
        out_port = evc.primary_links[-1].endpoint_a.port_number

        expected_flow_mods = [
            {
             'match': {'in_port': in_port, 'dl_vlan': in_vlan},
             'cookie': evc.get_cookie(),
             'actions': [
                    {'action_type': 'set_vlan', 'vlan_id': out_vlan},
                    {'action_type': 'output', 'port': out_port}
                ]
             },
            {
             'match': {'in_port': out_port, 'dl_vlan': out_vlan},
             'cookie': evc.get_cookie(),
             'actions': [
                {'action_type': 'set_vlan', 'vlan_id': in_vlan},
                {'action_type': 'output', 'port': in_port}
              ]
             }
        ]

        switch = evc.primary_links[0].endpoint_b.switch
        send_flow_mods_mock.assert_called_once_with(switch, expected_flow_mods)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVC.choose_vlans')
    @patch('napps.kytos.mef_eline.models.EVC.install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.install_uni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.activate')
    @patch('napps.kytos.mef_eline.models.EVC.should_deploy')
    def test_deploy_successfully(self, *args):
        """Test if all methods to deploy are called."""
        (should_deploy_mock, activate_mock, install_uni_flows_mock,
         install_nni_flows, chose_vlans_mock, log_mock) = args

        should_deploy_mock.return_value = True
        uni_a = get_uni_mocked(interface_port=2, tag_value=82,
                               switch_id="switch_uni_a", is_valid=True)
        uni_z = get_uni_mocked(interface_port=3, tag_value=83,
                               switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]
        }

        evc = EVC(**attributes)
        deployed = evc.deploy(attributes['primary_links'])

        self.assertEqual(should_deploy_mock.call_count, 1)
        self.assertEqual(activate_mock.call_count, 1)
        self.assertEqual(install_uni_flows_mock.call_count, 1)
        self.assertEqual(install_nni_flows.call_count, 1)
        self.assertEqual(chose_vlans_mock.call_count, 1)
        log_mock.info.assert_called_once_with(f"{evc} was deployed.")
        self.assertTrue(deployed)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVC.choose_vlans')
    @patch('napps.kytos.mef_eline.models.EVC.install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.install_uni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.activate')
    @patch('napps.kytos.mef_eline.models.EVC.should_deploy')
    def test_deploy_fail(self, *args):
        """Test if all methods is ignored when the should_deploy is false."""
        (should_deploy_mock, activate_mock, install_uni_flows_mock,
         install_nni_flows, chose_vlans_mock, log_mock) = args

        should_deploy_mock.return_value = False
        uni_a = get_uni_mocked(interface_port=2, tag_value=82,
                               switch_id="switch_uni_a", is_valid=True)
        uni_z = get_uni_mocked(interface_port=3, tag_value=83,
                               switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "primary_links": [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]
        }

        evc = EVC(**attributes)
        deployed = evc.deploy()

        self.assertEqual(should_deploy_mock.call_count, 1)
        self.assertEqual(activate_mock.call_count, 0)
        self.assertEqual(install_uni_flows_mock.call_count, 0)
        self.assertEqual(install_nni_flows.call_count, 0)
        self.assertEqual(chose_vlans_mock.call_count, 0)
        self.assertEqual(log_mock.info.call_count, 0)
        self.assertFalse(deployed)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVC.choose_vlans')
    @patch('napps.kytos.mef_eline.models.EVC.install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.install_uni_flows')
    @patch('napps.kytos.mef_eline.models.EVC.activate')
    @patch('napps.kytos.mef_eline.models.EVC.should_deploy')
    @patch('napps.kytos.mef_eline.models.EVC.discover_new_path')
    def test_deploy_without_path_case1(self, *args):
        """Test if not path is found a dynamic path is used."""
        (discover_new_path_mocked, should_deploy_mock, activate_mock,
         install_uni_flows_mock, install_nni_flows, chose_vlans_mock,
         log_mock) = args

        should_deploy_mock.return_value = True
        uni_a = get_uni_mocked(interface_port=2, tag_value=82,
                               switch_id="switch_uni_a", is_valid=True)
        uni_z = get_uni_mocked(interface_port=3, tag_value=83,
                               switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "enabled": True,
            "dynamic_backup_path": True
        }

        dynamic_backup_path = Path([
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
        ])

        evc = EVC(**attributes)
        discover_new_path_mocked.return_value = dynamic_backup_path
        deployed = evc.deploy()

        self.assertEqual(should_deploy_mock.call_count, 1)
        self.assertEqual(discover_new_path_mocked.call_count, 1)
        self.assertEqual(activate_mock.call_count, 1)
        self.assertEqual(install_uni_flows_mock.call_count, 1)
        self.assertEqual(install_nni_flows.call_count, 1)
        self.assertEqual(chose_vlans_mock.call_count, 1)
        self.assertEqual(log_mock.info.call_count, 1)
        self.assertTrue(deployed)

    @patch('napps.kytos.mef_eline.models.EVC.send_flow_mods')
    def test_remove_current_flows(self, send_flow_mods_mocked):
        """Test remove current flows."""
        uni_a = get_uni_mocked(interface_port=2, tag_value=82,
                               switch_id="switch_uni_a", is_valid=True)
        uni_z = get_uni_mocked(interface_port=3, tag_value=83,
                               switch_id="switch_uni_z", is_valid=True)

        attributes = {
            "name": "custom_name",
            "uni_a": uni_a,
            "uni_z": uni_z,
            "active": True,
            "enabled": True,
            "primary_links": [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]
        }

        evc = EVC(**attributes)
        evc.current_path = evc.primary_links
        evc.remove_current_flows()

        self.assertEqual(send_flow_mods_mocked.call_count, 2)
        self.assertFalse(evc.is_active())
        flows = [{'cookie': evc.get_cookie()}]
        switch1 = evc.primary_links[0].endpoint_a.switch
        switch2 = evc.primary_links[0].endpoint_b.switch
        send_flow_mods_mocked.assert_called_with(switch1, flows, 'delete')
        send_flow_mods_mocked.assert_called_with(switch2, flows, 'delete')
