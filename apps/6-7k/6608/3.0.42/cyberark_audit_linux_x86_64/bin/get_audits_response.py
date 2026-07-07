from pydantic import BaseModel


class Cursors(BaseModel):
    after: str
    before: str | None = None


class Paging(BaseModel):
    cursors: Cursors
    next: str
    previous: str | None = None


class GetAuditsResponse(BaseModel):
    data: list[dict] | None = None
    paging: Paging | None = None
