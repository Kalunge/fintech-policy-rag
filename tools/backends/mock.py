"""In-memory mock backend that reads from tools/data/*.json.

Each public function here matches the signature and return shape declared
in tools/banking.py. Swap this module for tools/backends/live.py to point
the agent at a real API; no other code changes.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from tools.errors import ToolError


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load_agents() -> dict[str, dict]:
    raw = json.loads((DATA_DIR / "agents.json").read_text(encoding="utf-8"))
    return {a["agent_id"]: a for a in raw}


@lru_cache(maxsize=1)
def _load_terminals() -> dict[str, dict]:
    raw = json.loads((DATA_DIR / "terminals.json").read_text(encoding="utf-8"))
    return {t["terminal_id"]: t for t in raw}


@lru_cache(maxsize=1)
def _load_transactions() -> dict[str, dict]:
    raw = json.loads((DATA_DIR / "transactions.json").read_text(encoding="utf-8"))
    return {t["reference"]: t for t in raw}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def check_agent_balance(agent_id: str) -> dict:
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent:
        raise ToolError(
            "AGENT_NOT_FOUND",
            f"No agent found with ID {agent_id!r}. Agent IDs look like 'AG-001'.",
        )

    return {
        "agent_id": agent["agent_id"],
        "business_name": agent["business_name"],
        "tier": agent["tier"],
        "status": agent["status"],
        "float_balance_kes": agent["float_balance_kes"],
        "float_minimum_kes": agent["float_minimum_kes"],
        "below_minimum": agent["float_balance_kes"] < agent["float_minimum_kes"],
        "currency": "KES",
        "as_of": agent["last_updated"],
    }


def lookup_transaction(reference: str) -> dict:
    transactions = _load_transactions()
    txn = transactions.get(reference)
    if not txn:
        raise ToolError(
            "TRANSACTION_NOT_FOUND",
            f"No transaction found with reference {reference!r}. "
            "References look like 'TXN-1001'.",
        )

    return {
        "reference": txn["reference"],
        "type": txn["type"],
        "amount_kes": txn["amount_kes"],
        "currency": txn["currency"],
        "status": txn["status"],
        "agent_id": txn.get("agent_id"),
        "terminal_id": txn.get("terminal_id"),
        "customer_msisdn_masked": txn["customer_msisdn_masked"],
        "channel": txn["channel"],
        "timestamp": txn["timestamp"],
        "failure_reason": txn.get("failure_reason"),
    }


def terminal_status(terminal_id: str) -> dict:
    terminals = _load_terminals()
    terminal = terminals.get(terminal_id)
    if not terminal:
        raise ToolError(
            "TERMINAL_NOT_FOUND",
            f"No terminal found with ID {terminal_id!r}. Terminal IDs look like 'TID-001'.",
        )

    return {
        "terminal_id": terminal["terminal_id"],
        "merchant_id": terminal["merchant_id"],
        "merchant_name": terminal["merchant_name"],
        "model": terminal["model"],
        "status": terminal["status"],
        "last_seen": terminal["last_seen"],
        "last_transaction_ref": terminal["last_transaction_ref"],
        "location": terminal["location"],
    }


def agent_compliance_scorecard(agent_id: str) -> dict:
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent:
        raise ToolError(
            "AGENT_NOT_FOUND",
            f"No agent found with ID {agent_id!r}.",
        )

    sc = agent["scorecard"]

    flags: list[str] = []
    if sc["kyc_completeness_pct"] < 90:
        flags.append("KYC completeness below 90%")
    if sc["transaction_reversal_rate_pct"] > 2.0:
        flags.append("Reversal rate above 2%")
    if sc["customer_complaints"] >= 5:
        flags.append(f"{sc['customer_complaints']} customer complaints this period")
    if sc["float_discipline_score"] < 3.0:
        flags.append("Float discipline score below 3.0")
    if agent["status"] != "active":
        flags.append(f"Agent status: {agent['status']}")

    return {
        "agent_id": agent["agent_id"],
        "business_name": agent["business_name"],
        "tier": agent["tier"],
        "period": sc["period"],
        "kyc_completeness_pct": sc["kyc_completeness_pct"],
        "transaction_reversal_rate_pct": sc["transaction_reversal_rate_pct"],
        "customer_complaints": sc["customer_complaints"],
        "float_discipline_score": sc["float_discipline_score"],
        "compliance_flags": flags,
        "overall_health": "healthy" if not flags else "needs_attention",
    }


# Single-transaction limits by tier, from the Agency Banking policy section 4.3
TIER_LIMITS_KES = {
    "Tier-1": 35_000,
    "Tier-2": 70_000,
    "Tier-3": 150_000,
    "Master": 250_000,
}


def initiate_mock_deposit(agent_id: str, customer_msisdn: str, amount_kes: int) -> dict:
    """Dry-run a deposit. Does NOT persist anything. Returns what the transaction
    would look like if processed, or a structured error explaining why it wouldn't.
    """
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent:
        raise ToolError("AGENT_NOT_FOUND", f"No agent found with ID {agent_id!r}.")

    if agent["status"] != "active":
        raise ToolError(
            "AGENT_NOT_ACTIVE",
            f"Agent {agent_id} has status {agent['status']!r} and cannot accept deposits.",
        )

    if amount_kes <= 0:
        raise ToolError("INVALID_AMOUNT", "Deposit amount must be greater than zero.")

    tier_limit = TIER_LIMITS_KES.get(agent["tier"])
    if tier_limit is None:
        raise ToolError("UNKNOWN_TIER", f"Agent tier {agent['tier']!r} has no configured limit.")

    if amount_kes > tier_limit:
        raise ToolError(
            "EXCEEDS_TIER_LIMIT",
            f"Amount {amount_kes:,} KES exceeds the single-transaction limit "
            f"of {tier_limit:,} KES for tier {agent['tier']}.",
        )

    if not customer_msisdn or not customer_msisdn.startswith("+254"):
        raise ToolError(
            "INVALID_MSISDN",
            "Customer MSISDN must be in international format (e.g., '+254712345678').",
        )

    # Mock everything past validation: generate a reference, return a "would-be" result.
    masked = customer_msisdn[:5] + "****" + customer_msisdn[-4:]
    rng = random.Random(f"{agent_id}|{customer_msisdn}|{amount_kes}")
    proposed_ref = f"TXN-MOCK-{rng.randint(10000, 99999)}"

    return {
        "dry_run": True,
        "would_succeed": True,
        "proposed_reference": proposed_ref,
        "agent_id": agent_id,
        "agent_tier": agent["tier"],
        "tier_single_transaction_limit_kes": tier_limit,
        "customer_msisdn_masked": masked,
        "amount_kes": amount_kes,
        "currency": "KES",
        "estimated_commission_kes": max(20, amount_kes // 1000 * 10),
        "as_of": _now_iso(),
        "note": "Mock deposit — no real transaction was created.",
    }
