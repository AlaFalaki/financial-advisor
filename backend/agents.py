import json
from typing import Any, Dict, List

from langgraph.graph import StateGraph, END

from . import chroma_kb
from . import db, llm


QUESTION_TYPES = {
    "MINIMIZE_TAX": ["minimize tax", "minimise tax", "tax efficient", "taxes"],
    "ACCOUNT_ORDER": ["which accounts", "draw from", "rrsp", "tfsa", "non-registered", "order"],
    "SAFE_WITHDRAWAL": ["safe withdrawal", "withdrawal rate", "sustainable"],
}


# classify question.
def classify_question(question_text: str) -> str:
    q = question_text.lower()
    for qtype, keywords in QUESTION_TYPES.items():
        if any(k in q for k in keywords):
            return qtype
    return "CUSTOM"


# build structured questions.
def build_structured_questions(question_text: str) -> Dict[str, Any]:
    qtype = classify_question(question_text)
    return {"type": qtype, "parameters": {}}


# check missing info.
def check_missing_info(profile: Dict[str, Any]) -> Dict[str, Any]:
    missing: List[str] = []

    user = profile.get("user", {}) if isinstance(profile.get("user"), dict) else {}
    income = profile.get("income", {}) if isinstance(profile.get("income"), dict) else {}
    spending = profile.get("spending", {}) if isinstance(profile.get("spending"), dict) else {}
    accounts = profile.get("accounts", {}) if isinstance(profile.get("accounts"), dict) else {}
    assumptions = profile.get("assumptions", {}) if isinstance(profile.get("assumptions"), dict) else {}

    tfsa = accounts.get("tfsa", {}) if isinstance(accounts.get("tfsa"), dict) else {}
    rrsp = accounts.get("rrsp", {}) if isinstance(accounts.get("rrsp"), dict) else {}
    nonreg = accounts.get("nonRegistered", {}) if isinstance(accounts.get("nonRegistered"), dict) else {}

    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    # Support both nested profile shape and flat DB-style shape.
    checks = [
        ("user.province", user.get("province", profile.get("province"))),
        ("user.birthYear", user.get("birthYear", profile.get("birth_year"))),
        ("user.maritalStatus", user.get("maritalStatus", profile.get("marital_status"))),
        ("user.retirementYear", user.get("retirementYear", profile.get("retirement_year"))),
        ("income.employmentIncomeAnnual", income.get("employmentIncomeAnnual", profile.get("employment_income_annual"))),
        ("income.pensionAnnual", income.get("pensionAnnual", profile.get("pension_annual"))),
        ("income.cppStartAge", income.get("cppStartAge", profile.get("cpp_start_age"))),
        ("income.oasStartAge", income.get("oasStartAge", profile.get("oas_start_age"))),
        ("income.otherIncomeAnnual", income.get("otherIncomeAnnual", profile.get("other_income_annual"))),
        ("spending.targetNetAnnual", spending.get("targetNetAnnual", profile.get("target_net_annual"))),
        ("spending.inflationAssumption", spending.get("inflationAssumption", profile.get("inflation_assumption"))),
        ("accounts.tfsa.balance", tfsa.get("balance", profile.get("tfsa_balance"))),
        ("accounts.rrsp.balance", rrsp.get("balance", profile.get("rrsp_balance"))),
        ("accounts.nonRegistered.balance", nonreg.get("balance", profile.get("nonreg_balance"))),
        ("accounts.nonRegistered.adjustedCostBase", nonreg.get("adjustedCostBase", profile.get("nonreg_acb"))),
        ("assumptions.expectedReturn", assumptions.get("expectedReturn", profile.get("expected_return"))),
        ("assumptions.returnVolatility", assumptions.get("returnVolatility", profile.get("return_volatility"))),
        ("assumptions.planningHorizonYears", assumptions.get("planningHorizonYears", profile.get("planning_horizon_years"))),
        ("assumptions.investmentRisk", assumptions.get("investmentRisk", profile.get("investment_risk"))),
    ]
    for field_path, value in checks:
        if _is_missing(value):
            missing.append(field_path)

    return {"missing": missing}


# retrieve sources.
def retrieve_sources(question_text: str) -> List[Dict[str, Any]]:
    return chroma_kb.retrieve_sources(question_text, n_results=5)


# build intake graph.
def build_intake_graph():
    graph = StateGraph(dict)

    def _classify(state):
        state["structured_questions"] = build_structured_questions(state["question_text"])
        return state

    def _missing(state):
        result = check_missing_info(state.get("profile_json", {}))
        state["missing"] = result.get("missing", [])
        return state

    graph.add_node("classify", _classify)
    graph.add_node("missing", _missing)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "missing")
    graph.add_edge("missing", END)
    return graph.compile()


# build draft graph.
def build_draft_graph():
    graph = StateGraph(dict)

    def _retrieve(state):
        state["citations"] = retrieve_sources(state["question_text"])
        return state

    def _table(state):
        risk_override = llm.extract_risk_override(state["question_text"])
        table = generate_yearly_table(state["profile_json"], risk_override=risk_override)
        state["table_rows"] = table.get("rows", [])
        state["investment_assumption"] = table.get("assumption_text")
        return state

    def _format(state):
        table_rows = state.get("table_rows", [])
        state["draft_md"] = llm.generate_report_md(
            profile_json=state["profile_json"],
            question_text=state["question_text"],
            citations=state["citations"],
            table_rows=table_rows,
            investment_assumption=state.get("investment_assumption"),
        )
        return state

    graph.add_node("retrieve", _retrieve)
    graph.add_node("table", _table)
    graph.add_node("format", _format)
    graph.set_entry_point("retrieve")
    def _needs_table(state):
        return should_include_table(state["question_text"])
    graph.add_conditional_edges("retrieve", _needs_table, {True: "table", False: "format"})
    graph.add_edge("table", "format")
    graph.add_edge("format", END)
    return graph.compile()


# build refine graph.
def build_refine_graph():
    graph = StateGraph(dict)

    def _refine(state):
        concerns = state.get("concerns", "")
        state["question_text"] = f"{state['question_text']}\nAdvisor concerns: {concerns}"
        return state

    def _retrieve(state):
        state["citations"] = retrieve_sources(state["question_text"])
        return state

    def _table(state):
        risk_override = llm.extract_risk_override(state["question_text"])
        table = generate_yearly_table(state["profile_json"], risk_override=risk_override)
        state["table_rows"] = table.get("rows", [])
        state["investment_assumption"] = table.get("assumption_text")
        return state

    def _format(state):
        table_rows = state.get("table_rows", [])
        state["draft_md"] = llm.generate_report_md(
            profile_json=state["profile_json"],
            question_text=state["question_text"],
            citations=state["citations"],
            table_rows=table_rows,
            investment_assumption=state.get("investment_assumption"),
        )
        return state

    graph.add_node("refine", _refine)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("table", _table)
    graph.add_node("format", _format)
    graph.set_entry_point("refine")
    graph.add_edge("refine", "retrieve")
    def _needs_table(state):
        return should_include_table(state["question_text"])
    graph.add_conditional_edges("retrieve", _needs_table, {True: "table", False: "format"})
    graph.add_edge("table", "format")
    graph.add_edge("format", END)
    return graph.compile()


# build chat graph.
def build_chat_graph():
    graph = StateGraph(dict)

    def _extract_patch(state):
        message = state["messages"][-1]["content"]
        state["patch"] = llm.extract_profile_patch_from_text(message)
        return state

    def _apply_patch(state):
        patch = state.get("patch") or {}
        result = apply_profile_patch_direct(state["user_id"], state["profile_json"], patch)
        state["profile_json"] = result.get("profile_json", state["profile_json"])
        state["actions"] = [{"tool": "apply_profile_patch", "result": result}]
        state["assistant_message"] = "Profile updated from your message."
        return state

    def _route_request(state):
        msg = state["messages"][-1]["content"].lower()
        state["should_create_report"] = should_create_report(msg)
        intake = build_intake_graph()
        intake_state = intake.invoke(
            {
                "question_text": state["messages"][-1]["content"],
                "profile_json": state.get("profile_json", {}),
            }
        )
        state["structured_questions"] = intake_state.get("structured_questions", {})
        state["missing"] = intake_state.get("missing", [])
        return state

    def _create_request(state):
        msg = state["messages"][-1]["content"]
        req = db.create_request(state["user_id"], msg, state.get("structured_questions", {}))
        state["actions"] = state.get("actions", []) + [{"tool": "create_request", "result": {"request_id": req["id"]}}]
        state["assistant_message"] = f"Request {req['id']} submitted for advisor review."
        return state

    def _assistant_reply(state):
        state["assistant_message"] = llm.generate_intake_reply(
            state["messages"],
            state.get("profile_json", {}),
            state.get("missing", []),
        )
        return state

    graph.add_node("extract_patch", _extract_patch)
    graph.add_node("apply_patch", _apply_patch)
    graph.add_node("route_request", _route_request)
    graph.add_node("create_request", _create_request)
    graph.add_node("assistant_reply", _assistant_reply)

    graph.set_entry_point("extract_patch")

    def has_patch(state):
        return bool(state.get("patch"))

    def should_report(state):
        return bool(state.get("should_create_report")) and not bool(state.get("missing"))

    graph.add_conditional_edges("extract_patch", has_patch, {True: "apply_patch", False: "route_request"})
    graph.add_conditional_edges("route_request", should_report, {True: "create_request", False: "assistant_reply"})
    graph.add_edge("apply_patch", "route_request")
    graph.add_edge("create_request", END)
    graph.add_edge("assistant_reply", END)
    return graph.compile()


#  merge patch.
def _merge_patch(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k] = _merge_patch(base.get(k, {}), v)
        else:
            base[k] = v
    return base


# apply profile patch direct.
def apply_profile_patch_direct(user_id: int, profile_json: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = _merge_patch(json.loads(json.dumps(profile_json)), patch)
    db.save_profile_version(user_id, merged, "USER")
    return {"action": "profile_updated", "profile_json": merged}


# should create report.
def should_create_report(message: str) -> bool:
    if "report" in message or "analysis" in message or "submit" in message:
        return True
    qtype = classify_question(message)
    return qtype in ("MINIMIZE_TAX", "ACCOUNT_ORDER", "SAFE_WITHDRAWAL")


def should_include_table(question_text: str) -> bool:
    text = question_text.lower()
    if "year-by-year" in text or "year by year" in text:
        return True
    return False


def generate_yearly_table(
    profile_json: Dict[str, Any],
    years: int = 10,
    risk_override: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    user = profile_json.get("user", {})
    income = profile_json.get("income", {})
    spending = profile_json.get("spending", {})
    accounts = profile_json.get("accounts", {})
    assumptions = profile_json.get("assumptions", {})

    start_year = int(user.get("retirementYear") or 2026)
    target_spend = float(spending.get("targetNetAnnual", 0))

    tfsa = float(accounts.get("tfsa", {}).get("balance", 0))
    rrsp = float(accounts.get("rrsp", {}).get("balance", 0))
    nonreg = float(accounts.get("nonRegistered", {}).get("balance", 0))

    risk_override = risk_override or {}
    risk = risk_override.get("investmentRisk") or assumptions.get("investmentRisk") or "medium"
    override = risk_override.get("investmentReturnOverride") or assumptions.get("investmentReturnOverride")
    risk_defaults = {
        "low": 5,
        "medium": 6,
        "high": 8,
    }
    try:
        if override is not None:
            override_val = int(override)
            return_rate = override_val / 100.0
            assumption_text = f"Investment return override: {override_val}%."
        else:
            default_pct = int(risk_defaults.get(str(risk).lower(), 6))
            return_rate = default_pct / 100.0
            assumption_text = f"Investment risk level: {str(risk).lower()} (default {default_pct}%)."
    except Exception:
        default_pct = int(risk_defaults.get("medium", 6))
        return_rate = default_pct / 100.0
        assumption_text = f"Investment risk level: medium (default {default_pct}%)."

    balance_total = tfsa + rrsp + nonreg
    rows = []
    for i in range(max(1, years)):
        year = start_year + i
        gross_income = float(income.get("pensionAnnual", 0)) + float(income.get("otherIncomeAnnual", 0))
        investment_income = balance_total * return_rate
        est_tax = (gross_income + investment_income) * 0.2
        net_change = gross_income + investment_income - est_tax - target_spend
        # Investment income already reflects growth; apply net change directly.
        balance_total = max(0.0, balance_total + net_change)
        rows.append(
            {
                "year": year,
                "income": round(gross_income, 2),
                "investment_income": round(investment_income, 2),
                "taxes": round(est_tax, 2),
                "spending": round(target_spend, 2),
                "net_change": round(net_change, 2),
                "balance_total": round(balance_total, 2),
            }
        )
    return {"rows": rows, "assumption_text": assumption_text}
