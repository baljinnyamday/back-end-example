from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    url_to_analyse: str
    prompt: str
