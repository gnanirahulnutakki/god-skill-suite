---
name: god-iam-aws
description: "God-level AWS IAM expertise. Covers IAM policies (identity-based, resource-based, permissions boundaries, SCPs, session policies), IAM roles (cross-account, service roles, IRSA, instance profiles), IAM users and groups (legacy patterns), AWS Organizations and SCPs, AWS SSO/Identity Center, ABAC with tags, IAM Access Analyzer, credential reports, CloudTrail IAM auditing, and least-privilege implementation patterns. Never fabricates IAM action names or condition keys — always verifies against AWS IAM documentation or the IAM policy simulator. Treats every permission as a potential security vulnerability."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level AWS IAM

## The Researcher-Warrior Identity for IAM

IAM is not configuration. IAM is the security nervous system of your entire AWS environment. Every misconfiguration is a potential breach. You approach every IAM policy the way a penetration tester does — asking "how can this be abused?" before asking "does this work?"

**Non-negotiable operating principles**:
- Every permission you grant is a liability until proven necessary.
- Least privilege is not a goal — it is the starting point. You start with zero and add only what is proven necessary.
- You never trust your memory for IAM action strings. One typo (`s3:GetObejct`) means the permission silently doesn't apply.
- You always ask: what can an attacker do if this principal is compromised?
- You never use `*` for actions or resources without a documented, reviewed justification.
- You treat every IAM audit finding as a fire to be put out today, not next sprint.

**Anti-Hallucination Rules (AWS IAM-Specific)**:
- NEVER fabricate IAM action names. Verify at: https://docs.aws.amazon.com/service-authorization/latest/reference/
- NEVER invent condition keys. Verify at the same reference above.
- NEVER state that a policy "allows" something without simulating it via IAM Policy Simulator or `aws iam simulate-principal-policy`.
- NEVER claim an SCP blocks something without testing — SCPs interact with permission boundaries and identity policies in complex ways.
- NEVER assume `*` in a resource ARN is safe because of a condition — conditions can be circumvented.

**Verification commands (use before asserting)**:
```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/my-role \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::my-bucket/\*

aws iam get-account-authorization-details  # Full account IAM dump
aws accessanalyzer list-findings           # External access findings
aws iam generate-credential-report         # All users and their credential ages
```

---

## Phase 1: IAM Mental Model

### 1.1 The Policy Evaluation Logic (Know This Cold)

AWS IAM evaluates permissions in this exact order:
1. **Explicit Deny** — If ANY policy attached to ANY context denies the action: DENY. Full stop. No override.
2. **SCP (Service Control Policy)** — If the org's SCP doesn't allow the action: DENY.
3. **Resource-based policy** — If the resource has a policy, it can grant access independently (for same-account principals).
4. **IAM permission boundary** — If a boundary is set, it caps the maximum permissions.
5. **Session policy** — If assuming a role with a session policy, further restricts.
6. **Identity-based policy** — If the principal's policies allow the action: ALLOW (only if all above pass).
7. **Default** — DENY.

**Common mistake**: Developers think "I have an Allow in my identity policy" = access. Wrong. All six layers must pass.

### 1.2 Policy Types — Use Each Correctly

| Policy Type | Attached To | Scope |
|-------------|------------|-------|
| Identity-based | IAM user, role, group | Permissions the principal has |
| Resource-based | S3, KMS, SQS, Lambda, etc. | Who can access the resource |
| Permissions boundary | IAM user or role | Maximum permissions cap |
| SCP | AWS account or OU | Maximum permissions for entire account |
| Session policy | Assume-role call | Further restrict a role assumption |
| ACL | S3 buckets/objects (legacy) | Cross-account access (prefer resource policies) |

---

## Phase 2: Writing IAM Policies Correctly

### 2.1 Least Privilege Pattern — Build Up From Zero

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSpecificS3Operations",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-specific-bucket",
        "arn:aws:s3:::my-specific-bucket/*"
      ],
      "Condition": {
        "StringEquals": {
          "s3:prefix": ["uploads/", "processed/"],
          "aws:RequestedRegion": "us-east-1"
        },
        "Bool": {
          "aws:SecureTransport": "true"
        }
      }
    }
  ]
}
```

**Never write**:
```json
{ "Effect": "Allow", "Action": "*", "Resource": "*" }
```
This is `AdministratorAccess`. Only for break-glass accounts. Always MFA-protected. Always logged. Always reviewed.

### 2.2 ABAC — Attribute-Based Access Control (Scalable Least Privilege)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AccessResourcesTaggedWithSameProject",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Project": "${aws:PrincipalTag/Project}",
          "ec2:ResourceTag/Environment": "${aws:PrincipalTag/Environment}"
        }
      }
    }
  ]
}
```

ABAC scales without policy changes as resources grow — the tag does the work.

### 2.3 Preventing Privilege Escalation

These actions are dangerous — they allow escalating beyond current permissions:
```
iam:CreatePolicyVersion
iam:SetDefaultPolicyVersion
iam:PassRole                     # Can pass roles to services that act on your behalf
iam:AttachUserPolicy
iam:AttachRolePolicy
iam:PutUserPolicy
iam:PutRolePolicy
iam:AddUserToGroup
iam:UpdateAssumeRolePolicy
sts:AssumeRole                   # If unrestricted resource
```

Always restrict these with specific resource ARNs and conditions. Audit any role that has these.

---

## Phase 3: IAM Roles (Prefer Over Users Always)

### 3.1 Role Trust Policies — The External Door

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSpecificServiceAssumeRole",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:my-function"
        }
      }
    }
  ]
}
```

**Confused deputy attack prevention**: Always add `aws:SourceAccount` and `aws:SourceArn` conditions when the principal is a service.

### 3.2 IRSA — IAM Roles for Service Accounts (EKS)

```bash
# Create OIDC provider for cluster
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster \
  --approve

# Create role with trust policy scoped to specific K8s service account
aws iam create-role \
  --role-name my-service-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/oidc.eks.REGION.amazonaws.com/id/CLUSTER_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.REGION.amazonaws.com/id/CLUSTER_ID:sub":
            "system:serviceaccount:NAMESPACE:SERVICE_ACCOUNT_NAME",
          "oidc.eks.REGION.amazonaws.com/id/CLUSTER_ID:aud": "sts.amazonaws.com"
        }
      }
    }]
  }'
```

### 3.3 Cross-Account Role Assumption

```json
// In the TARGET account — role trust policy
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::SOURCE_ACCOUNT:root"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "Bool": {
        "aws:MultiFactorAuthPresent": "true"    // Require MFA for cross-account
      },
      "StringEquals": {
        "sts:ExternalId": "unique-external-id"  // Prevent confused deputy
      }
    }
  }]
}
```

---

## Phase 4: AWS Organizations & SCPs

### 4.1 SCP Design Patterns

SCPs only RESTRICT — they never GRANT. An Allow in an SCP means "allow this to be granted by identity policies." A Deny is absolute.

```json
// Deny all actions outside approved regions
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyNonApprovedRegions",
    "Effect": "Deny",
    "NotAction": [
      "iam:*",
      "organizations:*",
      "support:*",
      "cloudfront:*",
      "route53:*",
      "sts:*"     // Global services — must be exempted
    ],
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestedRegion": ["us-east-1", "us-west-2"]
      }
    }
  }]
}
```

```json
// Prevent disabling security services
{
  "Statement": [{
    "Sid": "DenySecurityServiceDisable",
    "Effect": "Deny",
    "Action": [
      "cloudtrail:StopLogging",
      "cloudtrail:DeleteTrail",
      "guardduty:DeleteDetector",
      "guardduty:DisassociateFromMasterAccount",
      "config:DeleteConfigurationRecorder",
      "config:StopConfigurationRecorder",
      "securityhub:DisableSecurityHub",
      "macie2:DisableMacie"
    ],
    "Resource": "*"
  }]
}
```

---

## Phase 5: IAM Auditing

### 5.1 Credential Hygiene Audit

```bash
# Generate and review credential report
aws iam generate-credential-report
aws iam get-credential-report --output text --query Content | base64 -d | \
  csvcut -c user,access_key_1_active,access_key_1_last_used_date,\
             access_key_2_active,password_last_used,mfa_active

# Find unused access keys (>90 days)
aws iam list-users --query 'Users[*].UserName' --output text | \
  xargs -I{} aws iam list-access-keys --user-name {}

# Find roles not used in 90 days (via Access Advisor)
aws iam get-role --role-name my-role --query 'Role.RoleLastUsed'
```

### 5.2 IAM Access Analyzer

```bash
# Find externally accessible resources (cross-account, public)
aws accessanalyzer list-analyzers
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:ACCOUNT:analyzer/default \
  --filter '{"status": {"eq": ["ACTIVE"]}}'
```

### 5.3 Self-Review Checklist (AWS IAM)

- [ ] No IAM users with long-term access keys (use roles + SSO instead)
- [ ] All access keys rotated within 90 days (check credential report)
- [ ] MFA enabled for all IAM users (especially root)
- [ ] Root account access keys deleted
- [ ] Root account has MFA and is not used for daily operations
- [ ] All roles have minimum necessary permissions (validated via Access Advisor)
- [ ] No `"Action": "*"` or `"Resource": "*"` without documented justification
- [ ] SCPs blocking dangerous actions at org level
- [ ] CloudTrail enabled in all regions with log integrity validation
- [ ] IAM Access Analyzer enabled with zero active findings
- [ ] All IRSA roles scoped to specific namespace:serviceaccount
- [ ] Permissions boundaries applied to all developer-created roles
- [ ] No inline policies (use managed policies for auditability)
