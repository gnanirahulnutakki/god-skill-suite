---
name: god-security-cloud
description: "God-level cloud security skill covering CSPM (Cloud Security Posture Management), CWPP (Cloud Workload Protection), CIEM (Cloud Infrastructure Entitlement Management), AWS-native security services (GuardDuty, Security Hub, Macie, Inspector, Config, CloudTrail), Azure Defender for Cloud, GCP Security Command Center, misconfiguration detection patterns, cloud attack kill chains, lateral movement in cloud environments, data exfiltration detection, and multi-cloud security operations. Treats every public S3 bucket, every open security group, every unused admin role as an active incident. Never fabricates security service names or AWS Config rule names."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Cloud Security

## The Researcher-Warrior Identity

Cloud security is the fastest-moving threat landscape in existence. The same speed that lets a team deploy 50 microservices in a day also lets one misconfigured IAM role become a company-ending breach by evening. You operate at the intersection of IAM, networking, compute, and data — because cloud attacks don't respect service boundaries.

Every public S3 bucket, every security group with `0.0.0.0/0`, every unused admin role with standing access, every EC2 instance running without IMDSv2 — these are not configuration annoyances. These are active incidents waiting for a threat actor to press the trigger. You treat them accordingly.

**Non-negotiable operating principles**:
- Misconfiguration is the #1 cloud attack vector — more common than zero-days by an order of magnitude.
- The blast radius of a compromised cloud identity scales with the permissions of that identity. Minimize both.
- Logging that you can't query quickly is security theater. If you can't find an attacker in your logs in 15 minutes, the logs aren't working.
- Multi-cloud increases attack surface. Having three clouds without unified visibility is worse than having one cloud with fragmented visibility.
- Cloud attack kill chains move faster than on-premises ones. Lateral movement from initial access to data exfiltration can happen in under 10 minutes.

**Anti-Hallucination Rules (Cloud Security-Specific)**:
- NEVER fabricate AWS Config managed rule names. Verify at: https://docs.aws.amazon.com/config/latest/developerguide/managed-rules-by-aws-config.html
- NEVER invent GuardDuty finding type names. Verify at: https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-active.html
- NEVER fabricate Security Hub standard names or control IDs. Verify at: https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-standards.html
- NEVER claim a KQL query works without testing — Sentinel KQL has specific table names and schemas
- NEVER invent GCP Security Command Center finding source names
- If unsure about a specific service capability, say so and provide the documentation URL

**Verification commands (run before asserting)**:
```bash
# List all GuardDuty findings in a region
aws guardduty list-findings --detector-id <detectorId> --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}' --region us-east-1

# List all Security Hub findings
aws securityhub get-findings --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}'

# List all AWS Config rules
aws configservice describe-config-rules --output table

# List non-compliant resources for a specific rule
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name <rule-name> \
  --compliance-types NON_COMPLIANT

# CloudTrail event lookup (last 24 hours)
aws cloudtrail lookup-events \
  --start-time $(date -d '24 hours ago' +%s) \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateUser
```

---

## Phase 1: Cloud Shared Responsibility Model

### 1.1 The Model (Per Service Type)

The shared responsibility model defines what you own vs. what the cloud provider owns. Misunderstanding this is the root cause of most cloud breaches.

**Infrastructure as a Service (IaaS)** — e.g., EC2, GCE, Azure VMs:
| Layer | Cloud Owns | You Own |
|-------|-----------|---------|
| Physical | ✓ | |
| Hypervisor | ✓ | |
| Compute/Networking/Storage (hardware) | ✓ | |
| Guest OS | | ✓ |
| Runtime | | ✓ |
| Application | | ✓ |
| Data | | ✓ |
| Identity/Access | | ✓ |
| Network config (security groups, NACLs) | | ✓ |

**Platform as a Service (PaaS)** — e.g., RDS, App Engine, Azure App Service:
- Cloud owns: OS, runtime, patching of the managed service
- You own: Application code, data, access control, configuration of the service, who has access

**Software as a Service (SaaS)** — e.g., Salesforce, Microsoft 365, Workday:
- Cloud owns: Everything infrastructure, platform, and application
- You own: Data, user access management, data residency settings, audit log retention

**Critical insight**: In IaaS, you own the guest OS. An unpatched EC2 instance is entirely your vulnerability. In RDS (PaaS), you don't own OS patching — but you do own the database configuration, the security group rules, and who has database credentials. The model shifts but you never own nothing.

### 1.2 The Misunderstanding That Causes Breaches

Organizations assume: "We moved to the cloud — security is the cloud provider's problem now."
Reality: The cloud provider secures the data center, the hypervisor, and the managed service infrastructure. You secure everything built on top of it.

AWS, Azure, and GCP are responsible for a breach of their physical infrastructure. You are responsible for a breach caused by a public S3 bucket, an open security group, a leaked IAM key, or an unpatched OS on your EC2 instance. **These are on you.**

---

## Phase 2: CSPM — Cloud Security Posture Management

### 2.1 What CSPM Detects

CSPM continuously audits cloud configuration against security benchmarks:
- CIS (Center for Internet Security) Benchmarks for AWS, Azure, GCP
- NIST SP 800-53
- SOC 2, PCI-DSS, HIPAA, ISO 27001 frameworks

### 2.2 Top 10 Cloud Misconfigurations (Most Common, Most Dangerous)

**1. Publicly accessible cloud storage (S3, GCS, Azure Blob)**
- Every S3 bucket public-access block should be enabled at account level
- S3 Block Public Access (account-level setting) — if not enabled, any bucket can be made public
- Detection: AWS Config rule `s3-bucket-public-read-prohibited`, `s3-bucket-public-write-prohibited`

**2. Overly permissive security groups / NSGs**
- Port 22 (SSH) open to `0.0.0.0/0` — every scanner, bot, and threat actor hits this
- Port 3306 (MySQL), 5432 (PostgreSQL), 1433 (MSSQL) open to internet = data exposure
- Detection: AWS Config rule `restricted-ssh`, `restricted-common-ports`

**3. Root/admin account without MFA**
- AWS root account without MFA is a single password away from full account takeover
- Detection: AWS Config rule `root-account-mfa-enabled`, IAM Credential Report
- Fix: Enable MFA on root, then never use it (use IAM roles instead)

**4. IAM users with unused credentials (access keys > 90 days)**
- Stale access keys are credentials that have likely leaked and haven't been detected
- Detection: IAM Credential Report; AWS Config rule `access-keys-rotated`
- Fix: Rotate every 90 days maximum; prefer roles over long-lived keys

**5. Unencrypted data at rest**
- EBS volumes not encrypted (EC2 data at rest)
- S3 buckets without default encryption
- RDS instances without storage encryption
- Detection: AWS Config rules `ec2-ebs-encryption-by-default`, `s3-default-encryption-kms`, `rds-storage-encrypted`

**6. CloudTrail / logging disabled**
- No logging = no forensics = incident response in the dark
- Multi-region CloudTrail must be enabled to catch all API calls
- Detection: AWS Config rule `cloud-trail-enabled`, `multi-region-cloudtrail-enabled`

**7. No VPC Flow Logs**
- VPC Flow Logs record network traffic metadata — essential for detecting lateral movement, exfiltration, C2 communication
- Detection: AWS Config rule `vpc-flow-logs-enabled`

**8. Over-permissioned IAM roles and policies**
- Roles with `"Action": "*"` or `"Resource": "*"` without constraints
- Inline policies attached directly to users (no audit trail, no grouping)
- Detection: IAM Access Analyzer, AWS Config rule `iam-no-inline-policy-check`

**9. EC2 metadata service v1 (IMDSv1) enabled**
- IMDSv1 is session-less — any SSRF vulnerability can reach the metadata service and steal credentials
- IMDSv2 requires a session-oriented PUT request (adds SSRF protection)
- Detection: AWS Config rule `ec2-imdsv2-check`

**10. Publicly accessible databases/caches**
- RDS instances with `publicly_accessible = true`
- ElastiCache / Redis without auth token and exposed to internet
- Detection: AWS Config rule `rds-instance-public-access-check`

---

## Phase 3: Cloud Attack Kill Chain

### 3.1 The Phases (Cloud-Adapted)

Traditional kill chains are adapted for cloud environments. Cloud attacks are faster, more automated, and frequently start from credentials rather than malware.

**Phase 1: Initial Access**
- Exposed credentials in public GitHub repos (most common)
- Phishing → OAuth app consent → cloud credentials
- SSRF vulnerability → IMDS credential theft
- Publicly exposed admin panel (Kubernetes dashboard, Jupyter notebook, Grafana)
- Supply chain compromise (malicious package → CI/CD pipeline → cloud credentials)
- Leaked .env files, terraform.tfstate files, kubeconfig files

**Phase 2: Execution**
- Using stolen credentials to call cloud APIs
- Lambda function invocation for code execution
- Systems Manager Run Command on EC2 instances
- Container escape from compromised pod → node access

**Phase 3: Persistence**
- Creating new IAM users, access keys, or roles (backdoor identity)
- Adding SSO identity provider to trust org's IdP
- Creating Lambda layers or container images with backdoors
- Modifying user data scripts on EC2 launch configurations
- Creating CloudFormation stacks or Service Control Policies that ensure continued access

**Phase 4: Privilege Escalation**
- IAM privilege escalation (see Phase 3.2 below)
- Instance profile abuse: EC2 role has `iam:CreateRole` → escalate to higher-privilege role
- Lambda privilege escalation: pass a high-privilege role to a Lambda function you create

**Phase 5: Defense Evasion**
- Disabling GuardDuty, CloudTrail, or Security Hub
- Creating CloudTrail trails without S3 logging or with encryption keys you control
- Operating in regions without monitoring enabled
- Rotating compromised access keys to avoid detection of leaked key alerts

**Phase 6: Lateral Movement**
- Role chaining: AssumeRole from Account A → AssumeRole in Account B → AssumeRole in Account C
- Cross-account trust abuse: `"Principal": {"AWS": "*"}` on a role trust policy
- EC2 instance with a high-privilege role → extract role credentials from IMDS

**Phase 7: Exfiltration**
- Syncing S3 buckets to attacker-controlled storage
- Creating AMI snapshots and sharing with attacker account
- RDS snapshots shared with external account
- Bulk API data export (DynamoDB scan, CloudWatch logs, Secrets Manager bulk read)

### 3.2 IAM Privilege Escalation Patterns (AWS)

These are documented escalation paths. Know them so you can detect and block them. Verify current status at: https://bishopfox.com/blog/privilege-escalation-in-aws or Rhino Security Labs research.

Key escalation primitives:
- `iam:CreatePolicyVersion` — Create new version of existing policy with `"Action": "*"`
- `iam:AttachUserPolicy` / `iam:AttachRolePolicy` — Attach admin policy to yourself/role
- `iam:PassRole` + `ec2:RunInstances` — Launch EC2 with higher-privilege role, access IMDS
- `iam:PassRole` + `lambda:CreateFunction` + `lambda:InvokeFunction` — Create Lambda with admin role
- `iam:CreateAccessKey` on another user — Create access key for admin user
- `sts:AssumeRole` on a permissive trust policy — Directly assume admin role

Detection query (CloudTrail):
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AttachUserPolicy \
  --start-time $(date -d '24 hours ago' +%s)
```

---

## Phase 4: AWS-Native Security Services

### 4.1 AWS GuardDuty

GuardDuty is a managed threat detection service analyzing CloudTrail events, VPC Flow Logs, and DNS logs for threat indicators.

**Finding categories** (verify current list at AWS docs):
- `UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B` — Console login from unusual location
- `Recon:IAMUser/MaliciousIPCaller` — API calls from known malicious IP
- `PrivilegeEscalation:IAMUser/AdministrativePermissions` — IAM escalation pattern detected
- `Exfiltration:S3/ObjectRead.Unusual` — Unusual S3 object read patterns
- `CryptoCurrency:EC2/BitcoinTool.B!DNS` — Bitcoin mining DNS lookup from EC2
- `Trojan:EC2/BlackholeTraffic` — EC2 communicating with blackhole domain
- `UnauthorizedAccess:EC2/SSHBruteForce` — Brute force SSH attempts on EC2

```bash
# Enable GuardDuty in all regions (use AWS Organizations for org-wide)
aws guardduty create-detector --enable --finding-publishing-frequency FIFTEEN_MINUTES

# List high-severity findings
aws guardduty list-findings \
  --detector-id <detectorId> \
  --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}' \
  | xargs -I{} aws guardduty get-findings --detector-id <detectorId> --finding-ids {}

# Archive findings (after remediation)
aws guardduty archive-findings \
  --detector-id <detectorId> \
  --finding-ids <findingId1> <findingId2>
```

**Automated remediation pattern**: GuardDuty → EventBridge → Lambda → Quarantine
```
GuardDuty High-Severity Finding
  → EventBridge Rule (severity >= 7)
  → Lambda Function:
      - Attach explicit deny policy to compromised IAM principal
      - Isolate EC2 instance to quarantine security group
      - Create CloudWatch alarm for monitoring
      - Notify security team via SNS
```

### 4.2 AWS Security Hub

Security Hub aggregates findings from GuardDuty, Inspector, Macie, IAM Access Analyzer, and third-party tools. It runs compliance checks against security standards.

**Standards** (verify current list at AWS docs):
- CIS AWS Foundations Benchmark v1.4.0 and v3.0.0
- AWS Foundational Security Best Practices (FSBP)
- PCI DSS v3.2.1
- NIST SP 800-53 Rev. 5

```bash
# Enable Security Hub
aws securityhub enable-security-hub --enable-default-standards

# Get high/critical findings
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"},{"Value":"HIGH","Comparison":"EQUALS"}],"WorkflowStatus":[{"Value":"NEW","Comparison":"EQUALS"}]}' \
  --sort-criteria '[{"Field":"SeverityNormalized","SortOrder":"desc"}]'

# Aggregate findings across regions (Security Hub aggregation)
aws securityhub create-finding-aggregator --region-linking-mode ALL_REGIONS

# Get compliance score per standard
aws securityhub describe-standards-controls \
  --standards-subscription-arn arn:aws:securityhub:us-east-1::standards/aws-foundational-security-best-practices/v/1.0.0 \
  --control-status FAILED
```

### 4.3 AWS Config

Config records every configuration change to every supported resource. It detects drift and assesses compliance.

**Key managed rules** (NEVER fabricate rule names — verify at AWS documentation):
```bash
# List all available managed rules
aws configservice describe-config-rules --output json | jq '.ConfigRules[].ConfigRuleName'

# Commonly used rules (verify names before using):
# - access-keys-rotated (IAM access keys older than N days)
# - cloud-trail-enabled (CloudTrail must be enabled)
# - ec2-imdsv2-check (IMDSv2 must be required)
# - ec2-security-group-attached-to-eni (security groups attached to resources)
# - encrypted-volumes (EBS volumes must be encrypted)
# - iam-no-inline-policy-check (no inline IAM policies)
# - iam-password-policy (password policy meets requirements)
# - iam-root-access-key-check (root account has no access keys)
# - mfa-enabled-for-iam-console-access (console users must have MFA)
# - multi-region-cloudtrail-enabled (multi-region CloudTrail required)
# - rds-instance-public-access-check (RDS not publicly accessible)
# - restricted-ssh (no security group allows unrestricted SSH)
# - root-account-mfa-enabled (root account must have MFA)
# - s3-bucket-public-read-prohibited (S3 bucket not publicly readable)
# - s3-bucket-public-write-prohibited (S3 bucket not publicly writable)
# - vpc-flow-logs-enabled (VPC Flow Logs must be enabled)
```

**Conformance Packs** — pre-built sets of Config rules for compliance frameworks:
```bash
# Deploy a conformance pack
aws configservice put-conformance-pack \
  --conformance-pack-name "CIS-AWS-Foundations-Level-1" \
  --template-s3-uri s3://awsconfigconforms/AWS-Control-Tower-Detective-Guardrails.yaml
```

**Automated remediation with SSM Automation**:
```bash
# Associate a remediation with a Config rule
aws configservice put-remediation-configurations \
  --remediation-configurations '[{
    "ConfigRuleName": "restricted-ssh",
    "TargetType": "SSM_DOCUMENT",
    "TargetId": "AWS-DisablePublicAccessForSecurityGroup",
    "Automatic": true,
    "MaximumAutomaticAttempts": 3,
    "RetryAttemptSeconds": 60
  }]'
```

### 4.4 AWS CloudTrail

CloudTrail records every AWS API call. It is the foundational forensics tool for any cloud security investigation.

**What CloudTrail logs**:
- Management events: Control plane operations (creating EC2 instances, modifying IAM policies, changing security groups)
- Data events: Data plane operations on specific resources (S3 GetObject, DynamoDB GetItem, Lambda InvokeFunction) — **NOT enabled by default, must be configured explicitly**
- Insights events: Unusual API activity patterns (unusual spike in IAM API calls)

**What CloudTrail does NOT log**:
- Actions taken by AWS Support on your behalf (unless you enable it)
- Actions by AWS services acting as service principals on your behalf
- Data events not explicitly configured (S3 data access by default)
- Network traffic (use VPC Flow Logs for that)

```bash
# Create multi-region CloudTrail with log file validation
aws cloudtrail create-trail \
  --name organization-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --include-global-service-events \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456789012:log-group:CloudTrail \
  --cloud-watch-logs-role-arn arn:aws:iam::123456789012:role/CloudTrailCloudWatchRole

# Enable data events for S3
aws cloudtrail put-event-selectors \
  --trail-name organization-trail \
  --event-selectors '[{
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [{
      "Type": "AWS::S3::Object",
      "Values": ["arn:aws:s3:::"]
    }]
  }]'

# Validate log file integrity
aws cloudtrail validate-logs \
  --trail-arn arn:aws:cloudtrail:us-east-1:123456789012:trail/organization-trail \
  --start-time 2024-01-01T00:00:00Z
```

### 4.5 AWS Macie

Macie automatically discovers and protects sensitive data (PII, financial data, credentials) in S3.

```bash
# Enable Macie
aws macie2 enable-macie

# Create a classification job
aws macie2 create-classification-job \
  --job-type ONE_TIME \
  --name "PII-Discovery-All-Buckets" \
  --s3-job-definition '{
    "bucketDefinitions": [{"accountId": "123456789012", "buckets": ["*"]}]
  }' \
  --managed-data-identifier-selector ALL

# List findings
aws macie2 list-findings \
  --finding-criteria '{"criterion":{"severity.description":{"eq":["High","Critical"]}}}' \
  --output json
```

**Custom data identifiers** for organization-specific PII:
```bash
aws macie2 create-custom-data-identifier \
  --name "EmployeeID" \
  --regex "EMP-[0-9]{6}" \
  --description "Internal employee ID format"
```

### 4.6 AWS Inspector

Inspector provides automated vulnerability management for EC2 instances, ECR container images, and Lambda functions.

```bash
# Enable Inspector (uses AWS Organizations for org-wide)
aws inspector2 enable --resource-types EC2 ECR LAMBDA

# List critical findings
aws inspector2 list-findings \
  --filter-criteria '{"severity":[{"comparison":"EQUALS","value":"CRITICAL"}]}' \
  --sort-criteria '{"field":"SEVERITY","sortOrder":"DESC"}'

# Get finding statistics
aws inspector2 list-coverage-statistics --group-by RESOURCE_TYPE
```

---

## Phase 5: Azure Defender for Cloud

### 5.1 Secure Score

Defender for Cloud calculates a Secure Score (0-100%) based on your compliance with security recommendations. Each recommendation is weighted by severity.

```
Azure Portal > Defender for Cloud > Secure posture
Recommendations are organized by:
- Identity and access (MFA, service principal credentials)
- Data and storage (encryption, access control)
- Networking (open ports, firewall rules)
- Compute (OS updates, antimalware, endpoint protection)
```

**Key recommendations that lower score the most**:
- MFA not enabled for all users with subscription permissions
- Service principals with expiring credentials
- Public network access enabled on Azure resources
- Azure Kubernetes Service RBAC not enabled

### 5.2 Just-in-Time VM Access

JIT VM access restricts who can access a VM's management port (SSH/RDP) to a time-limited, approved window:

```bash
# Configure JIT access via Azure CLI
az security jit-policy initiate \
  --resource-group myRG \
  --vm-name myVM \
  --jit-policy-id /subscriptions/<subId>/resourceGroups/myRG/providers/Microsoft.Security/locations/eastus/jitNetworkAccessPolicies/default \
  --virtual-machines '[{
    "id": "/subscriptions/<subId>/resourceGroups/myRG/providers/Microsoft.Compute/virtualMachines/myVM",
    "ports": [{"number": 22, "allowedSourceAddressPrefix": "MY_IP", "endTimeUtc": "2024-01-01T18:00:00Z"}]
  }]'
```

### 5.3 Microsoft Sentinel (SIEM/SOAR)

Sentinel is Microsoft's cloud-native SIEM. Uses KQL (Kusto Query Language) for threat hunting.

Key KQL queries for threat hunting:
```kql
// Impossible travel detection
SigninLogs
| where ResultType == 0
| project TimeGenerated, UserPrincipalName, IPAddress, Location, UserAgent
| sort by UserPrincipalName, TimeGenerated asc
| serialize
| extend PrevLogin = prev(TimeGenerated, 1)
| extend PrevLocation = prev(Location, 1)
| extend TimeDiff = datetime_diff('minute', TimeGenerated, PrevLogin)
| where PrevLogin != TimeGenerated  // same user
| where TimeDiff < 60 and Location != PrevLocation  // different location within 1 hour
| project UserPrincipalName, Location, PrevLocation, TimeDiff, TimeGenerated

// Admin role assignments in last 24 hours
AuditLogs
| where TimeGenerated > ago(24h)
| where OperationName contains "Add member to role"
| extend Role = tostring(TargetResources[0].displayName)
| where Role in ("Global Administrator", "Privileged Role Administrator", "Security Administrator")
| project TimeGenerated, InitiatedBy, Role, TargetResources

// Bulk data access (potential exfiltration)
StorageBlobLogs
| where TimeGenerated > ago(1h)
| summarize count() by CallerIpAddress, AccountName
| where count_ > 1000  // Threshold: adjust based on baseline
| sort by count_ desc
```

---

## Phase 6: GCP Security Command Center

Security Command Center (SCC) is GCP's central security dashboard. It aggregates findings from GCP native scanners and third-party tools.

**Finding sources**:
- Security Health Analytics — detects misconfigurations (open firewall rules, public buckets, etc.)
- Web Security Scanner — DAST scanning for App Engine, GKE, and Compute Engine web apps
- Container Threat Detection — runtime threat detection for GKE
- Virtual Machine Threat Detection — memory-based threat detection for GCE VMs
- Event Threat Detection — detects threats in Cloud Logging

```bash
# List critical findings
gcloud scc findings list <organization-id> \
  --filter="state=ACTIVE AND severity=CRITICAL" \
  --format=json

# List findings by category
gcloud scc findings list <organization-id> \
  --filter="category=\"PUBLIC_BUCKET_ACL\" AND state=ACTIVE"

# Mark a finding as resolved
gcloud scc findings update-state <findingName> --state=INACTIVE
```

---

## Phase 7: CIEM — Cloud Infrastructure Entitlement Management

### 7.1 What CIEM Detects

CIEM identifies the gap between permissions granted and permissions actually used — the "entitlement sprawl" problem.

Key findings CIEM surfaces:
- **Over-permissioned identities**: A service account with `roles/editor` that only ever calls Cloud Storage APIs
- **Stale access**: IAM bindings for users who left the organization 6 months ago
- **Cross-account trust abuse**: Role trust policies that allow `"Principal": {"AWS": "*"}`
- **Shadow admins**: Identities that can escalate to admin via indirect paths (not direct admin role)
- **Unused credentials**: IAM access keys never used, federated identity unused in 90 days

### 7.2 AWS IAM Access Analyzer

Access Analyzer identifies resources shared with external entities (cross-account, cross-organization, public access).

```bash
# Create an analyzer
aws accessanalyzer create-analyzer \
  --analyzer-name organization-analyzer \
  --type ORGANIZATION

# List findings (external access)
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/organization-analyzer \
  --filter '{"status":{"eq":["ACTIVE"]}}' \
  --output json

# Validate an IAM policy (checks for common misconfigurations)
aws accessanalyzer validate-policy \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:*","Resource":"*"}]}' \
  --policy-type IDENTITY_POLICY

# Check unused access (requires IAM Access Analyzer with unused access configuration)
aws accessanalyzer list-findings-v2 \
  --analyzer-arn <analyzerArn> \
  --filter '{"findingType":{"eq":["UnusedIAMRole","UnusedIAMUserAccessKey","UnusedIAMUserPassword"]}}'
```

---

## Phase 8: Lateral Movement in Cloud Environments

### 8.1 SSRF → IMDS Exploitation (AWS)

The classic cloud lateral movement: SSRF vulnerability in a web application running on EC2 leads to metadata service access and credential theft.

**Attack path**:
1. Find SSRF in web app (URL parameter, webhook, PDF generator, image proxy)
2. Send request to `http://169.254.169.254/latest/meta-data/iam/security-credentials/`
3. Get role name from response
4. Fetch credentials: `http://169.254.169.254/latest/meta-data/iam/security-credentials/<ROLE_NAME>`
5. Use `AccessKeyId`, `SecretAccessKey`, and `Token` to authenticate to AWS

**Defense — IMDSv2**:
IMDSv2 requires a PUT request with a TTL-bounded session token before GET requests work. Standard SSRF attacks use GET, so they cannot obtain the session token.

```bash
# Enforce IMDSv2 on existing EC2 instances
aws ec2 modify-instance-metadata-options \
  --instance-id <instanceId> \
  --http-tokens required \
  --http-put-response-hop-limit 1

# Enforce IMDSv2 at account level (new instances)
aws ec2 modify-default-credit-specification --cpu-credits standard  # (different param)
# Actually enforce via Service Control Policy:
# Deny ec2:RunInstances if ec2:MetadataHttpTokens != "required"
```

SCP to enforce IMDSv2 on all new EC2 launches:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "ec2:RunInstances",
    "Resource": "arn:aws:ec2:*:*:instance/*",
    "Condition": {
      "StringNotEquals": {
        "ec2:MetadataHttpTokens": "required"
      }
    }
  }]
}
```

### 8.2 Role Chaining

Role chaining: AssumeRole from Account A's compromised principal → Role in Account B → Role in Account C.

Detection:
```bash
# Find all cross-account AssumeRole calls in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --start-time $(date -d '24 hours ago' +%s) \
  | jq '.Events[].CloudTrailEvent | fromjson | select(.requestParameters.roleArn | contains("arn:aws:iam") and (contains("123456789012") | not))'
```

### 8.3 Lambda Privilege Escalation

If a principal has `lambda:CreateFunction` + `iam:PassRole` + `lambda:InvokeFunction`, they can:
1. Create a Lambda function that exfiltrates environment variables or runs arbitrary code
2. Pass a high-privilege role to the function
3. Invoke the function to execute code with that role's permissions

Detection: CloudTrail events for `CreateFunction` + `PassRole` + `InvokeFunction` within a short time window from the same principal.

---

## Phase 9: Data Exfiltration Detection

### 9.1 S3 Exfiltration Patterns

CloudTrail + Athena query to detect bulk S3 reads:
```sql
-- Create Athena table over CloudTrail S3 logs first, then query:
SELECT useridentity.principalid, 
       count(*) as api_calls,
       sum(cast(json_extract_scalar(requestparameters, '$.contentLength') as bigint)) as bytes_read
FROM cloudtrail_logs
WHERE eventsource = 's3.amazonaws.com'
  AND eventname = 'GetObject'
  AND eventtime >= '2024-01-01T00:00:00Z'
GROUP BY useridentity.principalid
HAVING count(*) > 1000
ORDER BY api_calls DESC;
```

### 9.2 EC2 Snapshot Sharing

A common exfiltration technique: create AMI from compromised EC2, share with attacker's AWS account.

Detection via CloudTrail:
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ModifySnapshotAttribute \
  --start-time $(date -d '7 days ago' +%s) \
  | jq '.Events[].CloudTrailEvent | fromjson | select(.requestParameters.addUserGroup != null or .requestParameters.userId != null)'
```

---

## Self-Review Checklist: Cloud Security

**Logging and Visibility**
- [ ] CloudTrail enabled in all regions with multi-region trail; log file validation on
- [ ] CloudTrail S3 bucket: public access blocked, MFA delete enabled, server-side encryption enabled
- [ ] VPC Flow Logs enabled on all VPCs
- [ ] GuardDuty enabled in all regions, including delegated org administrator
- [ ] Security Hub enabled with CIS Foundations and AWS FSBP standards
- [ ] CloudTrail data events enabled for critical S3 buckets and Lambda functions
- [ ] Log retention: Security logs 1+ years in S3 Glacier; hot logs 90 days in CloudWatch

**IAM and Identity**
- [ ] Root account MFA enabled; root access keys deleted (verify: IAM Credential Report)
- [ ] All IAM users with console access have MFA
- [ ] IAM Access Analyzer enabled with organization-level analyzer
- [ ] No inline IAM policies (AWS Config rule `iam-no-inline-policy-check`)
- [ ] Access keys rotated within 90 days (AWS Config rule `access-keys-rotated`)
- [ ] IMDSv2 enforced on all EC2 instances; SCP enforcing for new launches
- [ ] No roles with trust policy `"Principal": {"AWS": "*"}`

**Network Security**
- [ ] No security group with SSH (22) or RDP (3389) open to `0.0.0.0/0`
- [ ] No security group with database ports open to internet
- [ ] VPC flow logs enabled for all VPCs
- [ ] S3 bucket public access block enabled at account level
- [ ] No RDS instances with `publicly_accessible = true`
- [ ] Private subnets for all backend services; NAT Gateway for outbound only

**Data Security**
- [ ] EBS encryption by default enabled for all regions
- [ ] S3 default encryption enabled on all buckets
- [ ] RDS storage encryption enabled
- [ ] AWS Macie enabled; PII findings reviewed weekly
- [ ] KMS key rotation enabled for all customer-managed keys

**CSPM and Compliance**
- [ ] AWS Security Hub Secure Score reviewed weekly; critical findings resolved within 24h
- [ ] AWS Config recording enabled for all resource types in all regions
- [ ] Non-compliant Config resources reviewed and remediated weekly
- [ ] GuardDuty high/critical findings remediated within 24h; automated quarantine for critical

**Incident Response**
- [ ] GuardDuty findings routed to EventBridge → Lambda automated response for critical findings
- [ ] Security runbooks documented for top 5 cloud attack scenarios
- [ ] Forensics access patterns defined (read-only forensics role, quarantine security group)
- [ ] Backup snapshots tested for recovery (not just created)

---

## Cross-Domain Connections

**Cloud Security → IAM**: Cloud security is 80% IAM. The most dangerous cloud attacks go through identity — stolen credentials, over-permissioned roles, SSRF to IMDS. Fix IAM first. CSPM findings about open S3 buckets and security groups are noise compared to an IAM role with `"Action": "*"` that can be assumed by any EC2 instance.

**Cloud Security → Networking**: SSRF attacks are the bridge between networking vulnerabilities and cloud IAM. A web application misconfiguration (following redirects to internal hosts, no URL allowlist) becomes a cloud IAM compromise via the IMDS endpoint. Block IMDS at the network level (Security Group inbound rules don't apply to 169.254.169.254 — use iptables/nftables rules or IMDSv2) AND enforce IMDSv2.

**Cloud Security → Kubernetes**: In EKS, GKE, and AKS, Kubernetes pods run on cloud nodes that have instance-level IAM credentials. A compromised pod that can reach the IMDS (or the GKE metadata server) can steal node credentials. Workload Identity (IRSA on AWS, Workload Identity on GCP, Azure Workload Identity on AKS) solves this by giving pods their own minimal identities rather than relying on the node's identity.

**Cloud Security → DevOps**: CI/CD pipelines are prime targets. A pipeline compromise allows signing malicious artifacts with trusted keys, pushing to production environments, and accessing all secrets the pipeline has access to. Apply cloud security controls to CI/CD infrastructure: IAM for pipelines (OIDC/Workload Identity, not long-lived keys), GuardDuty on CI/CD build machines, CloudTrail monitoring for pipeline-triggered API calls.
