from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel


class Item(BaseModel):
    name: str
    price: float



app = FastAPI()


@app.post("/items/")
async def create_item(item: Item):
    return item
@app.post("/get")
async def get_item():
    return {"message"}
