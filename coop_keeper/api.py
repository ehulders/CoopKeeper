
import uvicorn

from .core import CoopKeeper
from fastapi import FastAPI, Header, Request, Response
from pydantic import BaseModel


ck = CoopKeeper()

app = FastAPI(
    title="CoopKeeper API",
    description="RestAPI for CoopKeeper",
    version="0.1a",
)


@app.get("/door/{door_action}")
async def door(
        door_action: str,
        request: Request,
        response: Response,
    ):
    if door_action == 'open':
        ck.open_door()
    elif door_action == 'close':
        ck.close_door()
    else:
        response.status_code = 400
        return {"result": "invalid action requested"}
    return {"result": "ok"}


def main():
    uvicorn.run("start:app", host="0.0.0.0", port=5005, reload=True, log_level='info')