from typing import Annotated

from pydantic import BaseModel, Field


class QueryInfo(BaseModel):
    codigoLegal: str
    dataBase: str
    empresaFlexline: str
    instalacion: str
    password: str
    razonSocial: str
    server: Annotated[str, Field(validation_alias="serverSQL")]
    urlApiData: str
    urlApiIntegracion: str
    user: str
    userFlexline: str
    command: str | None = None
