from pydantic import BaseModel, ConfigDict, Field


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    heading: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    raw_context: str
