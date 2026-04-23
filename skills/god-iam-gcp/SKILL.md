---
name: god-iam-gcp
description: "God-level GCP IAM skill covering the GCP resource hierarchy (Org → Folder → Project → Resource), IAM roles (primitive, predefined, custom), IAM bindings and policies, Service Accounts (creation, impersonation, key management, Workload Identity Federation), Organization Policies, IAM Conditions, VPC Service Controls, Policy Intelligence (recommender, simulator, analyzer), IAM Deny policies, and Cloud Identity. Treats every service account key as a breach waiting to happen. Never fabricates GCP permission strings. Use for any GCP identity, access, organization policy, or service account task."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level GCP IAM

## The Researcher-Warrior Identity

GCP IAM is deceptively clean on the surface — elegant JSON policies, neat role names, tidy CLI commands. Do not be fooled. The inheritance model means a single `roles/editor` binding at the organization level touches every project, every service, every resource in your entire GCP footprint. Every service account key that exists is a ticking clock: rotated or leaked, there is no third option. The researcher-warrior doesn't accept "it works" — they demand "what can go wrong?" before every binding.

**Non-negotiable operating principles**:
- Service account keys are the last resort, not the first option. If a key exists, it's already a liability.
- Every `roles/owner` or `roles/editor` binding at project scope or above is a standing incident.
- Impersonation chains must be mapped. If SA-A can impersonate SA-B which has `roles/storage.admin`, SA-A effectively has `roles/storage.admin`.
- GCP IAM is eventually consistent. A revoked permission may still work for seconds to minutes. Design accordingly.
- Organization Policies are your hard stops. IAM can be overridden by a sufficiently privileged principal — org policies cannot (except by org policy admin).

**Anti-Hallucination Rules (GCP IAM-Specific)**:
- NEVER fabricate GCP permission strings. Format is `service.resource.verb`. Verify at: https://cloud.google.com/iam/docs/permissions-reference
- NEVER invent predefined role names. Verify with: `gcloud iam roles list --format="table(name,title)" --project=<project>` or `gcloud iam roles list` for curated roles
- NEVER assert a constraint name without checking: https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints
- NEVER fabricate workload identity pool/provider configuration without testing against `gcloud iam workload-identity-pools` commands
- NEVER claim `roles/owner` is equivalent to `roles/editor` plus something — Owner has `resourcemanager.projects.setIamPolicy` which editor does not
- If you don't know the exact permission string, say so and provide the lookup path

**Verification commands (run before asserting)**:
```bash
# List all roles available in a project
gcloud iam roles list --project=<project-id>

# Get details of a specific role
gcloud iam roles describe roles/storage.objectAdmin

# Get the IAM policy of a project
gcloud projects get-iam-policy <project-id> --format=json

# Get effective policy (including inherited)
gcloud asset search-all-iam-policies --scope=projects/<project-id> --query="policy:<principal>"

# List service accounts in a project
gcloud iam service-accounts list --project=<project-id>

# Check what a principal can do (Policy Analyzer)
gcloud asset analyze-iam-policy \
  --organization=<org-id> \
  --identity="user:alice@example.com" \
  --analyze-service-account-impersonation
```

---

## Phase 1: GCP Resource Hierarchy and Policy Inheritance

### 1.1 The Hierarchy

```
Organization (root)
├── Folder (e.g., Production)
│   ├── Folder (e.g., Backend)
│   │   └── Project (e.g., prod-backend-api)
│   │       └── Resources (GCS buckets, GCE VMs, GKE clusters, etc.)
│   └── Folder (e.g., Frontend)
│       └── Project (e.g., prod-frontend-web)
└── Folder (e.g., Development)
    └── Project (e.g., dev-sandbox)
```

**Policy inheritance**: IAM allow policies are attached to each level. The effective policy for a resource is the **union** of all policies from organization down to the resource itself. You cannot grant less access by attaching a policy lower in the hierarchy — you can only add, never remove, via allow policies.

**This is fundamentally different from AWS**: AWS has no automatic inheritance for IAM policies. In GCP, granting `roles/compute.instanceAdmin.v1` at the organization level grants it on every Compute Engine VM in every project. This is both the power and the danger.

### 1.2 Binding Model vs AWS Policy Model

| Dimension | GCP IAM | AWS IAM |
|-----------|---------|---------|
| Policy structure | `resource → {bindings: [{role, members}]}` | `principal → {statements: [{effect, action, resource}]}` |
| Default | Deny (no binding = no access) | Deny |
| Resource policy | Supported (e.g., bucket IAM) | Supported (S3 bucket policy) |
| Inheritance | Automatic downward through hierarchy | Not automatic (requires explicit policy) |
| Wildcards | Not in standard roles; custom roles use individual permissions | `*` allowed in actions and resources |
| Conditions | Supported via IAM Conditions (CEL) | Supported via condition keys |
| Explicit deny | IAM Deny policies (separate from allow policies) | `"Effect": "Deny"` in statement |

### 1.3 Policy Evaluation Order

1. **IAM Deny policies** — evaluated first; if deny matches, access denied regardless of allow policies
2. **Organization Policy** — not an IAM check but restricts what operations are allowed (orthogonal to IAM)
3. **Allow policies (union of all levels)** — if any binding in the hierarchy grants the permission, access is allowed
4. **Default** — DENY

---

## Phase 2: Roles — Never Use Primitive Roles in Production

### 2.1 Primitive Roles (Owner, Editor, Viewer)

These predate the predefined role system. They are coarse, dangerous, and should be avoided in production workloads. They exist for backward compatibility and testing.

**Owner** (`roles/owner`):
- All permissions on all resources in scope
- Can set IAM policies (`resourcemanager.projects.setIamPolicy`) — this is the dangerous permission
- A principal with Owner can grant themselves (or anyone) any permission

**Editor** (`roles/editor`):
- All permissions except setting IAM policies and a handful of sensitive admin operations
- Still extremely broad — can create/delete/modify virtually any resource
- "We gave them Editor because they needed Storage access" is a security failure

**Viewer** (`roles/viewer`):
- Read-only on all resource metadata
- Does NOT include data plane reads (e.g., cannot read Cloud Storage object contents without `roles/storage.objectViewer`)

**Never use Owner or Editor for**:
- Service accounts running automated workloads
- CI/CD pipeline identities
- Any non-interactive, non-human principal
- Any production access

### 2.2 Predefined Roles — The Right Choice

Predefined roles are Google-managed bundles of related permissions. Always choose the most specific predefined role that covers the use case.

Examples (verify current contents with `gcloud iam roles describe`):
- `roles/storage.objectViewer` — Read objects in GCS buckets
- `roles/storage.objectAdmin` — Full control of GCS objects
- `roles/storage.admin` — Full control of GCS buckets AND objects (broader)
- `roles/container.developer` — Deploy to GKE clusters
- `roles/container.clusterAdmin` — Full GKE cluster management
- `roles/bigquery.dataViewer` — Read BigQuery datasets
- `roles/bigquery.user` — Run queries (doesn't grant table access alone)
- `roles/cloudsql.client` — Connect to Cloud SQL (requires instance access separately)
- `roles/iam.serviceAccountTokenCreator` — Impersonate a service account

### 2.3 Custom Roles — When and How

Create custom roles when:
- No predefined role is narrow enough for your use case
- You need to combine permissions from multiple predefined roles without using a broader role
- You need to exclude specific permissions from a broader role

Custom roles cannot be assigned at organization level for projects that don't have them defined (use `--organization` flag to create org-level custom roles).

```bash
# Create a custom role from a YAML file
cat > custom-role.yaml << 'EOF'
title: "Cloud Run Deployer"
description: "Minimal permissions to deploy Cloud Run services"
stage: GA
includedPermissions:
  - run.services.create
  - run.services.update
  - run.services.get
  - run.services.list
  - iam.serviceAccounts.actAs
EOF

gcloud iam roles create cloudRunDeployer \
  --project=<project-id> \
  --file=custom-role.yaml

# Create at organization level
gcloud iam roles create cloudRunDeployer \
  --organization=<org-id> \
  --file=custom-role.yaml

# Update a custom role (add permissions)
gcloud iam roles update cloudRunDeployer \
  --project=<project-id> \
  --add-permissions=run.services.delete

# List custom roles
gcloud iam roles list --project=<project-id> --filter="stage:GA"

# Delete (must disable first)
gcloud iam roles update cloudRunDeployer --project=<project-id> --stage=DISABLED
gcloud iam roles delete cloudRunDeployer --project=<project-id>
```

**Custom role limits**: 300 custom roles per project, 1,000 per organization. Custom roles have a stage (`ALPHA`, `BETA`, `GA`, `DISABLED`).

---

## Phase 3: IAM Policies and Bindings

### 3.1 The Allow Policy Structure

Every GCP resource has an allow policy (IAM policy). Structure:

```json
{
  "version": 3,
  "bindings": [
    {
      "role": "roles/storage.objectViewer",
      "members": [
        "user:alice@example.com",
        "serviceAccount:my-sa@my-project.iam.gserviceaccount.com",
        "group:data-team@example.com"
      ]
    },
    {
      "role": "roles/storage.objectAdmin",
      "members": [
        "serviceAccount:pipeline-sa@my-project.iam.gserviceaccount.com"
      ],
      "condition": {
        "title": "Expires 2025-01-01",
        "description": "Temporary access for migration",
        "expression": "request.time < timestamp('2025-01-01T00:00:00Z')"
      }
    }
  ],
  "etag": "BwXxx..."
}
```

**Policy version 3** is required for IAM Conditions. Version 1 and 2 exist for backward compatibility; never downgrade.

**Member types**:
- `user:email` — Individual Google Account
- `serviceAccount:email` — GCP Service Account
- `group:email` — Google Group
- `domain:domain.com` — All users in a Workspace/Cloud Identity domain
- `allAuthenticatedUsers` — Any Google-authenticated user (DANGEROUS — means anyone with a Google account)
- `allUsers` — Completely public (DANGEROUS — means the entire internet)
- `principalSet://` — Workload Identity Federation principal sets
- `principal://` — Individual Workload Identity Federation principal

```bash
# Add a binding
gcloud projects add-iam-policy-binding <project-id> \
  --member="serviceAccount:my-sa@my-project.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Remove a binding
gcloud projects remove-iam-policy-binding <project-id> \
  --member="serviceAccount:my-sa@my-project.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

# Get full policy (ALWAYS verify before making changes — use etag for optimistic locking)
gcloud projects get-iam-policy <project-id> --format=json > current-policy.json
```

---

## Phase 4: Service Accounts

### 4.1 Service Account Security Fundamentals

Service accounts are both IAM principals (they have bindings granting them roles) and IAM resources (other principals can be granted access to them). This dual nature creates impersonation chains.

**The key insight from [GCP best practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)**:

Impersonation-enabling permissions (treat these as equivalent to granting the SA's permissions to the user):
- `iam.serviceAccounts.actAs` — Attach SA to resources, create tokens as SA
- `iam.serviceAccounts.getAccessToken` — Directly obtain access tokens
- `iam.serviceAccounts.getOpenIdToken` — Obtain OIDC tokens
- `iam.serviceAccounts.implicitDelegation` — Implicit delegation chain
- `iam.serviceAccounts.signBlob` — Sign arbitrary bytes
- `iam.serviceAccounts.signJwt` — Sign JWTs (can forge tokens)

Roles that include `iam.serviceAccounts.actAs`:
- `roles/owner`
- `roles/editor`
- `roles/iam.serviceAccountUser`
- `roles/iam.serviceAccountTokenCreator`
- `roles/deploymentmanager.editor`
- `roles/cloudbuild.builds.editor`

**If a developer has `roles/iam.serviceAccountUser` on a service account with `roles/bigquery.admin`, that developer effectively has `roles/bigquery.admin`.**

### 4.2 Service Account Key Management

Downloaded JSON keys are static, long-lived credentials. They are the highest-risk credential type in GCP.

```bash
# AVOID — only if absolutely no alternative exists
gcloud iam service-accounts keys create key.json \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com

# List all keys for a service account
gcloud iam service-accounts keys list \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com \
  --format="table(name,validAfterTime,validBeforeTime,keyType)"

# Delete a key
gcloud iam service-accounts keys delete <key-id> \
  --iam-account=my-sa@my-project.iam.gserviceaccount.com

# Disable key creation via Organization Policy
# In console: Organization > IAM & Admin > Organization Policies
# Constraint: constraints/iam.disableServiceAccountKeyCreation
```

**Enforce via Organization Policy**:
```bash
gcloud org-policies set-policy key-policy.yaml
# key-policy.yaml:
# name: organizations/<org-id>/policies/iam.disableServiceAccountKeyCreation
# spec:
#   rules:
#   - enforce: true
```

### 4.3 Service Account Impersonation (The Preferred Pattern)

Instead of keys, use short-lived tokens via impersonation:

```bash
# Generate a short-lived access token by impersonating a service account
# Requires iam.serviceAccounts.getAccessToken on the target SA
gcloud auth print-access-token \
  --impersonate-service-account=my-sa@my-project.iam.gserviceaccount.com

# Use impersonation in gcloud commands
gcloud storage buckets list \
  --impersonate-service-account=my-sa@my-project.iam.gserviceaccount.com

# Via Application Default Credentials in code:
# Use google-auth library's impersonated_credentials
```

```python
from google.auth import impersonated_credentials
from google.oauth2 import service_account
import google.auth

# Get source credentials (e.g., from ambient credentials on a VM)
source_credentials, project = google.auth.default()

# Create impersonated credentials
target_credentials = impersonated_credentials.Credentials(
    source_credentials=source_credentials,
    target_principal='my-sa@my-project.iam.gserviceaccount.com',
    target_scopes=['https://www.googleapis.com/auth/cloud-platform'],
    lifetime=3600  # 1 hour max for impersonation
)
```

---

## Phase 5: Workload Identity Federation

### 5.1 Architecture

Workload Identity Federation lets external workloads (GitHub Actions, AWS Lambda, on-prem Kubernetes) authenticate to GCP without service account keys. Uses OAuth 2.0 token exchange (RFC 8693). [Source: GCP Workload Identity Federation docs](https://cloud.google.com/iam/docs/workload-identity-federation)

Components:
1. **Workload Identity Pool**: Container for external identities
2. **Workload Identity Pool Provider**: Describes the external IdP (AWS, OIDC, SAML)
3. **IAM bindings**: Grant roles to the federated identity (directly or via service account impersonation)

### 5.2 GitHub Actions Configuration

```bash
# Create workload identity pool
gcloud iam workload-identity-pools create "github-pool" \
  --project=<project-id> \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Create OIDC provider for GitHub
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project=<project-id> \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_owner == 'my-org'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Grant access to specific repo (direct resource access)
gcloud projects add-iam-policy-binding <project-id> \
  --role="roles/storage.objectViewer" \
  --member="principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github-pool/attribute.repository/my-org/my-repo"

# OR: Grant via service account impersonation
gcloud iam service-accounts add-iam-policy-binding my-sa@<project-id>.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github-pool/attribute.repository/my-org/my-repo"
```

GitHub Actions workflow:
```yaml
permissions:
  id-token: write
  contents: read

steps:
  - id: auth
    uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: 'projects/<project-number>/locations/global/workloadIdentityPools/github-pool/providers/github-provider'
      service_account: 'my-sa@<project-id>.iam.gserviceaccount.com'  # if using SA impersonation
```

### 5.3 GKE Workload Identity

GKE Workload Identity binds a Kubernetes ServiceAccount to a GCP Service Account. [Source: GCP best practices for service accounts](https://cloud.google.com/iam/docs/best-practices-service-accounts)

```bash
# Enable Workload Identity on cluster
gcloud container clusters update <cluster-name> \
  --workload-pool=<project-id>.svc.id.goog \
  --region=<region>

# Create GCP service account
gcloud iam service-accounts create gke-workload-sa \
  --project=<project-id>

# Grant the K8s ServiceAccount permission to impersonate the GCP SA
gcloud iam service-accounts add-iam-policy-binding gke-workload-sa@<project-id>.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:<project-id>.svc.id.goog[<k8s-namespace>/<k8s-serviceaccount>]"

# Grant roles to the GCP SA
gcloud projects add-iam-policy-binding <project-id> \
  --role="roles/storage.objectViewer" \
  --member="serviceAccount:gke-workload-sa@<project-id>.iam.gserviceaccount.com"
```

Kubernetes side:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-k8s-serviceaccount
  namespace: my-namespace
  annotations:
    iam.gke.io/gcp-service-account: gke-workload-sa@<project-id>.iam.gserviceaccount.com
```

---

## Phase 6: Organization Policies

### 6.1 Constraint Types

Organization Policies enforce guardrails independent of IAM. Even an org admin cannot violate an enforced org policy without modifying the policy first.

**Boolean constraints**: On/off enforcement
```bash
# Example: Disable service account key creation
gcloud org-policies set-policy - << 'EOF'
name: organizations/<org-id>/policies/iam.disableServiceAccountKeyCreation
spec:
  rules:
  - enforce: true
EOF
```

**List constraints**: Deny or allow specific values
```bash
# Restrict resource location to specific regions
gcloud org-policies set-policy - << 'EOF'
name: projects/<project-id>/policies/gcp.resourceLocations
spec:
  rules:
  - values:
      allowedValues:
      - in:us-locations
      - in:europe-locations
EOF
```

### 6.2 Key Organization Policy Constraints

**Do NOT fabricate constraint names.** Verify the full list at: https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints

Commonly used constraints (verified):
- `constraints/iam.disableServiceAccountKeyCreation` — Block creation of service account keys
- `constraints/iam.disableServiceAccountKeyUpload` — Block uploading external keys
- `constraints/iam.allowedPolicyMemberDomains` — Restrict IAM bindings to specific domains (prevent `allUsers`)
- `constraints/compute.requireShieldedVm` — Require Shielded VMs
- `constraints/compute.vmExternalIpAccess` — Control external IP on VMs
- `constraints/gcp.resourceLocations` — Restrict resource locations

```bash
# Describe what a constraint does
gcloud org-policies describe-constraint constraints/iam.disableServiceAccountKeyCreation

# List all effective policies on a project (including inherited)
gcloud org-policies list --project=<project-id>
```

---

## Phase 7: IAM Conditions

IAM Conditions use the Common Expression Language (CEL) to add attribute-based conditions to bindings. Policy version must be 3.

### 7.1 Condition Attributes

```bash
# Time-based condition (expires at a specific time)
gcloud projects add-iam-policy-binding <project-id> \
  --member="user:alice@example.com" \
  --role="roles/storage.objectViewer" \
  --condition='expression=request.time < timestamp("2025-06-01T00:00:00Z"),title=Temp Access,description=Expires June 2025'

# Resource tag condition
# Must have tags applied to resources
gcloud projects add-iam-policy-binding <project-id> \
  --member="serviceAccount:my-sa@<project-id>.iam.gserviceaccount.com" \
  --role="roles/compute.instanceAdmin.v1" \
  --condition='expression=resource.matchTagId("tagKeys/123456", "tagValues/789"),title=Environment Prod'
```

**Common condition attributes**:
- `request.time` — Current time (for time-based conditions)
- `resource.name` — Resource name (for resource-specific conditions)
- `resource.service` — Service name (e.g., `storage.googleapis.com`)
- `resource.type` — Resource type
- `resource.matchTagId(key, value)` — Tag-based conditions

---

## Phase 8: IAM Deny Policies

Deny policies (v2 IAM API) are separate from allow policies and evaluated before allow policies. Unlike `NotActions` in Azure, GCP deny policies are a true security boundary.

```bash
# Create a deny policy (JSON format)
gcloud iam policies create deny-sa-key-creation \
  --attachment-point=cloudresourcemanager.googleapis.com/projects/<project-id> \
  --policy-file=deny-policy.json
```

```json
{
  "displayName": "Deny service account key operations",
  "rules": [
    {
      "denyRule": {
        "deniedPrincipals": ["principalSet://goog/public:all"],
        "deniedPermissions": [
          "iam.googleapis.com/serviceAccountKeys.create",
          "iam.googleapis.com/serviceAccountKeys.upload"
        ],
        "exceptionPrincipals": [
          "principal://goog/subject/break-glass@example.com"
        ]
      }
    }
  ]
}
```

**Note**: Deny policy permissions use the format `service.googleapis.com/resource.verb`, not `service.resource.verb`. Verify permission names at: https://cloud.google.com/iam/docs/deny-permissions-support

---

## Phase 9: Policy Intelligence

### 9.1 IAM Recommender

The IAM Recommender analyzes role usage over the past 90 days and suggests removing unused permissions.

```bash
# List recommendations for a project
gcloud recommender recommendations list \
  --project=<project-id> \
  --recommender=google.iam.policy.Recommender \
  --location=global \
  --format=json

# Apply a recommendation
gcloud recommender recommendations mark-claimed <recommendation-id> \
  --project=<project-id> \
  --recommender=google.iam.policy.Recommender \
  --location=global \
  --etag=<etag>
```

### 9.2 Policy Analyzer

Policy Analyzer answers "who can do what on which resource?" — across the entire resource hierarchy.

```bash
# Who has storage.objects.list on a bucket?
gcloud asset analyze-iam-policy \
  --project=<project-id> \
  --resource="//storage.googleapis.com/projects/_/buckets/my-bucket" \
  --permission="storage.objects.list"

# What can a user do?
gcloud asset analyze-iam-policy \
  --organization=<org-id> \
  --identity="user:alice@example.com" \
  --analyze-service-account-impersonation
```

### 9.3 Policy Simulator

Test the impact of IAM policy changes before applying them.

```bash
# Test if alice can do storage.objects.get after a proposed change
gcloud iam simulate-policy \
  --principal="user:alice@example.com" \
  --resource="//storage.googleapis.com/projects/_/buckets/my-bucket" \
  --permission="storage.objects.get"
```

---

## Phase 10: Audit Logging

### 10.1 Audit Log Types

GCP Cloud Audit Logs have four types:
- **Admin Activity audit logs**: Administrative actions (IAM changes, resource creation/deletion). **Always on, free, 400 days retention.**
- **Data Access audit logs**: Data reads/writes. **Off by default — must enable explicitly.** Can be expensive. Required for compliance.
- **System Event audit logs**: Google-generated events. Always on.
- **Policy Denied audit logs**: When a security policy denies access. Always on.

```bash
# Enable Data Access audit logs for IAM API (critical for service account impersonation tracking)
gcloud projects get-iam-policy <project-id> --format=json > policy.json
# Add auditConfigs section:
# {
#   "auditConfigs": [
#     {
#       "service": "iam.googleapis.com",
#       "auditLogConfigs": [
#         {"logType": "DATA_READ"},
#         {"logType": "DATA_WRITE"}
#       ]
#     },
#     {
#       "service": "sts.googleapis.com",
#       "auditLogConfigs": [
#         {"logType": "DATA_WRITE"}
#       ]
#     }
#   ]
# }
```

### 10.2 Key Queries in Cloud Logging

```bash
# All IAM policy changes in last 24 hours
resource.type="project"
protoPayload.serviceName="cloudresourcemanager.googleapis.com"
protoPayload.methodName:"setIamPolicy"
timestamp >= "2024-01-01T00:00:00Z"

# Service account key creation (should alert on this)
protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"

# Service account impersonation (access token generation)
protoPayload.serviceName="iamcredentials.googleapis.com"
protoPayload.methodName="GenerateAccessToken"

# Organization policy changes
protoPayload.serviceName="orgpolicy.googleapis.com"
```

---

## Phase 11: VPC Service Controls

VPC Service Controls create security perimeters around GCP APIs and services. Even if an IAM binding grants access, VPC Service Controls can block the request based on network context.

```bash
# Create an access policy (org-level resource)
gcloud access-context-manager policies create \
  --organization=<org-id> \
  --title="My Access Policy"

# Create a service perimeter
gcloud access-context-manager perimeters create my-perimeter \
  --policy=<policy-id> \
  --title="Production Perimeter" \
  --resources=projects/<project-number> \
  --restricted-services=storage.googleapis.com,bigquery.googleapis.com \
  --access-levels=<access-level-name>
```

VPC Service Controls is a defense-in-depth layer. It complements IAM — it doesn't replace it. Use it to prevent data exfiltration from compromised credentials that might still have valid IAM access.

---

## Self-Review Checklist: GCP IAM

**Service Account Hygiene**
- [ ] Zero downloaded service account keys in use for workloads on GCP (use attached SA, Workload Identity, or impersonation)
- [ ] `constraints/iam.disableServiceAccountKeyCreation` enforced at org or folder level
- [ ] `constraints/iam.disableServiceAccountKeyUpload` enforced at org or folder level
- [ ] No service account has `roles/owner` or `roles/editor` at project scope or above
- [ ] All service accounts are single-purpose with descriptive names per naming convention
- [ ] Unused service accounts identified and disabled (use IAM Recommender activity data)
- [ ] Default Compute Engine and App Engine service accounts not granted roles (they have `roles/editor` by default — revoke or constrain via org policy)

**IAM Bindings**
- [ ] No `allUsers` or `allAuthenticatedUsers` bindings on any non-public resource
- [ ] No primitive roles (`roles/owner`, `roles/editor`, `roles/viewer`) on service accounts in production
- [ ] `constraints/iam.allowedPolicyMemberDomains` enforced to prevent external domain bindings
- [ ] IAM Recommender recommendations reviewed and applied in last 90 days
- [ ] Policy Analyzer run to verify no unexpected access paths exist

**Organization Policies**
- [ ] Org policies reviewed at org, folder, and project levels quarterly
- [ ] Resource location constraints enforced for data sovereignty requirements
- [ ] Shielded VM enforcement enabled where applicable
- [ ] External IP access on Compute Engine restricted

**Workload Identity**
- [ ] All GKE workloads use Workload Identity Federation for GKE (not service account keys)
- [ ] All external workloads (GitHub Actions, CI/CD) use Workload Identity Federation pools
- [ ] Attribute conditions set on OIDC providers to restrict which external identities can authenticate

**Audit Logging**
- [ ] Data Access audit logs enabled for `iam.googleapis.com` and `sts.googleapis.com`
- [ ] Audit logs exported to Cloud Storage or BigQuery for long-term retention (default is 400 days for Admin Activity)
- [ ] Alerts configured for: `setIamPolicy` on org/folder/project, service account key creation, `GenerateAccessToken` from unexpected principals

**Impersonation Chain Analysis**
- [ ] No human user has `iam.serviceAccounts.actAs` on a service account with more privileges than the user should have
- [ ] `roles/iam.serviceAccountTokenCreator` assignments audited and minimized
- [ ] Policy Analyzer run with `--analyze-service-account-impersonation` to map all impersonation chains

**VPC Service Controls**
- [ ] Perimeters defined for production projects containing sensitive data
- [ ] Ingress/egress rules reviewed and documented
- [ ] Dry-run mode used before enforcing new perimeters

---

## Cross-Domain Connections

**GCP IAM → Kubernetes (GKE)**: GKE Workload Identity is the correct bridge between Kubernetes pod identity and GCP IAM. The Kubernetes ServiceAccount annotation `iam.gke.io/gcp-service-account` + the `roles/iam.workloadIdentityUser` binding on the GCP SA creates a trust relationship. Any pod using that K8s SA gets GCP credentials — so K8s RBAC protecting who can use that ServiceAccount is also GCP IAM security.

**GCP IAM → CI/CD**: Workload Identity Pools for GitHub Actions, GitLab, and Terraform Cloud eliminate the need for any service account keys in pipelines. The pool provider's `attribute-condition` is your guard — if you don't set it to restrict to specific repos/organizations, any GitHub Actions workflow can authenticate to your GCP project.

**GCP IAM → Networking**: VPC Service Controls create an IAM-aware network perimeter. Even valid credentials can be blocked if the request originates outside the VPC Service Controls perimeter. This is critical for preventing SSRF-based metadata server abuse — an attacker who exploits SSRF to reach the Compute Engine metadata server gets the attached service account token, but VPC Service Controls can prevent that token from reaching Cloud Storage or BigQuery APIs if the request comes from outside the perimeter.

**GCP IAM → Security**: The GCP metadata server at `169.254.169.254` is accessible from any GCE VM without authentication. Any SSRF vulnerability in an application running on GCE or GKE is a potential service account token theft. Defend by: restricting metadata server access at the network level, using Workload Identity (which uses projected tokens with short lifetimes, not IMDS metadata server keys), and enforcing VPC Service Controls to limit what stolen tokens can access.
