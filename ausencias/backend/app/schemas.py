"""Schemas Pydantic (validação de entrada)."""
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

from .constants import Role


class LoginIn(BaseModel):
    email: str
    password: str


class RequestIn(BaseModel):
    type: str
    start_date: date
    end_date: date
    subjects: str = Field(min_length=3, max_length=1000)
    reason: str = Field(min_length=3, max_length=3000)
    notes: str | None = Field(default=None, max_length=3000)
    suggested_substitute_id: int | None = None

    @field_validator("type")
    @classmethod
    def _type(cls, v):
        if v not in ("PROGRAMADA", "NAO_PROGRAMADA"):
            raise ValueError("Tipo deve ser PROGRAMADA ou NAO_PROGRAMADA.")
        return v

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("A data final não pode ser anterior à data inicial.")
        # Programada = conhecida com antecedência; não programada pode ser registrada depois.
        if self.type == "PROGRAMADA" and self.start_date < date.today():
            raise ValueError("Ausência programada deve começar hoje ou em data futura. Use 'não programada' para imprevistos já ocorridos.")
        return self


class ActionIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)
    substitute_id: int | None = None


class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    password: str | None = Field(default=None, min_length=6, max_length=72)
    role: str
    course_id: int | None = None
    active: bool = True

    @field_validator("role")
    @classmethod
    def _role(cls, v):
        if v not in Role.ALL:
            raise ValueError("Perfil inválido.")
        return v


class CourseIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
