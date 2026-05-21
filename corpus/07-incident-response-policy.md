# Incident Response Policy

**Document ID:** TBP-POL-IR-001
**Version:** 3.2
**Effective Date:** 1 January 2026
**Policy Owner:** Chief Information Security Officer (CISO)
**Approver:** Board Risk & Compliance Committee

---

## 1. Purpose

This policy defines how ThaBytePay detects, classifies, responds to,
communicates about, and learns from security and operational incidents. The
goal is to minimise customer impact, contain damage, and meet regulatory
notification obligations.

## 2. Scope

This policy applies to all incidents affecting Group information assets,
customer data, financial transactions, or service availability. It covers
employees, agents, and third-party providers operating on the Group's behalf.

## 3. Definitions

- **Incident:** Any event that disrupts, or threatens to disrupt, the
  confidentiality, integrity, or availability of Group services or data.
- **Event:** A potential precursor to an incident (e.g., a suspicious log
  entry that has not yet been confirmed as malicious).
- **Severity:** Classification of impact, from SEV1 (catastrophic) to SEV4
  (minor).
- **Incident Commander (IC):** The on-call lead during active response.
- **Post-Incident Review (PIR):** The blameless review meeting held after
  every SEV1, SEV2, and SEV3 incident.

## 4. Policy Statements

### 4.1 Severity Classification

| Severity | Description | Examples | Response SLA |
|----------|-------------|----------|--------------|
| SEV1 | Catastrophic; customer-facing outage or major data breach | Core banking down; PII breach affecting >1000 customers | Response within 15 minutes |
| SEV2 | Significant; partial outage or contained data exposure | Single channel down; targeted phishing successful | Response within 1 hour |
| SEV3 | Limited; degraded performance or internal-only issue | Slow login; non-customer service down | Response within 4 hours |
| SEV4 | Minor; no customer impact | Stale dashboard; non-critical job failure | Response within 1 business day |

### 4.2 Detection and Reporting

Incidents may be detected through:

- SIEM alerts (24/7 SOC monitoring)
- Automated health checks and synthetic monitoring
- Customer reports via Customer Care
- Employee reports via the internal reporting tool or SOC hotline
- Third-party notifications (vendors, law enforcement, regulators)

**Any employee suspecting an incident must report immediately** to the SOC
(security@thabytepay.com or extension 9999). Underreporting is a violation of
this policy.

### 4.3 Incident Response Lifecycle

The Group follows a six-phase lifecycle:

1. **Detection:** Initial identification and triage by the SOC.
2. **Containment:** Stop the bleeding; isolate affected systems.
3. **Eradication:** Remove the cause (malware, unauthorised access, etc.).
4. **Recovery:** Restore service to normal operation.
5. **Notification:** Communicate to affected parties, regulators, and
   leadership as required.
6. **Post-Incident Review:** Blameless review and action items.

### 4.4 Incident Commander Authority

For SEV1 and SEV2 incidents, an IC is assigned within 15 minutes of
declaration. The IC has authority to:

- Page any employee, including executives
- Make production changes outside change management process (with mandatory
  retrospective approval)
- Engage external resources (vendors, legal counsel, law enforcement)
- Approve customer communications in coordination with Communications team

### 4.5 Customer Notification

| Scenario | Notification Requirement |
|----------|--------------------------|
| Service outage > 30 minutes | Status page update + SMS to affected customers |
| Data breach affecting customers | Direct notification within 72 hours (per DP Policy) |
| Suspected card fraud | Card hotlisting + customer call within 4 hours |
| Confirmed phishing campaign | Group-wide alert + customer advisory |

### 4.6 Regulator Notification

The MLRO and Compliance team handle regulator notifications. Key timelines:

- **Data Protection Commissioner:** Within 72 hours of confirmed personal
  data breach with risk to data subjects.
- **Central Bank operational incident report:** Within 24 hours for major
  operational disruptions.
- **Financial Reporting Centre:** STR within statutory timeline (where
  applicable).

### 4.7 Evidence Handling

- Logs, memory dumps, disk images, and other evidence must be preserved with
  chain-of-custody documentation.
- The Information Security team maintains the forensic capability.
- Evidence must be retained until the longer of (a) 7 years or (b)
  resolution of any associated legal/regulatory matter.

### 4.8 Post-Incident Review

A PIR is held within 10 business days of incident closure for SEV1, SEV2, and
SEV3 incidents. The PIR:

- Is **blameless** — focuses on systems and processes, not individuals
- Produces a written report distributed to relevant leadership
- Generates action items with owners and deadlines
- Identifies any policy or training gaps

### 4.9 Tabletop Exercises

The CISO sponsors at least one tabletop exercise per quarter, simulating
plausible incidents. Findings inform updates to runbooks and this policy.

## 5. Roles & Responsibilities

- **CISO:** Owns this policy and the incident response programme.
- **SOC:** Detection, triage, initial containment.
- **Incident Commander (rotational):** Coordinates active response.
- **Communications Team:** Customer and external messaging.
- **Compliance Team:** Regulator notifications.
- **All Employees:** Must report suspected incidents and not impede response.

## 6. Compliance & Enforcement

Failure to report a known or suspected incident is a serious policy violation.
Performance during incidents is assessed for SOC and IC staff but not used
punitively against individuals in blameless PIRs.

## 7. Related Policies

- Information Security Policy (TBP-POL-IS-001)
- Data Protection & Privacy Policy (TBP-POL-DP-001)
- KYC & AML Compliance Policy (TBP-POL-KA-001)
- Business Continuity & Disaster Recovery Policy (TBP-POL-BC-001)
- Agency Banking Operations Policy (TBP-POL-AB-001)

## Document Control

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 3.1 | 2025-02-10 | CISO | Added severity matrix and quarterly tabletop requirement |
| 3.2 | 2026-01-01 | CISO | Tightened SEV1 response SLA and notification timelines |
