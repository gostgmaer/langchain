# SDK Examples

These are the official reference clients for external teams. They are not
published packages; they are copyable examples showing the supported submit,
poll, tool callback, and approval flows. This service trusts the
`x-tenant-id` / `x-principal-id` headers forwarded by your API gateway and
performs no authentication of its own — see
[authentication.md](authentication.md).

## 1. Node.js reference client

```javascript
export class AiPlatformClient {
  constructor({ baseUrl, tenantId, principalId }) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.tenantId = tenantId;
    this.principalId = principalId;
  }

  async submit(path, body, { traceId } = {}) {
    const payload = JSON.stringify(body);
    const headers = this.#headers({ method: "POST", path, body: payload, traceId });
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: payload,
    });
    return this.#json(response);
  }

  async get(path, { traceId } = {}) {
    const headers = this.#headers({ method: "GET", path, body: "", traceId });
    const response = await fetch(`${this.baseUrl}${path}`, { method: "GET", headers });
    return this.#json(response);
  }

  async submitWorkflow(command, options = {}) {
    return this.submit("/v1/workflows/run", { tenant_id: this.tenantId, ...command }, options);
  }

  async getWorkflow(workflowId, options = {}) {
    const path = `/v1/workflows/${workflowId}?tenant_id=${encodeURIComponent(this.tenantId)}`;
    return this.get(path, options);
  }

  async getJob(jobId, options = {}) {
    const path = `/v1/jobs/${jobId}?tenant_id=${encodeURIComponent(this.tenantId)}`;
    return this.get(path, options);
  }

  async deliverToolResult(workflowId, { toolName, result }, options = {}) {
    return this.submit(`/v1/workflows/${workflowId}/tool-results`, {
      tenant_id: this.tenantId,
      tool_name: toolName,
      result,
    }, options);
  }

  async resolveApproval(workflowId, decision, options = {}) {
    return this.submit(`/v1/workflows/${workflowId}/approvals`, {
      tenant_id: this.tenantId,
      ...decision,
    }, options);
  }

  async waitForTerminal(workflowId, { timeoutMs = 30000, initialDelayMs = 250 } = {}) {
    const startedAt = Date.now();
    let delayMs = initialDelayMs;
    while (Date.now() - startedAt < timeoutMs) {
      const status = await this.getWorkflow(workflowId);
      if (["SUCCESS", "FAILED", "CANCELLED", "DEAD"].includes(status.status)) {
        return status;
      }
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      delayMs = Math.min(Math.round(delayMs * 1.5), 2000);
    }
    throw new Error(`workflow ${workflowId} did not reach terminal state within ${timeoutMs}ms`);
  }

  #headers({ traceId }) {
    const headers = {
      "content-type": "application/json",
      "x-tenant-id": this.tenantId,
    };
    if (this.principalId) headers["x-principal-id"] = this.principalId;
    if (traceId) headers["x-trace-id"] = traceId;
    return headers;
  }

  async #json(response) {
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload?.error?.message || `HTTP ${response.status}`);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }
}
```

### 1.1 Node.js usage

```javascript
const client = new AiPlatformClient({
  baseUrl: process.env.AI_PLATFORM_BASE_URL,
  tenantId: "tenant_acme",
  principalId: "svc_support_bot",
});

const queued = await client.submitWorkflow({
  workflow: "support_automation",
  task: "generate_customer_reply",
  context_ids: ["brand_voice_default", "customer_8821"],
  payload: {
    channel: "email",
    body: "Where is my order?",
  },
});

const finalStatus = await client.waitForTerminal(queued.workflow_id);
```

## 2. Python reference client

```python
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(slots=True)
class AiPlatformClient:
    base_url: str
    tenant_id: str
    principal_id: str | None = None
    timeout_seconds: float = 30.0
    _client: httpx.Client = field(init=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds)

    def submit_workflow(self, command: dict[str, Any], *, trace_id: str | None = None) -> dict[str, Any]:
        body = {"tenant_id": self.tenant_id, **command}
        return self._request("POST", "/v1/workflows/run", json_body=body, trace_id=trace_id)

    def get_workflow(self, workflow_id: str, *, trace_id: str | None = None) -> dict[str, Any]:
        path = f"/v1/workflows/{workflow_id}?tenant_id={self.tenant_id}"
        return self._request("GET", path, trace_id=trace_id)

    def get_job(self, job_id: str, *, trace_id: str | None = None) -> dict[str, Any]:
        path = f"/v1/jobs/{job_id}?tenant_id={self.tenant_id}"
        return self._request("GET", path, trace_id=trace_id)

    def deliver_tool_result(
        self,
        workflow_id: str,
        *,
        tool_name: str,
        result: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/workflows/{workflow_id}/tool-results",
            json_body={
                "tenant_id": self.tenant_id,
                "tool_name": tool_name,
                "result": result,
            },
            trace_id=trace_id,
        )

    def resolve_approval(
        self,
        workflow_id: str,
        *,
        approval_type: str,
        decision: str,
        approval_payload: dict[str, Any] | None = None,
        reason: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "tenant_id": self.tenant_id,
            "approval_type": approval_type,
            "decision": decision,
        }
        if approval_payload is not None:
            payload["approval_payload"] = approval_payload
        if reason is not None:
            payload["reason"] = reason
        return self._request(
            "POST",
            f"/v1/workflows/{workflow_id}/approvals",
            json_body=payload,
            trace_id=trace_id,
        )

    def wait_for_terminal(
        self,
        workflow_id: str,
        *,
        timeout_seconds: float = 30.0,
        initial_delay_seconds: float = 0.25,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        delay = initial_delay_seconds
        while time.monotonic() < deadline:
            status = self.get_workflow(workflow_id)
            if status["status"] in {"SUCCESS", "FAILED", "CANCELLED", "DEAD"}:
                return status
            time.sleep(delay)
            delay = min(delay * 1.5, 2.0)
        raise TimeoutError(f"workflow {workflow_id} did not reach terminal state")

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(json_body or {}, separators=(",", ":")) if json_body is not None else ""
        headers = self._headers(method=method, path=path, body=body, trace_id=trace_id)
        response = self._client.request(method, path, content=body if json_body is not None else None, headers=headers)
        payload = response.json()
        response.raise_for_status()
        return payload

    def _headers(self, *, method: str, path: str, body: str, trace_id: str | None) -> dict[str, str]:
        headers = {
            "content-type": "application/json",
            "x-tenant-id": self.tenant_id,
        }
        if self.principal_id:
            headers["x-principal-id"] = self.principal_id
        if trace_id:
            headers["x-trace-id"] = trace_id
        return headers
```

## 3. Callback pattern

For both languages, the supported callback loop is:

1. Submit a workflow.
2. Poll `get_workflow(...)`.
3. If `status == "WAITING_TOOL"`, read `pending_action.tool_name` and
   `pending_action.tool_payload`, execute your tool, then call
   `deliver_tool_result(...)`.
4. If `status == "WAITING_APPROVAL"`, read `pending_action.approval_type` and
   `pending_action.approval_payload`, present it to an approver, then call
   `resolve_approval(...)`.
5. Stop on `SUCCESS`, `FAILED`, or `DEAD`.

## 4. Production notes

* Keep these examples as thin wrappers; put retries, logging, and metrics in
  your own adapter.
* Persist `trace_id`, `workflow_id`, and `job_id` on submission.
* Honor `Retry-After` on HTTP 429.
* Treat all HTTP 422 responses as non-retriable input errors.
