"""Module responsible to handle schedules."""
import time
from pytz import utc

from uuid import uuid4
from apscheduler.schedulers.background import BackgroundScheduler

from apscheduler.triggers.cron import CronTrigger
from kytos.core.helpers import now
from kytos.core import log


class CircuitSchedule:
    """Schedule events."""

    def __init__(self, **kwargs):
        """CircuitSchedule contructor."""
        self._id = kwargs.get('id', uuid4().hex)
        self.date  = kwargs.get('date', None)
        self.interval = kwargs.get('interval', None)
        self.frequency  = kwargs.get('frequency', None)
        self.action = kwargs.get('action', 'create')

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return this EVC's ID."""
        return self._id

    def as_dict(self):
        """A dictionary representing an circuit schedule object."""
        circuit_schedule_dict = {'id': self.id, 'action': self.action}

        if self.date:
            circuit_schedule_dict['date'] = self.date
        if self.frequency:
            circuit_schedule_dict['frequency'] = self.frequency
        if self.interval:
            circuit_schedule_dict['interval'] = self.interval

        return circuit_schedule_dict

    @classmethod
    def from_dict(cls, data):
        """Return a CircuitSchedule object from dict."""
        return cls(**data)

class Scheduler:
    """Class to schedule the circuits rules."""

    def __init__(self):
        """Initialize the schedule structure."""
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdoown(wait=False)

    def add(self, circuit):
        """Add all circuit_schedule from specific circuit."""
        for circuit_schedule in circuit.circuit_rules:
            data = {'id': circuit_schedule.id}
            action = None

            if circuit_schedule.action == 'create':
                action = circuit.deploy
            elif circuit_schedule.action == 'remove':
                action = circuit.remove

            if circuit_schedule.date:
                data.update({'run_time': circuit_schedule.date,
                             'start_date': circuit.start_date,
                             'end_date': circuit.end_date})
                self.scheduler.add_job(action, 'date', **data)

            if circuit_schedule.interval:
                data = data.update(circuit_schedule.interval)
                self.scheduler.add_job(action, 'interval', **data)

            if circuit_schedule.frequency:
                cron = CronTrigger.from_crontab(circuit_schedule.frequency)
                self.scheduler.add_job(action, cron, **data)


    def cancel_job(self, circuit_schedule_id):
        """Cancel a specific job from scheduler."""
        self.scheduler.remove_job(circuit_schedule_id)
