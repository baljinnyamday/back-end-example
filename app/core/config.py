import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_env_list(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


cavecad_config = {
    "host": "MNOYTPGSQL1",
    "port": "5432",
    "user": "sa-mn-plotlyservice",
    "password": "jfP;YN9k8c(J1Dh]inLZ",
    "database": "cavecad_prd",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    LDAP_BASE: str = "DC=corp,DC=riotinto,DC=org"
    LDAP_SERVER_URI: str = "ldap://10.45.251.21"

    LDAP_ALLOWED_GROUP: Annotated[list[str] | str, BeforeValidator(parse_env_list)] = [
        "CN=OT_FileShare_T&IP_UG Geosciences_Geotechnical_RO,OU=OT PowerScale,OU=Folder Permissions,OU=Rights,OU=MN-Oyu_Tolgoi,OU=APAC,OU=PROD,DC=corp,DC=riotinto,DC=org",
        "CN=OT_FileShare_T&IP_UG Geosciences_Geotechnical_RW,OU=OT PowerScale,OU=Folder Permissions,OU=Rights,OU=MN-Oyu_Tolgoi,OU=APAC,OU=PROD,DC=corp,DC=riotinto,DC=org",
    ]

    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    TOKEN_KEY: str = "access_token"
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    PROJECT_NAME: str = ""
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def ASYNCPG_URL(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field
    @property
    def CAVECAD_URL(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql",
            username=cavecad_config["user"],
            password=cavecad_config["password"],
            host=cavecad_config["host"],
            port=int(cavecad_config["port"]),
            path=cavecad_config["database"],
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    CONTENT_URL: str = "http://mnoytaspd1"
    RAW_DIR: str = r"/app/contents/static"
    UAT_MONITORED_DP_DATA: str = "/app/static/csv/dp_data"
    UAT_MONITORED_FRAGMENTATION: str = "/app/static/csv/fragmentation"
    UAT_WATER_MONITORING: str = "/app/static/csv/water_monitoring"
    SUBSCRIBED_CHANNEL: str = "JOB_CHANNEL"

    @computed_field
    @property
    def UAT_PATHS(self) -> dict[str, str]:
        return {
            "Monitored DP Data": self.UAT_MONITORED_DP_DATA,
            "Monitored Fragmentation": self.UAT_MONITORED_FRAGMENTATION,
            "Water Monitoring": self.UAT_WATER_MONITORING,
        }


settings = Settings()  # type: ignore
