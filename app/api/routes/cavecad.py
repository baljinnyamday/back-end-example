import logging
from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse
import pandas as pd


from app.api.deps import CurrentUser
from app.core.config import settings
from app.services.cavecad.main import create_and_dump_csv, fetch_cavecad_data
from app.services.cavecad.schema import CavecadSubmitElement
from app.services.cavecad.submission import save_submitted_results
from asyncer import asyncify

router = APIRouter(prefix="/cavecad", tags=["Cavecad CSV"])
logger = logging.getLogger(__name__)


@router.post("/")
async def POST(input: CavecadSubmitElement, current_user: CurrentUser):
    try:
        drawpoints = [record.drawpoint_name for record in input.data]
        cavecad_df = await fetch_cavecad_data(drawpoints)

        data = []
        for each_record in input.data:
            _data = await save_submitted_results(each_record, current_user)
            data.append(_data)
        # return drawpoints

        records = [
            {**x.model_dump(), "username": current_user.username} for x in input.data
        ]

        records_df = pd.DataFrame(records)
        await asyncify(create_and_dump_csv)(records_df, cavecad_df, settings.UAT_PATHS)

        return data
    except Exception as e:
        logger.error(e)
        return JSONResponse("ERROR", status_code=500)
