import csv
import os
import pandas as pd

import logging
from app.core.config import settings
import asyncpg

logger = logging.getLogger(__name__)


async def fetch_cavecad_data(drawpoints: list[str]) -> pd.DataFrame:
    """
    Fetches metadata for the given list of drawpoints from the CaveCAD database
    by dynamically building the IN-list placeholders.
    """
    if not drawpoints:
        return pd.DataFrame()
    unique_dpts = set(drawpoints)
    try:
        # Build $1, $2, ... depending on length
        placeholders = ", ".join(f"${i+1}" for i in range(len(unique_dpts)))
        cavecad_query = f"""
            SELECT DISTINCT
                dp.short_name   AS drawpoint_name,
                pr.name         AS project_id,
                pa.name         AS panel,
                ar.name         AS area,
                ph.name         AS primary_heading,
                sh.name         AS secondary_heading
            FROM cavecad_ot.draw_points dp
            JOIN cavecad_ot.secondaryheading sh
              ON sh.secondaryheadingid = dp.secondaryheadingid
            JOIN cavecad_ot.primaryheadings ph
              ON ph.primaryheadingid = sh.primaryheadingid
            JOIN cavecad_ot.area ar
              ON ar.areaid = ph.areaid
            JOIN cavecad_ot.panel pa
              ON pa.panelid = ar.panelid
            JOIN cavecad_ot.projects pr
              ON pr.project_id = pa.project_id
            WHERE pa.name = '0'
              AND ar.name = 'EXL'
              AND dp.short_name IN ({placeholders})
            ORDER BY drawpoint_name
        """
        conn = await asyncpg.connect(str(settings.CAVECAD_URL))
        # Unpack the drawpoints list into parameters
        rows = await conn.fetch(cavecad_query, *unique_dpts)
        cavecad_data = [dict(row) for row in rows]
        print(cavecad_data)
        print(cavecad_data)
        print(cavecad_data)
        await conn.close()
        return pd.DataFrame(cavecad_data)

    except Exception as e:
        # Consider logging the exception here
        print(e)
        print(e)
        print(e)
        return pd.DataFrame()


def create_and_dump_csv(records_df, cavecad_df, uat_paths):
    """
    Creates and dumps CSV files into specified UAT paths by matching drawpoint names.
    """
    try:
        logger.info("Merging approved records with CaveCAD data.")
        # Merge approved records with CaveCAD data
        merged_df = records_df.merge(cavecad_df, on="drawpoint_name", how="inner")

        # Format upload_time and observer columns
        merged_df["upload_time"] = pd.to_datetime(merged_df["upload_time"]).dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
        merged_df["observer"] = "CORP\\" + merged_df["username"].astype(str)

        def write_csv(file_path, header_rows, data_rows):
            """
            Writes CSV file with specified headers and data.
            """
            try:
                final_rows = header_rows + data_rows.values.tolist()
                os.makedirs(
                    os.path.dirname(file_path), exist_ok=True
                )  # Ensure directories exist
                with open(file_path, "w", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(final_rows)
                logger.info(
                    f"{os.path.basename(file_path)} generated and saved to {file_path}"
                )
            except (IOError, OSError) as file_error:
                logger.error(f"Failed to write CSV file at {file_path}: {file_error}")
                raise

        def generate_csv(header, data, columns, uat_key, filename):
            """
            Helper function to generate CSV with error handling.
            """
            try:
                data_subset = merged_df[columns].copy()
                for col, value in data.items():
                    data_subset[col] = value
                csv_path = os.path.join(uat_paths[uat_key], filename)
                logger.info(f"Generating CSV: {filename} at {csv_path}")
                write_csv(csv_path, header, data_subset)
            except KeyError as key_error:
                logger.error(f"Missing required columns for {filename}: {key_error}")
                raise

        # --------------------------------------------
        # Create Monitored DP Data CSV
        # --------------------------------------------
        dp_header = [
            ["Drawptdata.CSV: Drawpoint Variable Data Table"],
            ["All"],
            [
                "Project ID",
                "Panel",
                "Area",
                "Primary Heading",
                "Secondary Heading",
                "DP ID",
                "Date",
                "Bund",
                "Status",
                "Comments",
                "Observer",
            ],
            [
                "ID",
                "ID",
                "ID",
                "ID",
                "ID",
                "ID",
                "Datetime",
                "Drawpoint bund",
                "Drawpoint condition",
                "Observation",
                "Name",
            ],
            [
                "Text",
                "Text",
                "Text",
                "Text",
                "Text",
                "Text",
                "dd/mm/yyyy hh:mm:ss",
                "yes/no",
                "Very good->1/Good->2/Fair->3/Fair to poor-4/Poor->5/Very poor->6",
                "Text",
                "Text",
            ],
        ]
        dp_columns = [
            "project_id",
            "panel",
            "area",
            "primary_heading",
            "secondary_heading",
            "drawpoint_name",
            "upload_time",
        ]
        dp_data = {
            "bund": merged_df["bund"],
            "status": merged_df["condition"],
            "comments": merged_df["drawpointConditionComment"],
            "observer": merged_df["observer"],
        }
        generate_csv(
            dp_header, dp_data, dp_columns, "Monitored DP Data", "MonitoredDPData.csv"
        )

        # --------------------------------------------
        # Create Monitored Fragmentation CSV
        # --------------------------------------------
        frag_header = [
            ["Monitored FRAG.CSV: Monitored Fragmentation Data Table"],
            ["All"],
            [
                "Project ID",
                "Panel",
                "Area",
                "Primary Heading",
                "Secondary Heading",
                "DP ID",
                "Date",
                "TARP",
                "0| <50mm - fines",
                "1| 50-500mm - small fragment",
                "2| 500-1000mm - medium fragment",
                "3| 1000-2000mm - large fragment",
                "4| >2000mm - very large",
                "Comments",
                "Observer",
            ],
            [
                "ID",
                "ID",
                "ID",
                "ID",
                "ID",
                "ID",
                "Datetime",
                "Size",
                "Size",
                "Size",
                "Size",
                "Size",
                "Size",
                "Observation",
                "Name",
            ],
            [
                "Text",
                "Text",
                "Text",
                "Text",
                "Text",
                "Text",
                "dd/mm/yyyy hh:mm:ss",
                "Integer",
                "%",
                "%",
                "%",
                "%",
                "%",
                "Text",
                "Text",
            ],
        ]
        frag_columns = [
            "project_id",
            "panel",
            "area",
            "primary_heading",
            "secondary_heading",
            "drawpoint_name",
            "upload_time",
        ]
        frag_data = {
            "tarp": "",
            "0| <50mm - fines": merged_df["fine_area"],
            "1| 50-500mm - small fragment": merged_df["small_area"],
            "2| 500-1000mm - medium fragment": merged_df["medium_area"],
            "3| 1000-2000mm - large fragment": merged_df["large_area"],
            "4| >2000mm - very large": merged_df["oversized_area"],
            "comments": merged_df["fragmentationComment"],
            "observer": merged_df["observer"],
        }
        generate_csv(
            frag_header,
            frag_data,
            frag_columns,
            "Monitored Fragmentation",
            "MonitoredFragmentation.csv",
        )

        # --------------------------------------------
        # Create Water Monitoring CSV
        # --------------------------------------------
        water_header = [
            ["WATER.CSV: Water Monitoring Data Table"],
            ["All"],
            [
                "Project ID",
                "Panel",
                "Area",
                "Primary Heading",
                "Secondary Heading",
                "DP ID",
                "Date",
                "Wet Muck",
                "Comments",
                "Observer",
            ],
            [
                "ID",
                "ID",
                "ID",
                "ID",
                "ID",
                "ID",
                "Datetime",
                "Water",
                "Observation",
                "Name",
            ],
            [
                "Text",
                "Text",
                "Text",
                "Text",
                "Text",
                "Text",
                "dd/mm/yyyy hh:mm:ss",
                "Dry->1/Damp->2/Wet->3",
                "Text",
                "Text",
            ],
        ]
        water_columns = [
            "project_id",
            "panel",
            "area",
            "primary_heading",
            "secondary_heading",
            "drawpoint_name",
            "upload_time",
        ]
        water_data = {
            "wet_muck": merged_df["wetness"],
            "comments": merged_df["wetnessComment"],
            "observer": merged_df["observer"],
        }
        generate_csv(
            water_header,
            water_data,
            water_columns,
            "Water Monitoring",
            "WaterMonitoring.csv",
        )

    except Exception as e:
        logger.exception(f"Error creating and dumping CSV files: {e}")
        raise
