"""Module to test the schedule.py file."""
import datetime
from unittest import TestCase
from unittest.mock import patch

from apscheduler.triggers.cron import CronTrigger
from pytz import utc

from napps.kytos.mef_eline.models import EVC
from napps.kytos.mef_eline.scheduler import CircuitSchedule, Scheduler
from tests.helpers import get_controller_mock


class TestCircuitSchedule(TestCase):
    """Tests to verify circuit_schedule class."""

    def test_id(self):
        """Test method id with different values."""
        self.assertNotEqual(CircuitSchedule().id, CircuitSchedule().id)

    def test_with_date(self):
        """Test create circuit schedule with date."""
        time_fmt = "%Y-%m-%dT%H:%M:%S"
        options = {
            "action": "create",
            "date": datetime.datetime.now().strftime(time_fmt)
        }
        circuit_schedule = CircuitSchedule(**options)
        self.assertEqual("create", circuit_schedule.action)
        self.assertEqual(options["date"], circuit_schedule.date)

    def test_with_interval(self):
        """Test create circuit schedule with interval."""
        options = {
            "action": "create",
            "interval": {
                "hours": 2
            }
        }
        circuit_schedule = CircuitSchedule(**options)
        self.assertEqual("create", circuit_schedule.action)
        self.assertEqual(options["interval"], circuit_schedule.interval)

    def test_with_frequency(self):
        """Test create circuit schedule with frequency."""
        options = {
            "action": "create",
            "frequency": "1 * * * *"
        }
        circuit_schedule = CircuitSchedule(**options)
        self.assertEqual("create", circuit_schedule.action)
        self.assertEqual(options["frequency"], circuit_schedule.frequency)

    def test_from_dict(self):
        """Test create circuit schedule from dict."""
        circuit_schedule_dict = {
            "id": 52342432,
            "action": "create",
            "frequency": "1 * * * *"
        }
        circuit_schedule = CircuitSchedule.from_dict(circuit_schedule_dict)
        self.assertEqual(circuit_schedule.id, circuit_schedule_dict["id"])
        self.assertEqual(circuit_schedule.action,
                         circuit_schedule_dict["action"])
        self.assertEqual(circuit_schedule.frequency,
                         circuit_schedule_dict["frequency"])

    def test_as_dict(self):
        """Test method as_dict from circuit_schedule."""
        options = {
            "id": 234243242,
            "action": "create",
            "frequency": "1 * * * *"
        }
        circuit_schedule_dict = CircuitSchedule(**options).as_dict()
        self.assertEqual(options, circuit_schedule_dict)


class TestScheduler(TestCase):
    """Class to test the structure Schedule."""

    def setUp(self):
        """Procedure executed before each test."""
        self.scheduler = Scheduler()

    def tearDown(self):
        """Proedure executed after each test."""
        self.scheduler.shutdown()

    @patch('apscheduler.schedulers.background.BackgroundScheduler.add_job')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_new_circuit_with_run_time(self, validate_mock,
                                       scheduler_add_job_mock):
        """Test if add new circuit with run_time."""
        scheduler_add_job_mock.return_value = True
        validate_mock.return_value = True
        time_fmt = "%Y-%m-%dT%H:%M:%S"
        date = datetime.datetime.now().strftime(time_fmt)
        circuit_scheduler = CircuitSchedule(action="remove", date=date)
        options = {"controller": get_controller_mock(),
                   "name": 'my evc1',
                   "uni_a": 'uni_a',
                   "uni_z": 'uni_z',
                   "circuit_scheduler": [circuit_scheduler]
                   }
        evc = EVC(**options)
        self.scheduler.add(evc)
        expected_parameters = {
            "id": circuit_scheduler.id,
            "run_date": circuit_scheduler.date,
            }
        scheduler_add_job_mock.assert_called_once_with(evc.remove, 'date',
                                                       **expected_parameters)

    @patch('apscheduler.schedulers.background.BackgroundScheduler.add_job')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_new_circuit_with_interval(self, validate_mock,
                                       scheduler_add_job_mock):
        """Test if add new circuit with interval."""
        scheduler_add_job_mock.return_value = True
        validate_mock.return_value = True
        interval = {
            'hours': 2,
            'minutes': 3
        }
        circuit_scheduler = CircuitSchedule(action="create", interval=interval)
        options = {"controller": get_controller_mock(),
                   "name": 'my evc1',
                   "uni_a": 'uni_a',
                   "uni_z": 'uni_z',
                   "start_date": "2019-08-09T19:25:06",
                   "circuit_scheduler": [circuit_scheduler]
                   }
        evc = EVC(**options)
        self.scheduler.add(evc)

        expected_parameters = {
            "id": circuit_scheduler.id,
            "hours": 2,
            "minutes": 3,
            "end_date": None,
            "start_date": datetime.datetime(
                2019, 8, 9, 19, 25, 6, 0, tzinfo=datetime.timezone.utc)
        }
        scheduler_add_job_mock.assert_called_once_with(evc.deploy, 'interval',
                                                       **expected_parameters)

    @patch('apscheduler.triggers.cron.CronTrigger.from_crontab')
    @patch('apscheduler.schedulers.background.BackgroundScheduler.add_job')
    @patch('napps.kytos.mef_eline.models.EVC._validate')
    def test_new_circuit_with_frequency(self, validate_mock,
                                        scheduler_add_job_mock,
                                        trigger_mock):
        """Test if add new circuit with frequency."""
        scheduler_add_job_mock.return_value = True
        validate_mock.return_value = True

        frequency = "* * * * *"
        circuit_scheduler = CircuitSchedule(action="create",
                                            frequency=frequency)

        trigger = CronTrigger.from_crontab(circuit_scheduler.frequency,
                                           timezone=utc)
        trigger_mock.return_value = trigger

        options = {"controller": get_controller_mock(),
                   "name": 'my evc1',
                   "uni_a": 'uni_a',
                   "uni_z": 'uni_z',
                   "start_date": "2019-08-09T19:25:06",
                   "circuit_scheduler": [circuit_scheduler]
                   }
        evc = EVC(**options)
        self.scheduler.add(evc)
        expected_parameters = {
            "id": circuit_scheduler.id,
            "end_date": None,
            "start_date": datetime.datetime(
                2019, 8, 9, 19, 25, 6, 0, tzinfo=datetime.timezone.utc)
        }
        scheduler_add_job_mock.assert_called_once_with(evc.deploy, trigger,
                                                       **expected_parameters)
