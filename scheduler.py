"""Module responsible for handling schedulers."""
from uuid import uuid4

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import utc

from kytos.core import log


class CircuitSchedule:
    """Schedule events."""

    def __init__(self, **kwargs):
        """Create a CircuitSchedule object."""
        self._id = kwargs.get('id', uuid4().hex)
        self.date = kwargs.get('date', None)
        # The minimum number of seconds to wait between retries
        self.interval = kwargs.get('interval', None)
        # Frequency uses Cron format. Ex: "* * * * * *"
        self.frequency = kwargs.get('frequency', None)
        self.action = kwargs.get('action', 'create')

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return this EVC's ID."""
        return self._id

    @id.setter
    def id(self, value):  # pylint: disable=invalid-name
        """Set this EVC's ID."""
        self._id = value

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
    """Class to schedule the circuits rules.

    It is responsible to create/remove schedule jobs based on
    Circuit Schedules.
    """

    def __init__(self):
        """Create a new schedule structure."""
        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.start()

    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=False)

    def add(self, circuit):
        """
        Add all circuit_scheduler from specific circuit.

        Args:
            circuit (napps.kytos.mef_eline.models.EVCBase): EVC circuit

        """
        for circuit_scheduler in circuit.circuit_scheduler:
            self.add_circuit_job(circuit, circuit_scheduler)

    def remove(self, circuit):
        """Remove all scheduler from a circuit."""
        for job in circuit.circuit_scheduler:
            self.cancel_job(job.id)

    def add_circuit_job(self, circuit, circuit_scheduler):
        """
        Prepare the Circuit data to be added to the Scheduler.

        :param circuit(napps.kytos.mef_eline.models.EVCBase): EVC circuit
        :param circuit_scheduler (CircuitSchedule): Circuit schedule data
        :return:
        """
        if circuit_scheduler.action == 'create':
            job_call = circuit.deploy
        elif circuit_scheduler.action == 'remove':
            job_call = circuit.remove
        else:
            return

        data = {'id': circuit_scheduler.id}
        if circuit_scheduler.date:
            data.update({'run_date': circuit_scheduler.date})
        else:
            data.update({'start_date': circuit.start_date,
                         'end_date': circuit.end_date})

        if circuit_scheduler.interval:
            data.update(circuit_scheduler.interval)

        self.add_job(circuit_scheduler, job_call, data)

    def add_job(self, circuit_scheduler, job_call, data):
        """
        Add a specific cron job to the scheduler.

        Args:
            circuit_scheduler: CircuitSchedule object
            job_call: function to be called by the job
            data: Dict to pass to the job_call as parameter
                if job_call is a date, the template is like:
                 {'id': <ID>, 'run_date': date } or
                 {'id': <ID>, 'start_date': date, 'end_date': date }
                if job_call is an interval, the template is like:
                    {   'id': <ID>,
                        'hours': 2,
                        'minutes': 3
                    }
                if job_call is frequency, the template is the cron format.

        """
        if circuit_scheduler.date:
            self.scheduler.add_job(job_call, 'date', **data)

        elif circuit_scheduler.interval:
            self.scheduler.add_job(job_call, 'interval', **data)

        elif circuit_scheduler.frequency:
            cron = CronTrigger.from_crontab(circuit_scheduler.frequency,
                                            timezone=utc)
            self.scheduler.add_job(job_call, cron, **data)

    def cancel_job(self, circuit_scheduler_id):
        """Cancel a specific job from scheduler."""
        try:
            self.scheduler.remove_job(circuit_scheduler_id)
        except JobLookupError as job_error:
            # Job was not found... Maybe someone already remove it.
            log.error("Scheduler error cancelling job. %s" % job_error)
