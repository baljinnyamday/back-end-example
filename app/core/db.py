from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate
from app.core.postgres import ProductionPostgres
import logging

logger = logging.getLogger(__name__)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)


async def table_exists(db: ProductionPostgres, table_name: str) -> bool:
    """Check if a table exists in the current database schema."""
    query = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = $1
    );
    """
    result = await db.execute_one(query, table_name)
    exists = result and result.get("exists", False)
    logger.debug(f"Table '{table_name}' exists: {exists}")
    return exists


async def initialize_tables(db: ProductionPostgres):
    logger.info("Starting table initialization...")

    tables_to_create = {
        "approved_fragmentation": """
            CREATE TABLE approved_fragmentation (
                id SERIAL PRIMARY KEY,
                image_id INT,
                drawpoint_name VARCHAR(255) NULL,
                new_fine_area REAL,
                new_small_area REAL,
                new_medium_area REAL,
                new_large_area REAL,
                new_oversized_area REAL,
                dp_condition SMALLINT,
                bund VARCHAR(3),
                wetness SMALLINT,
                drawpointConditionComment VARCHAR(1000) NULL,
                fragmentationComment VARCHAR(1000) NULL,
                wetnessComment VARCHAR(1000) NULL,
                username VARCHAR(500),
                submitted_date TIMESTAMP WITHOUT TIME ZONE NULL,
                created_date TIMESTAMP WITHOUT TIME ZONE NULL
            );
        """,
        "fragmentation_images": """
            CREATE TABLE fragmentation_images (
                id SERIAL PRIMARY KEY,
                drawpoint_name VARCHAR(255) NOT NULL,
                edited_dp_name VARCHAR(255) NULL,
                fine_area REAL DEFAULT 0,
                small_area REAL DEFAULT 0,
                medium_area REAL DEFAULT 0,
                large_area REAL DEFAULT 0,
                oversized_area REAL DEFAULT 0,
                raw_image_path VARCHAR(500) NOT NULL,
                predicted_image_path VARCHAR(500) NULL,
                bbox_image_path VARCHAR(500),
                has_bund VARCHAR(3),
                image_status VARCHAR(20),
                is_edited VARCHAR(3),
                imagetaken_date TIMESTAMP WITHOUT TIME ZONE NULL,
                created_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                updated_date TIMESTAMP WITHOUT TIME ZONE NULL
            );
        """,
    }

    for table_name, create_sql in tables_to_create.items():
        try:
            if await table_exists(db, table_name):
                logger.info(f"Table '{table_name}' already exists. Skipping creation.")
            else:
                logger.info(f"Creating table '{table_name}'...")
                await db.execute_command(create_sql)
                logger.info(f"Table '{table_name}' created successfully.")
        except Exception as e:
            logger.error(
                f"Error while creating table '{table_name}': {e}", exc_info=True
            )

    logger.info("Table initialization completed.")
