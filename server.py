import os
import sys
import time
import pytz
import datetime
import logging
import glob
import uvicorn
#import RPi.GPIO as GPIO
import _thread as thread


from threading import Thread
from astral import Astral
from fastapi import FastAPI, Header, Request, Response
from pydantic import BaseModel


app = FastAPI(
    title="CoopKeeper API",
    description="RestAPI for CoopKeeper",
    version="0.1a",
)

APP_NAME = "CoopKeeper"
WEBHOOK_SECRET = "My precious"


@app.get("/")
def read_root():
    return {"Hello": "World"}


class Coop:
    MAX_MANUAL_MODE_TIME = 60 * 60
    MAX_MOTOR_ON = 45
    TIMEZONE_CITY = 'Seattle'
    AFTER_SUNSET_DELAY = 0
    AFTER_SUNRISE_DELAY = -15
    SECOND_CHANCE_DELAY = 60 * 10
    IDLE = UNKNOWN = NOT_TRIGGERED = AUTO = 0
    UP = OPEN = TRIGGERED = MANUAL = 1
    DOWN = CLOSED = HALT = 2

    PIN_LED = 5
    PIN_BUTTON_UP = 4
    PIN_BUTTON_DOWN = 22
    PIN_SENSOR_TOP = 13
    PIN_SENSOR_BOTTOM = 16
    PIN_MOTOR_ENABLE = 25
    PIN_MOTOR_A = 24
    PIN_MOTOR_B = 23
    """
    def setupPins(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(Coop.PIN_MOTOR_ENABLE, GPIO.OUT)
        GPIO.setup(Coop.PIN_MOTOR_A, GPIO.OUT)
        GPIO.setup(Coop.PIN_MOTOR_B, GPIO.OUT)
        GPIO.setup(Coop.PIN_LED, GPIO.OUT)
        GPIO.setup(Coop.PIN_SENSOR_BOTTOM, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(Coop.PIN_SENSOR_TOP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(Coop.PIN_BUTTON_UP, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(Coop.PIN_BUTTON_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    """

class CoopKeeper:
    def __init__(self):
        self.door_status = Coop.UNKNOWN
        self.started_motor = None
        self.direction = Coop.IDLE
        self.door_mode = Coop.AUTO
        self.manual_mode_start = 0
        coop_time = CoopTime()

        uvicorn.run("server:app", host="0.0.0.0", port=5005, reload=True, log_level='info')


    def open_door(self):
        pass

    def close_door(self):
        pass

    def stop_door(self):
        pass

    def blink(self):
        pass

    def button_press(self):
        pass

    def check_triggers(self):
        pass

    def set_mode(self):
        pass


class CoopTime:

    a = Astral()
    city = a[Coop.TIMEZONE_CITY]

    def __init__(self):
        self.current_time = None
        self.open_time = None
        self.close_time = None
        t = Thread(target = self.check_time)
        t.setDaemon(True)
        t.start()

    def check_time(self):
        while True:
            self.current_time = datetime.datetime.now(pytz.timezone(self.city.timezone))
            sun = self.city.sun(date=datetime.datetime.now(), local=True)
            self.open_time = sun["sunrise"] + datetime.timedelta(minutes=Coop.AFTER_SUNRISE_DELAY)
            self.close_time = sun["sunset"] + datetime.timedelta(minutes=Coop.AFTER_SUNSET_DELAY)
            CoopLogger.log_info('Updating time for location: {}'.format(CoopTime.city))
            time.sleep(3600)


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


if __name__ == "__main__":
    CoopKeeper()