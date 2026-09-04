from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["invalid_api_key"])
    message: str = Field(..., examples=["Missing or invalid API key."])


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthStatus(BaseModel):
    status: str = Field(..., examples=["ok"])
    environment: str
    version: str
