from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .domain import get_product, preview_order
from .errors import register_handlers

app = FastAPI(title="Global Error Handling Laboratuvarı", debug=False)
register_handlers(app)


@app.middleware("http")
async def request_context(request: Request, call_next):
    # İstemciden gelen keyfi kimliği log'a taşımak yerine sunucuda üret.
    request.state.request_id = uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


class OrderInput(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


@app.get("/", include_in_schema=False)
async def lab():
    return FileResponse(Path(__file__).with_name("lab.html"))


@app.get("/products/{product_id}")
async def product(product_id: int):
    return get_product(product_id)


@app.post("/orders/preview")
async def order(body: OrderInput):
    # Burada try/except yok. Hata yukarı taşınır, handler HTTP yanıtı üretir.
    return preview_order(body.product_id, body.quantity)


@app.get("/demo/unauthorized")
async def unauthorized():
    raise HTTPException(401, "Demo", headers={"WWW-Authenticate": "Bearer"})


@app.get("/demo/crash")
async def crash():
    # Yalnızca PoC: bu ayrıntı istemciye gitmemeli, sunucu logunda kalmalı.
    raise RuntimeError("DEMO_INTERNAL_DETAIL: simulated database failure")
