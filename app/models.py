from pydantic import BaseModel


class SearchRequest(BaseModel):
    lat :float
    long: float
    cat: str
    rad: float
    