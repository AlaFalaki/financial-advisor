import json
import os
from typing import Any, Callable, Dict, List, Tuple
import base64

from openai import OpenAI
from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Literal, Optional


MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
SMALL_MODEL = os.getenv("OPENAI_SMALL_MODEL", "gpt-4o-mini")
REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")


# get client.
def get_client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI()


# embed texts.
def embed_texts(texts: List[str]) -> List[List[float]]:
    client = get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        encoding_format="float",
    )
    return [item.embedding for item in response.data]


# get chat model.
def get_chat_model(reasoning_effort: str | None = None) -> ChatOpenAI:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    _effort = reasoning_effort or REASONING_EFFORT
    return ChatOpenAI(model=MODEL_NAME, temperature=0)


# get small chat model.
def get_small_chat_model(reasoning_effort: str | None = None) -> ChatOpenAI:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    _effort = reasoning_effort or REASONING_EFFORT
    return ChatOpenAI(model=SMALL_MODEL, temperature=0)


# extract profile patch from text (or pdf).
def extract_profile_patch_from_text(text_input: str = "", pdf_bytes: bytes | None = None) -> Dict[str, Any]:
    class ProfileUser(BaseModel):
        province: Optional[str] = Field(default=None)
        birthYear: Optional[int] = Field(default=None)
        maritalStatus: Optional[str] = Field(default=None)
        retirementYear: Optional[int] = Field(default=None)

    class ProfileIncome(BaseModel):
        employmentIncomeAnnual: Optional[float] = Field(default=None)
        pensionAnnual: Optional[float] = Field(default=None)
        cppStartAge: Optional[int] = Field(default=None)
        oasStartAge: Optional[int] = Field(default=None)
        otherIncomeAnnual: Optional[float] = Field(default=None)

    class ProfileSpending(BaseModel):
        targetNetAnnual: Optional[float] = Field(default=None)
        inflationAssumption: Optional[float] = Field(default=None)

    class ProfileTfsa(BaseModel):
        balance: Optional[float] = Field(default=None)

    class ProfileRrsp(BaseModel):
        balance: Optional[float] = Field(default=None)

    class ProfileNonRegistered(BaseModel):
        balance: Optional[float] = Field(default=None)
        adjustedCostBase: Optional[float] = Field(default=None)

    class ProfileAccounts(BaseModel):
        tfsa: Optional[ProfileTfsa] = Field(default=None)
        rrsp: Optional[ProfileRrsp] = Field(default=None)
        nonRegistered: Optional[ProfileNonRegistered] = Field(default=None)

    class ProfileAssumptions(BaseModel):
        expectedReturn: Optional[float] = Field(default=None)
        returnVolatility: Optional[float] = Field(default=None)
        planningHorizonYears: Optional[int] = Field(default=None)
        investmentRisk: Optional[Literal["low", "medium", "high"]] = Field(default=None)
        investmentReturnOverride: Optional[int] = Field(default=None)

    class ProfilePatch(BaseModel):
        user: Optional[ProfileUser] = Field(default=None)
        income: Optional[ProfileIncome] = Field(default=None)
        spending: Optional[ProfileSpending] = Field(default=None)
        accounts: Optional[ProfileAccounts] = Field(default=None)
        assumptions: Optional[ProfileAssumptions] = Field(default=None)

    def _prune_empty(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned = {k: _prune_empty(v) for k, v in value.items()}
            cleaned = {k: v for k, v in cleaned.items() if v is not None and v != {}}
            return cleaned
        return value

    instruction = (
        "Extract profile updates using structured output only. "
        "Only populate fields explicitly stated by the user or present in the provided document. "
        "If a field is not provided, leave it null. "
        "If a field value is zero, keep it as 0 (or 0.0) and do not convert it to null. "
        "Zero is a valid value for numeric fields. "
        "For investmentRisk use one of: low, medium, high. "
        "Return no extra keys."
    )
    model = get_chat_model(reasoning_effort="high").with_structured_output(ProfilePatch)
    if pdf_bytes is not None:
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        content = [
            {
                "type": "file",
                "file": {
                    "filename": "document.pdf",
                    "file_data": f"data:application/pdf;base64,{b64}",
                },
            },
            {"type": "text", "text": "Extract and map all profile fields from this PDF."},
        ]
        result = model.invoke([SystemMessage(content=instruction), HumanMessage(content=content)])
    else:
        result = model.invoke([SystemMessage(content=instruction), HumanMessage(content=text_input)])
    return _prune_empty(result.model_dump(exclude_none=True))


# generate report md.
def generate_report_md(
    profile_json: Dict[str, Any],
    question_text: str,
    citations: List[Dict[str, Any]],
    table_rows: List[Dict[str, Any]] | None = None,
    investment_assumption: str | None = None,
    previous_report_md: str | None = None,
) -> str:
    model = get_chat_model()
    instruction = (
        "You are a retirement drawdown assistant. Generate a Markdown report based on the user's question. "
        "Include: Summary, Assumptions used, Recommended strategy, Alternatives, Risks/what could change, Sources. "
        "If previous_report_md is provided, revise that report in place based on updated concerns/question context. "
        "Preserve useful sections and only change what is needed. "
        "If table data is provided, include a Year-by-Year table using that data. "
        "If table data is provided, explicitly state the investment return assumption used "
        "(risk level or percentage) in the table section. "
        "Table columns must be: year, income, investment_income, taxes, spending, net_change, balance_total. "
        "Use only the provided data and be concise."
        "Don't add a sources section in the report itself."
    )
    content = {
        "profile": profile_json,
        "question": question_text,
        "citations": citations,
        "table_rows": table_rows or [],
        "investment_assumption": investment_assumption or "",
        "previous_report_md": previous_report_md or "",
    }
    response = model.invoke(
        [SystemMessage(content=instruction), HumanMessage(content=json.dumps(content))]
    )
    return response.content or ""


# extract risk or return override from text.
def extract_risk_override(text_input: str) -> Dict[str, Any]:
    class RiskOverride(BaseModel):
        investmentRisk: Optional[Literal["low", "medium", "high"]] = Field(default=None)
        investmentReturnOverride: Optional[int] = Field(
            default=None, description="Return percentage number, integer, e.g., 6 for 6%"
        )

    instruction = (
        "Extract investment risk preference or explicit return percentage from the text. "
        "Return only structured output. "
        "investmentRisk must be one of: low, medium, high. "
        "investmentReturnOverride must be an integer percentage, e.g., 6 for 6%."
    )
    model = get_small_chat_model(reasoning_effort="high").with_structured_output(RiskOverride)
    result = model.invoke([SystemMessage(content=instruction), HumanMessage(content=text_input)])
    data = result.model_dump()
    return {k: v for k, v in data.items() if v is not None}


# generate intake reply.
def generate_intake_reply(
    messages: List[Dict[str, Any]], profile_json: Dict[str, Any], missing_fields: List[str] | None = None
) -> str:
    missing_fields = missing_fields or []
    instruction = (
        "You are an intake assistant. Do NOT provide financial advice. "
        "Focus only on collecting missing profile info or asking the user to submit a request. "
        "If profile info is missing, ask concise follow-up questions to fill it. "
        "Use the provided missing_fields list as the source of truth. "
        "If missing_fields is empty, explicitly state there is nothing missing. "
        "If enough info is present, suggest submitting a report request. "
        "Keep the response short."
    )
    model = get_small_chat_model()
    prompt = {
        "profile": profile_json,
        "missing_fields": missing_fields,
        "messages": messages,
    }
    response = model.invoke(
        [SystemMessage(content=instruction), HumanMessage(content=json.dumps(prompt))]
    )
    return response.content or ""
