"""Module to test the EVCBase class."""
import sys
from unittest import TestCase

from kytos.core.interface import UNI

# pylint: disable=wrong-import-position
sys.path.insert(0, '/var/lib/kytos/napps/..')
# pylint: enable=wrong-import-position

from napps.kytos.mef_eline.models import EVC  # NOQA
from napps.kytos.mef_eline.tests.helpers import get_uni_mocked  # NOQA


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
            "uni_a": get_uni_mocked(tag_value=82)
        }
        error_message = "VLAN tag 82 is not available in uni_a"
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_without_uni_z(self):
        """Test if the EVC raises and error with UNI Z is required."""
        attributes = {
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True)
        }
        error_message = "uni_z is required."
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_with_invalid_uni_z(self):
        """Test if the EVC raises and error with UNI Z is required."""
        attributes = {
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(tag_value=83)
        }
        error_message = "VLAN tag 83 is not available in uni_z"
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_update_name(self):
        """Test if raises and error when trying to update the name."""
        attributes = {
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
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
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }
        update_dict = {
            "uni_a": get_uni_mocked(is_valid=True)
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
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }
        update_dict = {
            "uni_z": get_uni_mocked(is_valid=True)
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
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }
        evc = EVC(**attributes)
        expected_value = f'EVC({evc.id}, {evc.name})'
        self.assertEqual(str(evc), expected_value)

    def test_comparison_method(self):
        """Test the method __eq__."""
        attributes = {
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }
        evc1 = EVC(**attributes)
        evc2 = EVC(**attributes)

        attributes = {
            "name": "circuit_name_2",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }
        evc3 = EVC(**attributes)
        evc4 = EVC(**attributes)

        self.assertEqual(evc1 == evc2, True)
        self.assertEqual(evc1 == evc3, False)
        self.assertEqual(evc2 == evc3, False)
        self.assertEqual(evc3 == evc4, True)

    def test_as_dict(self):
        """Test the method as_dict."""
        attributes = {
            "id": "custom_id",
            "name": "custom_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True),
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
