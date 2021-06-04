import uvicorn
import RPi.GPIO as GPIO

from .core import Coop, CoopKeeper, GPIOInit
from fastapi import FastAPI, Header, Request, Response
from pydantic import BaseModel


class App(FastAPI):
    app = FastAPI(
        title="CoopKeeper API",
        description="RestAPI for CoopKeeper",
        version="0.1a",
    )
    ck = CoopKeeper()


app = App()


def get_app():
    return app


@app.get("/api/v1/door/{door_action}")
async def door(
        door_action: str,
        request: Request,
        response: Response,
    ):
    if door_action == 'open':
        app.ck.set_mode(Coop.MANUAL)
        result = app.ck.open_door()
    elif door_action == 'close':
        app.ck.set_mode(Coop.MANUAL)
        result = app.ck.close_door()
    elif door_action == 'auto':
        result = app.ck.set_mode(Coop.AUTO)
    else:
        response.status_code = 400
        return {"result": "invalid action requested"}
    return {"result": result}


def main():
    #uvicorn.run("start:app", host="0.0.0.0", port=5005, reload=True, log_level='info')
    get_app()
    GPIO.output(GPIOInit.PIN_LED, GPIO.LOW)
    app.ck.stop_door()