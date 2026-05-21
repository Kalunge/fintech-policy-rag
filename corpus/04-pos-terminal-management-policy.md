# POS Terminal Management Policy

**Document ID:** TBP-POL-PT-001
**Version:** 2.0
**Effective Date:** 1 January 2026
**Policy Owner:** Head of Merchant Acquiring
**Approver:** Chief Operations Officer

---

## 1. Purpose

This policy governs the deployment, operation, monitoring, and decommissioning
of Point-of-Sale (POS) terminals used by ThaBytePay merchants to accept card
payments. It ensures terminal estate integrity, customer card data security,
and operational continuity.

## 2. Scope

This policy applies to:

- All POS terminals issued under ThaBytePay's merchant acquiring licence
- All staff involved in terminal onboarding, deployment, support, and
  decommissioning
- All systems integrated with the POS estate including the POS Switch, Terminal
  Management System (TMS), and Estate Monitoring Dashboard
- Third-party deployment partners under signed Service Level Agreements

## 3. Definitions

- **POS Terminal:** Any certified hardware device used to accept card payments
  on the Group's network (countertop, mobile, mPOS, or SoftPOS).
- **Merchant:** A legal entity contracted to accept card payments through a POS
  terminal.
- **TID:** Terminal Identifier — unique ID assigned to each terminal.
- **MID:** Merchant Identifier — unique ID assigned to each merchant.
- **Key Block:** Encrypted package containing PIN encryption keys (PEK) and
  message authentication keys (MAK).

## 4. Policy Statements

### 4.1 Terminal Procurement and Certification

- Only terminal models on the Group's Approved Hardware List may be deployed.
- All terminals must be **PCI PTS certified** (current version).
- Software loaded onto terminals must be certified against EMV Level 1, EMV
  Level 2, and the relevant card scheme rules (Visa, Mastercard, Verve).
- Procurement decisions for new terminal models require approval from the
  Head of Merchant Acquiring and the Information Security team.

### 4.2 Merchant Onboarding

A merchant may receive a POS terminal only after:

- KYC verification per Section 5 of the KYC & AML Compliance Policy
- Business risk assessment (low/medium/high risk categorisation)
- Site visit by the Merchant Operations team for medium and high-risk merchants
- Execution of a Merchant Services Agreement
- Settlement account setup
- Initial Merchant Training (minimum 2 hours)

High-risk merchants (cash advance, online gambling, FX bureaus) require
additional approval from the Head of Compliance.

### 4.3 Terminal Deployment

- Each terminal must be deployed with a unique TID linked to a single MID at
  the time of deployment.
- Initial key injection must occur at the Group's secure Key Loading Facility
  or via an approved Remote Key Injection (RKI) service.
- Terminals must be sealed with tamper-evident labels before dispatch.
- Deployment is logged in the TMS with deployment officer, merchant location,
  and serial numbers.

### 4.4 Key Management

- **PIN encryption keys (PEK)** are rotated every 90 days.
- **Message authentication keys (MAK)** are rotated every 365 days.
- Key rotation is performed remotely via the TMS during off-peak hours (02:00
  to 04:00 local time).
- Failed key rotations are escalated to the Estate Operations team within
  1 hour.
- Manual key loading is permitted only as a fallback and requires dual control
  (two authorised key custodians).

### 4.5 Transaction Monitoring

The POS estate is monitored 24/7 by the Estate Operations Centre. Key metrics:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Uptime per terminal | 99.5% monthly | Below 98% triggers field visit |
| Transaction success rate | 98.5% | Below 95% triggers investigation |
| Settlement reconciliation accuracy | 99.99% | Any mismatch >100 KES |
| Tamper alarms | 0 | Any alarm triggers immediate suspension |
| Velocity (per terminal) | Risk-based | Anomalies flagged in real time |

### 4.6 Tamper Detection and Response

Terminals that report a tamper alarm must be:

1. **Suspended immediately** in the TMS to prevent further transactions
2. Recovered from the merchant within 24 hours by the Field Services team
3. Quarantined at the secure terminal store pending forensic review
4. Reviewed by the Information Security team within 5 business days
5. Either re-certified for deployment or securely destroyed

Material tamper incidents must be escalated per the Incident Response Policy.

### 4.7 Card Data Handling

- POS terminals must not store cardholder data beyond what is permitted by
  PCI DSS.
- Full PANs must be masked on customer receipts (display only the last 4
  digits).
- CVV2 / CVC2 values must never be stored.
- Logs and reports containing card data must be encrypted at rest.

### 4.8 Decommissioning

Terminals are decommissioned when:

- The merchant relationship ends
- The terminal reaches end-of-life (typically 5 years)
- The terminal fails recertification
- A tamper investigation requires destruction

Decommissioned terminals must have all keys zeroised, all stored data wiped,
and either be returned to the supplier for refurbishment or physically
destroyed. Destruction is witnessed and recorded.

### 4.9 Settlement

- Settlement to merchant accounts occurs daily by 11:00 local time for
  transactions processed before the 23:00 cutoff the previous day.
- Disputes (chargebacks, customer claims) follow the timelines mandated by
  the relevant card scheme.

## 5. Roles & Responsibilities

- **Head of Merchant Acquiring:** Owns this policy and the overall channel
- **Estate Operations Centre:** 24/7 monitoring and Tier-1 support
- **Field Services Team:** Physical deployment, swap-out, recovery
- **Merchant Risk Team:** Onboarding KYC, ongoing risk monitoring
- **Information Security:** Key management oversight, tamper investigations

## 6. Compliance & Enforcement

The POS estate is subject to:

- Annual PCI DSS audit by a Qualified Security Assessor (QSA)
- Card scheme audits as scheduled by Visa / Mastercard
- Internal audit at least annually
- Regulatory inspections as required

## 7. Related Policies

- Information Security Policy (TBP-POL-IS-001)
- KYC & AML Compliance Policy (TBP-POL-KA-001)
- Agency Banking Operations Policy (TBP-POL-AB-001)
- Incident Response Policy (TBP-POL-IR-001)
- Card Issuance & Management Policy (TBP-POL-CI-001)

## Document Control

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 1.4 | 2024-08-01 | Head of Merchant Acquiring | Introduced SoftPOS in approved hardware list |
| 2.0 | 2026-01-01 | Head of Merchant Acquiring | Refresh aligned with PCI DSS v4.0 |
