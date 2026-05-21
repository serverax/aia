# Security Baseline Criteria

## Purpose

This document defines how Sprint 8 OWASP ZAP baseline results are interpreted for `compliance-service`. It separates release-blocking findings from warnings that can be accepted, documented, or deferred.

## Pass Criteria

Sprint 8 security baseline passes only when:

- Critical findings: `0`
- High findings: `0` unless explicitly approved by the security owner
- Medium findings: `<= 5`, each documented with remediation or risk acceptance
- Low findings: logged and triaged
- Informational findings: logged only unless they expose secrets, credentials, or client data
- ZAP execution target is verified as the correct Talos/Sprint 8 endpoint
- No scan failure, target failure, or wrong-context evidence is present

If `FAIL-NEW > 0`, the default decision is `FAIL` until reviewed.

## Severity Matrix

| Severity | Release Decision | Examples | Required Action |
| --- | --- | --- | --- |
| Critical | Block | Remote code execution, auth bypass, exposed admin token, direct secret disclosure | Stop release, escalate to security, patch or rollback |
| High | Block by default | SQL/command injection, stored XSS, unrestricted privileged endpoint, sensitive data exposure | Security owner approval required to proceed |
| Medium | Conditional | Missing auth on non-sensitive endpoint, weak header policy, unsafe redirect with limited impact | Fix before release or document accepted risk |
| Low | Non-blocking | Server header version leak, cacheable 404, missing optional header | Record for Sprint 9 tuning |
| Informational | Non-blocking | Spider warnings, expected 404s, scanner coverage notices | Record only |

## OWASP Categories Relevant To Compliance Service

The following categories matter most for `compliance-service`:

- Injection: policy inputs must not trigger command, template, SQL, or log injection.
- Broken authentication: write/admin endpoints must require authorized operator identity.
- Broken access control: agent/project/capability checks must not be bypassable.
- Sensitive data exposure: API keys, policy state, audit data, and client identifiers must not leak.
- Security misconfiguration: debug headers, stack traces, default credentials, unsafe CORS, broad ingress.
- Vulnerable and outdated components: runtime images and dependencies must be supported and scanned.
- Identification and authentication failures: no unauthenticated mutation of kill-switch policy.
- Software and data integrity failures: container image provenance and ConfigMap runtime exceptions must be tracked.
- SSRF and outbound misuse: policy evaluation must not fetch arbitrary user-supplied URLs.

## Known ZAP False Positives And Handling

| Finding | Typical Cause | Handling |
| --- | --- | --- |
| Server version header exposed | Python/BaseHTTP or nginx default header | Low severity; remove in Sprint 9 unless paired with exploitable version |
| Cacheable 404 responses | Minimal HTTP server lacks cache-control headers | Informational; add `Cache-Control: no-store` for error responses |
| Spider expected 404 on `/` | Service only exposes `/health`, `/ready`, `/compliance/evaluate` | Non-blocking if documented and core endpoints pass |
| Missing CSP header | API-only JSON service has no browser-rendered UI | Low/conditional; required if serving HTML |
| Missing anti-clickjacking header | API-only service not rendered in browser | Low/conditional; required if UI pages are added |
| Cookie flags missing | Service does not set cookies | False positive if no cookies are present |

False positives must include:

- ZAP rule ID
- affected URL
- reason it is safe
- owner accepting or deferring the risk
- target Sprint for remediation if needed

## Post-Scan Review Checklist

- [ ] Confirm target URL is the intended Sprint 8 environment.
- [ ] Confirm scan completed successfully.
- [ ] Record `FAIL-NEW`, `WARN-NEW`, `INFO`, and `PASS` counts.
- [ ] Review every critical/high item manually.
- [ ] Confirm no credentials or client data appear in response bodies, headers, URLs, or logs.
- [ ] Confirm write endpoints are not exposed without auth.
- [ ] Confirm expected 404s are not hiding route misconfiguration.
- [ ] Confirm warnings are either fixed, deferred to Sprint 9, or risk-accepted.
- [ ] Attach ZAP report to Sprint 8 release evidence.

## Escalation Rules

Escalate to security immediately when:

- Any critical finding appears.
- Any high finding appears.
- ZAP discovers exposed secrets, tokens, API keys, or client data.
- ZAP discovers unauthenticated mutation of kill-switch or policy state.
- Scanner output suggests the target is not the expected environment.

Escalate to platform/ops when:

- ZAP cannot reach the target.
- Ingress returns unexpected upstream errors.
- The scan hits AKS/local/stale context instead of Talos/Sprint 8 target.

Do not escalate for known low-severity header tuning items unless they combine with a concrete exploit path.

## Sprint 9 Tuning Backlog

Known non-blocking items to schedule:

- Strip or normalize `Server` response headers.
- Add `Cache-Control: no-store` on 4xx/5xx responses.
- Add explicit JSON error bodies for unsupported paths.
- Add production image provenance and image scan evidence.
- Replace placeholder runtime with packaged compliance-service image and `imagePullSecret` if required.
