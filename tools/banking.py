"""Public banking tool surface for the LangChain agent.

Each function here is a stable contract. The docstrings are what the LLM
reads to decide which tool to call and how to format its arguments — they
are part of the public API, not just human documentation.

The implementation is selected via the TOOLS_BACKEND environment variable:
- TOOLS_BACKEND=mock (default) reads from tools/data/*.json
- TOOLS_BACKEND=live would talk to a real fintech API (not implemented yet)

To swap in a real backend later, create tools/backends/live.py with the
same function signatures and set TOOLS_BACKEND=live. No other code changes.
"""
from __future__ import annotations

import os

from tools.errors import ToolError  # noqa: F401  (re-exported for callers)


_BACKEND_NAME = os.getenv("TOOLS_BACKEND", "mock").lower()

if _BACKEND_NAME == "live":
    # Placeholder — implement tools/backends/live.py when a real API is available.
    raise RuntimeError(
        "TOOLS_BACKEND=live is not implemented yet. "
        "Create tools/backends/live.py with matching function signatures."
    )
else:
    from tools.backends import mock as _backend


def check_agent_balance(agent_id: str) -> dict:
    """Look up the current float balance for a ThaBytePay agent.

    Use this tool when the user asks about a specific agent's float, balance,
    tier status, liquidity, or whether they have enough float to handle a
    transaction. The agent_id must be in the format 'AG-NNN' (e.g.,
    'AG-001'). Do not invent agent IDs — if the user hasn't given one, ask.

    Do NOT use this tool for general questions about the agency banking
    policy or tier rules — those are answered from the policy corpus.

    Returns a dict with:
        agent_id, business_name, tier ('Tier-1' | 'Tier-2' | 'Tier-3' |
        'Master'), status ('active' | 'suspended'), float_balance_kes,
        float_minimum_kes, below_minimum (bool), currency ('KES'),
        and as_of (ISO 8601 timestamp).

    Raises ToolError(AGENT_NOT_FOUND) if the agent_id is unknown.
    """
    return _backend.check_agent_balance(agent_id)


def lookup_transaction(reference: str) -> dict:
    """Fetch the details of a single transaction by its reference number.

    Use this tool when the user asks about a specific transaction, dispute,
    failed payment, or status check, AND they provide a reference number.
    Reference numbers look like 'TXN-1001'.

    Do NOT use this tool to list multiple transactions or search by customer
    — only single-reference lookups are supported.

    Returns a dict with:
        reference, type ('deposit' | 'withdrawal' | 'transfer' |
        'card_payment'), amount_kes, currency, status ('SUCCESS' | 'FAILED'
        | 'REVERSED' | 'PENDING'), agent_id (or null for POS card payments),
        terminal_id (or null for agent transactions), customer_msisdn_masked,
        channel ('agent' | 'pos'), timestamp, and failure_reason (or null).

    Raises ToolError(TRANSACTION_NOT_FOUND) if the reference is unknown.
    """
    return _backend.lookup_transaction(reference)


def terminal_status(terminal_id: str) -> dict:
    """Check the operational status of a POS terminal.

    Use this tool when the user asks about a specific terminal's status,
    when it was last seen, what its last transaction was, or which merchant
    it belongs to. The terminal_id must be in the format 'TID-NNN' (e.g.,
    'TID-001').

    Do NOT use this tool for general POS policy questions or for questions
    that don't include a specific terminal ID.

    Returns a dict with:
        terminal_id, merchant_id, merchant_name, model (the hardware
        model), status ('online' | 'offline' | 'tamper_suspended'),
        last_seen (ISO 8601), last_transaction_ref, and location.

    Raises ToolError(TERMINAL_NOT_FOUND) if the terminal_id is unknown.
    """
    return _backend.terminal_status(terminal_id)


def agent_compliance_scorecard(agent_id: str) -> dict:
    """Retrieve the latest monthly compliance scorecard for an agent.

    Use this tool when the user asks how an agent is performing, whether
    they are compliant, whether they should be upgraded or downgraded, or
    whether there are any compliance flags. The agent_id must be in the
    format 'AG-NNN'.

    Returns a dict with:
        agent_id, business_name, tier, period ('YYYY-MM'),
        kyc_completeness_pct, transaction_reversal_rate_pct,
        customer_complaints, float_discipline_score (0-5),
        compliance_flags (list of human-readable concern strings),
        and overall_health ('healthy' | 'needs_attention').

    Raises ToolError(AGENT_NOT_FOUND) if the agent_id is unknown.
    """
    return _backend.agent_compliance_scorecard(agent_id)


def initiate_mock_deposit(agent_id: str, customer_msisdn: str, amount_kes: int) -> dict:
    """Dry-run a customer deposit at an agent. Does NOT persist any state.

    This is a SIMULATION tool. It validates whether a proposed deposit
    would succeed based on the agent's status, tier limits, and basic
    input checks, then returns what the resulting transaction would look
    like. Nothing is recorded — calling this twice does not create two
    transactions.

    Use this tool ONLY when the user explicitly asks to simulate, preview,
    or test a deposit. Do not call it as part of a general policy
    discussion.

    Arguments:
        agent_id: 'AG-NNN' format
        customer_msisdn: international format starting with '+254'
        amount_kes: positive integer

    Returns a dict with:
        dry_run (True), would_succeed (True), proposed_reference,
        agent_id, agent_tier, tier_single_transaction_limit_kes,
        customer_msisdn_masked, amount_kes, currency, estimated_commission_kes,
        as_of, and a note clarifying it is a mock.

    Raises ToolError with codes:
        AGENT_NOT_FOUND, AGENT_NOT_ACTIVE, INVALID_AMOUNT,
        EXCEEDS_TIER_LIMIT, INVALID_MSISDN.
    """
    return _backend.initiate_mock_deposit(agent_id, customer_msisdn, amount_kes)
