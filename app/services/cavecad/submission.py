import logging
import pandas as pd
from datetime import datetime
import logging

from app.api.deps import CurrentUser
from app.services.cavecad.schema import CavecadType
from app.core.queries.cavecad import CavecadQueries

logger = logging.getLogger(__name__)
from app.core.postgres import db_pg
from asyncio import sleep


# ? if you ever want transaction uncomment this decorator and use it. (TRANSACTION AND ROLLBACK IS BETTER APPROACH)
# @db_pg.transaction
async def save_submitted_results(
    input: CavecadType, current_user: CurrentUser, connection=None
):

    updated_date = datetime.now()
    queries = CavecadQueries()

    try:
        record_id = input.id
        drawpoint_name = input.drawpoint_name
        fine_area = input.fine_area
        small_area = input.small_area
        medium_area = input.medium_area
        large_area = input.large_area
        oversized_area = input.oversized_area

        wetness = input.wetness
        condition = input.condition
        bund = input.bund
        username = current_user.username
        date = input.upload_time

        drawpointconditioncomment = input.drawpointConditionComment
        fragmentationcomment = input.fragmentationComment
        wetnesscomment = input.wetnessComment
        username = current_user.username
        if not all([record_id, drawpoint_name, date]):
            error_msg = "Missing required fields in record."
            logger.error(error_msg)
            raise ValueError(error_msg)

        existing_record = await db_pg.execute_one(
            queries.retreive_query, int(record_id)
        )

        if existing_record:
            is_edited = (
                fine_area != existing_record["fine_area"]
                or small_area != existing_record["small_area"]
                or medium_area != existing_record["medium_area"]
                or large_area != existing_record["large_area"]
                or oversized_area != existing_record["oversized_area"]
            )
            logger.debug(f"Record ID {record_id} edited status: {is_edited}")

            # cursor.execute(
            #     ,
            #     ("Yes" if is_edited else "No", updated_date, int(record_id)),
            # )
            await db_pg.execute_command(
                queries.update,
                "Yes" if is_edited else "No",
                updated_date,
                int(record_id),
            )

            final_exists = await db_pg.execute_one(queries.count, int(record_id))
            if not final_exists:
                raise

            final_exists = final_exists.get("count", 0) > 0

            if final_exists:
                await db_pg.execute_command(
                    queries.final_update,
                    fine_area,
                    small_area,
                    medium_area,
                    large_area,
                    oversized_area,
                    int(condition or -1),
                    bund,
                    int(wetness or -1),
                    username,
                    drawpoint_name,
                    updated_date,
                    updated_date,
                    drawpointconditioncomment,
                    fragmentationcomment,
                    wetnesscomment,
                    int(record_id),
                )
                logger.info(f"Updated final table for record ID {record_id}.")
            else:
                # Insert a new record into the 'final' table
                await db_pg.execute_command(
                    queries.insert,
                    int(record_id),
                    fine_area,
                    small_area,
                    medium_area,
                    large_area,
                    oversized_area,
                    int(condition or -1),
                    bund,
                    int(wetness or -1),
                    username,
                    drawpoint_name,
                    updated_date,
                    drawpointconditioncomment,
                    fragmentationcomment,
                    wetnesscomment,
                    updated_date,
                )
                logger.info(
                    f"Inserted new record into final table for record ID {record_id}."
                )
        else:
            error_msg = f"No record found in db for ID {record_id}."
            logger.error(error_msg)
            return False, error_msg

        return True, "Record processed successfully"

    except (ValueError, TypeError) as record_error:
        logger.error(f"Error processing record ID {input.id}: {record_error}")
        return False, str(record_error)
