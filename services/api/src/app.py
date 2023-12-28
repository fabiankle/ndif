import logging
from datetime import datetime
from typing import Dict
from uuid import uuid4

import socketio
import uvicorn
from bson.objectid import ObjectId
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_socketio import SocketManager
from pymongo import MongoClient

from .celery import celeryconfig
from .celery.tasks import app as celery_app
from .celery.tasks import process_request
from .pydantics import RequestModel, ResponseModel

logger = logging.getLogger("uvicorn")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

socketio_manager = socketio.AsyncAioPikaManager(
    url=celeryconfig.broker_url, logger=logger
)
sm = SocketManager(app=app, mount_location="/ws/", client_manager=socketio_manager)


@sm.on("blocking_request")
async def blocking_request(sid, request: RequestModel):
    try:
        request = RequestModel(**request)
        request.received = datetime.now()
        request.id = str(ObjectId())
        request.blocking = True
        request.session_id = sid

        process_request.apply_async([request], queue="request").forget()

        response = (
            ResponseModel(
                id=request.id,
                received=request.received,
                blocking=True,
                session_id=request.session_id,
                status=ResponseModel.JobStatus.RECEIVED,
                description="Your job has been received and is waiting approval",
            )
            .log(logger)
            .model_dump(exclude_defaults=True, exclude_none=True)
        )

        await _blocking_response(response)

    except Exception as exception:
        response = (
            ResponseModel(
                id=request.id,
                received=request.received,
                blocking=request.blocking,
                session_id=request.session_id,
                status=ResponseModel.JobStatus.ERROR,
                description=str(exception),
            )
            .log(logger)
            .model_dump(exclude_defaults=True, exclude_none=True)
        )

        await _blocking_response(response)

        raise exception


async def _blocking_response(response: Dict):
    await sm.emit("blocking_response", data=response, to=response["session_id"])


@app.get("/blocking_response/{id}")
async def blocking_response(id: str):
    client: MongoClient = celery_app.backend._get_connection()

    responses_collection = client["ndif_database"]["responses"]

    response = responses_collection.find_one({"_id": ObjectId(id)}, {"_id": False})

    await _blocking_response(response)


@app.get("/ping")
async def ping(status_code=200):
    return "pong"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, workers=1)
