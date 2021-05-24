import pytz
import datetime as dt
import logging

#import RPi.GPIO as GPIO

from threading import Thread, Event
from astral import Astral


APP_NAME = "CoopKeeper"


class Coop:
    MAX_MANUAL_MODE_TIME = 60
    MAX_MOTOR_ON = 45
    TIMEZONE_CITY = 'Seattle'
    AFTER_SUNSET_DELAY = 0
    AFTER_SUNRISE_DELAY = 0
    IDLE = UNKNOWN = AUTO = 0
    UP = OPEN = TRIGGERED = MANUAL = 1
    DOWN = CLOSED = HALT = 2


class GPIOInit:
    PIN_LED = 5
    PIN_BUTTON_UP = 4
    PIN_BUTTON_DOWN = 22
    PIN_SENSOR_TOP = 13
    PIN_SENSOR_BOTTOM = 16
    PIN_MOTOR_ENABLE = 25
    PIN_MOTOR_A = 24
    PIN_MOTOR_B = 23
"""
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIOInit.PIN_MOTOR_ENABLE, GPIO.OUT)
        GPIO.setup(GPIOInit.PIN_MOTOR_A, GPIO.OUT)
        GPIO.setup(GPIOInit.PIN_MOTOR_B, GPIO.OUT)
        GPIO.setup(GPIOInit.PIN_LED, GPIO.OUT)
        GPIO.setup(GPIOInit.PIN_SENSOR_BOTTOM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(GPIOInit.PIN_SENSOR_TOP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(GPIOInit.PIN_BUTTON_UP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(GPIOInit.PIN_BUTTON_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
"""

class CoopKeeper:
    def __init__(self):
        self.door_status = Coop.UNKNOWN
        self.started_motor = None
        self.direction = Coop.IDLE
        self.door_mode = Coop.AUTO
        self.manual_mode_start = 0
        self.coop_time = CoopTime()
        #self.triggers = Triggers()

    def open_door(self):
        print("open door")

    def close_door(self):
        print("close door")

    def stop_door(self):
        pass

    def blink(self):
        pass

    def set_mode(self):
        pass

"""
class Buttons:

    def __init__(self):
        GPIO.add_event_detect(GPIOInit.PIN_BUTTON_UP, GPIO.FALLING, callback=self.button_press, bouncetime=200)
        GPIO.add_event_detect(GPIOInit.PIN_BUTTON_DOWN, GPIO.FALLING, callback=self.button_press, bouncetime=200)

    def button_press(self):
        pass
"""

class Triggers(Thread):
    status = None #(GPIO.input(Coop.PIN_SENSOR_BOTTOM), GPIO.input(Coop.PIN_SENSOR_TOP))

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def run(self):
        while not Event().wait(1):
            print('checking triggers')


class CoopTime(Thread):
    a = Astral()
    city = a[Coop.TIMEZONE_CITY]
    current_time = dt.datetime.now()
    open_time = None
    close_time = None

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def run(self):
        while not Event().wait(5):
            sun = self.city.sun(date=dt.datetime.now(), local=True)
            self.open_time = sun["sunrise"] + dt.timedelta(minutes=Coop.AFTER_SUNRISE_DELAY)
            self.close_time = sun["sunset"] + dt.timedelta(minutes=Coop.AFTER_SUNSET_DELAY)
            self.current_time = dt.datetime.now(pytz.timezone(self.city.timezone))


class CoopLogger:
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler('/tmp/{}.log'.format(APP_NAME))
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

    @classmethod
    def log_info(cls, message):
        cls.logger.info(message)

    @classmethod
    def log_error(cls, message):
        cls.logger.error(message)

    @classmethod
    def log_debug(cls, message):
        cls.logger.debug(message)