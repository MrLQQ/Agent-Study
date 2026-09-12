import asyncio
from dataclasses import replace

import pytest

from week2.tool_governance import (
    ACCOUNTS,
    SIDE_EFFECTS,
    ApprovalStore,
    AuditSink,
    DecisionAction,
    PermissionEngine,
    ToolCall,
    ToolRuntime,
    base_context,
    build_runtime,
    build_tools,
    reset_side_effects,
)


def _transfer_arguments(
    amount: float = 100.0,
    *,
    from_account: str = "ACC-A-123456",
    to_account: str = "ACC-A-888888",
) -> dict[str, object]:
    return {"from_account": from_account, "to_account": to_account, "amount": amount}


def _invoke(runtime: ToolRuntime, call_id: str, arguments: dict[str, object], context=None):
    return asyncio.run(runtime.invoke(ToolCall(call_id, "transfer", arguments), context or base_context()))


@pytest.fixture(autouse=True)
def restore_runtime_state():
    account_snapshot = ACCOUNTS.copy()
    reset_side_effects()
    yield
    ACCOUNTS.clear()
    ACCOUNTS.update(account_snapshot)
    reset_side_effects()


def test_transfer_schema_rejects_extra():
    runtime, _, _ = build_runtime()
    invalid_account = _invoke(
        runtime,
        "call_invalid_account",
        _transfer_arguments(from_account="invalid-account"),
    )
    injected_argument = _invoke(
        runtime,
        "call_injected_argument",
        {**_transfer_arguments(), "approved": True},
    )

    assert invalid_account.code == "INVALID_ARGUMENT"
    assert injected_argument.code == "INVALID_ARGUMENT"
    assert SIDE_EFFECTS["transfer_executions"] == 0


def test_transfer_precheck_insufficient():
    runtime, _, _ = build_runtime()

    result = _invoke(
        runtime,
        "call_insufficient",
        _transfer_arguments(6000.0, from_account="ACC-A-654321"),
    )

    assert result.code == "INSUFFICIENT_BALANCE"
    assert SIDE_EFFECTS["transfer_executions"] == 0


def test_transfer_precheck_exceed_limit():
    runtime, _, _ = build_runtime()

    result = _invoke(runtime, "call_exceed_limit", _transfer_arguments(60_000.0))

    assert result.code == "EXCEED_LIMIT"
    assert SIDE_EFFECTS["transfer_executions"] == 0


def test_transfer_approval_binding():
    runtime, approvals, audit = build_runtime()
    context = base_context()
    approved_arguments = _transfer_arguments(100.0)

    confirmation = _invoke(runtime, "call_confirm", approved_arguments, context)
    assert confirmation.action is DecisionAction.CONFIRM
    assert confirmation.code == "APPROVAL_REQUIRED"
    assert SIDE_EFFECTS["transfer_executions"] == 0

    approvals.approve("approval_bound", context, "transfer", approved_arguments)
    changed_arguments = _transfer_arguments(200.0)
    mismatch = _invoke(
        runtime,
        "call_mismatch",
        changed_arguments,
        replace(context, approval_id="approval_bound"),
    )
    assert mismatch.action is DecisionAction.CONFIRM
    assert mismatch.code == "APPROVAL_REQUIRED"
    assert SIDE_EFFECTS["transfer_executions"] == 0

    approvals.approve("approval_valid", context, "transfer", approved_arguments)
    success = _invoke(
        runtime,
        "call_success",
        approved_arguments,
        replace(context, approval_id="approval_valid"),
    )
    assert success.ok is True
    assert success.content["from"] == "ACC-A-****3456"
    assert success.content["to"] == "ACC-A-****8888"
    print(
        {
            "pre_approval_action": confirmation.action,
            "result": success.content,
            "audit_codes": [record.code for record in audit.records],
        }
    )


def test_transfer_timeout_no_retry():
    transfer_tool = next(tool for tool in build_tools() if tool.name == "transfer")
    timeout_tool = replace(transfer_tool, precheck=None)
    approvals = ApprovalStore()
    runtime = ToolRuntime([timeout_tool], PermissionEngine((), approvals), AuditSink())
    context = base_context(
        permissions=frozenset({"transfer:execute"}),
        allowed_tools=frozenset({"transfer"}),
    )
    arguments = _transfer_arguments(90_000.0)
    balances_before = ACCOUNTS.copy()
    approvals.approve("approval_timeout", context, "transfer", arguments)

    result = _invoke(
        runtime,
        "call_timeout",
        arguments,
        replace(context, approval_id="approval_timeout"),
    )

    assert result.code == "TIMEOUT_UNKNOWN"
    assert SIDE_EFFECTS["transfer_executions"] <= 1
    assert ACCOUNTS == balances_before
