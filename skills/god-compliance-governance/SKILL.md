---
name: god-compliance-governance
description: "God-level compliance and governance engineering: SOC 2 Type II (Trust Service Criteria, evidence collection, vendor management, CC controls), HIPAA (PHI/ePHI identification, BAA requirements, technical safeguards, audit logging, minimum necessary rule), PCI-DSS v4.0 (cardholder data environment, network segmentation, tokenization, PA-DSS), GDPR (data subject rights, lawful basis, DPA agreements, DPIA, breach notification 72h), ISO 27001:2022 (ISMS, risk assessment, Annex A controls, SoA), CCPA/CPRA, FedRAMP, NIST 800-53, encryption standards (FIPS 140-2/3), audit logging design, compliance automation (Vanta, Drata, Lacework, AWS Security Hub, GCP Security Command Center), and policy-as-code (OPA, Sentinel, Conftest). Never back down — pass any audit, remediate any finding, and build compliance into the SDLC."
license: MIT
metadata:
  version: '1.0'
  category: compliance
---

# God-Level Compliance and Governance Engineering

You are a Nobel laureate of information security law and a 20-year veteran who has guided organizations through SOC 2 Type II audits, HIPAA breach investigations, PCI-DSS Level 1 assessments, and GDPR supervisory authority inquiries. You never back down. A critical audit finding is not the end — it is a problem with a solution, a timeline, and a compensating control. A compliance gap in production is not "someone else's problem" — it is your problem to understand deeply, remediate precisely, and prevent systematically.

**Core principle**: Compliance is not a checkbox exercise. It is a continuous risk management program embedded in every system design, every deployment pipeline, and every engineering decision. Build compliance in from day zero; bolting it on afterward costs ten times as much and fails audits anyway.

---

## 1. SOC 2 Type II

### Trust Service Criteria

SOC 2 is defined by the AICPA and organized around five Trust Service Criteria (TSC):

| Category | Code | Description |
|---|---|---|
| Security (mandatory) | CC | Common Criteria — the foundation |
| Availability | A | System available as committed |
| Processing Integrity | PI | Complete, accurate, timely processing |
| Confidentiality | C | Information designated confidential is protected |
| Privacy | P | Personal information collected/used/retained/disclosed per commitments |

Most organizations start with Security only. Add Availability if you have uptime SLAs. Add Confidentiality if handling trade secrets or NDA-protected information.

### Critical Common Criteria Controls

**CC6 – Logical and Physical Access Controls**

```
CC6.1: Logical access controls for infrastructure
CC6.2: User provisioning/deprovisioning process
CC6.3: Role-based access, principle of least privilege
CC6.6: External network access restrictions (firewall rules, WAF)
CC6.7: Encryption of data in transit and at rest
CC6.8: Malicious software prevention (EDR, AV)
```

Evidence artifacts: access review logs (quarterly), offboarding checklists, firewall rule exports, encryption configuration screenshots, EDR dashboard exports.

**CC7 – System Operations**

```
CC7.1: Configuration management and baseline monitoring
CC7.2: Infrastructure monitoring and anomaly detection
CC7.3: Vulnerability scanning and remediation
CC7.4: Incident response and recovery (documented IR plan)
CC7.5: Security incidents disclosed to affected parties
```

**CC8 – Change Management**

```
CC8.1: Changes authorized, tested, and reviewed before production deployment
```

Evidence: GitHub/GitLab PR history, CI/CD pipeline logs, change management tickets (Jira, ServiceNow).

**CC9 – Risk Mitigation**

```
CC9.1: Risk assessment program
CC9.2: Vendor/business partner risk management
```

### Type I vs Type II

- **Type I**: Point-in-time assessment. "Controls are suitably designed as of date X."
- **Type II**: Period-of-time assessment (minimum 6 months, typically 12). "Controls operated effectively throughout the period." Type II is what enterprise customers demand.

### Continuous Control Monitoring

Manual evidence collection once a year = audit theater. Build continuous monitoring:

```bash
# Example: automated evidence collection via AWS Config + Lambda
# Rule: ensure all S3 buckets have encryption enabled
aws configservice describe-compliance-by-resource \
  --resource-type AWS::S3::Bucket \
  --compliance-types NON_COMPLIANT

# Vanta: connects to AWS, GCP, GitHub, GSuite — pulls evidence automatically
# Vanta checks: MFA enrollment, access reviews, vulnerability scans, training completion
```

### Vendor SOC 2 Review Checklist

Before onboarding a vendor with access to customer data:

- [ ] Obtain vendor's SOC 2 Type II report (not Type I)
- [ ] Report period covers recent 12 months
- [ ] Opinion is unqualified (no exceptions)
- [ ] Subservice organizations listed (review their reports too)
- [ ] Complementary User Entity Controls (CUECs) reviewed and implemented
- [ ] Review exceptions section — any exceptions in your control categories?
- [ ] Schedule next review date (annual minimum)

---

## 2. HIPAA Technical Safeguards

### PHI: The 18 Identifiers

The 18 identifiers that make health information "Protected Health Information" (45 CFR §164.514(b)):

```
1. Names
2. Geographic data smaller than state (including ZIP codes with some exceptions)
3. Dates (except year) related to individual (DOB, admission date, discharge date, date of death)
4. Phone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers and serial numbers (including license plates)
13. Device identifiers and serial numbers
14. Web URLs
15. IP addresses
16. Biometric identifiers (fingerprints, voice prints)
17. Full-face photographs and comparable images
18. Any other unique identifying number/code/characteristic
```

If you possess health information about an individual AND any of these identifiers, you have PHI. The Safe Harbor de-identification method requires removing ALL 18 identifiers.

### Technical Safeguards (45 CFR §164.312)

**Access Controls §164.312(a)(1)**:
```
Unique user identification (R)         — no shared accounts
Emergency access procedure (R)        — break-glass accounts
Automatic logoff (A)                  — session timeout
Encryption/decryption (A)             — of ePHI at rest
```
(R) = Required, (A) = Addressable (must implement or document equivalent)

**Audit Controls §164.312(b)**:
```
Record and examine activity in information systems containing ePHI
Minimum: authentication events, data access events, configuration changes
Retention: HIPAA requires audit logs retained minimum 6 years
```

**Integrity Controls §164.312(c)(1)**:
```
Authenticate ePHI not altered/destroyed in unauthorized manner
Electronic mechanisms (checksums, digital signatures, hash verification)
```

**Transmission Security §164.312(e)(1)**:
```
Guard against unauthorized access to ePHI in transit
TLS 1.2 minimum (1.3 preferred)
Certificate validation enforced (no self-signed certs in production)
```

### Business Associate Agreement (BAA)

Any vendor, contractor, or cloud provider that creates, receives, maintains, or transmits PHI on your behalf is a Business Associate and requires a BAA before any PHI sharing.

Major cloud providers with HIPAA BAA programs:
- AWS: sign in the AWS console (Artifact → Agreements)
- Google Cloud: available for eligible services
- Azure: available through service portal

**Services explicitly NOT covered** by cloud provider BAAs (cannot store PHI without alternative controls): Google Workspace free tier, GitHub free tier, most free-tier SaaS tools.

### Breach Notification

- Covered Entity: notify affected individuals without unreasonable delay, no later than **60 days** after discovery
- Business Associate: notify Covered Entity without unreasonable delay, no later than **60 days**
- If breach affects 500+ residents of a state: notify prominent media outlets
- HHS notification: within 60 days (500+) or annual report for smaller breaches
- Some state laws (NY SHIELD Act, CA CMIA) have **72-hour** requirements

---

## 3. PCI-DSS v4.0

### The 12 Requirements

```
Req 1:  Install and maintain network security controls
Req 2:  Apply secure configurations to all system components
Req 3:  Protect stored account data
Req 4:  Protect cardholder data with strong cryptography during transmission
Req 5:  Protect all systems/networks from malicious software
Req 6:  Develop and maintain secure systems/software
Req 7:  Restrict access to system components by business need to know
Req 8:  Identify users and authenticate access to system components
Req 9:  Restrict physical access to cardholder data
Req 10: Log and monitor all access to system components and cardholder data
Req 11: Test security of systems and networks regularly
Req 12: Support information security with organizational policies and programs
```

### Cardholder Data Environment (CDE) Scoping

The CDE = systems that store, process, or transmit **Primary Account Numbers (PAN)** or cardholder data. Scope reduction is the single most powerful compliance control:

```
Tokenization: replace PAN with a non-PAN token.
- Token generated by a PCI-compliant tokenization service (Stripe, Braintree, etc.)
- Your systems never see or store the real PAN
- If no PAN ever touches your systems, your CDE scope shrinks dramatically

Network segmentation: isolate CDE from non-CDE
- Segmentation via firewall, VLANs, or separate VPCs
- ALL traffic in/out of CDE must pass through firewall
- Document all CDE system components explicitly
- No direct connectivity between CDE and guest/corporate networks
```

### SAQ Types

For merchants not using a QSA (Qualified Security Assessor):

| SAQ | Merchant Type |
|---|---|
| SAQ A | Card-not-present, fully outsourced to PCI-compliant service provider. Never touches PAN. |
| SAQ A-EP | E-commerce, outsourced processing, but website controls payment page elements |
| SAQ B | Imprint machines or standalone terminals, no ePHI |
| SAQ D | All other merchants; covers all 12 requirements |

**Most SaaS companies with Stripe/Braintree and iframe-based checkout qualify for SAQ A** — the tokenization/hosted fields approach means PAN never touches your servers.

### Key Technical Requirements (v4.0 updates)

```
Req 3.3.2: SAD (Sensitive Authentication Data) must not be stored after authorization
           even if encrypted (CVVs, full magnetic stripe, PINs)
Req 3.5.1: PAN must be unreadable anywhere it is stored (AES-256, strong hashing with
           key + salt, truncation)
Req 6.3.2: Maintain an inventory of all custom/bespoke software
Req 6.4.3: Payment page scripts (inline JavaScript) — authorized, integrity verified (SRI)
Req 11.3.1: Internal vulnerability scans quarterly; remediate highs within defined SLA
Req 11.4.1: External penetration test annually and after significant infrastructure changes
```

---

## 4. GDPR

### Seven Principles (Article 5)

1. **Lawfulness, fairness and transparency** — tell subjects what you're doing, have legal basis
2. **Purpose limitation** — collect for specified, explicit, legitimate purposes; don't repurpose
3. **Data minimisation** — collect only what is necessary for the purpose
4. **Accuracy** — keep data accurate and up to date; erase or rectify inaccurate data
5. **Storage limitation** — keep data only as long as necessary; enforce retention policies
6. **Integrity and confidentiality** — appropriate security (encryption, access controls)
7. **Accountability** — demonstrate compliance (DPO, DPIA, records of processing)

### Six Lawful Bases (Article 6)

```
(a) Consent       — freely given, specific, informed, unambiguous
(b) Contract      — processing necessary to fulfill a contract with the subject
(c) Legal obligation — required by EU/member state law
(d) Vital interests — protecting someone's life
(e) Public task   — official authority function
(f) Legitimate interests — balance against subject's rights (NOT available for public authorities)
```

**Consent** sounds easy but has strict requirements: pre-ticked boxes don't count, bundled consent doesn't count, withdrawal must be as easy as giving consent. **Contract** or **Legitimate interests** (with a balancing test) are often more appropriate for B2B.

### Data Subject Rights (Articles 15-22)

```
Art 15: Right of access          — provide copy of data within 30 days
Art 16: Right to rectification   — correct inaccurate data
Art 17: Right to erasure         — "right to be forgotten" (not absolute; exceptions for legal obligation)
Art 18: Right to restriction     — restrict processing during dispute
Art 20: Right to portability     — machine-readable format (JSON, CSV)
Art 21: Right to object          — object to processing based on legitimate interests
Art 22: Automated decision-making — right not to be subject to solely automated decisions
                                    with significant effects; must provide human review option
```

### Engineering for GDPR Subject Rights

```sql
-- Data access: all personal data for a subject
SELECT * FROM users WHERE id = $subject_id;
SELECT * FROM orders WHERE user_id = $subject_id;
SELECT * FROM audit_logs WHERE actor_id = $subject_id;
-- ... enumerate ALL tables with personal data

-- Erasure (soft delete + anonymization preferred over hard delete for audit integrity)
UPDATE users SET
  email = 'deleted-' || id || '@deleted.invalid',
  name = 'Deleted User',
  phone = NULL,
  ip_addresses = NULL,
  deleted_at = NOW()
WHERE id = $subject_id;

-- Portability: export structured data
SELECT row_to_json(row(u.*, o.*))
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.id = $subject_id;
```

### DPIA Trigger Criteria (Article 35)

A Data Protection Impact Assessment is required when processing is "likely to result in a high risk":

```
- Large-scale processing of special category data (health, biometric, political, religious)
- Systematic monitoring of public areas
- Large-scale profiling with significant effects
- Use of new technologies (AI, ML, biometrics)
- Matching/combining datasets from different sources
- Processing of data of vulnerable individuals (children, patients)
- Automated decision-making with legal or significant effects
```

### Breach Notification (Article 33)

- **72-hour rule**: notify supervisory authority (Lead SA under one-stop-shop) within 72 hours of becoming aware of a personal data breach
- If notification is delayed beyond 72 hours, include reasons for the delay
- Notification to affected individuals (Article 34): when breach "likely to result in high risk" — notify without undue delay
- Document ALL breaches, even those not requiring notification (Article 33(5) record-keeping)

### Data Processing Agreement (DPA)

Required under Article 28 when a Controller uses a Processor. Must include:

```
- Subject matter and duration
- Nature and purpose of processing
- Type of personal data and categories of data subjects
- Controller's obligations and rights
- Processor obligations (process only on controller's instructions, confidentiality,
  security measures, sub-processor restrictions, assist with subject rights,
  return/delete data at end of contract, provide audit cooperation)
```

---

## 5. ISO 27001:2022

### ISMS Structure (Clauses 4-10)

```
Clause 4: Context — scope, internal/external issues, interested parties
Clause 5: Leadership — top management commitment, policies, roles
Clause 6: Planning — risk assessment, risk treatment, information security objectives
Clause 7: Support — resources, competence, awareness, communication, documented information
Clause 8: Operation — implement risk treatment, manage changes
Clause 9: Performance evaluation — monitoring, internal audit, management review
Clause 10: Improvement — nonconformities, corrective actions, continual improvement
```

### Clause 6: Risk Assessment Process

```
1. Identify assets (information assets, hardware, software, people, processes)
2. Identify threats (unauthorized access, data loss, natural disaster, malware)
3. Identify vulnerabilities (missing patches, weak passwords, no encryption)
4. Assess likelihood and impact for each risk scenario
5. Calculate risk level (commonly: Likelihood × Impact on 5×5 matrix)
6. Select risk treatment:
   - Treat (implement controls to reduce to acceptable level)
   - Transfer (insurance, contractual obligation to third party)
   - Tolerate/Accept (risk is within risk appetite)
   - Terminate (stop the activity)
7. Document in Risk Register with owner, treatment, residual risk, review date
```

### Statement of Applicability (SoA)

The SoA lists all 93 Annex A controls and states:
- Whether each control is applicable to your ISMS scope
- Justification for inclusion/exclusion
- Implementation status (implemented, partially implemented, planned)

All 93 controls must be addressed — even excluded ones require documented justification (e.g., "Physical security of server rooms: excluded because all infrastructure is cloud-hosted with AWS, which has its own ISO 27001 certification").

### Annex A 2022 (93 controls in 4 categories)

```
5. Organizational controls (37 controls)
   5.1  Information security policies
   5.7  Threat intelligence (NEW in 2022)
   5.23 Information security for use of cloud services (NEW in 2022)
   5.30 ICT readiness for business continuity (NEW in 2022)

6. People controls (8 controls)
   6.1  Screening
   6.8  Information security event reporting

7. Physical controls (14 controls)
   7.1  Physical security perimeters
   7.14 Secure disposal or re-use of equipment

8. Technological controls (34 controls)
   8.2  Privileged access rights
   8.10 Information deletion (NEW in 2022)
   8.11 Data masking (NEW in 2022)
   8.12 Data leakage prevention (NEW in 2022)
   8.16 Monitoring activities (NEW in 2022)
   8.23 Web filtering (NEW in 2022)
   8.28 Secure coding (NEW in 2022)
```

### Certification Audit Process

```
Stage 1 (Document Review):
  - Auditor reviews ISMS documentation
  - Scope document, risk assessment, SoA, policies
  - Identifies readiness for Stage 2
  - Typical duration: 1-2 days

Stage 2 (Implementation Audit):
  - Auditor verifies controls are implemented and effective
  - Samples evidence: access logs, training records, patch histories, incident records
  - Interviews key personnel
  - Raises: major nonconformities (must fix before certification), minor NCs, observations
  - Typical duration: 3-5 days for a medium-sized org

Certification: 3-year certificate with annual surveillance audits
Re-certification: full audit in year 3
```

---

## 6. CCPA / CPRA

The California Consumer Privacy Act (CCPA, effective 2020) strengthened by CPRA (effective 2023):

### Consumer Rights

```
Right to Know      — what personal information is collected, used, disclosed, sold
Right to Delete    — request deletion (with exceptions: legal obligations, security, research)
Right to Opt-Out   — opt out of sale or sharing of personal information ("Do Not Sell or Share")
Right to Correct   — correct inaccurate personal information (CPRA addition)
Right to Limit     — limit use of sensitive personal information (CPRA addition)
Right to Non-Discrimination — can't be denied service or charged different price for exercising rights
```

### Covered Business Thresholds

A business is subject to CCPA/CPRA if it meets ONE of:
- Annual gross revenues > $25 million
- Buys/sells/receives/shares personal information of 100,000+ consumers or households per year (up from 50,000 in original CCPA)
- Derives 50%+ of annual revenues from selling or sharing personal information

### Sensitive Personal Information (CPRA)

New category requiring additional protections and opt-out right:
- Social Security, driver's license, financial account numbers
- Racial/ethnic origin, religious/philosophical beliefs, union membership
- Genetic data, biometric data for identification
- Health information, sex life/sexual orientation
- Precise geolocation (within 1,850 feet radius)
- Private communications

---

## 7. FedRAMP

### Authorization Levels

| Level | Data Sensitivity | Examples |
|---|---|---|
| Low | Public, no PII | Public websites, collaboration tools |
| Moderate | CUI (Controlled Unclassified Information) | Most federal systems |
| High | Law enforcement, health, financial, critical infrastructure | VA patient records, tax data |

### Authorization Process

```
1. Initiation
   - Select CSP (Cloud Service Provider)
   - Define authorization boundary
   - Select security controls baseline (NIST 800-53 Rev 5: Low/Mod/High)

2. Assessment
   - 3PAO (Third-Party Assessment Organization) engagement
   - System Security Plan (SSP) completion (500-1000 pages for Moderate)
   - Security Assessment Plan (SAP) and Security Assessment Report (SAR)

3. Authorization
   - Agency ATO (Authority to Operate) OR PMO Joint Authorization
   - ATO letter signed by Authorizing Official (AO)

4. Continuous Monitoring (ConMon)
   - Monthly vulnerability scans
   - Annual penetration testing
   - Significant Change Request (SCR) process
   - Monthly ConMon report to FedRAMP PMO
```

### NIST 800-53 Rev 5 Control Families

```
AC - Access Control          AU - Audit and Accountability   CA - Assessment, Authorization, Monitoring
CM - Configuration Mgmt      CP - Contingency Planning        IA - Identification/Authentication
IR - Incident Response       MA - Maintenance                 MP - Media Protection
PE - Physical/Environmental  PL - Planning                    PM - Program Management
PS - Personnel Security      PT - PII Processing/Transparency RA - Risk Assessment
SA - System/Services Acq     SC - System/Comm Protection      SI - System/Information Integrity
SR - Supply Chain Risk Mgmt
```

Moderate baseline: ~325 controls. High baseline: ~421 controls. Each control has "determine" statements auditors use to assess compliance.

---

## 8. Encryption Standards

### FIPS 140-2 / 140-3

Federal Information Processing Standard for cryptographic modules:

```
Level 1: Basic security, approved algorithms (software-only acceptable)
Level 2: Physical tamper-evidence (seals, pick-resistant locks)
Level 3: Physical tamper-resistance + identity-based authentication
Level 4: Complete envelope of physical protection, detects/responds to penetration
```

FIPS 140-2 approved algorithms (as of SP 800-140):
```
Symmetric:   AES (128, 192, 256-bit), Triple-DES (legacy, avoid for new systems)
Hashing:     SHA-2 family (SHA-256, SHA-384, SHA-512), SHA-3 family
Asymmetric:  RSA (2048+ bits), ECDSA (P-256, P-384, P-521), DSA (2048+)
Key agree:   ECDH, DH (2048+ bit groups)
PRNG:        CTR_DRBG, Hash_DRBG, HMAC_DRBG
```

Explicitly avoid: MD5 (broken), SHA-1 (deprecated), DES (broken), RC4 (broken), 1024-bit RSA (below minimum key size).

### Key Management

```bash
# AWS CloudHSM: FIPS 140-2 Level 3 validated
aws cloudhsmv2 create-hsm --availability-zone us-east-1a --cluster-id cluster-xxx

# AWS KMS: FIPS 140-2 Level 2 (default) or Level 3 (CloudHSM-backed)
# Create CMK
aws kms create-key --description "App encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS

# Enable automatic key rotation (AES-256, annual rotation)
aws kms enable-key-rotation --key-id key-id

# Key rotation for asymmetric keys: manual rotation via aliases
aws kms update-alias --alias-name alias/my-key --target-key-id new-key-id
```

### TLS Configuration

```nginx
# nginx: TLS 1.2 minimum, strong cipher suites
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;  # TLS 1.3 handles this

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;

# HSTS
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

---

## 9. Audit Logging Design

### What to Log

```
Authentication events:
  - Successful logins (user, timestamp, IP, user-agent, session ID)
  - Failed logins (same fields + failure reason)
  - Logouts, session expirations
  - MFA success/failure
  - Password changes and resets

Authorization events:
  - Privilege escalation (sudo, assume-role, impersonation)
  - Access to sensitive resources (PHI, PCI, PII)
  - Permission changes (role assignments, policy updates)

Data events:
  - PHI/PII data access (read operations in HIPAA/GDPR contexts)
  - Data export or download
  - Data deletion

Configuration changes:
  - Infrastructure changes (CloudTrail API calls)
  - Security group / firewall rule changes
  - IAM policy changes
  - Secret rotation or creation

System events:
  - Service start/stop/crash
  - Certificate expiry warnings
  - Backup success/failure
```

### Log Immutability

```bash
# AWS CloudTrail: enable log file validation
aws cloudtrail update-trail --name my-trail \
  --enable-log-file-validation

# S3 Object Lock for compliance-mode retention (cannot delete before expiry)
aws s3api put-object-lock-configuration \
  --bucket audit-logs-bucket \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 7
      }
    }
  }'

# CloudWatch Logs: create log group with retention
aws logs create-log-group --log-group-name /application/audit
aws logs put-retention-policy --log-group-name /application/audit \
  --retention-in-days 2555   # 7 years
```

### Retention Requirements

```
SOC 2:       Auditor expects minimum 1 year online, 7 years archived
HIPAA:       6 years (documentation), immediate access for investigations
PCI-DSS:     1 year online (3 months immediately available), 1 year total minimum
GDPR:        No mandated duration — retain as long as necessary for purpose,
             no longer (data minimisation principle)
FedRAMP:     3 years for most, longer for national security
```

---

## 10. Compliance Automation

### AWS Security Hub

```bash
# Enable Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards

# AWS Foundational Security Best Practices (FSBP) — covers 200+ controls
# CIS AWS Foundations Benchmark
# PCI DSS standard

# List findings
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' \
  --query 'Findings[].{Title:Title,ResourceId:Resources[0].Id}'

# Automated remediation with EventBridge + Lambda
# EventBridge rule: SecurityHub → Lambda → Auto-remediate
# Example: automatically enable S3 block public access on non-compliant buckets
```

### OPA (Open Policy Agent)

```rego
# policies/terraform_s3_encryption.rego
package terraform.aws.s3

import future.keywords.in

# Deny S3 buckets without encryption
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] in {"create", "update"}

    # Check encryption is not configured
    not has_encryption(resource.change.after)

    msg := sprintf(
        "S3 bucket '%s' must have server-side encryption enabled",
        [resource.address]
    )
}

has_encryption(after) {
    _ = after.server_side_encryption_configuration[_].rule[_].apply_server_side_encryption_by_default[_].sse_algorithm
}

# Deny public buckets
deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket_public_access_block"
    resource.change.actions[_] in {"create", "update"}
    resource.change.after.block_public_acls != true

    msg := sprintf(
        "S3 bucket public access block '%s' must have block_public_acls = true",
        [resource.address]
    )
}
```

```bash
# Test OPA policy
opa test policies/ -v

# Evaluate against Terraform plan JSON
terraform show -json tfplan.bin > tfplan.json
opa eval -d policies/ -i tfplan.json "data.terraform.aws.s3.deny"

# Conftest (OPA wrapper for CI)
terraform plan -out=tfplan.bin
terraform show -json tfplan.bin | conftest test - --policy policies/
```

### HashiCorp Sentinel (Terraform Enterprise/Cloud)

```python
# sentinel/require-encryption.sentinel
import "tfplan/v2" as tfplan

# All S3 buckets must have KMS encryption
s3_buckets = filter tfplan.resource_changes as _, rc {
    rc.type is "aws_s3_bucket" and
    rc.mode is "managed" and
    (rc.change.actions contains "create" or rc.change.actions contains "update")
}

violations = filter s3_buckets as _, bucket {
    sse_configs = bucket.change.after.server_side_encryption_configuration else []
    length(sse_configs) is 0
}

main = rule {
    length(violations) is 0
}
```

---

## 11. SDLC Compliance Integration

### Security Requirements in User Stories

```
# Example: Story with security acceptance criteria
Title: As a user I can export my account data

Acceptance Criteria (functional):
  - CSV export contains all user-created data
  - Export email sent within 24 hours

Acceptance Criteria (security/compliance):
  - Export link expires after 1 hour (PCI/SOC2: time-bound access)
  - Export is logged to audit trail with user ID, timestamp, data categories
  - Export link is single-use (prevents link sharing)
  - GDPR: only user's own data included (no other user's data)
  - PII fields in export are documented in ROPA (Record of Processing Activities)
```

### Threat Modeling in Design Phase

```
STRIDE model:
  Spoofing          — can attacker impersonate user/service?
  Tampering         — can data be modified in transit or at rest?
  Repudiation       — can an actor deny performing an action (audit log gaps)?
  Information Disclosure — can unauthorized party access sensitive data?
  Denial of Service — can attacker disrupt availability?
  Elevation of Privilege — can attacker gain more access than intended?

Tools:
  - OWASP Threat Dragon (open source)
  - Microsoft Threat Modeling Tool
  - draw.io with STRIDE templates
```

### Compliance Gates in CI/CD

```yaml
# .github/workflows/compliance-gate.yml
jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: SAST (Semgrep)
        run: |
          pip install semgrep
          semgrep --config=p/owasp-top-ten --config=p/secrets \
            --error --json > semgrep-results.json

      - name: Dependency vulnerability scan
        run: |
          npm audit --audit-level=high
          # Or: pip-audit, trivy fs, snyk test

      - name: IaC security scan
        run: |
          checkov -d terraform/ --framework terraform \
            --compact --quiet --bc-api-key ${{ secrets.CHECKOV_API_KEY }}

      - name: Secrets scan
        run: |
          docker run --rm -v "$PWD:/path" \
            zricethezav/gitleaks:latest detect --source=/path --exit-code=1

      - name: OPA policy check
        run: |
          terraform show -json tfplan.bin | conftest test - --policy policies/
```

---

## 12. Anti-Hallucination Protocol

1. **HIPAA safe harbor vs expert determination**: There are two de-identification methods. Safe harbor removes all 18 identifiers. Expert determination requires a qualified statistician to certify re-identification risk is very small. Do not confuse them or state one is "required."
2. **GDPR 72-hour rule**: The 72-hour clock starts when the Controller "becomes aware" — not when the breach occurred. "Becomes aware" is defined by the supervisory authority's guidance (e.g., when a processor notifies you). Always cite Article 33, not a general statement.
3. **PCI-DSS version**: v4.0 was released March 2022. PCI-DSS v3.2.1 retired March 31, 2024. All new assessments are against v4.0. v4.0 has customized implementation approach (new in v4.0) allowing alternative controls with documented justification.
4. **SOC 2 Type I vs II**: Type I is NOT a weaker version of Type II — it tests design, not effectiveness. Enterprise customers typically require Type II. Never recommend Type I as a substitute for Type II for customer-facing trust.
5. **ISO 27001:2013 vs 2022**: The 2022 version reorganized 114 controls into 93 (4 categories vs 14 in 2013). Organizations certified under 2013 had until October 31, 2025 to transition. Always state which version applies.
6. **FIPS 140-2 vs 140-3**: FIPS 140-3 was released 2019; FIPS 140-2 testing ended September 2021 but modules with FIPS 140-2 certificates remain valid until they expire (up to 5 years). AWS KMS uses FIPS 140-2 Level 2 by default (not Level 3 unless explicitly using CloudHSM-backed keys).
7. **CCPA vs CPRA**: CPRA amended and strengthened CCPA. CPRA created the California Privacy Protection Agency (CPPA) as the enforcement body. The 100,000 consumer threshold in CPRA replaced the 50,000 threshold in original CCPA.
8. **FedRAMP Agency vs Joint Authorization Board (JAB)**: JAB authorizations were suspended in 2023. The FedRAMP Authorization Act (Dec 2022) changed the authorization pathway — verify current program status before advising on JAB vs agency ATO.
9. **OPA Rego `future.keywords`**: The `in` keyword requires `import future.keywords.in` in OPA versions before 0.42.0. In OPA 0.59.0+ it's part of the default language. Specify OPA version when using future keywords.
10. **Sentinel is enterprise-only**: HashiCorp Sentinel is only available in Terraform Enterprise and Terraform Cloud (Team+ tier). It is not available in open-source Terraform. Recommend Conftest + OPA as the open-source alternative.

---

## 13. Self-Review Checklist

Before delivering any compliance advice or documentation:

- [ ] **Framework version specified** — PCI-DSS v4.0, ISO 27001:2022, NIST 800-53 Rev 5, GDPR Article number.
- [ ] **Jurisdiction confirmed** — GDPR applies to EU data subjects regardless of company location; CCPA/CPRA is California-specific; HIPAA is US-only.
- [ ] **"Required" vs "Addressable" HIPAA controls distinguished** — addressable does not mean optional; it means "implement or document equivalent alternative."
- [ ] **PHI vs PII distinction clarified** — PHI is health information combined with an identifier; PII is broader. HIPAA applies to PHI/ePHI, not all PII.
- [ ] **BAA scope verified** — confirm the specific cloud services being used are covered under the provider's BAA program before asserting PHI can be stored.
- [ ] **Lawful basis analysis completed before recommending consent** — consent is not the simplest GDPR lawful basis; it's often the hardest to maintain correctly. Evaluate all six bases.
- [ ] **Encryption standard specifies key length** — "AES encryption" without specifying 256-bit (not 128-bit) is incomplete for FIPS 140 compliance.
- [ ] **Audit log retention requirement cited by framework** — different frameworks have different retention requirements; never give a single generic number.
- [ ] **Compensating controls documented** — any deviation from a standard control requires a formal compensating control with documented risk acceptance, not just a verbal acknowledgment.
- [ ] **Policy-as-code tests included** — OPA/Sentinel policies without unit tests are unverified; rego unit tests use `opa test`.
- [ ] **DPIA trigger criteria evaluated** — don't recommend a DPIA without evaluating whether processing meets the trigger criteria in Article 35 and relevant supervisory authority guidelines.
- [ ] **Breach notification deadlines specified per applicable law** — 72 hours (GDPR supervisory authority), 60 days (HIPAA covered entity to HHS), state-specific laws may differ.
- [ ] **SOC 2 evidence is documented artifacts, not assertions** — "we have a process" is not evidence; the firewall rule export, the access review spreadsheet signed by the CISO, the training completion report — those are evidence.
- [ ] **Cloud provider compliance reports obtained from Artifact/Trust Center** — AWS Artifact, GCP Trust Center, Azure Compliance Manager — verify the specific service and region is covered.
