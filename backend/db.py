import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path("data/app.db")


# get conn.
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# init db.
def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        cur = conn.cursor()
        _migrate_profiles_if_needed(conn)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                province TEXT,
                birth_year INTEGER,
                marital_status TEXT,
                retirement_year INTEGER,
                employment_income_annual REAL,
                pension_annual REAL,
                cpp_start_age INTEGER,
                oas_start_age INTEGER,
                other_income_annual REAL,
                target_net_annual REAL,
                inflation_assumption REAL,
                tfsa_balance REAL,
                rrsp_balance REAL,
                nonreg_balance REAL,
                nonreg_acb REAL,
                expected_return REAL,
                return_volatility REAL,
                planning_horizon_years INTEGER,
                investment_risk TEXT,
                investment_return_override INTEGER,
                version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by_role TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                structured_questions_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY,
                request_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                draft_md TEXT NOT NULL,
                final_md TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY,
                report_id INTEGER NOT NULL,
                citation_key TEXT NOT NULL,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                excerpt TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS review_events (
                id INTEGER PRIMARY KEY,
                report_id INTEGER NOT NULL,
                advisor_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                notes TEXT,
                diff_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_profiles_user_version ON profiles(user_id, version)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requests_user_status ON requests(user_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_status ON reports(user_id, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_citations_report ON citations(report_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_review_events_report ON review_events(report_id)")
        # Remove legacy table no longer used by the app.
        cur.execute("DROP TABLE IF EXISTS extractions")
        conn.commit()
        _ensure_profile_columns(conn)


# ensure profile columns.
def _ensure_profile_columns(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(profiles)")
    existing = {row["name"] for row in cur.fetchall()}
    columns = [
        ("province", "TEXT"),
        ("birth_year", "INTEGER"),
        ("marital_status", "TEXT"),
        ("retirement_year", "INTEGER"),
        ("employment_income_annual", "REAL"),
        ("pension_annual", "REAL"),
        ("cpp_start_age", "INTEGER"),
        ("oas_start_age", "INTEGER"),
        ("other_income_annual", "REAL"),
        ("target_net_annual", "REAL"),
        ("inflation_assumption", "REAL"),
        ("tfsa_balance", "REAL"),
        ("rrsp_balance", "REAL"),
        ("nonreg_balance", "REAL"),
        ("nonreg_acb", "REAL"),
        ("expected_return", "REAL"),
        ("return_volatility", "REAL"),
        ("planning_horizon_years", "INTEGER"),
        ("investment_risk", "TEXT"),
        ("investment_return_override", "INTEGER"),
    ]
    for name, ctype in columns:
        if name not in existing:
            cur.execute(f"ALTER TABLE profiles ADD COLUMN {name} {ctype}")
    conn.commit()


# migrate profiles table if needed.
def _migrate_profiles_if_needed(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profiles'")
    if not cur.fetchone():
        return
    cur.execute("PRAGMA table_info(profiles)")
    cols = {row["name"] for row in cur.fetchall()}
    if "profile_json" not in cols:
        return

    cur.execute("DROP TABLE IF EXISTS profiles_new")
    cur.execute(
        """
        CREATE TABLE profiles_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            province TEXT,
            birth_year INTEGER,
            marital_status TEXT,
            retirement_year INTEGER,
            employment_income_annual REAL,
            pension_annual REAL,
            cpp_start_age INTEGER,
            oas_start_age INTEGER,
            other_income_annual REAL,
            target_net_annual REAL,
            inflation_assumption REAL,
            tfsa_balance REAL,
            rrsp_balance REAL,
            nonreg_balance REAL,
            nonreg_acb REAL,
            expected_return REAL,
            return_volatility REAL,
            planning_horizon_years INTEGER,
            investment_risk TEXT,
            investment_return_override INTEGER,
            version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by_role TEXT NOT NULL
        )
        """
    )
    cur.execute("SELECT * FROM profiles")
    rows = cur.fetchall()
    for r in rows:
        row = dict(r)
        try:
            profile_json = json.loads(row.get("profile_json") or "{}")
        except Exception:
            profile_json = {}
        data = _profile_json_to_row(profile_json)
        cur.execute(
            """
            INSERT INTO profiles_new (
                id,
                user_id,
                province,
                birth_year,
                marital_status,
                retirement_year,
                employment_income_annual,
                pension_annual,
                cpp_start_age,
                oas_start_age,
                other_income_annual,
                target_net_annual,
                inflation_assumption,
                tfsa_balance,
                rrsp_balance,
                nonreg_balance,
                nonreg_acb,
                expected_return,
                return_volatility,
                planning_horizon_years,
                investment_risk,
                investment_return_override,
                version,
                created_at,
                updated_at,
                updated_by_role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("id"),
                row.get("user_id"),
                data.get("province"),
                data.get("birth_year"),
                data.get("marital_status"),
                data.get("retirement_year"),
                data.get("employment_income_annual"),
                data.get("pension_annual"),
                data.get("cpp_start_age"),
                data.get("oas_start_age"),
                data.get("other_income_annual"),
                data.get("target_net_annual"),
                data.get("inflation_assumption"),
                data.get("tfsa_balance"),
                data.get("rrsp_balance"),
                data.get("nonreg_balance"),
                data.get("nonreg_acb"),
                data.get("expected_return"),
                data.get("return_volatility"),
                data.get("planning_horizon_years"),
                data.get("investment_risk"),
                data.get("investment_return_override"),
                row.get("version"),
                row.get("created_at"),
                row.get("updated_at"),
                row.get("updated_by_role"),
            ),
        )
    cur.execute("DROP TABLE profiles")
    cur.execute("ALTER TABLE profiles_new RENAME TO profiles")
    conn.commit()


# Seed data for mock auth

# seed users.
def seed_users() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        if cur.fetchone()["c"] == 0:
            cur.execute(
                "INSERT INTO users (id, role, name, email, created_at) VALUES (1, 'USER', 'Jamie Client', 'jamie@example.com', datetime('now'))"
            )
            cur.execute(
                "INSERT INTO users (id, role, name, email, created_at) VALUES (2, 'ADVISOR', 'Avery Advisor', 'avery@example.com', datetime('now'))"
            )
            conn.commit()


# get user.
def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# get profile latest.
def get_profile_latest(user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM profiles WHERE user_id = ? ORDER BY updated_at DESC, id DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        result["profile_json"] = _row_to_profile_json(result)
        return result


# save profile version.
def save_profile_version(user_id: int, profile_json: Dict[str, Any], updated_by_role: str) -> Dict[str, Any]:
    latest = get_profile_latest(user_id)
    data = _profile_json_to_row(profile_json)
    with get_conn() as conn:
        cur = conn.cursor()
        if latest:
            cur.execute(
                """
                UPDATE profiles
                SET
                    province = ?,
                    birth_year = ?,
                    marital_status = ?,
                    retirement_year = ?,
                    employment_income_annual = ?,
                    pension_annual = ?,
                    cpp_start_age = ?,
                    oas_start_age = ?,
                    other_income_annual = ?,
                    target_net_annual = ?,
                    inflation_assumption = ?,
                    tfsa_balance = ?,
                    rrsp_balance = ?,
                    nonreg_balance = ?,
                    nonreg_acb = ?,
                    expected_return = ?,
                    return_volatility = ?,
                    planning_horizon_years = ?,
                    investment_risk = ?,
                    investment_return_override = ?,
                    updated_at = datetime('now'),
                    updated_by_role = ?
                WHERE id = ?
                """,
                (
                    data.get("province"),
                    data.get("birth_year"),
                    data.get("marital_status"),
                    data.get("retirement_year"),
                    data.get("employment_income_annual"),
                    data.get("pension_annual"),
                    data.get("cpp_start_age"),
                    data.get("oas_start_age"),
                    data.get("other_income_annual"),
                    data.get("target_net_annual"),
                    data.get("inflation_assumption"),
                    data.get("tfsa_balance"),
                    data.get("rrsp_balance"),
                    data.get("nonreg_balance"),
                    data.get("nonreg_acb"),
                    data.get("expected_return"),
                    data.get("return_volatility"),
                    data.get("planning_horizon_years"),
                    data.get("investment_risk"),
                    data.get("investment_return_override"),
                    updated_by_role,
                    latest["id"],
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO profiles (
                    user_id,
                    province,
                    birth_year,
                    marital_status,
                    retirement_year,
                    employment_income_annual,
                    pension_annual,
                    cpp_start_age,
                    oas_start_age,
                    other_income_annual,
                    target_net_annual,
                    inflation_assumption,
                    tfsa_balance,
                    rrsp_balance,
                    nonreg_balance,
                    nonreg_acb,
                    expected_return,
                    return_volatility,
                    planning_horizon_years,
                    investment_risk,
                    investment_return_override,
                    version,
                    created_at,
                    updated_at,
                    updated_by_role
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)
                """,
                (
                    user_id,
                    data.get("province"),
                    data.get("birth_year"),
                    data.get("marital_status"),
                    data.get("retirement_year"),
                    data.get("employment_income_annual"),
                    data.get("pension_annual"),
                    data.get("cpp_start_age"),
                    data.get("oas_start_age"),
                    data.get("other_income_annual"),
                    data.get("target_net_annual"),
                    data.get("inflation_assumption"),
                    data.get("tfsa_balance"),
                    data.get("rrsp_balance"),
                    data.get("nonreg_balance"),
                    data.get("nonreg_acb"),
                    data.get("expected_return"),
                    data.get("return_volatility"),
                    data.get("planning_horizon_years"),
                    data.get("investment_risk"),
                    data.get("investment_return_override"),
                    1,
                    updated_by_role,
                ),
            )
        conn.commit()
        return {
            "user_id": user_id,
            "profile_json": profile_json,
        }


# create request.
def create_request(user_id: int, question_text: str, structured_questions_json: Dict[str, Any]) -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO requests (user_id, question_text, structured_questions_json, status, created_at)
            VALUES (?, ?, ?, 'SUBMITTED', datetime('now'))
            """,
            (user_id, question_text, json.dumps(structured_questions_json)),
        )
        conn.commit()
        return {"id": cur.lastrowid}


# list requests.
def list_requests(user_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM requests WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]


# list pending requests.
def list_pending_requests() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT r.*, rep.id AS report_id, rep.status AS report_status
            FROM requests r
            LEFT JOIN reports rep ON rep.request_id = r.id
            WHERE rep.id IS NULL OR rep.status IN ('UNDER_REVIEW','NEEDS_INFO')
            ORDER BY r.created_at DESC
            """
        )
        return [dict(r) for r in cur.fetchall()]


# create report.
def create_report(request_id: int, user_id: int, draft_md: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reports (request_id, user_id, draft_md, final_md, status, created_at, updated_at)
            VALUES (?, ?, ?, NULL, 'UNDER_REVIEW', datetime('now'), datetime('now'))
            """,
            (request_id, user_id, draft_md),
        )
        conn.commit()
        return cur.lastrowid


# update report final.
def update_report_final(report_id: int, final_md: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE reports SET final_md = ?, updated_at = datetime('now') WHERE id = ?
            """,
            (final_md, report_id),
        )
        conn.commit()


# update report draft.
def update_report_draft(report_id: int, draft_md: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE reports SET draft_md = ?, updated_at = datetime('now') WHERE id = ?
            """,
            (draft_md, report_id),
        )
        conn.commit()


# set report status.
def set_report_status(report_id: int, status: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE reports SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, report_id))
        conn.commit()


# get report.
def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# list reports for user.
def list_reports_for_user(user_id: int, status: str | None = None) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        if status:
            cur.execute(
                "SELECT * FROM reports WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
                (user_id, status),
            )
        else:
            cur.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]


# list advisor queue.
def list_advisor_queue() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM reports WHERE status IN ('UNDER_REVIEW','NEEDS_INFO') ORDER BY updated_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]


# set request status.
def set_request_status(request_id: int, status: str) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE requests SET status = ? WHERE id = ?", (status, request_id))
        conn.commit()


# add citations.
def add_citations(report_id: int, citations: List[Dict[str, Any]]) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM citations WHERE report_id = ?", (report_id,))
        for idx, c in enumerate(citations, start=1):
            citation_key = c.get("citation_key") or f"SRC-{idx:03d}"
            cur.execute(
                """
                INSERT INTO citations (report_id, citation_key, title, source_type, source_ref, excerpt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    report_id,
                    citation_key,
                    c.get("title", "Untitled"),
                    c.get("source_type", "KB"),
                    c.get("source_ref", ""),
                    c.get("excerpt"),
                ),
            )
        conn.commit()


# list citations.
def list_citations(report_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM citations WHERE report_id = ? ORDER BY id ASC", (report_id,))
        return [dict(r) for r in cur.fetchall()]


# add review event.
def add_review_event(report_id: int, advisor_id: int, action: str, notes: Optional[str], diff_json: Optional[Dict[str, Any]]) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO review_events (report_id, advisor_id, action, notes, diff_json, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (report_id, advisor_id, action, notes, json.dumps(diff_json) if diff_json else None),
        )
        conn.commit()


# list review events.
def list_review_events(report_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM review_events WHERE report_id = ? ORDER BY created_at DESC", (report_id,))
    return [dict(r) for r in cur.fetchall()]


# get request.
def get_request(request_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# row to profile json.
def _row_to_profile_json(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user": {
            "province": row.get("province"),
            "birthYear": row.get("birth_year"),
            "maritalStatus": row.get("marital_status"),
            "retirementYear": row.get("retirement_year"),
        },
        "income": {
            "employmentIncomeAnnual": row.get("employment_income_annual"),
            "pensionAnnual": row.get("pension_annual"),
            "cppStartAge": row.get("cpp_start_age"),
            "oasStartAge": row.get("oas_start_age"),
            "otherIncomeAnnual": row.get("other_income_annual"),
        },
        "spending": {
            "targetNetAnnual": row.get("target_net_annual"),
            "inflationAssumption": row.get("inflation_assumption"),
        },
        "accounts": {
            "tfsa": {"balance": row.get("tfsa_balance")},
            "rrsp": {"balance": row.get("rrsp_balance")},
            "nonRegistered": {
                "balance": row.get("nonreg_balance"),
                "adjustedCostBase": row.get("nonreg_acb"),
            },
        },
        "assumptions": {
            "expectedReturn": row.get("expected_return"),
            "returnVolatility": row.get("return_volatility"),
            "planningHorizonYears": row.get("planning_horizon_years"),
            "investmentRisk": row.get("investment_risk"),
            "investmentReturnOverride": row.get("investment_return_override"),
        },
        "documents": [],
    }


# profile json to row.
def _profile_json_to_row(profile_json: Dict[str, Any]) -> Dict[str, Any]:
    user = profile_json.get("user", {})
    income = profile_json.get("income", {})
    spending = profile_json.get("spending", {})
    accounts = profile_json.get("accounts", {})
    assumptions = profile_json.get("assumptions", {})
    nonreg = accounts.get("nonRegistered", {})
    return {
        "province": user.get("province"),
        "birth_year": user.get("birthYear"),
        "marital_status": user.get("maritalStatus"),
        "retirement_year": user.get("retirementYear"),
        "employment_income_annual": income.get("employmentIncomeAnnual"),
        "pension_annual": income.get("pensionAnnual"),
        "cpp_start_age": income.get("cppStartAge"),
        "oas_start_age": income.get("oasStartAge"),
        "other_income_annual": income.get("otherIncomeAnnual"),
        "target_net_annual": spending.get("targetNetAnnual"),
        "inflation_assumption": spending.get("inflationAssumption"),
        "tfsa_balance": (accounts.get("tfsa") or {}).get("balance"),
        "rrsp_balance": (accounts.get("rrsp") or {}).get("balance"),
        "nonreg_balance": nonreg.get("balance"),
        "nonreg_acb": nonreg.get("adjustedCostBase"),
        "expected_return": assumptions.get("expectedReturn"),
        "return_volatility": assumptions.get("returnVolatility"),
        "planning_horizon_years": assumptions.get("planningHorizonYears"),
        "investment_risk": assumptions.get("investmentRisk"),
        "investment_return_override": assumptions.get("investmentReturnOverride"),
    }
