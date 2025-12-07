from pydantic import BaseModel, ConfigDict


class DigitalAssistantBase(BaseModel): 
    model_config = ConfigDict(arbitrary_types_allowed=True)