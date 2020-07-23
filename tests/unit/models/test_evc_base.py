"""Module to test the EVCBase class."""
import sys
from unittest import TestCase

# pylint: disable=wrong-import-position
sys.path.insert(0, '/var/lib/kytos/napps/..')
# pylint: enable=wrong-import-position
from napps.kytos.mef_eline.models import EVC  # NOQA  pycodestyle
from napps.kytos.mef_eline.scheduler import \
    CircuitSchedule   # NOQA  pycodestyle
from tests.helpers import get_uni_mocked, \
    get_controller_mock  # NOQA  pycodestyle


class TestEVC(TestCase):  # pylint: disable=too-many-public-methods
    """Tests to verify EVC class."""

    def test_attributes_empty(self):
        """Test if the EVC raises an error with name is required."""
        attributes = {"controller": get_controller_mock()}
        error_message = "name is required."
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_without_uni_a(self):
        """Test if the EVC raises and error with UNI A is required."""
        attributes = {"controller": get_controller_mock(),
                      "name": "circuit_name"}
        error_message = "uni_a is required."
        with self.assertRaises(ValueError) as handle_error:
            EVC(**attributes)
        self.assertEqual(str(handle_error.exception), error_message)

    def test_with_invalid_uni_a(self):
        """Test if the EVC raises and error with invalid UNI A."""
        attributes = {
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
            "name": "circuit_name",
            "uni_a": get_uni_mocked(is_valid=True),
            "uni_z": get_uni_mocked(is_valid=True)
        }
        evc1 = EVC(**attributes)
        evc2 = EVC(**attributes)

        attributes = {
            "controller": get_controller_mock(),
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
            "controller": get_controller_mock(),
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
            'circuit_scheduler': [
                CircuitSchedule.from_dict({"id": 234243247, "action": "create",
                                          "frequency": "1 * * * *"}),
                CircuitSchedule.from_dict({"id": 234243239, "action": "create",
                                          "interval": {"hours": 2}})
            ],
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
            'request_time': '2018-08-21T19:10:41',
            'creation_time': '2018-08-21T18:44:54',
            'circuit_scheduler': [
                {
                    "id": 234243247,
                    "action": "create",
                    "frequency": "1 * * * *"
                },
                {
                    "id": 234243239,
                    "action": "create",
                    "interval": {
                        "hours": 2
                    }
                }
            ],
            'active': False,
            'enabled': True,
            'priority': 2
        }
        actual_dict = evc.as_dict()
        for name, value in expected_dict.items():
            actual = actual_dict.get(name)
            self.assertEqual(value, actual)
