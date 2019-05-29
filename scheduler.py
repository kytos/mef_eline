"""Module responsible to handle schedulers."""
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import utc


class CircuitSchedule:
    """Schedule events."""

    def __init__(self, **kwargs):
        """Create a CircuitSchedule object."""
        self._id = kwargs.get('id', uuid4().hex)
        self.date = kwargs.get('date', None)
        self.interval = kwargs.get('interval', None)
        self.frequency = kwargs.get('frequency', None)
        self.action = kwargs.get('action', 'create')

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return this EVC's ID."""
        return self._id

    def as_dict(self):
        """Return a dictionary representing an circuit schedule object."""
        circuit_scheduler_dict = {'id': self.id, 'action': self.action}

        if self.date:
            circuit_scheduler_dict['date'] = self.date
        if self.frequency:
            circuit_scheduler_dict['frequency'] = self.frequency
        if self.interval:
            circuit_scheduler_dict['interval'] = self.interval

        return circuit_scheduler_dict

    @classmethod
    def from_dict(cls, data):
        """Return a CircuitSchedule object from dict."""
        return cls(**data)


class Scheduler:
    """Class to schedule the circuits rules."""

    def __init__(self):
        """Create a new schedule structure."""
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=False)

    def add(self, circuit):
        """Add all circuit_scheduler from specific circuit."""
        for circuit_scheduler in circuit.circuit_scheduler:
            data = {'id': circuit_scheduler.id}
            action = None

            if circuit_scheduler.action == 'create':
                action = circuit.schedule_deploy
            elif circuit_scheduler.action == 'remove':
                action = circuit.schedule_remove

            if circuit_scheduler.date:
                data.update({'run_date': circuit_scheduler.date})
                self.scheduler.add_job(action, 'date', **data)
            else:
                data.update({'start_date': circuit.start_date,
                             'end_date': circuit.end_date})

            if circuit_scheduler.interval:
                data.update(circuit_scheduler.interval)
                self.scheduler.add_job(action, 'interval', **data)

            elif circuit_scheduler.frequency:
                cron = CronTrigger.from_crontab(circuit_scheduler.frequency,
                                                timezone=utc)
                self.scheduler.add_job(action, cron, **data)

    def cancel_job(self, circuit_scheduler_id):
        """Cancel a specific job from scheduler."""
        self.scheduler.remove_job(circuit_scheduler_id)
