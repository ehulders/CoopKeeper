import os
import sys
import hmac
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


@app.get("/door/{door_action}")
async def door(
        door_action: str,
        request: Request,
        response: Response,
    ):
    if door_action == 'open':
        CoopKeeper.open_door()
    elif door_action == 'close':
        CoopKeeper.close_door()
    else:
        response.status_code = 400
        CoopLogger.log_info("invalid action requested")
        return {"result": "invalid action requested"}
    return {"result": "ok"}


class Coop:
    MAX_MANUAL_MODE_TIME = 60
    MAX_MOTOR_ON = 45
    TIMEZONE_CITY = 'Seattle'
    AFTER_SUNSET_DELAY = 0
    AFTER_SUNRISE_DELAY = -15
    IDLE = UNKNOWN = AUTO = 0
    UP = OPEN = TRIGGERED = MANUAL = 1
    DOWN = CLOSED = HALT = 2

    """
    PIN_LED = 5
    PIN_BUTTON_UP = 4
    PIN_BUTTON_DOWN = 22
    PIN_SENSOR_TOP = 13
    PIN_SENSOR_BOTTOM = 16
    PIN_MOTOR_ENABLE = 25
    PIN_MOTOR_A = 24
    PIN_MOTOR_B = 23
    
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
        triggers = Triggers()

        uvicorn.run("server:app", host="0.0.0.0", port=5005, reload=True, log_level='info')

    @classmethod
    def open_door(cls):
        print("open door")

    @classmethod
    def close_door(cls):
        print("close door")

    @classmethod
    def stop_door(cls):
        pass

    def blink(self):
        pass

    def button_press(self):
        pass

    def set_mode(self):
        pass


class Triggers:

    def __init__(self):
        t = Thread(target = self.monitor_triggers)
        t.setDaemon(True)
        t.start()

    def monitor_triggers(self):
        while True:
            time.sleep(1)


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
            CoopLogger.log_info('Checking time for location: {}'.format(CoopTime.city))
            time.sleep(7200)


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