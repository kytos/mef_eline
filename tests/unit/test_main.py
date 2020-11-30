"""Module to test the main napp file."""
import json
from unittest import TestCase
from unittest.mock import MagicMock, PropertyMock, patch, create_autospec, call

from kytos.core.interface import UNI, Interface
from kytos.core.events import KytosEvent

from napps.kytos.mef_eline.models import EVC
from tests.helpers import get_controller_mock, get_uni_mocked


# pylint: disable=too-many-public-methods, too-many-lines
class TestMain(TestCase):
    """Test the Main class."""

    def setUp(self):
        """Execute steps before each tests.

        Set the server_name_url_url from kytos/mef_eline
        """
        self.server_name_url = 'http://localhost:8181/api/kytos/mef_eline'

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch('kytos.core.helpers.run_on_thread', lambda x: x).start()
        from napps.kytos.mef_eline.main import Main

        self.addCleanup(patch.stopall)
        self.napp = Main(get_controller_mock())

    def test_get_event_listeners(self):
        """Verify all event listeners registered."""
        expected_events = ['kytos/core.shutdown',
                           'kytos/core.shutdown.kytos/mef_eline',
                           'kytos/topology.link_up',
                           'kytos/topology.link_down']
        actual_events = self.napp.listeners()

        for _event in expected_events:
            self.assertIn(_event, actual_events, '%s' % _event)

    def test_verify_api_urls(self):
        """Verify all APIs registered."""
        expected_urls = [
            ({}, {'POST', 'OPTIONS'},
             '/api/kytos/mef_eline/v2/evc/'),

            ({}, {'OPTIONS', 'HEAD', 'GET'},
             '/api/kytos/mef_eline/v2/evc/'),

            ({'circuit_id': '[circuit_id]'}, {'OPTIONS', 'DELETE'},
             '/api/kytos/mef_eline/v2/evc/<circuit_id>'),

            ({'circuit_id': '[circuit_id]'}, {'OPTIONS', 'HEAD', 'GET'},
             '/api/kytos/mef_eline/v2/evc/<circuit_id>'),

            ({'circuit_id': '[circuit_id]'}, {'OPTIONS', 'PATCH'},
             '/api/kytos/mef_eline/v2/evc/<circuit_id>'),

            ({}, {'OPTIONS', 'GET', 'HEAD'},
             '/api/kytos/mef_eline/v2/evc/schedule'),

            ({}, {'POST', 'OPTIONS'},
             '/api/kytos/mef_eline/v2/evc/schedule/'),

            ({'schedule_id': '[schedule_id]'},
             {'OPTIONS', 'DELETE'},
             '/api/kytos/mef_eline/v2/evc/schedule/<schedule_id>'),

            ({'schedule_id': '[schedule_id]'},
             {'OPTIONS', 'PATCH'},
             '/api/kytos/mef_eline/v2/evc/schedule/<schedule_id>')
            ]

        urls = self.get_napp_urls(self.napp)
        self.assertCountEqual(expected_urls, urls)

    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.models.EVCBase._validate')
    def test_evc_from_dict(self, _validate_mock, uni_from_dict_mock):
        """
        Test the helper method that create an EVN from dict.

        Verify object creation with circuit data and schedule data.
        """
        _validate_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        payload = {
            "name": "my evc1",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
                "tag": {
                    "tag_type": 1,
                    "value": 80
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:02:2",
                "tag": {
                    "tag_type": 1,
                    "value": 1
                }
            },
            "circuit_scheduler": [{
                "frequency": "* * * * *",
                "action": "create"
            }]
        }
        # pylint: disable=protected-access
        evc_response = self.napp._evc_from_dict(payload)
        self.assertIsNotNone(evc_response)
        self.assertIsNotNone(evc_response.uni_a)
        self.assertIsNotNone(evc_response.uni_z)
        self.assertIsNotNone(evc_response.circuit_scheduler)
        self.assertIsNotNone(evc_response.name)

    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.models.EVCBase._validate')
    @patch('kytos.core.Controller.get_interface_by_id')
    def test_evc_from_dict_paths(self, _get_interface_by_id_mock,
                                 _validate_mock, uni_from_dict_mock):
        """
        Test the helper method that create an EVN from dict.

        Verify object creation with circuit data and schedule data.
        """
        _get_interface_by_id_mock.return_value = True
        _validate_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        payload = {
            "name": "my evc1",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
                "tag": {
                    "tag_type": 1,
                    "value": 80
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:02:2",
                "tag": {
                    "tag_type": 1,
                    "value": 1
                }
            },
            "current_path": [],
            "primary_path": [
                {"endpoint_a": {"interface_id": "00:00:00:00:00:00:00:01:1"},
                 "endpoint_b": {"interface_id": "00:00:00:00:00:00:00:02:2"}}
            ],
            "backup_path": []
        }

        # pylint: disable=protected-access
        evc_response = self.napp._evc_from_dict(payload)
        self.assertIsNotNone(evc_response)
        self.assertIsNotNone(evc_response.uni_a)
        self.assertIsNotNone(evc_response.uni_z)
        self.assertIsNotNone(evc_response.circuit_scheduler)
        self.assertIsNotNone(evc_response.name)
        self.assertEqual(len(evc_response.current_path), 0)
        self.assertEqual(len(evc_response.backup_path), 0)
        self.assertEqual(len(evc_response.primary_path), 1)

    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.models.EVCBase._validate')
    @patch('kytos.core.Controller.get_interface_by_id')
    def test_evc_from_dict_links(self, _get_interface_by_id_mock,
                                 _validate_mock, uni_from_dict_mock):
        """
        Test the helper method that create an EVN from dict.

        Verify object creation with circuit data and schedule data.
        """
        _get_interface_by_id_mock.return_value = True
        _validate_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        payload = {
            "name": "my evc1",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
                "tag": {
                    "tag_type": 1,
                    "value": 80
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:02:2",
                "tag": {
                    "tag_type": 1,
                    "value": 1
                }
            },
            "primary_links": [
                {"endpoint_a": {"interface_id": "00:00:00:00:00:00:00:01:1"},
                 "endpoint_b": {"interface_id": "00:00:00:00:00:00:00:02:2"}}
            ],
            "backup_links": []
        }

        # pylint: disable=protected-access
        evc_response = self.napp._evc_from_dict(payload)
        self.assertIsNotNone(evc_response)
        self.assertIsNotNone(evc_response.uni_a)
        self.assertIsNotNone(evc_response.uni_z)
        self.assertIsNotNone(evc_response.circuit_scheduler)
        self.assertIsNotNone(evc_response.name)
        self.assertEqual(len(evc_response.current_links_cache), 0)
        self.assertEqual(len(evc_response.backup_links), 0)
        self.assertEqual(len(evc_response.primary_links), 1)

    def test_list_without_circuits(self):
        """Test if list circuits return 'no circuit stored.'."""
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/'
        response = api.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(json.loads(response.data.decode()), {})

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_list_no_circuits_stored(self, storehouse_data_mock):
        """Test if list circuits return all circuits stored."""
        circuits = {}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/'

        response = api.get(url)
        expected_result = circuits
        self.assertEqual(json.loads(response.data), expected_result)

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_list_with_circuits_stored(self, storehouse_data_mock):
        """Test if list circuits return all circuits stored."""
        circuits = {'1': {'name': 'circuit_1'},
                    '2': {'name': 'circuit_2'}}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/'

        response = api.get(url)
        expected_result = circuits
        self.assertEqual(json.loads(response.data), expected_result)

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_list_with_archived_circuits_stored_1(self, storehouse_data_mock):
        """Test if list circuits return only circuits not archived."""
        circuits = {'1': {'name': 'circuit_1'},
                    '2': {'name': 'circuit_2', 'archived': True}}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/'

        response = api.get(url)
        expected_result = {'1': circuits['1']}
        self.assertEqual(json.loads(response.data), expected_result)

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_list_with_archived_circuits_stored_2(self, storehouse_data_mock):
        """Test if list circuits return all circuits."""
        circuits = {'1': {'name': 'circuit_1'},
                    '2': {'name': 'circuit_2', 'archived': True}}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/?archived=True'

        response = api.get(url)
        expected_result = circuits
        self.assertEqual(json.loads(response.data), expected_result)

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_circuit_with_valid_id(self, storehouse_data_mock):
        """Test if get_circuit return the circuit attributes."""
        circuits = {'1': {'name': 'circuit_1'},
                    '2': {'name': 'circuit_2'}}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/1'
        response = api.get(url)
        expected_result = circuits['1']
        self.assertEqual(json.loads(response.data), expected_result)

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_circuit_with_invalid_id(self, storehouse_data_mock):
        """Test if get_circuit return invalid circuit_id."""
        circuits = {'1': {'name': 'circuit_1'},
                    '2': {'name': 'circuit_2'}}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/3'
        response = api.get(url)
        expected_result = 'circuit_id 3 not found'
        self.assertEqual(json.loads(response.data)['description'],
                         expected_result)

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_create_a_circuit_case_1(self, *args):
        """Test create a new circuit."""
        # pylint: disable=too-many-locals
        (validate_mock, evc_as_dict_mock, save_evc_mock,
         uni_from_dict_mock, sched_add_mock, storehouse_data_mock) = args

        validate_mock.return_value = True
        save_evc_mock.return_value = True
        uni1 = create_autospec(UNI)
        uni2 = create_autospec(UNI)
        uni1.interface = create_autospec(Interface)
        uni2.interface = create_autospec(Interface)
        uni1.interface.switch = '00:00:00:00:00:00:00:01'
        uni2.interface.switch = '00:00:00:00:00:00:00:02'
        uni_from_dict_mock.side_effect = [uni1, uni2]
        evc_as_dict_mock.return_value = {}
        sched_add_mock.return_value = True
        storehouse_data_mock.return_value = {}

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/'
        payload = {
                   "name": "my evc1",
                   "frequency": "* * * * *",
                   "uni_a": {
                     "interface_id": "00:00:00:00:00:00:00:01:1",
                     "tag": {
                       "tag_type": 1,
                       "value": 80
                     }
                   },
                   "uni_z": {
                     "interface_id": "00:00:00:00:00:00:00:02:2",
                     "tag": {
                       "tag_type": 1,
                       "value": 1
                     }
                   }
                 }

        response = api.post(url, data=json.dumps(payload),
                            content_type='application/json')
        current_data = json.loads(response.data)

        # verify expected result from request
        self.assertEqual(201, response.status_code, response.data)
        self.assertIn('circuit_id', current_data)

        # verify uni called
        uni_from_dict_mock.called_twice()
        uni_from_dict_mock.assert_any_call(payload['uni_z'])
        uni_from_dict_mock.assert_any_call(payload['uni_a'])

        # verify validation called
        validate_mock.assert_called_once()
        validate_mock.assert_called_with(frequency='* * * * *',
                                         name='my evc1',
                                         uni_a=uni1,
                                         uni_z=uni2)
        # verify save method is called
        save_evc_mock.assert_called_once()

        # verify evc as dict is called to save in the box
        evc_as_dict_mock.assert_called_once()
        # verify add circuit in sched
        sched_add_mock.assert_called_once()

    @staticmethod
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

    @staticmethod
    def get_app_test_client(napp):
        """Return a flask api test client."""
        napp.controller.api_server.register_napp_endpoints(napp)
        return napp.controller.api_server.app.test_client()

    def test_create_a_circuit_case_2(self):
        """Test create a new circuit trying to send request without a json."""
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/'

        response = api.post(url)
        current_data = json.loads(response.data)
        expected_data = 'The request body mimetype is not application/json.'

        self.assertEqual(415, response.status_code, response.data)
        self.assertEqual(current_data['description'], expected_data)

    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    def test_create_circuit_already_enabled(self, *args):
        """Test create an already created circuit."""
        (evc_as_dict_mock, validate_mock, save_evc_mock,
         uni_from_dict_mock, sched_add_mock) = args

        validate_mock.return_value = True
        save_evc_mock.return_value = True
        sched_add_mock.return_value = True
        uni1 = create_autospec(UNI)
        uni2 = create_autospec(UNI)
        uni1.interface = create_autospec(Interface)
        uni2.interface = create_autospec(Interface)
        uni1.interface.switch = '00:00:00:00:00:00:00:01'
        uni2.interface.switch = '00:00:00:00:00:00:00:02'
        uni_from_dict_mock.side_effect = [uni1, uni2, uni1, uni2]

        api = self.get_app_test_client(self.napp)
        payload = {
            "name": "my evc1",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
                "tag": {
                    "tag_type": 1,
                    "value": 80
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:02:2",
                "tag": {
                    "tag_type": 1,
                    "value": 1
                }
            }
        }

        evc_as_dict_mock.return_value = payload
        response = api.post(f'{self.server_name_url}/v2/evc/',
                            data=json.dumps(payload),
                            content_type='application/json')
        self.assertEqual(201, response.status_code)

        response = api.post(f'{self.server_name_url}/v2/evc/',
                            data=json.dumps(payload),
                            content_type='application/json')
        current_data = json.loads(response.data)
        expected_data = 'The EVC already exists.'
        self.assertEqual(current_data['description'], expected_data)
        self.assertEqual(409, response.status_code)

    def test_load_circuits_by_interface(self):
        """Test if existing circuits are correctly loaded to the cache."""
        stored_circuits = {
            "182f5bac84074017a262a2321195dbb4": {
                "active": False,
                "archived": True,
                "backup_links": [],
                "backup_path": [],
                "bandwidth": 0,
                "circuit_scheduler": [
                    {
                        "action": "create",
                        "frequency": "*/3 * * * *",
                        "id": "db7f8a301e2b4ff69a2ad9a6267430e2"
                    },
                    {
                        "action": "remove",
                        "frequency": "2-59/3 * * * *",
                        "id": "b8a8bbe85bc144b0afc65181e4c069a1"
                    }
                ],
                "creation_time": "2019-08-09T19:25:06",
                "current_path": [],
                "dynamic_backup_path": True,
                "enabled": False,
                "end_date": "2018-12-29T15:16:50",
                "id": "182f5bac84074017a262a2321195dbb4",
                "name": "Teste2",
                "owner": None,
                "primary_links": [],
                "primary_path": [],
                "priority": 0,
                "request_time": "2019-08-09T19:25:06",
                "start_date": "2019-08-09T19:25:06",
                "uni_a": {
                    "interface_id": "00:00:00:00:00:00:00:03:12",
                    "tag": {
                        "tag_type": 1,
                        "value": 321
                    }
                },
                "uni_z": {
                    "interface_id": "00:00:00:00:00:00:00:06:11",
                    "tag": {
                        "tag_type": 1,
                        "value": 612
                    }
                }
            },
            "65c4582cc8f249c2a5947ef500c19e37": {
                "active": False,
                "archived": False,
                "backup_links": [],
                "backup_path": [],
                "bandwidth": 0,
                "circuit_scheduler": [
                    {
                        "action": "create",
                        "frequency": "*/3 * * * *",
                        "id": "0939dedf66ce431f85beb53daf578d73"
                    },
                    {
                        "action": "remove",
                        "frequency": "2-59/3 * * * *",
                        "id": "6cdcab31a11f44708e23776b4dad7893"
                    }
                ],
                "creation_time": "2019-07-22T16:01:24",
                "current_path": [],
                "dynamic_backup_path": True,
                "enabled": False,
                "end_date": "2018-12-29T15:16:50",
                "id": "65c4582cc8f249c2a5947ef500c19e37",
                "name": "Teste2",
                "owner": None,
                "primary_links": [],
                "primary_path": [
                    {
                        "active": False,
                        "enabled": True,
                        "endpoint_a": {
                            "active": False,
                            "enabled": True,
                            "id": "00:00:00:00:00:00:00:03:3",
                            "link": "0e2b5d7bc858b9f38db11b69",
                            "mac": "ae:6e:d3:96:83:5a",
                            "metadata": {},
                            "name": "s3-eth3",
                            "nni": True,
                            "port_number": 3,
                            "speed": 1250000000.0,
                            "switch": "00:00:00:00:00:00:00:03",
                            "type": "interface",
                            "uni": False
                        },
                        "endpoint_b": {
                            "active": False,
                            "enabled": True,
                            "id": "00:00:00:00:00:00:00:05:2",
                            "link": "0e2b5d7bc858b9f38db11b69",
                            "mac": "de:eb:d0:b0:14:cf",
                            "metadata": {},
                            "name": "s5-eth2",
                            "nni": True,
                            "port_number": 2,
                            "speed": 1250000000.0,
                            "switch": "00:00:00:00:00:00:00:05",
                            "type": "interface",
                            "uni": False
                        },
                        "id": "0e2b5d7bc858b9f38db11b69",
                        "metadata": {}
                    },
                    {
                        "active": False,
                        "enabled": True,
                        "endpoint_a": {
                            "active": False,
                            "enabled": True,
                            "id": "00:00:00:00:00:00:00:05:4",
                            "link": "53bd36ff55a5aa2029bd5d50",
                            "mac": "6e:c2:ea:c4:18:12",
                            "metadata": {},
                            "name": "s5-eth4",
                            "nni": True,
                            "port_number": 4,
                            "speed": 1250000000.0,
                            "switch": "00:00:00:00:00:00:00:05",
                            "type": "interface",
                            "uni": False
                        },
                        "endpoint_b": {
                            "active": False,
                            "enabled": True,
                            "id": "00:00:00:00:00:00:00:06:2",
                            "link": "53bd36ff55a5aa2029bd5d50",
                            "mac": "5a:25:7b:7c:0d:ac",
                            "metadata": {},
                            "name": "s6-eth2",
                            "nni": True,
                            "port_number": 2,
                            "speed": 1250000000.0,
                            "switch": "00:00:00:00:00:00:00:06",
                            "type": "interface",
                            "uni": False
                        },
                        "id": "53bd36ff55a5aa2029bd5d50",
                        "metadata": {}
                    }
                ],
                "priority": 0,
                "request_time": "2019-07-22T16:01:24",
                "start_date": "2019-07-22T16:01:24",
                "uni_a": {
                    "interface_id": "00:00:00:00:00:00:00:03:12",
                    "tag": {
                        "tag_type": 1,
                        "value": 321
                    }
                },
                "uni_z": {
                    "interface_id": "00:00:00:00:00:00:00:06:11",
                    "tag": {
                        "tag_type": 1,
                        "value": 612
                    }
                }
            }
        }

        expected_result = {
            '00:00:00:00:00:00:00:03:12':
                {'182f5bac84074017a262a2321195dbb4',
                 '65c4582cc8f249c2a5947ef500c19e37'},
            '00:00:00:00:00:00:00:06:11':
                {'182f5bac84074017a262a2321195dbb4',
                 '65c4582cc8f249c2a5947ef500c19e37'},
            '00:00:00:00:00:00:00:03:3':
                {'65c4582cc8f249c2a5947ef500c19e37'},
            '00:00:00:00:00:00:00:05:2':
                {'65c4582cc8f249c2a5947ef500c19e37'},
            '00:00:00:00:00:00:00:05:4':
                {'65c4582cc8f249c2a5947ef500c19e37'},
            '00:00:00:00:00:00:00:06:2':
                {'65c4582cc8f249c2a5947ef500c19e37'}
        }
        self.napp.load_circuits_by_interface(stored_circuits)
        # pylint: disable=protected-access
        self.assertEqual(self.napp._circuits_by_interface, expected_result)

    def test_list_schedules__no_data(self):
        """Test list of schedules."""
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule'
        response = api.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(json.loads(response.data.decode()), {})

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_list_schedules__no_data_stored(self, storehouse_data_mock):
        """Test if list circuits return all circuits stored."""
        circuits = {}
        storehouse_data_mock.return_value = circuits

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule'

        response = api.get(url)
        expected_result = circuits

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(json.loads(response.data), expected_result)

    # pylint: disable=no-self-use
    def _add_storehouse_schedule_data(self, storehouse_data_mock):
        """Add schedule data to storehouse mock object."""
        circuits = {}
        payload_1 = {
            "id": "aa:aa:aa",
            "name": "my evc1",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
                "tag": {
                    "tag_type": 1,
                    "value": 80
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:02:2",
                "tag": {
                    "tag_type": 1,
                    "value": 1
                }
            },
            "circuit_scheduler": [
                {
                    "id": "1",
                    "frequency": "* * * * *",
                    "action": "create"
                },
                {
                    "id": "2",
                    "frequency": "1 * * * *",
                    "action": "remove"
                }
            ]
        }
        circuits.update({"aa:aa:aa": payload_1})
        payload_2 = {
            "id": "bb:bb:bb",
            "name": "my second evc2",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:2",
                "tag": {
                    "tag_type": 1,
                    "value": 90
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:03:2",
                "tag": {
                    "tag_type": 1,
                    "value": 100
                }
            },
            "circuit_scheduler": [
                {
                    "id": "3",
                    "frequency": "1 * * * *",
                    "action": "create"
                },
                {
                    "id": "4",
                    "frequency": "2 * * * *",
                    "action": "remove"
                }
            ]
        }
        circuits.update({"bb:bb:bb": payload_2})
        payload_3 = {
            "id": "cc:cc:cc",
            "name": "my third evc3",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:03:1",
                "tag": {
                    "tag_type": 1,
                    "value": 90
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:04:2",
                "tag": {
                    "tag_type": 1,
                    "value": 100
                }
            }
        }
        circuits.update({"cc:cc:cc": payload_3})
        # Add one circuit to the storehouse.
        storehouse_data_mock.return_value = circuits

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_list_schedules_from_storehouse(self, storehouse_data_mock):
        """Test if list circuits return specific circuits stored."""
        self._add_storehouse_schedule_data(storehouse_data_mock)

        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule'

        # Call URL
        response = api.get(url)
        # Expected JSON data from response
        expected = [{'circuit_id': 'aa:aa:aa',
                     'schedule': {'action': 'create',
                                  'frequency': '* * * * *', 'id': '1'},
                     'schedule_id': '1'},
                    {'circuit_id': 'aa:aa:aa',
                     'schedule': {'action': 'remove',
                                  'frequency': '1 * * * *', 'id': '2'},
                     'schedule_id': '2'},
                    {'circuit_id': 'bb:bb:bb',
                     'schedule': {'action': 'create',
                                  'frequency': '1 * * * *', 'id': '3'},
                     'schedule_id': '3'},
                    {'circuit_id': 'bb:bb:bb',
                     'schedule': {'action': 'remove',
                                  'frequency': '2 * * * *', 'id': '4'},
                     'schedule_id': '4'}]

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(expected, json.loads(response.data))

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    def test_get_specific_schedule_from_storehouse(self, storehouse_data_mock):
        """Test get schedules from a circuit."""
        self._add_storehouse_schedule_data(storehouse_data_mock)

        requested_circuit_id = "bb:bb:bb"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/{requested_circuit_id}'

        # Call URL
        response = api.get(url)

        # Expected JSON data from response
        expected = [{'action': 'create', 'frequency': '1 * * * *', 'id': '3'},
                    {'action': 'remove', 'frequency': '2 * * * *', 'id': '4'}]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected,
                         json.loads(response.data)["circuit_scheduler"])

    def test_get_specific_schedules_from_storehouse_not_found(self):
        """Test get specific schedule ID that does not exist."""
        requested_id = "blah"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/{requested_id}'

        # Call URL
        response = api.get(url)

        expected = 'circuit_id blah not found'
        # Assert response not found
        self.assertEqual(response.status_code, 404, response.data)
        self.assertEqual(expected, json.loads(response.data)['description'])

    def _uni_from_dict_side_effect(self, uni_dict):
        interface_id = uni_dict.get("interface_id")
        tag_dict = uni_dict.get("tag")
        interface = Interface(interface_id, "0", "switch")
        return UNI(interface, tag_dict)

    @patch('apscheduler.schedulers.background.BackgroundScheduler.add_job')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_create_schedule(self, *args):  # pylint: disable=too-many-locals
        """Test create a circuit schedule."""
        (validate_mock, evc_as_dict_mock, save_evc_mock,
         uni_from_dict_mock, sched_add_mock, storehouse_data_mock,
         scheduler_add_job_mock) = args

        validate_mock.return_value = True
        save_evc_mock.return_value = True
        uni_from_dict_mock.side_effect = self._uni_from_dict_side_effect
        evc_as_dict_mock.return_value = {}
        sched_add_mock.return_value = True
        storehouse_data_mock.return_value = {}

        self._add_storehouse_schedule_data(storehouse_data_mock)

        requested_id = "bb:bb:bb"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule/'

        payload = {
              "circuit_id": requested_id,
              "schedule": {
                "frequency": "1 * * * *",
                "action": "create"
              }
            }

        # Call URL
        response = api.post(url, data=json.dumps(payload),
                            content_type='application/json')

        response_json = json.loads(response.data)

        self.assertEqual(response.status_code, 201, response.data)
        scheduler_add_job_mock.assert_called_once()
        save_evc_mock.assert_called_once()
        self.assertEqual(payload["schedule"]["frequency"],
                         response_json["frequency"])
        self.assertEqual(payload["schedule"]["action"],
                         response_json["action"])
        self.assertIsNotNone(response_json["id"])

    @patch('apscheduler.schedulers.background.BackgroundScheduler.remove_job')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_update_schedule(self, *args):  # pylint: disable=too-many-locals
        """Test create a circuit schedule."""
        (validate_mock, evc_as_dict_mock, save_evc_mock,
         uni_from_dict_mock, sched_add_mock, storehouse_data_mock,
         scheduler_remove_job_mock) = args

        storehouse_payload_1 = {
            "aa:aa:aa": {
                "id": "aa:aa:aa",
                "name": "my evc1",
                "uni_a": {
                    "interface_id": "00:00:00:00:00:00:00:01:1",
                    "tag": {
                        "tag_type": 1,
                        "value": 80
                    }
                },
                "uni_z": {
                    "interface_id": "00:00:00:00:00:00:00:02:2",
                    "tag": {
                        "tag_type": 1,
                        "value": 1
                    }
                },
                "circuit_scheduler": [{
                    "id": "1",
                    "frequency": "* * * * *",
                    "action": "create"
                }
                ]
            }
        }

        validate_mock.return_value = True
        save_evc_mock.return_value = True
        sched_add_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        evc_as_dict_mock.return_value = {}
        storehouse_data_mock.return_value = storehouse_payload_1
        scheduler_remove_job_mock.return_value = True

        requested_schedule_id = "1"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule/{requested_schedule_id}'

        payload = {
            "frequency": "*/1 * * * *",
            "action": "create"
        }

        # Call URL
        response = api.patch(url, data=json.dumps(payload),
                             content_type='application/json')

        response_json = json.loads(response.data)

        self.assertEqual(response.status_code, 200, response.data)
        scheduler_remove_job_mock.assert_called_once()
        save_evc_mock.assert_called_once()
        self.assertEqual(payload["frequency"], response_json["frequency"])
        self.assertEqual(payload["action"], response_json["action"])
        self.assertIsNotNone(response_json["id"])

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_update_schedule_archived(self, *args):
        """Test create a circuit schedule."""
        # pylint: disable=too-many-locals
        (validate_mock, evc_as_dict_mock,
         uni_from_dict_mock, sched_add_mock, storehouse_data_mock) = args

        storehouse_payload_1 = {
            "aa:aa:aa": {
                "id": "aa:aa:aa",
                "name": "my evc1",
                "archived": True,
                "circuit_scheduler": [{
                    "id": "1",
                    "frequency": "* * * * *",
                    "action": "create"
                }
                ]
            }
        }

        validate_mock.return_value = True
        sched_add_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        evc_as_dict_mock.return_value = {}
        storehouse_data_mock.return_value = storehouse_payload_1

        requested_schedule_id = "1"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule/{requested_schedule_id}'

        payload = {
            "frequency": "*/1 * * * *",
            "action": "create"
        }

        # Call URL
        response = api.patch(url, data=json.dumps(payload),
                             content_type='application/json')

        self.assertEqual(response.status_code, 403, response.data)

    @patch('apscheduler.schedulers.background.BackgroundScheduler.remove_job')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_delete_schedule(self, *args):
        """Test create a circuit schedule."""
        (validate_mock, evc_as_dict_mock, save_evc_mock,
         uni_from_dict_mock, storehouse_data_mock,
         scheduler_remove_job_mock) = args

        storehouse_payload_1 = {
            "2": {
                "id": "2",
                "name": "my evc1",
                "uni_a": {
                    "interface_id": "00:00:00:00:00:00:00:01:1",
                    "tag": {
                        "tag_type": 1,
                        "value": 80
                    }
                },
                "uni_z": {
                    "interface_id": "00:00:00:00:00:00:00:02:2",
                    "tag": {
                        "tag_type": 1,
                        "value": 1
                    }
                },
                "circuit_scheduler": [{
                    "id": "1",
                    "frequency": "* * * * *",
                    "action": "create"
                }]
            }
        }
        validate_mock.return_value = True
        save_evc_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        evc_as_dict_mock.return_value = {}
        storehouse_data_mock.return_value = storehouse_payload_1
        scheduler_remove_job_mock.return_value = True

        requested_schedule_id = "1"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule/{requested_schedule_id}'

        # Call URL
        response = api.delete(url)

        self.assertEqual(response.status_code, 200, response.data)
        scheduler_remove_job_mock.assert_called_once()
        save_evc_mock.assert_called_once()
        self.assertIn("Schedule removed", f"{response.data}")

    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.get_data')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_delete_schedule_archived(self, *args):
        """Test create a circuit schedule."""
        (validate_mock, evc_as_dict_mock,
         uni_from_dict_mock, storehouse_data_mock) = args

        storehouse_payload_1 = {
            "2": {
                "id": "2",
                "name": "my evc1",
                "archived": True,
                "circuit_scheduler": [{
                    "id": "1",
                    "frequency": "* * * * *",
                    "action": "create"
                }]
            }
        }

        validate_mock.return_value = True
        uni_from_dict_mock.side_effect = ['uni_a', 'uni_z']
        evc_as_dict_mock.return_value = {}
        storehouse_data_mock.return_value = storehouse_payload_1

        requested_schedule_id = "1"
        api = self.get_app_test_client(self.napp)
        url = f'{self.server_name_url}/v2/evc/schedule/{requested_schedule_id}'

        # Call URL
        response = api.delete(url)

        self.assertEqual(response.status_code, 403, response.data)

    @patch('requests.post')
    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    @patch('kytos.core.Controller.get_interface_by_id')
    @patch('napps.kytos.mef_eline.models.EVCDeploy.deploy')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    def test_update_circuit(self, *args):
        """Test update a circuit circuit."""
        (evc_as_dict_mock, uni_from_dict_mock, evc_deploy, *mocks) = args

        for mock in mocks:
            mock.return_value = True
        unis = [get_uni_mocked(switch_dpid='00:00:00:00:00:00:00:01'),
                get_uni_mocked(switch_dpid='00:00:00:00:00:00:00:02')]
        uni_from_dict_mock.side_effect = 2 * unis

        api = self.get_app_test_client(self.napp)
        payloads = [
            {
                "name": "my evc1",
                "active": True,
                "uni_a": {
                    "interface_id": "00:00:00:00:00:00:00:01:1",
                    "tag": {
                        "tag_type": 1,
                        "value": 80
                    }
                },
                "uni_z": {
                    "interface_id": "00:00:00:00:00:00:00:02:2",
                    "tag": {
                        "tag_type": 1,
                        "value": 1
                    }
                }
            },
            {
                "primary_path": [
                    {
                        "endpoint_a": {"id": "00:00:00:00:00:00:00:01:1"},
                        "endpoint_b": {"id": "00:00:00:00:00:00:00:02:2"}
                    }
                ]
            },
            {
                "priority": 3
            },
            {
                "enable": True
            }
        ]

        evc_as_dict_mock.return_value = payloads[0]
        response = api.post(f'{self.server_name_url}/v2/evc/',
                            data=json.dumps(payloads[0]),
                            content_type='application/json')
        self.assertEqual(201, response.status_code)

        evc_deploy.reset_mock()
        evc_as_dict_mock.return_value = payloads[1]
        current_data = json.loads(response.data)
        circuit_id = current_data['circuit_id']
        response = api.patch(f'{self.server_name_url}/v2/evc/{circuit_id}',
                             data=json.dumps(payloads[1]),
                             content_type='application/json')
        evc_deploy.assert_called_once()
        self.assertEqual(200, response.status_code)

        evc_deploy.reset_mock()
        evc_as_dict_mock.return_value = payloads[2]
        response = api.patch(f'{self.server_name_url}/v2/evc/{circuit_id}',
                             data=json.dumps(payloads[2]),
                             content_type='application/json')
        evc_deploy.assert_not_called()
        self.assertEqual(200, response.status_code)

        evc_deploy.reset_mock()
        response = api.patch(f'{self.server_name_url}/v2/evc/{circuit_id}',
                             data='{"priority":5,}',
                             content_type='application/json')
        evc_deploy.assert_not_called()
        self.assertEqual(400, response.status_code)

        evc_deploy.reset_mock()
        response = api.patch(f'{self.server_name_url}/v2/evc/{circuit_id}',
                             data=json.dumps(payloads[3]),
                             content_type='application/json')
        evc_deploy.assert_called_once()
        self.assertEqual(200, response.status_code)

        response = api.patch(f'{self.server_name_url}/v2/evc/1234',
                             data=json.dumps(payloads[1]),
                             content_type='application/json')
        current_data = json.loads(response.data)
        expected_data = f'circuit_id 1234 not found'
        self.assertEqual(current_data['description'], expected_data)
        self.assertEqual(404, response.status_code)

        api.delete(f'{self.server_name_url}/v2/evc/{circuit_id}')
        evc_deploy.reset_mock()
        response = api.patch(f'{self.server_name_url}/v2/evc/{circuit_id}',
                             data=json.dumps(payloads[1]),
                             content_type='application/json')
        evc_deploy.assert_not_called()
        self.assertEqual(405, response.status_code)

    @patch('napps.kytos.mef_eline.scheduler.Scheduler.add')
    @patch('napps.kytos.mef_eline.main.Main._uni_from_dict')
    @patch('napps.kytos.mef_eline.storehouse.StoreHouse.save_evc')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    @patch('napps.kytos.mef_eline.main.EVC.as_dict')
    def test_update_circuit_invalid_json(self, *args):
        """Test update a circuit circuit."""
        # pylint: disable=too-many-locals
        (evc_as_dict_mock, validate_mock, save_evc_mock,
         uni_from_dict_mock, sched_add_mock) = args

        validate_mock.return_value = True
        save_evc_mock.return_value = True
        sched_add_mock.return_value = True
        uni1 = create_autospec(UNI)
        uni2 = create_autospec(UNI)
        uni1.interface = create_autospec(Interface)
        uni2.interface = create_autospec(Interface)
        uni1.interface.switch = '00:00:00:00:00:00:00:01'
        uni2.interface.switch = '00:00:00:00:00:00:00:02'
        uni_from_dict_mock.side_effect = [uni1, uni2, uni1, uni2]

        api = self.get_app_test_client(self.napp)
        payload1 = {
            "name": "my evc1",
            "uni_a": {
                "interface_id": "00:00:00:00:00:00:00:01:1",
                "tag": {
                    "tag_type": 1,
                    "value": 80
                }
            },
            "uni_z": {
                "interface_id": "00:00:00:00:00:00:00:02:2",
                "tag": {
                    "tag_type": 1,
                    "value": 1
                }
            }
        }

        payload2 = {
            "dynamic_backup_path": True,
        }

        evc_as_dict_mock.return_value = payload1
        response = api.post(f'{self.server_name_url}/v2/evc/',
                            data=json.dumps(payload1),
                            content_type='application/json')
        self.assertEqual(201, response.status_code)

        evc_as_dict_mock.return_value = payload2
        current_data = json.loads(response.data)
        circuit_id = current_data['circuit_id']
        response = api.patch(f'{self.server_name_url}/v2/evc/{circuit_id}',
                             data=payload2,
                             content_type='application/json')
        current_data = json.loads(response.data)
        expected_data = 'The request body is not a well-formed JSON.'
        self.assertEqual(current_data['description'], expected_data)
        self.assertEqual(400, response.status_code)

    def test_handle_link_up(self):
        """Test handle_link_up method."""
        evc_mock = create_autospec(EVC)
        evc_mock.is_enabled = MagicMock(side_effect=[True, False, True])
        type(evc_mock).archived = \
            PropertyMock(side_effect=[True, False, False])
        evcs = [evc_mock, evc_mock, evc_mock]
        event = KytosEvent(name='test', content={'link': 'abc'})
        self.napp.circuits = dict(zip(['1', '2', '3'], evcs))
        self.napp.handle_link_up(event)
        evc_mock.handle_link_up.assert_called_once_with('abc')

    def test_handle_link_down(self):
        """Test handle_link_down method."""
        evc_mock = create_autospec(EVC)
        evc_mock.is_affected_by_link = \
            MagicMock(side_effect=[True, False, True])
        evcs = [evc_mock, evc_mock, evc_mock]
        event = KytosEvent(name='test', content={'link': 'abc'})
        self.napp.circuits = dict(zip(['1', '2', '3'], evcs))
        self.napp.handle_link_down(event)
        evc_mock.handle_link_down.assert_has_calls([call(), call()])
