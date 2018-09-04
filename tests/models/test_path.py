"""Module to test the Path class."""
import sys
from unittest import TestCase

from kytos.core.common import EntityStatus

# pylint: disable=wrong-import-position
sys.path.insert(0, '/var/lib/kytos/napps/..')
# pylint: enable=wrong-import-position

from napps.kytos.mef_eline.models import Path  # NOQA
from napps.kytos.mef_eline.tests.helpers import get_link_mocked  # NOQA


class TestPath(TestCase):
    """"Class to test path methods."""

    def test_status_case_1(self):
        """Test if empty link is DISABLED."""
        current_path = Path()
        self.assertEqual(current_path.status, EntityStatus.DISABLED)

    def test_status_case_2(self):
        """Test if link status is DOWN."""
        links = [
                 get_link_mocked(status=EntityStatus.DOWN),
                 get_link_mocked(status=EntityStatus.UP)
        ]
        current_path = Path(links)
        self.assertEqual(current_path.status, EntityStatus.DOWN)

    def test_status_case_3(self):
        """Test if link status is DISABLED."""
        links = [
                 get_link_mocked(status=EntityStatus.DISABLED),
                 get_link_mocked(status=EntityStatus.UP)
        ]
        current_path = Path(links)
        self.assertEqual(current_path.status, EntityStatus.DISABLED)

    def test_status_case_4(self):
        """Test if link status is UP."""
        links = [
                 get_link_mocked(status=EntityStatus.UP),
                 get_link_mocked(status=EntityStatus.UP)
        ]
        current_path = Path(links)
        self.assertEqual(current_path.status, EntityStatus.UP)

    def test_compare_same_paths(self):
        """Test compare paths with same links."""
        links = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]

        path_1 = Path(links)
        path_2 = Path(links)
        self.assertEqual(path_1, path_2)

    def test_compare_different_paths(self):
        """Test compare paths with different links."""
        links_1 = [
                get_link_mocked(endpoint_a_port=9, endpoint_b_port=10,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=11, endpoint_b_port=12,
                                metadata={"s_vlan": 6})
            ]
        links_2 = [
                get_link_mocked(endpoint_a_port=12, endpoint_b_port=11,
                                metadata={"s_vlan": 5}),
                get_link_mocked(endpoint_a_port=14, endpoint_b_port=16,
                                metadata={"s_vlan": 11})
            ]

        path_1 = Path(links_1)
        path_2 = Path(links_2)
        self.assertNotEqual(path_1, path_2)

    def test_as_dict(self):
        """Test path as dict."""
        links = [
                get_link_mocked(link_dict={"id": 3}),
                get_link_mocked(link_dict={"id": 2})
            ]

        current_path = Path(links)
        expected_dict = [{"id": 3}, {"id": 2}]
        self.assertEqual(expected_dict, current_path.as_dict())


