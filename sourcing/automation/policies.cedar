// Zine Machine execution layer: tool-call authorization policies (Cedar).
// Evaluated by the tool gateway for every MCP tools/call. Default is deny:
// anything not permitted below is refused. Sketch, not a tested policy set.
//
// Entities: Agent::"procurement" (in Role::"buyer"), Human::"dave" (in Role::"approver"),
// Action::"mcp__mouser__create_order", Tool::"...". Context carries the tool input,
// the run's input trust level and the linked approval, filled in by the gateway.

// 1. Read tools: any agent, any trust level.
permit (principal is Agent, action in Action::"group:read", resource);

// 2. Drafting and proposing: agents in the right role, internal or sanitized input only.
permit (principal in Role::"buyer", action in [Action::"mcp__plm__create_rfq", Action::"mcp__plm__propose_po", Action::"mcp__mail__draft_rfq"], resource)
when { context.run_trust != "untrusted" };

// 3. Sending email to a supplier: only to verified contacts, only on an existing thread
//    or an approved RFQ, and never while the run has touched unsanitized content.
permit (principal in Role::"comms", action == Action::"mcp__mail__send", resource)
when {
  context.input.to_contact_verified == true &&
  (context.input.thread_known == true || context.approval.status == "approved") &&
  context.run_trust != "untrusted"
};

// 4. Spending money: executors only, with an approved approval whose payload hash matches.
permit (principal is Executor, action in Action::"group:spend", resource)
when {
  context.approval.status == "approved" &&
  context.approval.payload_hash == context.payload_hash &&
  context.amount_usd_cents <= 500000                       // hard ceiling $5,000 per PO at MVP
};

// 5. Dual control above $1,000 or for a first PO to a new supplier.
forbid (principal, action in Action::"group:spend", resource)
when {
  (context.amount_usd_cents > 100000 || context.supplier_first_po == true) &&
  context.approval.distinct_approvers < 2
};

// 6. Supplier bank-detail changes: never by an agent, human dual control only.
forbid (principal is Agent, action == Action::"mcp__plm__update_supplier_bank", resource);

// 7. Outbound calls: approved call plan, business hours in the callee's time zone,
//    and only to numbers whose consent / recording rules are known.
permit (principal is Executor, action == Action::"twilio_call_create", resource)
when {
  context.approval.status == "approved" &&
  context.callee.local_hour >= 9 && context.callee.local_hour < 17 &&
  context.callee.recording_rule != "unknown"
};

// 8. Global kill switch and per-agent pause override everything.
forbid (principal, action, resource) when { context.kill_switch == true };
forbid (principal is Agent, action, resource) when { context.agent_paused == true };
