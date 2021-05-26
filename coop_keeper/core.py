import pytz
import datetime as dt
import logging
import asyncio

#import RPi.GPIO as GPIO

from threading import Thread, Event
from astral import Astral


APP_NAME = "CoopKeeper"


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
        self.coop_time = CoopClock()
        self.triggers = Triggers()
        self.buttons = Buttons(self)
        self.enforce_mode()

    def open_door(self):
        print("open door")

    def close_door(self):
        print("close door")

    def stop_door(self):
        pass

    def blink(self):
        print('blink')

    def set_mode(self):
        pass

    def enforce_mode(self):
        while True:
            print(self.coop_time.current_time)
            Event().wait(1)


class Buttons(Thread):
    """
    listener for button press to change mode
    """
    #GPIO.add_event_detect(GPIOInit.PIN_BUTTON_UP, GPIO.FALLING, callback=self.button_press, bouncetime=200)
    #GPIO.add_event_detect(GPIOInit.PIN_BUTTON_DOWN, GPIO.FALLING, callback=self.button_press, bouncetime=200)

    def __init__(self, coop_keeper):
        Thread.__init__(self)
        self.coop_keeper = coop_keeper
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            logger.info(self.coop_keeper.blink())
            Event().wait(1)


class Triggers(Thread):
    status = None #(GPIO.input(Coop.PIN_SENSOR_BOTTOM), GPIO.input(Coop.PIN_SENSOR_TOP))

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            logger.info('Updating trigger status')
            Event().wait(1)


class CoopClock(Thread):
    a = Astral()
    city = a[Coop.TIMEZONE_CITY]
    sun = city.sun(date=dt.datetime.now(), local=True)
    current_time = None
    open_time = None
    close_time = None

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            self.open_time = self.sun["sunrise"] + dt.timedelta(minutes=Coop.AFTER_SUNRISE_DELAY)
            self.close_time = self.sun["sunset"] + dt.timedelta(minutes=Coop.AFTER_SUNSET_DELAY)
            self.current_time = dt.datetime.now(pytz.timezone(self.city.timezone))
            logger.info('Updating CoopClock current_time={}'.format(self.current_time))
            Event().wait(1)