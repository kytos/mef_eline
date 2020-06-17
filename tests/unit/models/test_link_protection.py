"""Module to test the LinkProtection class."""
import sys
from unittest import TestCase
from unittest.mock import patch
from unittest.mock import Mock

from kytos.core.common import EntityStatus

# pylint: disable=wrong-import-position
sys.path.insert(0, '/var/lib/kytos/napps/..')
# pylint: enable=wrong-import-position
from napps.kytos.mef_eline.models import EVC, Path  # NOQA pycodestyle
from tests.helpers import MockResponse, get_link_mocked,\
    get_uni_mocked, get_controller_mock  # NOQA pycodestyle

DEPLOY_TO_PRIMARY_PATH = \
    'napps.kytos.mef_eline.models.LinkProtection.deploy_to_primary_path'


class TestLinkProtection(TestCase):  # pylint: disable=too-many-public-methods
    """Tests to validate LinkProtection class."""

    def test_is_using_backup_path(self):
        """Test test is using backup path."""
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
        ]

        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "backup_path": backup_path
        }

        evc = EVC(**attributes)
        self.assertFalse(evc.is_using_backup_path())
        evc.current_path = evc.backup_path
        self.assertTrue(evc.is_using_backup_path())

    def test_is_using_primary_path(self):
        """Test test is using primary path."""
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
        ]

        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path
        }

        evc = EVC(**attributes)
        self.assertFalse(evc.is_using_primary_path())
        evc.current_path = evc.primary_path
        self.assertTrue(evc.is_using_primary_path())

    @patch('napps.kytos.mef_eline.models.log')
    def test_deploy_to_case_1(self, log_mocked):
        """Test if the path is equal to current_path."""
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path
        }
        evc = EVC(**attributes)
        evc.current_path = evc.primary_path

        expected_deployed = evc.deploy_to('primary_path', evc.primary_path)
        expected_msg = 'primary_path is equal to current_path.'
        log_mocked.debug.assert_called_with(expected_msg)
        self.assertTrue(expected_deployed)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.EVC._install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC._install_uni_flows')
    @patch('napps.kytos.mef_eline.models.Path.status', EntityStatus.UP)
    def test_deploy_to_case_2(self, install_uni_flows_mocked,
                              install_nni_flows_mocked,
                              deploy_mocked):
        """Test deploy with all links up."""
        deploy_mocked.return_value = True

        primary_path = [
                 get_link_mocked(status=EntityStatus.UP),
                 get_link_mocked(status=EntityStatus.UP)
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "enabled": True
        }
        evc = EVC(**attributes)

        # storehouse mock
        evc._storehouse.box = Mock()  # pylint: disable=protected-access
        evc._storehouse.box.data = {}  # pylint: disable=protected-access

        deployed = evc.deploy_to('primary_path', evc.primary_path)
        install_uni_flows_mocked.assert_called_with(evc.primary_path)
        install_nni_flows_mocked.assert_called_with(evc.primary_path)
        self.assertTrue(deployed)

    # This method will be used by the mock to replace requests.get
    def _mocked_requests_get_path_down(self):
        # pylint: disable=no-self-use
        return MockResponse({'links': {'abc': {'active': False},
                                       'def': {'active': True}}}, 200)

    @patch('requests.get', side_effect=_mocked_requests_get_path_down)
    def test_deploy_to_case_3(self, requests_mocked):
        # pylint: disable=unused-argument
        """Test deploy with one link down."""
        link1 = get_link_mocked()
        link2 = get_link_mocked()
        link1.id = 'abc'
        link2.id = 'def'
        primary_path = [link1, link2]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "enabled": True
        }
        evc = EVC(**attributes)

        # storehouse initialization mock
        evc._storehouse.box = Mock()  # pylint: disable=protected-access
        evc._storehouse.box.data = {}  # pylint: disable=protected-access

        deployed = evc.deploy_to('primary_path', evc.primary_path)
        self.assertFalse(deployed)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy._send_flow_mods')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to_backup_path')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.Path.status')
    def test_handle_link_down_case_1(self, path_status_mocked,
                                     deploy_mocked, deploy_to_mocked,
                                     _send_flow_mods_mocked, log_mocked):
        """Test if deploy_to backup path is called."""
        deploy_mocked.return_value = True
        path_status_mocked.side_effect = [EntityStatus.DOWN, EntityStatus.UP]

        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True
        }
        evc = EVC(**attributes)

        evc.current_path = evc.primary_path
        current_handle_link_down = evc.handle_link_down()
        self.assertEqual(deploy_mocked.call_count, 0)
        deploy_to_mocked.assert_called_once()

        self.assertTrue(current_handle_link_down)
        msg = f"{evc} deployed after link down."
        log_mocked.debug.assert_called_once_with(msg)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch(DEPLOY_TO_PRIMARY_PATH)
    @patch('napps.kytos.mef_eline.models.Path.status')
    def test_handle_link_down_case_2(self, path_status_mocked,
                                     deploy_to_mocked, deploy_mocked,
                                     log_mocked):
        """Test if deploy_to backup path is called."""
        deploy_mocked.return_value = True
        deploy_to_mocked.return_value = True
        path_status_mocked.side_effect = [EntityStatus.UP, EntityStatus.DOWN]
        primary_path = [
                get_link_mocked(endpoint_a_port=7, endpoint_b_port=8,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True
        }

        evc = EVC(**attributes)
        evc.current_path = evc.backup_path
        current_handle_link_down = evc.handle_link_down()
        self.assertEqual(deploy_mocked.call_count, 0)
        deploy_to_mocked.assert_called_once()
        self.assertTrue(current_handle_link_down)
        msg = f"{evc} deployed after link down."
        log_mocked.debug.assert_called_once_with(msg)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch(DEPLOY_TO_PRIMARY_PATH)
    @patch('napps.kytos.mef_eline.models.DynamicPathManager.get_paths')
    @patch('napps.kytos.mef_eline.models.Path.status', EntityStatus.DOWN)
    def test_handle_link_down_case_3(self, get_paths_mocked,
                                     deploy_to_mocked, deploy_mocked,
                                     log_mocked):
        """Test if circuit without dynamic path is return failed."""
        deploy_mocked.return_value = False
        deploy_to_mocked.return_value = False
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=13, endpoint_b_port=14,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True
        }

        evc = EVC(**attributes)
        evc.current_path = evc.backup_path
        current_handle_link_down = evc.handle_link_down()

        self.assertEqual(get_paths_mocked.call_count, 0)
        self.assertEqual(deploy_mocked.call_count, 0)
        self.assertEqual(deploy_to_mocked.call_count, 1)

        self.assertFalse(current_handle_link_down)
        msg = f'Failed to re-deploy {evc} after link down.'
        log_mocked.debug.assert_called_once_with(msg)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy_to_path')
    @patch('napps.kytos.mef_eline.models.EVCDeploy._send_flow_mods')
    @patch(DEPLOY_TO_PRIMARY_PATH)
    @patch('napps.kytos.mef_eline.models.Path.status', EntityStatus.DOWN)
    def test_handle_link_down_case_4(self, deploy_to_mocked,
                                     _send_flow_mods_mocked,
                                     deploy_mocked,
                                     log_mocked):
        """Test if circuit with dynamic path is return success."""
        deploy_mocked.return_value = True
        deploy_to_mocked.return_value = False
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=13, endpoint_b_port=14,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True,
            "dynamic_backup_path": True
        }

        evc = EVC(**attributes)
        evc.current_path = evc.backup_path

        # storehouse mock
        evc._storehouse.box = Mock()  # pylint: disable=protected-access
        evc._storehouse.box.data = {}  # pylint: disable=protected-access

        current_handle_link_down = evc.handle_link_down()
        self.assertEqual(deploy_to_mocked.call_count, 1)

        self.assertTrue(current_handle_link_down)
        msg = f"{evc} deployed after link down."
        log_mocked.debug.assert_called_with(msg)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_up_case_1(self, deploy_to_mocked, deploy_mocked):
        """Test if handle link up do nothing when is using primary path."""
        deploy_mocked.return_value = True
        deploy_to_mocked.return_value = True
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True,
            "dynamic_backup_path": True
        }

        evc = EVC(**attributes)
        evc.current_path = evc.primary_path
        current_handle_link_up = evc.handle_link_up(backup_path[0])
        self.assertEqual(deploy_mocked.call_count, 0)
        self.assertEqual(deploy_to_mocked.call_count, 0)
        self.assertTrue(current_handle_link_up)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy_to_path')
    @patch('napps.kytos.mef_eline.models.Path.status', EntityStatus.UP)
    def test_handle_link_up_case_2(self, deploy_to_path_mocked, deploy_mocked):
        """Test if it is changing from backup_path to primary_path."""
        deploy_mocked.return_value = True
        deploy_to_path_mocked.return_value = True
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True,
            "dynamic_backup_path": True
        }

        evc = EVC(**attributes)
        evc.current_path = evc.backup_path
        current_handle_link_up = evc.handle_link_up(primary_path[0])
        self.assertEqual(deploy_mocked.call_count, 0)
        self.assertEqual(deploy_to_path_mocked.call_count, 1)
        deploy_to_path_mocked.assert_called_once_with(evc.primary_path)
        self.assertTrue(current_handle_link_up)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy_to_path')
    @patch('napps.kytos.mef_eline.models.DynamicPathManager.get_best_path')
    @patch('napps.kytos.mef_eline.models.EVC._install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC._install_uni_flows')
    @patch('napps.kytos.mef_eline.models.Path.status', EntityStatus.UP)
    def test_handle_link_up_case_3(self, _install_uni_flows_mocked,
                                   _install_nni_flows_mocked,
                                   get_best_path_mocked,
                                   deploy_to_path_mocked, deploy_mocked):
        """Test if it is deployed after the backup is up."""
        deploy_mocked.return_value = True
        deploy_to_path_mocked.return_value = True
        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=13, endpoint_b_port=14,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True,
            "dynamic_backup_path": True
        }

        evc = EVC(**attributes)

        # storehouse initialization mock
        evc._storehouse.box = Mock()  # pylint: disable=protected-access
        evc._storehouse.box.data = {}  # pylint: disable=protected-access

        evc.current_path = Path([])
        current_handle_link_up = evc.handle_link_up(backup_path[0])

        self.assertEqual(get_best_path_mocked.call_count, 0)
        self.assertEqual(deploy_mocked.call_count, 0)
        self.assertEqual(deploy_to_path_mocked.call_count, 1)
        deploy_to_path_mocked.assert_called_once_with(evc.backup_path)
        self.assertTrue(current_handle_link_up)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy_to_path')
    @patch('napps.kytos.mef_eline.models.DynamicPathManager.get_best_path')
    @patch('napps.kytos.mef_eline.models.EVC._install_nni_flows')
    @patch('napps.kytos.mef_eline.models.EVC._install_uni_flows')
    @patch('napps.kytos.mef_eline.models.Path.status', EntityStatus.DOWN)
    def test_handle_link_up_case_4(self, *args):
        """Test if not path is found a dynamic path is used."""
        (_install_uni_flows_mocked, _install_nni_flows_mocked,
         get_best_path_mocked, deploy_to_path_mocked) = args

        deploy_to_path_mocked.return_value = True

        primary_path = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.UP),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.DOWN),
        ]
        backup_path = [
                get_link_mocked(endpoint_a_port=13, endpoint_b_port=14,
                                metadata={"s_vlan": 5},
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.DOWN),
        ]

        # Setup best_path mock
        best_path = Path()
        best_path.append(primary_path[0])
        get_best_path_mocked.return_value = best_path

        attributes = {
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "backup_path": backup_path,
            "enabled": True,
            "dynamic_backup_path": True
        }

        evc = EVC(**attributes)
        evc.current_path = Path([])

        # storehouse mock
        evc._storehouse.box = Mock()  # pylint: disable=protected-access
        evc._storehouse.box.data = {}  # pylint: disable=protected-access

        current_handle_link_up = evc.handle_link_up(backup_path[0])

        self.assertEqual(get_best_path_mocked.call_count, 0)
        self.assertEqual(deploy_to_path_mocked.call_count, 1)
        deploy_to_path_mocked.assert_called_once_with()
        self.assertTrue(current_handle_link_up)
