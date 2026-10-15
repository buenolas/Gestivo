from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


class FinancialAssistantMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def require_non_blank_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A mensagem não pode estar vazia.")
        return normalized


class FinancialAssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[FinancialAssistantMessage] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_conversation(self) -> "FinancialAssistantRequest":
        if self.messages[-1].role != "user":
            raise ValueError("A última mensagem precisa ser do usuário.")
        if sum(len(message.content) for message in self.messages) > 12000:
            raise ValueError("A conversa excede o tamanho permitido.")
        return self


class FinancialAssistantResponse(BaseModel):
    answer: str
