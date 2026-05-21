# Business Continuity & Disaster Recovery Policy

**Document ID:** TBP-POL-BC-001
**Version:** 2.2
**Effective Date:** 1 January 2026
**Policy Owner:** Chief Operating Officer (COO)
**Approver:** Board Risk & Compliance Committee

---

## 1. Purpose

This policy establishes ThaBytePay's framework for maintaining critical
business operations during disruptions and recovering systems and services
after major incidents. It ensures the Group can continue to serve customers,
meet regulatory obligations, and protect assets under adverse conditions.

## 2. Scope

This policy applies to all business units, technology services, and
third-party providers supporting critical processes. It covers operational
continuity, technology disaster recovery, crisis communications, and
post-event recovery.

## 3. Definitions

- **Business Continuity (BC):** The capability to continue delivery of
  products and services at acceptable predefined levels following a
  disruption.
- **Disaster Recovery (DR):** The technology subset of BC; the process of
  restoring IT systems after disruption.
- **Recovery Time Objective (RTO):** The maximum acceptable time for a
  process or system to be unavailable.
- **Recovery Point Objective (RPO):** The maximum acceptable amount of data
  loss measured in time.
- **Business Impact Analysis (BIA):** Assessment of the impact of disruption
  on each business process.
- **Disaster Declaration:** Formal invocation of DR procedures by the COO
  or delegate.

## 4. Policy Statements

### 4.1 Business Impact Analysis

A BIA is performed at least every 24 months for all business processes. The
BIA identifies:

- Process criticality (Tier-1 to Tier-4)
- RTO and RPO per process
- Resource dependencies (systems, people, third parties)
- Maximum tolerable downtime

### 4.2 Process Criticality and Recovery Targets

| Tier | Description | RTO | RPO |
|------|-------------|-----|-----|
| Tier-1 | Mission-critical (payments, card auth, ATM/POS, mobile banking) | 1 hour | 5 minutes |
| Tier-2 | Critical customer-facing (branches, agency network) | 4 hours | 1 hour |
| Tier-3 | Internal business (HR systems, back-office) | 24 hours | 12 hours |
| Tier-4 | Non-critical (reporting, analytics dashboards) | 72 hours | 24 hours |

### 4.3 Technology DR Architecture

- **Primary data centre:** Nairobi (Tier-3 facility).
- **Disaster recovery data centre:** Mombasa (geographically diverse,
  Tier-3 facility).
- **Cloud workloads:** Multi-region active-active for Tier-1 systems.
- **Replication:** Synchronous replication for Tier-1 data; asynchronous
  for Tier-2 and below.
- **Backup:** Daily full backups retained for 30 days; weekly retained for
  6 months; monthly retained for 7 years.

### 4.4 Crisis Management Team (CMT)

The CMT convenes for any event with potential Tier-1 impact or major
reputational risk. Composition:

- COO (Chair)
- CISO
- CFO
- Chief People Officer
- Head of Communications
- Head of Customer Experience
- Heads of affected business units
- Legal Counsel

The CMT meets within 1 hour of activation and decides on declaration of
disaster, customer communications, and external engagement.

### 4.5 Disaster Declaration

A disaster is declared when:

- One or more Tier-1 processes are expected to remain unavailable beyond
  their RTO, OR
- The primary data centre is rendered unusable, OR
- A major external event (pandemic, civil unrest, regulatory directive)
  necessitates BC plan activation

Authority to declare: COO, with concurrence from CISO for technology
disasters or CFO for financial disasters.

### 4.6 Customer Communications During Disruption

- Status page updates within 30 minutes of confirmed incident affecting
  customer-facing services.
- SMS notifications to affected customers within 1 hour for outages
  exceeding 30 minutes.
- Branch and agent network notification through the internal communications
  channel.
- Media engagement only through the Head of Communications.

### 4.7 Testing

- Each Tier-1 system: full failover test annually.
- Each Tier-2 system: failover test biennially.
- CMT tabletop exercise: quarterly.
- End-to-end BC exercise (simulated regional outage): annually.

Test failures result in remediation plans tracked by the COO until closure.

### 4.8 Workforce Continuity

- Critical roles have documented succession in place.
- Key system documentation is maintained centrally and not held only by
  individuals.
- Remote work capability (per Remote Work Policy) provides resilience
  against site-specific disruptions.

### 4.9 Third-Party Continuity

- All Tier-1 vendors must demonstrate documented BC plans.
- Tier-1 vendor failure scenarios are tested annually.
- The Group maintains contingency arrangements for critical vendor
  dependencies.

### 4.10 Post-Event Review

After every disaster declaration or major BC plan activation:

- A formal post-event review is held within 15 business days
- Findings are documented and shared with the Board Risk & Compliance
  Committee
- Lessons learned drive updates to plans, runbooks, and this policy

## 5. Roles & Responsibilities

- **Board Risk & Compliance Committee:** Approves this policy and reviews
  programme effectiveness annually.
- **COO:** Owns this policy and the BC programme.
- **CISO:** Owns technology DR and coordinates with COO.
- **Business Unit Heads:** Maintain BC plans for their functions.
- **BC Coordinator:** Day-to-day coordination of BC activities.
- **All Employees:** Participate in exercises and follow plans during
  activation.

## 6. Compliance & Enforcement

The BC programme is subject to:

- Internal audit at least annually
- Regulator inspection as required (Central Bank operational resilience
  requirements)
- Independent external review every 36 months

## 7. Related Policies

- Information Security Policy (TBP-POL-IS-001)
- Incident Response Policy (TBP-POL-IR-001)
- Data Protection & Privacy Policy (TBP-POL-DP-001)
- POS Terminal Management Policy (TBP-POL-PT-001)
- Card Issuance & Management Policy (TBP-POL-CI-001)
- Remote Work Policy (TBP-POL-RW-001)

## Document Control

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 2.0 | 2024-07-01 | COO | Cloud multi-region active-active introduced |
| 2.1 | 2025-09-10 | COO | Refined RTOs; quarterly CMT tabletop frequency |
| 2.2 | 2026-01-01 | COO | Added third-party continuity testing requirement |
