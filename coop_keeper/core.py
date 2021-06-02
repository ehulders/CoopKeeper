from typing import MutableSequence
import pytz
import time
import datetime as dt
import logging
import asyncio

import RPi.GPIO as GPIO

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


class CoopKeeper(Thread):
    def __init__(self):
        self.t = Thread.__init__(self)
        self.door_status = Coop.UNKNOWN
        self.started_motor = None
        self.direction = Coop.IDLE
        self.door_mode = Coop.AUTO
        self.manual_mode_start = 0
        GPIOInit()
        self.coop_time = CoopClock()
        self.triggers = Triggers()
        self.buttons = Buttons(self)
        #self.blink = Blink(self)
        #self.setDaemon(True)
        #self.start()

    def close_door(self):
        top, bottom = self.triggers.get_status()
        if bottom == Coop.TRIGGERED:
            msg = "Door is already closed"
            logger.info(msg)
            return msg
        msg = "Closing door"
        logger.info(msg)
        self.started_motor = dt.datetime.now()
        GPIO.output(GPIOInit.PIN_MOTOR_ENABLE, GPIO.HIGH)
        GPIO.output(GPIOInit.PIN_MOTOR_A, GPIO.LOW)
        GPIO.output(GPIOInit.PIN_MOTOR_B, GPIO.HIGH)
        self.direction = Coop.DOWN
        return msg

    def open_door(self):
        top, bottom = self.triggers.get_status()
        if top == Coop.TRIGGERED:
            msg = "Door is already open"
            logger.info(msg)
            return msg
        msg = "Opening door"
        logger.info(msg)
        self.started_motor = dt.datetime.now()
        GPIO.output(GPIOInit.PIN_MOTOR_ENABLE, GPIO.HIGH)
        GPIO.output(GPIOInit.PIN_MOTOR_A, GPIO.HIGH)
        GPIO.output(GPIOInit.PIN_MOTOR_B, GPIO.LOW)
        self.direction= Coop.UP
        return msg

    def stop_door(self, delay=0):
        if self.direction != Coop.IDLE:
            logger.info("Stop door")
            time.sleep(delay)
            GPIO.output(GPIOInit.PIN_MOTOR_ENABLE, GPIO.LOW)
            GPIO.output(GPIOInit.PIN_MOTOR_A, GPIO.LOW)
            GPIO.output(GPIOInit.PIN_MOTOR_B, GPIO.LOW)
            self.direction = Coop.IDLE
            self.started_motor = None

        top, bottom = self.triggers.get_status()
        if top == Coop.TRIGGERED:
            logger.info("Door is open")
            self.door_status = Coop.OPEN
        elif bottom == Coop.TRIGGERED:
            logger.info("Door is closed")
            self.door_status = Coop.CLOSED
        else:
            logger.info("Door is in an unknown state")
            self.door_status = Coop.UNKNOWN
            payload = {'status': self.door_status, 'ts': dt.datetime.now() }

    def set_mode(self, mode):
        if mode == Coop.AUTO:
            self.door_mode = Coop.AUTO
            msg = "Entering auto mode"
            logger.info(msg)
        else:
            self.door_mode = Coop.MANUAL
            msg = "Entering manul mode"
            logger.info(msg)
        return msg

    def run(self):
        while True:
            print(self.coop_time.current_time)
            Event().wait(1)


class Blink(Thread):
    def __init__(self, ck):
        Thread.__init__(self)
        self.ck = ck
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            if self.ck.door_mode == Coop.MANUAL:
                print('blink...')
            Event().wait(1)


class Buttons:
    def __init__(self, kp):
        self.kp = kp
        GPIO.add_event_detect(GPIOInit.PIN_BUTTON_UP, GPIO.FALLING, callback=self.press, bouncetime=200)
        GPIO.add_event_detect(GPIOInit.PIN_BUTTON_DOWN, GPIO.FALLING, callback=self.press, bouncetime=200)

    def press(self, button):
        start = int(round(time.time() * 1000))
        while GPIO.input(button) == 0:
            pass
        end = int(round(time.time() * 1000))
        if end - start > 4000:
            if self.door_mode == Coop.AUTO:
                self.kp.set_mode(Coop.MANUAL)
            else:
                self.kp.set_mode(Coop.AUTO)

        if self.kp.door_mode == Coop.MANUAL:
            if end - start < 4000:
                if self.kp.direction != Coop.IDLE:
                    self.kp.stop_door(0)
                elif button == Coop.PIN_BUTTON_UP:
                    self.kp_open_door()
                else:
                    self.kp.close_door()       


class Triggers(Thread):
    bottom, top = None, None #(GPIO.input(Coop.PIN_SENSOR_BOTTOM), GPIO.input(Coop.PIN_SENSOR_TOP))

    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    def get_status(self):
        return GPIO.input(GPIOInit.PIN_SENSOR_BOTTOM), GPIO.input(GPIOInit.PIN_SENSOR_TOP)

    def run(self):
        while True:
            # bottom, top = None, None #(GPIO.input(Coop.PIN_SENSOR_BOTTOM), GPIO.input(Coop.PIN_SENSOR_TOP))
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
            #logger.info('Updating CoopClock current_time={}'.format(self.current_time))
            Event().wait(1)
