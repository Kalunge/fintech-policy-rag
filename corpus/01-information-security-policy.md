# Information Security Policy

**Document ID:** TBP-POL-IS-001
**Version:** 4.2
**Effective Date:** 1 January 2026
**Policy Owner:** Chief Information Security Officer (CISO)
**Approver:** Board Risk & Compliance Committee

---

## 1. Purpose

This policy defines ThaBytePay's baseline information security requirements
across all business units, technology environments, and third-party engagements.
It exists to protect the confidentiality, integrity, and availability of
information assets entrusted to the Group by customers, employees, partners, and
regulators.

## 2. Scope

This policy applies to:

- All employees, contractors, interns, and temporary staff of ThaBytePay.
- All Group subsidiaries operating retail banking, agency banking, card issuance,
  POS acquiring, and digital wallet services.
- All third-party service providers and vendors with logical or physical access
  to Group systems.
- All information assets owned, leased, licensed, or otherwise operated by the
  Group, including production, staging, test, and development environments.

## 3. Definitions

- **Information Asset:** Any data, system, application, network, or device that
  stores, processes, or transmits Group information.
- **Confidential Information:** Customer data, financial records, authentication
  credentials, cryptographic keys, source code, and any data classified as
  Restricted or Confidential per the Data Protection & Privacy Policy.
- **Privileged Access:** Access rights that allow modification of security
  configurations, user permissions, or critical business logic.

## 4. Policy Statements

### 4.1 Access Control

Access to Group systems is granted on a least-privilege basis. The default state
for any new account is no access until an access request is approved by the
employee's line manager and the relevant system owner.

- **Multi-factor authentication (MFA)** is required for all employees on all
  administrative consoles, source code repositories, cloud provider portals,
  and any system handling customer financial data.
- **Privileged access** must be requested through the Privileged Access
  Management (PAM) system. Sessions are recorded and time-bound, with a
  maximum session length of 8 hours.
- **Access reviews** must be performed quarterly. System owners are responsible
  for revoking access for terminated employees within 24 hours of termination.

### 4.2 Password Management

- Minimum password length: 14 characters.
- Passwords must include at least one uppercase letter, one lowercase letter,
  one number, and one special character.
- Passwords expire every 180 days for standard users and every 90 days for
  privileged users.
- Reuse of the last 12 passwords is prohibited.
- Service account passwords must be stored in the approved enterprise secrets
  manager (HashiCorp Vault). Hardcoded credentials in source code are
  strictly forbidden.

### 4.3 Encryption

- **Data in transit** must be encrypted using TLS 1.2 or higher. Internal
  service-to-service communication must use mutual TLS where feasible.
- **Data at rest** must be encrypted using AES-256 or stronger. Encryption keys
  must be managed through the Key Management Service (KMS) provided by the
  Group's approved cloud provider.
- **Key rotation:** Symmetric encryption keys must be rotated at least every
  365 days; asymmetric keys at least every 730 days. PIN encryption keys for
  POS terminals are rotated every 90 days per the POS Terminal Management Policy.

### 4.4 Network Security

- All production networks must be segmented from corporate networks. Direct
  routing from a developer laptop to a production database is prohibited.
- Bastion hosts are the only permitted entry point to production environments
  and require MFA.
- Inbound traffic to production is restricted to documented service ports.
  Default-deny is the standard for all firewall rules.
- All external-facing services must be protected by a Web Application Firewall
  (WAF) configured with the OWASP Core Rule Set or equivalent.

### 4.5 Endpoint Security

- All Group-issued laptops and mobile devices must run the approved Endpoint
  Detection & Response (EDR) agent.
- Full-disk encryption is mandatory.
- Unauthorized software installation on Group devices is prohibited; only
  software available in the approved software catalogue may be installed
  without explicit IT approval.
- Lost or stolen devices must be reported within 1 hour to the IT Service Desk
  for remote wipe.

### 4.6 Logging and Monitoring

- Security-relevant events (authentication, authorization changes, data
  access, privilege escalation) must be logged centrally in the SIEM.
- Logs are retained for a minimum of 365 days, with logs related to
  financial transactions retained for 7 years per regulatory requirements.
- Critical security alerts must trigger paging of the Security Operations
  Centre (SOC), which is staffed 24/7.

### 4.7 Vulnerability Management

- All production systems are scanned at least weekly using approved
  vulnerability scanners.
- Critical vulnerabilities (CVSS 9.0+) must be remediated within 7 days.
- High vulnerabilities (CVSS 7.0-8.9) must be remediated within 30 days.
- Medium vulnerabilities must be remediated within 90 days.
- Exceptions require documented risk acceptance from the CISO or delegate.

### 4.8 Third-Party Risk

Before onboarding a vendor with access to Group data or systems:

- A security assessment must be completed by the Information Security team.
- The vendor must sign a Data Processing Agreement aligned with the Data
  Protection & Privacy Policy.
- Vendor access is subject to the same access control and MFA requirements
  as employee access.

## 5. Roles & Responsibilities

- **Board Risk & Compliance Committee:** Approves this policy and reviews
  security posture quarterly.
- **Chief Information Security Officer (CISO):** Owns this policy, security
  strategy, and major risk decisions.
- **Security Operations Centre (SOC):** 24/7 monitoring, incident triage,
  initial containment.
- **System Owners:** Responsible for access control, vulnerability remediation,
  and security configuration of their assigned systems.
- **All Employees:** Must complete annual security awareness training and
  report suspected security incidents promptly.

## 6. Compliance & Enforcement

Violations of this policy may result in disciplinary action up to and including
termination, in line with the Employee Code of Conduct. Violations that constitute
criminal activity will be reported to law enforcement and regulatory bodies as
required.

Compliance is monitored through:

- Quarterly access reviews
- Annual penetration testing of customer-facing systems
- Continuous SIEM monitoring
- Annual third-party security audit

## 7. Related Policies

- Data Protection & Privacy Policy (TBP-POL-DP-001)
- Incident Response Policy (TBP-POL-IR-001)
- Acceptable Use Policy (TBP-POL-AU-001)
- Business Continuity & Disaster Recovery Policy (TBP-POL-BC-001)
- KYC & AML Compliance Policy (TBP-POL-KA-001)

## Document Control

| Version | Date | Author | Change Summary |
|---------|------|--------|----------------|
| 4.0 | 2024-01-15 | CISO | Major rewrite for cloud-native operations |
| 4.1 | 2025-04-10 | CISO | Updated MFA requirements and PAM session limits |
| 4.2 | 2026-01-01 | CISO | Added vendor MFA requirement and refined CVSS timelines |
