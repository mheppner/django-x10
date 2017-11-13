from django.db import models
from django.conf import settings
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver
from django.core.cache import cache
from rest_framework.authtoken.models import Token

from x10.lock import cache_lock
from x10.interface import send_command


class InvalidSignalError(Exception):
    pass


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class Unit(models.Model):
    HOUSE_CHOICES = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
        ('F', 'F'),
        ('G', 'G'),
        ('H', 'H'),
        ('I', 'I'),
        ('J', 'J'),
        ('K', 'K'),
        ('L', 'L'),
        ('M', 'M'),
        ('N', 'N'),
        ('O', 'O'),
        ('P', 'P'),
    )

    NUMBER_CHOICES = (
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
        (5, '5'),
        (6, '6'),
        (7, '7'),
        (8, '8'),
        (9, '9'),
        (10, '10'),
        (11, '11'),
        (12, '12'),
        (13, '13'),
        (14, '14'),
        (15, '15'),
        (16, '16'),
    )

    class Meta:
        ordering = ('order',)
        permissions = (
            ('view_unit', 'Can view unit'),
        )

    _previous_state = None

    name = models.CharField(
        max_length=128)
    slug = models.SlugField(
        unique=True)
    number = models.PositiveSmallIntegerField(
        choices=NUMBER_CHOICES)
    house = models.CharField(
        max_length=1,
        choices=HOUSE_CHOICES,
        default='M')
    dimmable = models.BooleanField(
        default=False)
    order = models.PositiveSmallIntegerField(
        default=0,
        editable=False,
        db_index=True)
    state = models.BooleanField(
        default=False)
    auto_managed = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.name

    def send_signal(self, command=None, multiplier=1, attempts=10, sleep_time=0.5):
        """Sends a signal to the unit.

        This uses a lock to prevent multiple messages from being sent at once.
        A command can be specified, but will default to self.state.

        :param command: the command to send to the unit
        :param multiplier: the number of times to send the command
        :param attempts: max number of attempts to try grabbing the lock
        :param sleep_time: how long to wait before checking the lock again
        :raises: CacheLockException
        :raises: InvalidSignalError
        :returns: the status if the command was sent
        """
        status = True
        if command is None:
            command = 'on' if self.state else 'off'

        command = command.lower()
        if command not in ('on', 'off', 'brt', 'dim'):
            raise InvalidSignalError(f'the command {command} does not exist')

        if (command == 'brt' or command == 'dim') and not self.dimmable:
            raise InvalidSignalError(f'the {command} command cannot be sent to this device')

        with cache_lock('x10_interface', attempts, sleep_time):
            for i in range(0, multiplier):
                status = status and send_command(
                    settings.X10_SERIAL,
                    self.house,
                    self.number,
                    command)
        return status

    @staticmethod
    def post_init(sender, instance, **kwargs):
        instance._previous_state = instance.state

    @staticmethod
    def post_save(sender, instance, **kwargs):
        # check if the state is different and send the signal
        if instance._previous_state != instance.state:
            instance.send_signal()


post_save.connect(Unit.post_save, sender=Unit)
post_init.connect(Unit.post_init, sender=Unit)


class Scene(models.Model):

    class Meta:
        ordering = ('name',)

    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    units = models.ManyToManyField(Unit)

    def __str__(self):
        return self.name
