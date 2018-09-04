"""Module to test the LinkProtection class."""
import sys
from unittest import TestCase
from unittest.mock import patch

from kytos.core.common import EntityStatus

# pylint: disable=wrong-import-position
sys.path.insert(0, '/var/lib/kytos/napps/..')
# pylint: enable=wrong-import-position

from napps.kytos.mef_eline.models import EVC, Path  # NOQA
from napps.kytos.mef_eline.tests.helpers import get_link_mocked, get_uni_mocked  # NOQA


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
    def test_deploy_to_case_2(self, deploy_mocked):
        """Test deploy with all links up."""
        deploy_mocked.return_value = True

        primary_path = [
                 get_link_mocked(status=EntityStatus.UP),
                 get_link_mocked(status=EntityStatus.UP)
        ]
        attributes = {
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "enabled": True
        }
        evc = EVC(**attributes)
        deployed = evc.deploy_to('primary_path', evc.primary_path)
        deploy_mocked.assert_called_with(evc.primary_path)
        self.assertTrue(deployed)

    def test_deploy_to_case_3(self):
        """Test deploy with one link down."""
        primary_path = [
                 get_link_mocked(status=EntityStatus.DOWN),
                 get_link_mocked(status=EntityStatus.UP)
        ]
        attributes = {
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
            "primary_path": primary_path,
            "enabled": True
        }
        evc = EVC(**attributes)
        deployed = evc.deploy_to('primary_path', evc.primary_path)
        self.assertFalse(deployed)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_down_case_1(self, deploy_to_mocked, deploy_mocked,
                                     log_mocked):
        """Test if deploy_to backup path is called."""
        deploy_mocked.return_value = True
        deploy_to_mocked.return_value = True
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
        deploy_to_mocked.assert_called_once_with('backup_path',
                                                 evc.backup_path)
        self.assertTrue(current_handle_link_down)
        msg = f"{evc} deployed after link down."
        log_mocked.debug.assert_called_once_with(msg)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_down_case_2(self, deploy_to_mocked, deploy_mocked,
                                     log_mocked):
        """Test if deploy_to backup path is called."""
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
                                status=EntityStatus.DOWN),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
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
        deploy_to_mocked.assert_called_once_with('primary_path',
                                                 evc.primary_path)
        self.assertTrue(current_handle_link_down)
        msg = f"{evc} deployed after link down."
        log_mocked.debug.assert_called_once_with(msg)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_down_case_3(self, deploy_to_mocked, deploy_mocked,
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
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
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
        self.assertEqual(deploy_to_mocked.call_count, 1)
        deploy_to_mocked.assert_called_once_with('primary_path',
                                                 evc.primary_path)
        self.assertFalse(current_handle_link_down)
        msg = f'Failed to re-deploy {evc} after link down.'
        log_mocked.debug.assert_called_once_with(msg)

    @patch('napps.kytos.mef_eline.models.log')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_down_case_4(self, deploy_to_mocked, deploy_mocked,
                                     log_mocked):
        """Test if circuit without dynamic path is return failed."""
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
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
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
        current_handle_link_down = evc.handle_link_down()
        self.assertEqual(deploy_mocked.call_count, 1)
        self.assertEqual(deploy_to_mocked.call_count, 1)
        deploy_to_mocked.assert_called_once_with('primary_path',
                                                 evc.primary_path)
        self.assertTrue(current_handle_link_down)
        msg = f"{evc} deployed after link down."
        log_mocked.debug.assert_called_once_with(msg)

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
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_up_case_2(self, deploy_to_mocked, deploy_mocked):
        """Test if it is changing from backup_path to primary_path."""
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
        self.assertEqual(deploy_to_mocked.call_count, 1)
        deploy_to_mocked.assert_called_once_with('primary_path',
                                                 evc.primary_path)
        self.assertTrue(current_handle_link_up)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_up_case_3(self, deploy_to_mocked, deploy_mocked):
        """Test if it is deployed after the backup is up."""
        deploy_mocked.return_value = True
        deploy_to_mocked.return_value = True
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
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
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
        current_handle_link_up = evc.handle_link_up(backup_path[0])
        self.assertEqual(deploy_mocked.call_count, 0)
        self.assertEqual(deploy_to_mocked.call_count, 1)
        deploy_to_mocked.assert_called_once_with('backup_path',
                                                 evc.backup_path)
        self.assertTrue(current_handle_link_up)

    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.models.LinkProtection.deploy_to')
    def test_handle_link_up_case_4(self, deploy_to_mocked, deploy_mocked):
        """Test if it is deployed after the dynamic_backup_path deploy."""
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
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6},
                                status=EntityStatus.UP),
        ]
        attributes = {
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
        current_handle_link_up = evc.handle_link_up(backup_path[0])
        self.assertEqual(deploy_mocked.call_count, 1)
        self.assertEqual(deploy_to_mocked.call_count, 1)
        deploy_to_mocked.assert_called_once_with('backup_path',
                                                 evc.backup_path)
        self.assertTrue(current_handle_link_up)
