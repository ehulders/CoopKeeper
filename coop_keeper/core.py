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
    MAX_MANUAL_MODE_TIME = 60 * 10
    MAX_MOTOR_ON = 30
    TIMEZONE_CITY = 'Seattle'
    AFTER_SUNSET_DELAY = 15
    AFTER_SUNRISE_DELAY = 30
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


class CoopKeeper:
    def __init__(self):
        GPIOInit()
        self.door_status = Coop.UNKNOWN
        self.started_motor = None
        self.direction = Coop.IDLE
        self.door_mode = Coop.AUTO
        self.manual_mode_start = 0
        self.buttons = Buttons(self)
        self.triggers = Triggers(self)
        self.coop_time = CoopClock(self)
        self.set_mode(Coop.AUTO)
        self.stop_door(0)

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
            payload = {'status': self.door_status, 'ts': dt.datetime.now()}

    def emergency_stop(self, reason):
        logger.info("Emergency Stop door: {}".format(reason))
        GPIO.output(GPIOInit.PIN_MOTOR_ENABLE, GPIO.LOW)
        GPIO.output(GPIOInit.PIN_MOTOR_A, GPIO.LOW)
        GPIO.output(GPIOInit.PIN_MOTOR_B, GPIO.LOW)
        self.direction = Coop.IDLE
        self.started_motor = None
        self.set_mode(Coop.HALT)
        self.stop_door(0)

    def set_mode(self, new_mode):
        if new_mode == Coop.AUTO:
            msg = "Entering auto mode"
            logger.info(msg)
            self.door_mode = Coop.AUTO
            GPIO.output(GPIOInit.PIN_LED, GPIO.HIGH)
        else:
            msg = "Entering manual mode"
            logger.info(msg)
            self.door_mode = new_mode
            self.manual_mode_start = int(time.time())
            Blink(self)
        return msg


class Blink(Thread):
    def __init__(self, ck):
        Thread.__init__(self)
        self.ck = ck
        self.setDaemon(True)
        self.start()

    def run(self):
        while(self.ck.door_mode != Coop.AUTO):
            GPIO.output(GPIOInit.PIN_LED, GPIO.LOW)
            Event().wait(1)
            GPIO.output(GPIOInit.PIN_LED, GPIO.HIGH)
            Event().wait(1)
            if self.ck.door_mode == Coop.MANUAL: 
                if int(time.time()) - self.ck.manual_mode_start > Coop.MAX_MANUAL_MODE_TIME:
                    logger.info("In manual mode too long, switching to auto")
                    self.ck.set_mode(Coop.AUTO)


class Buttons:
    def __init__(self, ck):
        self.ck = ck
        GPIO.add_event_detect(GPIOInit.PIN_BUTTON_UP, GPIO.FALLING, callback=self.press, bouncetime=200)
        GPIO.add_event_detect(GPIOInit.PIN_BUTTON_DOWN, GPIO.FALLING, callback=self.press, bouncetime=200)

    def press(self, button):
        start = int(round(time.time() * 1000))
        while GPIO.input(button) == 0:
            pass
        end = int(round(time.time() * 1000))
        if end - start > 4000:
            if self.ck.door_mode == Coop.AUTO:
                self.ck.set_mode(Coop.MANUAL)
            else:
                self.ck.set_mode(Coop.AUTO)
        if self.ck.door_mode == Coop.MANUAL:
            if end - start < 4000:
                if self.ck.direction != Coop.IDLE:
                    self.ck.stop_door(0)
                elif button == GPIOInit.PIN_BUTTON_UP:
                    self.ck.open_door()
                else:
                    self.ck.close_door()


class Triggers(Thread):

    def __init__(self, ck):
        Thread.__init__(self)
        self.ck = ck
        self.setDaemon(True)
        self.start()

    def get_status(self):
        return GPIO.input(GPIOInit.PIN_SENSOR_TOP), GPIO.input(GPIOInit.PIN_SENSOR_BOTTOM)

    def run(self):
        while True:
            top, bottom = self.get_status()

            if self.ck.direction == Coop.UP and top == Coop.TRIGGERED:
                logger.info("Top sensor triggered")
                self.ck.stop_door(1.5)

            if self.ck.direction == Coop.DOWN and bottom == Coop.TRIGGERED:
                logger.info("Bottom sensor triggered")
                self.ck.stop_door(4)

            if self.ck.started_motor is not None:
                if (dt.datetime.now() - self.ck.started_motor).seconds > Coop.MAX_MOTOR_ON:
                    self.ck.emergency_stop('Motor ran too long')

            Event().wait(1)


class CoopClock(Thread):
    a = Astral()
    city = a[Coop.TIMEZONE_CITY]

    def __init__(self, ck):
        Thread.__init__(self)
        self.current_time = None
        self.open_time = None
        self.close_time = None
        self.ck = ck
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            if self.ck.door_mode == Coop.AUTO:
                sun = self.city.sun(date=dt.datetime.now(), local=True)
                self.open_time = sun["sunrise"] + dt.timedelta(minutes=Coop.AFTER_SUNRISE_DELAY)
                self.close_time = sun["sunset"] + dt.timedelta(minutes=Coop.AFTER_SUNSET_DELAY)
                self.current_time = dt.datetime.now(pytz.timezone(self.city.timezone))

                if (self.current_time < self.open_time or self.current_time > self.close_time) \
                        and self.ck.door_status != Coop.CLOSED and self.ck.direction != Coop.DOWN:
                    logger.info("Door should be closed based on time of day")
                    self.ck.close_door()

                elif self.current_time > self.open_time and self.current_time < self.close_time \
                        and self.ck.door_status != Coop.OPEN and self.ck.direction != Coop.UP:
                    logger.info("Door should be open based on time of day")
                    self.ck.open_door()
            Event().wait(1)
