---
name: god-iam-azure
description: "God-level Azure IAM skill covering Microsoft Entra ID (formerly Azure AD), Azure RBAC, Managed Identities, Privileged Identity Management (PIM), Conditional Access, App Registrations, Service Principals, Enterprise Applications, Workload Identity Federation, Azure AD B2C, administrative units, and cross-tenant access. Covers the researcher-warrior approach to identity: every identity is a potential attack vector, every role assignment is a liability, every token is a secret. Never fabricates Azure permission names or role definitions. Use for any Azure identity, access, or authentication task."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Azure IAM (Microsoft Entra ID)

## The Researcher-Warrior Identity

Azure identity is the perimeter. Not the network firewall. Not the WAF. The identity layer is where breaches start and where they spread. When you work this skill, you operate like a red-teamer who also has to write the blue-team runbook: every identity you create is a target, every permission you grant is a pivot point, every token that exists in memory or disk is a secret waiting to leak.

**Non-negotiable operating principles**:
- Every role assignment is a liability until proven necessary. Start from zero, add only what is documented and justified.
- Never trust your memory for Azure permission strings. `Microsoft.Compute/virtualMachines/write` and `Microsoft.Compute/virtualMachines/Write` are different in case — but Azure is case-insensitive for built-ins. Custom roles are not exempt from careful review.
- You always ask: if this service principal's secret leaked tomorrow, what could an attacker do? If the answer is "anything significant," you've over-privileged.
- Managed Identities first, Service Principals second, user credentials last (never for automation).
- Token lifespan × permission scope = blast radius. Minimize both.
- PIM is not optional for privileged roles. Standing access to Owner or Contributor at subscription scope is a misconfiguration, not a convenience.

**Anti-Hallucination Rules (Azure IAM-Specific)**:
- NEVER fabricate Azure RBAC action strings. Verify at: https://learn.microsoft.com/en-us/azure/role-based-access-control/resource-provider-operations
- NEVER invent Microsoft Graph API permission names. Verify at: https://learn.microsoft.com/en-us/graph/permissions-reference
- NEVER claim a built-in role exists without verifying with `az role definition list --query "[?roleName=='<name>']"`
- NEVER assert what a Conditional Access policy blocks without testing in Report-only mode first
- NEVER state an App Registration has a permission without checking `az ad app permission list --id <appId>`
- NEVER fabricate Entra ID role names. Verify at: https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference

**Verification commands (run before asserting)**:
```bash
# List all role assignments at subscription scope
az role assignment list --scope /subscriptions/<subId> --include-inherited --output table

# List all role definitions (built-in + custom)
az role definition list --output table

# Show exact permissions of a role
az role definition list --name "Contributor" --output json

# Check what a principal can do
az role assignment list --assignee <principalId> --all --include-inherited

# List app registrations
az ad app list --all --output table

# List service principals
az ad sp list --all --output table
```

---

## Phase 1: Azure IAM Mental Model

### 1.1 The Resource Hierarchy (Identity Scope Ladder)

Azure scopes define where a role assignment takes effect. Permissions inherit downward — never upward.

```
Tenant (Microsoft Entra ID)
└── Management Group (root)
    └── Management Group (child)
        └── Subscription
            └── Resource Group
                └── Resource (e.g., VM, Storage Account, Key Vault)
```

**Key rules**:
- An Owner at Management Group scope has Owner over every subscription, resource group, and resource inside it.
- A Reader at Resource Group scope cannot see anything outside that resource group.
- Assignments at broader scope always include everything narrower. Never assume "subscription-level access" is limited.
- Management Groups require separate RBAC consideration — Azure RBAC at Management Group scope is different from Entra ID roles.

### 1.2 Entra ID Roles vs Azure RBAC Roles

These are two entirely separate systems that confusion breeds security holes:

| Dimension | Entra ID (Directory) Roles | Azure RBAC Roles |
|-----------|---------------------------|------------------|
| Scope | Tenant-wide (or Admin Unit) | Azure resource hierarchy |
| Purpose | Manage Entra objects (users, groups, apps) | Manage Azure resources |
| Example role | Global Administrator, User Administrator | Owner, Contributor, Reader |
| Assigned via | Entra ID > Roles and administrators | Azure > Access control (IAM) |
| API surface | Microsoft Graph | Azure Resource Manager |

**Critical**: A Global Administrator in Entra ID does NOT automatically have access to Azure resources. They can *elevate* to User Access Administrator at root scope (a dangerous, audited operation) — but this is opt-in and logged. Know the difference. Conflating them causes both over-privileging and under-privileging.

### 1.3 Policy Evaluation (Azure RBAC)

Azure RBAC uses an additive model with explicit deny overriding:

1. **Explicit Deny assignment** — Any deny assignment covering the action/principal: DENY. Final.
2. **Allow assignments (union)** — All role assignments are unioned. If ANY allows the action: ALLOW.
3. **Default** — DENY.

Deny assignments are rare (used by Blueprints, some managed services). Most Azure RBAC is purely additive — which means every role assignment adds permissions, nothing subtracts unless you use `NotActions` in a role definition (which carves exceptions from the Allow, not creates a hard Deny).

**Important**: `NotActions` is NOT a security boundary. `NotActions` means "this role's `Actions` don't include this operation." Another role assignment that includes that action still grants it. `NotActions` ≠ Deny.

---

## Phase 2: Built-in Roles — What They Actually Do

### 2.1 The Four Fundamental Built-in Roles

Verify current definitions with:
```bash
az role definition list --name "Owner" --output json
az role definition list --name "Contributor" --output json
az role definition list --name "Reader" --output json
az role definition list --name "User Access Administrator" --output json
```

**Owner** (ID: `8e3af657-a8ff-443c-a75c-2fe8c4bcb635`)
- Full control over all resources in scope
- Can assign and remove roles (including Owner itself)
- Can manage RBAC — this is the dangerous part
- Use only at resource group scope, never subscription or management group without PIM
- Source: [Azure built-in roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)

**Contributor** (ID: `b24988ac-6180-42a0-ab88-20f7382dd24c`)
- Full resource management but CANNOT assign roles
- Cannot manage Azure Blueprints assignments
- Cannot share image galleries
- Still extremely powerful — can delete, reconfigure, access data in many services
- Do not treat Contributor as "safe." A Contributor on a storage account can create SAS tokens, exfiltrate data, and delete blobs.

**Reader** (ID: `acdd72a7-3385-48ef-bd42-f606fba81ae7`)
- Read-only on all resource metadata
- Does NOT grant data plane access (cannot read blob contents, Key Vault secrets, etc.)
- Data plane access requires separate DataActions roles (e.g., `Storage Blob Data Reader`)

**User Access Administrator** (ID: `18d7d88d-d35e-4fb5-a5c3-7773c20a72d9`)
- Manages user access (role assignments) but has no resource management permissions
- Dangerous when combined with Contributor via two separate assignments
- Useful for delegation scenarios where a team manages their own RBAC without full Owner

### 2.2 Control Plane vs Data Plane

This is a critical distinction that breaks most developers' mental models:

- **Control plane** (`Actions`) — Operations on Azure Resource Manager (ARM). Creating/deleting/configuring resources. `Microsoft.Storage/storageAccounts/write`
- **Data plane** (`DataActions`) — Operations on data within a resource. Reading blob contents, accessing Key Vault secrets. `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`

A user with `Contributor` can manage the storage account (configure it, delete it, change firewall rules) but CANNOT read blob data unless they also have a role with the appropriate `DataAction`.

---

## Phase 3: Custom Role Authoring

### 3.1 Custom Role JSON Structure

Always use the Azure CLI format for creating custom roles. The structure below is verified against [Azure custom roles documentation](https://learn.microsoft.com/en-us/azure/role-based-access-control/custom-roles):

```json
{
  "Name": "My Custom Role",
  "Description": "Minimal permissions for specific task",
  "Actions": [
    "Microsoft.Compute/virtualMachines/read",
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/restart/action"
  ],
  "NotActions": [],
  "DataActions": [
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
  ],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscriptionId}",
    "/providers/Microsoft.Management/managementGroups/{groupId}"
  ]
}
```

**Fields**:
- `Actions`: Control plane operations allowed (ARM)
- `NotActions`: Carve-outs from `Actions` (NOT a security deny — other roles can still grant)
- `DataActions`: Data plane operations allowed
- `NotDataActions`: Carve-outs from `DataActions`
- `AssignableScopes`: Where this role can be assigned (management group, subscription, resource group, or resource)

**Important limits**: Custom roles with `DataActions` cannot be assigned at management group scope. Maximum 5,000 custom roles per Entra ID tenant.

### 3.2 Create and Manage Custom Roles

```bash
# Create from JSON file
az role definition create --role-definition @custom-role.json

# Update an existing custom role
az role definition update --role-definition @updated-role.json

# List custom roles in a subscription
az role definition list --custom-role-filter true --output table

# Delete a custom role
az role definition delete --name "My Custom Role"

# Verify a role's exact permissions before assigning
az role definition list --name "My Custom Role" --output json
```

---

## Phase 4: Managed Identities

### 4.1 System-Assigned vs User-Assigned

**System-assigned Managed Identity**:
- Lifecycle is tied to the Azure resource it's assigned to (VM, App Service, Function, etc.)
- One identity per resource
- Automatically deleted when the resource is deleted
- Identity principal ID is in the resource's properties

Use when: A single resource needs to authenticate to other Azure services and you want automatic lifecycle management.

```bash
# Enable system-assigned identity on a VM
az vm identity assign --name myVM --resource-group myRG

# Get the principal ID of the system-assigned identity
az vm show --name myVM --resource-group myRG \
  --query "identity.principalId" --output tsv

# Assign a role to the system-assigned identity
az role assignment create \
  --assignee <principalId> \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/<subId>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<sa>
```

**User-assigned Managed Identity**:
- Standalone Azure resource (separate lifecycle from any VM/service)
- Can be assigned to multiple resources simultaneously
- Survives resource deletion
- Requires explicit management (create, delete, assign)

Use when: Multiple resources share the same identity (e.g., a fleet of VMs all need the same Key Vault access), or when you need the identity to survive resource recreation.

```bash
# Create a user-assigned managed identity
az identity create --name myIdentity --resource-group myRG

# Get the client ID and principal ID
az identity show --name myIdentity --resource-group myRG \
  --query "{clientId:clientId, principalId:principalId}" --output json

# Assign to a VM
az vm identity assign \
  --name myVM \
  --resource-group myRG \
  --identities /subscriptions/<subId>/resourceGroups/<rg>/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myIdentity

# Assign role to the user-assigned identity
az role assignment create \
  --assignee <principalId> \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/<subId>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kvName>
```

### 4.2 Getting Tokens from Managed Identity (IMDS)

From within an Azure resource, get a token via the Instance Metadata Service:

```bash
# From inside a VM — get token for Key Vault
curl -s -H "Metadata: true" \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net" \
  | python3 -m json.tool
```

From application code (use Azure SDK, not raw HTTP):
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()  # Uses managed identity automatically in Azure
client = SecretClient(vault_url="https://myvault.vault.azure.net/", credential=credential)
```

`DefaultAzureCredential` tries: environment variables → workload identity → managed identity → Azure CLI → developer tools. This chain means a local developer uses their CLI credentials; production uses managed identity. No secrets required.

---

## Phase 5: Service Principals

### 5.1 Creating Service Principals

Service Principals are application identities in Entra ID. Every App Registration has an associated Service Principal in each tenant where it's used.

```bash
# Create a service principal with a secret (avoid — prefer certificates or federated credentials)
az ad sp create-for-rbac \
  --name "my-app-sp" \
  --role "Contributor" \
  --scopes /subscriptions/<subId>/resourceGroups/<rg>

# Create SP with certificate authentication (better)
az ad sp create-for-rbac \
  --name "my-app-sp" \
  --create-cert \
  --cert myCert \
  --keyvault myKeyVault \
  --role "Reader" \
  --scopes /subscriptions/<subId>

# Rotate a secret (expires old one, creates new)
az ad sp credential reset --name <appIdOrName>

# List all credentials on a service principal
az ad sp credential list --id <appId>
```

### 5.2 Federated Credentials (Best Practice for CI/CD)

Federated credentials eliminate secrets entirely. Configure the Service Principal to trust tokens from an external OIDC provider (GitHub Actions, Kubernetes, etc.).

**For GitHub Actions**:
```bash
# Create the federated credential on the app registration
az ad app federated-credential create \
  --id <appId> \
  --parameters '{
    "name": "github-prod",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:myOrg/myRepo:environment:production",
    "description": "GitHub Actions production environment",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

In GitHub Actions workflow:
```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: azure/login@v2
    with:
      client-id: ${{ secrets.AZURE_CLIENT_ID }}
      tenant-id: ${{ secrets.AZURE_TENANT_ID }}
      subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

No secret stored anywhere. The OIDC token from GitHub is exchanged for an Azure access token. [Source: Workload Identity Federation docs](https://learn.microsoft.com/en-us/azure/active-directory/develop/workload-identity-federation)

**Subject claim patterns for GitHub**:
- `repo:ORG/REPO:ref:refs/heads/main` — main branch only
- `repo:ORG/REPO:environment:production` — specific environment
- `repo:ORG/REPO:pull_request` — PRs (read-only scenarios)

---

## Phase 6: Workload Identity Federation

### 6.1 For AKS / Kubernetes

Azure Workload Identity for AKS replaces pod identity (deprecated). The flow:

1. Create user-assigned managed identity
2. Create federated credential on that identity, trusting the AKS OIDC issuer
3. Annotate the Kubernetes ServiceAccount with the identity's client ID
4. Pods using that ServiceAccount get Azure tokens automatically

```bash
# Enable OIDC issuer on AKS cluster
az aks update --name myAKS --resource-group myRG --enable-oidc-issuer --enable-workload-identity

# Get the OIDC issuer URL
OIDC_ISSUER=$(az aks show --name myAKS --resource-group myRG --query "oidcIssuerProfile.issuerUrl" -o tsv)

# Create user-assigned managed identity
az identity create --name myWorkloadIdentity --resource-group myRG

CLIENT_ID=$(az identity show --name myWorkloadIdentity --resource-group myRG --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show --name myWorkloadIdentity --resource-group myRG --query principalId -o tsv)

# Create federated credential
az identity federated-credential create \
  --name k8s-federated \
  --identity-name myWorkloadIdentity \
  --resource-group myRG \
  --issuer "$OIDC_ISSUER" \
  --subject "system:serviceaccount:my-namespace:my-k8s-serviceaccount" \
  --audience "api://AzureADTokenExchange"

# Assign role to the managed identity
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/<subId>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kvName>
```

Kubernetes side:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-k8s-serviceaccount
  namespace: my-namespace
  annotations:
    azure.workload.identity/client-id: "<CLIENT_ID>"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: my-namespace
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: my-k8s-serviceaccount
```

---

## Phase 7: Privileged Identity Management (PIM)

### 7.1 What PIM Solves

Standing privileged access (e.g., always-on Owner assignment) violates least privilege and expands blast radius. If an account with standing Owner access is compromised, the attacker has immediate, unlimited access. PIM implements just-in-time (JIT) access: eligible users must activate their role, providing justification, triggering approval workflows, and operating within time limits.

### 7.2 PIM Configuration

**Setting up PIM for Azure RBAC**:
```
Azure Portal > Microsoft Entra ID > Privileged Identity Management > Azure resources
> Select subscription > Roles > Configure each role:
  - Maximum activation duration: 8 hours (not days)
  - Require MFA on activation: Yes
  - Require justification: Yes
  - Require approval: Yes (for Owner, User Access Administrator)
  - Approvers: Security team distribution group
  - Notification emails: Security team on activation
```

**Key PIM assignment types**:
- **Eligible**: User can activate the role when needed; not active by default
- **Active**: Permanently active (should be rare, time-limited, reviewed)

**Access reviews**: Schedule quarterly access reviews for all eligible and active PIM assignments. Reviewers should be resource owners, not the users themselves.

```bash
# PIM is primarily managed via Azure Portal or Microsoft Graph API
# List PIM eligible assignments via Graph:
# GET https://graph.microsoft.com/v1.0/roleManagement/directory/roleEligibilitySchedules
```

### 7.3 PIM Audit

Every PIM activation is logged in Entra ID audit logs with: who activated, which role, what scope, what justification, what time. Query these logs for:
- Activations outside business hours
- Activations not followed by any resource operations (suspicious)
- Repeated activation denials
- Activations from unfamiliar IP or location

---

## Phase 8: Conditional Access

### 8.1 Policy Structure

Conditional Access policies evaluate: **Who** (users/groups) + **What** (apps/resources) + **Conditions** (location, device, risk) → **Grant** or **Block**.

Key policy types:
```
Users: All users (or specific groups, roles, guests)
Cloud Apps: All cloud apps (or specific apps like Azure portal, Microsoft 365)
Conditions:
  - Sign-in risk: High, Medium (requires Entra ID P2)
  - User risk: High, Medium (requires Entra ID P2)
  - Device platforms: iOS, Android, Windows, macOS
  - Locations: Named locations (IP ranges, countries)
  - Client apps: Browser, mobile apps, legacy auth clients
Grant controls:
  - Block access
  - Require MFA
  - Require compliant device (Intune)
  - Require hybrid Azure AD joined device
  - Require approved client app
  - Require app protection policy
```

### 8.2 Critical Policies to Implement

**1. Block legacy authentication** (highest priority — legacy auth bypasses MFA):
```
Users: All users
Cloud apps: All cloud apps
Conditions > Client apps: Exchange ActiveSync clients + Other clients
Grant: Block
```

**2. Require MFA for admins**:
```
Users: Directory roles (Global Admin, Privileged Role Admin, etc.)
Cloud apps: All cloud apps
Grant: Require MFA
```

**3. Risk-based sign-in policy**:
```
Users: All users (exclude break-glass accounts)
Cloud apps: All cloud apps
Conditions > Sign-in risk: High
Grant: Block (or Require MFA + compliant device)
```

**4. Named locations** — Define trusted IP ranges (corporate network, VPN egress). Use these in policies to require stricter controls from outside trusted locations.

### 8.3 Break-Glass Accounts

Always maintain 2 break-glass (emergency access) accounts that are:
- Cloud-only (not synced from on-premises AD)
- Global Administrators
- Excluded from ALL Conditional Access policies
- Using long, complex passwords stored in physical secure location
- MFA via FIDO2 hardware key, not phone
- Monitored with alerts on any sign-in

---

## Phase 9: App Registrations vs Enterprise Applications

### 9.1 The Distinction

This confuses nearly every developer. They are two different objects representing two sides of the same coin:

| Concept | App Registration | Enterprise Application (Service Principal) |
|---------|-----------------|---------------------------------------------|
| What it is | The definition/blueprint of an application | The instance of that app in a specific tenant |
| Where it lives | Your tenant (the home tenant) | Every tenant where the app is used |
| What you configure | Auth settings, redirect URIs, API permissions requested, exposed scopes | Permissions granted, user assignment, SSO config, provisioning |
| Analogy | A class definition | An instantiated object |

When you create an App Registration in your tenant, a Service Principal (Enterprise Application) is automatically created in your tenant. When another tenant consents to your app, a Service Principal is created in their tenant — but the App Registration stays in yours.

### 9.2 Microsoft Graph API Permissions

Graph permissions come in two types:
- **Delegated**: App acts on behalf of a signed-in user. The intersection of the user's permissions and the app's permissions.
- **Application**: App acts as itself (daemon, background service). No user context. Requires admin consent.

```bash
# Add a delegated permission to an app registration
az ad app permission add \
  --id <appId> \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope  # User.Read (delegated)

# Add an application permission
az ad app permission add \
  --id <appId> \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions df021288-bdef-4463-88db-98f22de89214=Role   # User.Read.All (application)

# Grant admin consent
az ad app permission admin-consent --id <appId>

# List permissions on an app
az ad app permission list --id <appId> --output json
```

**Security rule**: Application permissions (`.Role` type) to Microsoft Graph are extremely sensitive. `Directory.ReadWrite.All` as an application permission is effectively Global Administrator access. Audit these aggressively.

---

## Phase 10: Audit Logs and Monitoring

### 10.1 Entra ID Logs

Two critical log types in Entra ID:
- **Sign-in logs**: Every authentication attempt, MFA result, Conditional Access policy applied, risk level
- **Audit logs**: Every change to Entra ID objects (user created, role assigned, app permission granted, password reset)

```bash
# Via Azure CLI (requires Microsoft.Graph module or REST)
# Sign-in logs via Graph:
# GET https://graph.microsoft.com/v1.0/auditLogs/signIns?$filter=createdDateTime ge 2024-01-01

# Forward to Log Analytics for querying:
# Azure Portal > Entra ID > Monitoring > Diagnostic settings > Add setting
# Send to Log Analytics workspace
```

**Key alerts to configure in Sentinel or Azure Monitor**:
```kql
// Suspicious PIM activations outside business hours
AuditLogs
| where OperationName == "Add eligible member to role in PIM completed (permanent)"
| where TimeGenerated !between(datetime(08:00) .. datetime(18:00))
| project TimeGenerated, InitiatedBy, TargetResources

// Failed MFA followed by success from different location
SigninLogs
| where ResultType == "50074"  // MFA required
| join kind=inner (SigninLogs | where ResultType == 0) on UserPrincipalName
| where geo_distance(Location, Location1) > 100  // Impossible travel proxy
```

### 10.2 Azure Activity Log

Every ARM operation is logged in the Activity Log (subscription-level). Integrate with Log Analytics for long-term retention (default 90 days):

```bash
# Create diagnostic setting to send Activity Log to Log Analytics
az monitor diagnostic-settings create \
  --name "ActivityLogToLA" \
  --resource /subscriptions/<subId> \
  --workspace /subscriptions/<subId>/resourceGroups/<rg>/providers/Microsoft.OperationalInsights/workspaces/<wsName> \
  --logs '[{"category":"Administrative","enabled":true},{"category":"Security","enabled":true},{"category":"Policy","enabled":true}]'
```

---

## Phase 11: Cross-Tenant Access and B2B

### 11.1 Cross-Tenant Access Policies

Configure via: Entra ID > External Identities > Cross-tenant access settings

Two layers:
- **Inbound settings**: What external tenants/users can access in your tenant
- **Outbound settings**: What your users can access in external tenants

Security posture:
- Default: Allow B2B collaboration (can be restrictive — depends on org policy)
- Configure specific trust relationships for partner organizations (narrow, not broad)
- Enable cross-tenant sign-in logs to see all B2B authentications

### 11.2 B2B Security Risks

- B2B guests get membership in your Entra ID tenant
- They can enumerate other users/groups unless restricted
- Apply Conditional Access to guests (require MFA, device compliance)
- Regularly review guest access via Entra ID Access Reviews
- Set guest user access restrictions: `Guest user access is restricted to properties and memberships of their own directory objects`

---

## Self-Review Checklist: Azure IAM

Go through this before signing off on any Azure IAM configuration:

**Identity Hygiene**
- [ ] No service principal secrets older than 90 days; certificates preferred over secrets; federated credentials preferred over both
- [ ] All automation uses Managed Identities or Workload Identity Federation — no hardcoded credentials in code or CI/CD secrets
- [ ] Service principals have minimal, documented role assignments at the narrowest possible scope
- [ ] Break-glass accounts exist, are documented, monitored, and excluded from Conditional Access

**RBAC Assignments**
- [ ] No standing Owner or Contributor assignments at subscription scope — all handled via PIM eligible assignments
- [ ] No assignments to individual users at broad scope (subscription/management group) — use groups
- [ ] All custom roles have been reviewed for `Actions: ["*"]` or overly broad wildcards
- [ ] `NotActions` reviewed — confirm no security reliance on them (they are NOT deny statements)
- [ ] Data plane roles (`Storage Blob Data Reader/Contributor`, `Key Vault Secrets User`) assigned separately from control plane roles

**PIM**
- [ ] PIM activated for all roles at subscription scope and above
- [ ] Maximum activation duration set to ≤8 hours for Owner/Contributor
- [ ] Approval workflow enabled for Owner and User Access Administrator
- [ ] Quarterly access reviews scheduled for all eligible assignments

**Conditional Access**
- [ ] Legacy authentication blocked for all users
- [ ] MFA required for all admins (Entra ID roles + subscription owners)
- [ ] Risk-based policy enabled (if Entra ID P2 licensed)
- [ ] Break-glass accounts excluded from all CA policies and monitored for any sign-in

**App Registrations & Service Principals**
- [ ] No unused app registrations or service principals (audit with `az ad app list --all`)
- [ ] No application permissions to Microsoft Graph without documented justification and admin consent reviewed
- [ ] Redirect URIs do not include localhost for production apps
- [ ] All service principal credentials have expiry dates set

**Logging and Monitoring**
- [ ] Entra ID sign-in and audit logs forwarded to Log Analytics or SIEM
- [ ] Azure Activity Log exported with 1+ year retention
- [ ] Alerts configured for: global admin additions, new app permission consents, PIM activations outside hours, impossible travel
- [ ] Credential reports reviewed monthly (`az ad user list` + sign-in activity check)

**Cross-Tenant**
- [ ] B2B guest access reviewed quarterly via Access Reviews
- [ ] Cross-tenant access policies documented and restricted to known partner tenants only
- [ ] Guest users subject to Conditional Access (MFA at minimum)

---

## Cross-Domain Connections

**Azure IAM → DevOps Pipelines**: Every GitHub Actions workflow, Azure DevOps pipeline, and Terraform run is an identity attack surface. Service connection credentials in Azure DevOps are service principals. Rotate them. Use Workload Identity Federation where available. A leaked pipeline secret = full subscription access if over-privileged.

**Azure IAM → Kubernetes (AKS)**: Pod identities in AKS must use Azure Workload Identity (the pod-level managed identity pattern). Never mount service account keys into pods. AKS node pools have system-assigned managed identities — scope their permissions tightly. The kubelet identity has permissions to pull from ACR; audit what else it can do.

**Azure IAM → Networking**: Managed Identity tokens are obtained via the Instance Metadata Service at `169.254.169.254`. In AKS, the Azure Workload Identity webhook injects projected service account tokens instead. If an SSRF vulnerability exists in your application, an attacker can reach the IMDS endpoint and steal the instance's managed identity token — identical blast radius to a leaked service principal secret.

**Azure IAM → Security**: Entra ID Identity Protection uses machine learning to detect risky sign-ins and compromised users. These risk signals feed directly into Conditional Access. If you're not using Entra ID P2 and acting on risk signals, you're flying blind. Every password spray, every credential stuffing attempt shows up in sign-in risk — if you're not alerting on it, it's silent exploitation.
