from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from pydantic import Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """Api settings that are set using environment variables."""

    title: str = "pdf-api"
    version: str = "1.0"

    # Set to False to disable docs at /docs and /redoc
    docs_enabled: bool = True

    # Cors origin list to allow requests from.
    # This list is set using the set_cors_origin_list validator
    # which uses the runtime_env variable to set the
    # default cors origin list.
    cors_origin_list: Optional[List[str]] = Field(None, validate_default=True)


    # Dramatiq
    dramatiq_broker_url: str = Field(alias="DRAMATIQ_BROKER_URL")

    # Database
    database_url: str = Field(alias="DATABASE_URL")

    # OpenAI
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4.1-mini", alias="OPENAI_MODEL")

    # Google Drive
    google_service_account_json_base64: str | None = Field(
        default=None, alias="GOOGLE_SERVICE_ACCOUNT_JSON_BASE64"
    )
    google_drive_folder_id: str = Field(alias="GOOGLE_DRIVE_FOLDER_ID")
    google_drive_csv_folder_id: str = Field(alias="GOOGLE_DRIVE_CSV_FOLDER_ID")

    # Woovi
    woovi_app_id: str | None = Field(default=None, alias="WOOVI_APP_ID")
    woovi_env: str = Field("production", alias="WOOVI_ENV")
    woovi_webhook_token: str | None = Field(default=None, alias="WOOVI_WEBHOOK_TOKEN")

    # BotConversa
    botconversa_api_key: str | None = Field(default=None, alias="BOTCONVERSA_API_KEY")

    # Ploomes
    ploomes_user_key: str | None = Field(default=None, alias="PLOOMES_USER_KEY")
    formbricks_webhook_secret: Optional[str] = Field(default=None, alias="FORMBRICKS_WEBHOOK_SECRET")
    formbricks_survey_url: str = Field(
        default="https://forms.spreed-automacao.com.br/s/cmkzs8mm80000rn014bepotpk", 
        alias="FORMBRICKS_SURVEY_URL"
    )

    @field_validator("cors_origin_list", mode="before")
    def set_cors_origin_list(cls, cors_origin_list, info: FieldValidationInfo):
        valid_cors = cors_origin_list or []

        # Add localhost to cors to allow requests from the local environment.
        valid_cors.append("http://localhost")
        # Add localhost:3000 to cors to allow requests from local Agent UI.
        valid_cors.append("http://localhost:3000")

        return valid_cors


# Create ApiSettings object
api_settings = ApiSettings()
