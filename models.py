"""
Shared models and utilities for the API Processor system
"""
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime
import json


class ProcessingRequest(BaseModel):
    """Model for an API request to be processed"""
    request_id: str
    endpoint: str
    method: str = "POST"
    payload: dict
    timestamp: datetime
    client_id: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode='json'))

    @classmethod
    def from_json(cls, json_str: str) -> "ProcessingRequest":
        data = json.loads(json_str)
        return cls(**data)


class ProcessingResponse(BaseModel):
    """Model for the response after processing"""
    request_id: str
    status: str  # "success", "failed", "processing"
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode='json'))

    @classmethod
    def from_json(cls, json_str: str) -> "ProcessingResponse":
        data = json.loads(json_str)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ApiRequestModel(BaseModel):
    """Model for incoming API requests"""
    endpoint: str
    method: str = "POST"
    payload: dict
    client_id: Optional[str] = None
