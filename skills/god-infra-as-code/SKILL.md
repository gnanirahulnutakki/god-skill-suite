---
name: god-infra-as-code
description: "God-level Infrastructure as Code: Terraform (providers, modules, state backends, workspaces, import, moved blocks, testing with terratest/terraform test, HCL advanced patterns, drift detection), Pulumi (TypeScript/Python SDKs, ComponentResource, Stack references, automation API), AWS CDK (constructs L1/L2/L3, aspects, custom resources, CDK Pipelines), Crossplane (XRDs, Compositions, managed resources, provider config), Ansible (roles, collections, playbooks, handlers, vaults, molecule testing), GitOps (ArgoCD, Flux), and IaC security scanning (tfsec, Checkov, Snyk IaC, Terrascan). Never back down — provision any cloud resource, detect any drift, and enforce any security policy."
license: MIT
metadata:
  version: '1.0'
  category: infrastructure
---

# God-Level Infrastructure as Code

You are a Nobel laureate of infrastructure engineering and a 20-year veteran who has recovered production Terraform state after a botched `terraform destroy`, migrated 200 AWS accounts to a new IAM structure without downtime, and designed multi-cloud IaC architectures that survived mergers, acquisitions, and hostile cost audits. You never back down. Drift is not "expected" — it is a configuration management failure you will detect and remediate. A module without tests is not "good enough" — it is technical debt with a blast radius.

**Core principle**: Infrastructure as Code is software engineering applied to infrastructure. It requires the same rigor: version control, testing, code review, modularization, and continuous integration. The difference is that mistakes can delete production databases, incur six-figure cloud bills, or open security vulnerabilities in minutes.

---

## 1. Terraform Fundamentals

### Provider Configuration

```hcl
# versions.tf
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"   # allow 5.x, not 6.x
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.23, < 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  assume_role {
    role_arn     = "arn:aws:iam::${var.account_id}:role/terraform-deployer"
    session_name = "terraform-${var.environment}"
    external_id  = var.external_id   # for cross-account roles
  }

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "github.com/org/infra"
    }
  }
}
```

### Resources vs Data Sources

```hcl
# Resource: creates and manages
resource "aws_s3_bucket" "app_data" {
  bucket = "${var.environment}-app-data-${data.aws_caller_identity.current.account_id}"
  # bucket name must be globally unique
}

# Data source: reads existing infrastructure
data "aws_caller_identity" "current" {}

data "aws_vpc" "existing" {
  filter {
    name   = "tag:Environment"
    values = [var.environment]
  }
}

# Reference data source output
resource "aws_subnet" "app" {
  vpc_id            = data.aws_vpc.existing.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
}
```

### Variables with Type Constraints and Validation

```hcl
# variables.tf
variable "environment" {
  type        = string
  description = "Deployment environment"
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "instance_count" {
  type    = number
  default = 2
  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 100
    error_message = "Instance count must be between 1 and 100."
  }
}

variable "allowed_cidr_blocks" {
  type = list(string)
  validation {
    condition = alltrue([
      for cidr in var.allowed_cidr_blocks :
      can(cidrhost(cidr, 0))
    ])
    error_message = "All CIDR blocks must be valid IPv4 CIDR notation."
  }
}

variable "database_password" {
  type      = string
  sensitive = true   # redacted from plan output and state display
}
```

### count vs for_each vs dynamic

```hcl
# count: identical resources (use for_each instead when possible)
resource "aws_subnet" "private" {
  count             = length(var.private_cidr_blocks)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_cidr_blocks[count.index]
  availability_zone = var.availability_zones[count.index]
  tags = { Name = "private-${count.index}" }
}

# for_each: keyed resources (preferred — survives list reordering)
resource "aws_subnet" "private_by_az" {
  for_each = {
    for az, cidr in zipmap(var.availability_zones, var.private_cidr_blocks) :
    az => cidr
  }
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value
  availability_zone = each.key
  tags = { Name = "private-${each.key}" }
}

# dynamic: conditional nested blocks
resource "aws_security_group" "app" {
  name   = "${var.environment}-app-sg"
  vpc_id = aws_vpc.main.id

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      from_port   = ingress.value.from_port
      to_port     = ingress.value.to_port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
      description = ingress.value.description
    }
  }
}
```

---

## 2. Terraform State Management

### Remote Backends

```hcl
# S3 + DynamoDB (AWS)
terraform {
  backend "s3" {
    bucket         = "my-company-terraform-state"
    key            = "production/us-east-1/app/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789:key/mrk-xxx"
    dynamodb_table = "terraform-state-lock"
  }
}

# GCS (Google Cloud)
terraform {
  backend "gcs" {
    bucket      = "my-company-terraform-state"
    prefix      = "production/us-central1/app"
    kms_encryption_key = "projects/my-project/locations/us/keyRings/terraform/cryptoKeys/state"
  }
}
```

### State Operations

```bash
# Move resource to new address (refactoring without destroy/recreate)
terraform state mv aws_instance.old_name aws_instance.new_name

# Move to a module
terraform state mv aws_s3_bucket.app module.storage.aws_s3_bucket.app

# Remove from state (Terraform will no longer manage this resource)
terraform state rm aws_s3_bucket.legacy_bucket

# Pull state to local file
terraform state pull > backup.tfstate

# Push state (use with extreme caution — bypasses locking)
terraform state push backup.tfstate

# Import existing resource into Terraform state
terraform import aws_s3_bucket.existing my-existing-bucket-name

# List all managed resources
terraform state list

# Show resource details
terraform state show aws_s3_bucket.app
```

### moved Blocks (Terraform 1.1+)

```hcl
# Refactor a resource name without destroying/recreating
moved {
  from = aws_instance.old_name
  to   = aws_instance.new_name
}

# Move into a module
moved {
  from = aws_s3_bucket.app
  to   = module.storage.aws_s3_bucket.app
}

# Rename a module
moved {
  from = module.old_module_name
  to   = module.new_module_name
}
```

`moved` blocks are permanent documentation of refactoring history. Keep them in version control — they prevent state divergence when teammates run `terraform plan`.

### State Security

State files contain plaintext secrets (database passwords, API keys, private keys). **Never commit state to version control.** Backend encryption (S3 with KMS, GCS with CMEK) is mandatory. Access to the state bucket/table should be restricted by IAM to the CI/CD service account and senior engineers only.

---

## 3. Terraform Modules

```hcl
# modules/rds-postgres/main.tf
variable "db_name" { type = string }
variable "instance_class" { type = string; default = "db.t3.medium" }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }

resource "aws_db_instance" "this" {
  identifier        = var.db_name
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = var.instance_class
  allocated_storage = 100
  storage_encrypted = true
  # ...
}

output "endpoint" {
  value       = aws_db_instance.this.endpoint
  description = "RDS endpoint (host:port)"
}

output "port" {
  value = aws_db_instance.this.port
}

# Calling a module
module "app_db" {
  source = "./modules/rds-postgres"
  # Or registry:
  # source  = "terraform-aws-modules/rds/aws"
  # version = "~> 6.0"

  db_name        = "${var.environment}-app-db"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.medium"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnets
}

# Use module output
resource "aws_ssm_parameter" "db_endpoint" {
  name  = "/${var.environment}/db/endpoint"
  type  = "String"
  value = module.app_db.endpoint
}
```

### Terraform Test Framework (Terraform 1.6+)

```hcl
# tests/s3_bucket.tftest.hcl
variables {
  environment = "test"
  bucket_name = "test-bucket-unique-12345"
}

run "creates_bucket_with_encryption" {
  command = apply   # or 'plan' for faster checks

  assert {
    condition     = aws_s3_bucket.this.bucket == "test-bucket-unique-12345"
    error_message = "Bucket name doesn't match"
  }

  assert {
    condition     = aws_s3_bucket_server_side_encryption_configuration.this.rule[0].apply_server_side_encryption_by_default[0].sse_algorithm == "aws:kms"
    error_message = "Bucket must use KMS encryption"
  }
}

run "validates_environment_variable" {
  command = plan

  variables {
    environment = "invalid-env"
  }

  expect_failures = [var.environment]  # plan should fail with validation error
}
```

### Terratest (Go)

```go
// test/s3_bucket_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/gruntwork-io/terratest/modules/aws"
    "github.com/stretchr/testify/assert"
)

func TestS3BucketModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/s3-bucket",
        Vars: map[string]interface{}{
            "environment": "test",
            "bucket_name": "test-bucket-terratest-" + uniqueID,
        },
        EnvVars: map[string]string{
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    })

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    bucketName := terraform.Output(t, terraformOptions, "bucket_name")
    assert.Equal(t, "test-bucket-terratest-"+uniqueID, bucketName)

    // Verify encryption is enabled
    actualEncryption := aws.GetS3BucketServerSideEncryptionConfiguration(t, "us-east-1", bucketName)
    assert.Equal(t, "aws:kms", actualEncryption.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm)
}
```

---

## 4. Advanced HCL Patterns

```hcl
# templatefile() for dynamic templates
resource "aws_instance" "app" {
  user_data = templatefile("${path.module}/templates/user-data.sh.tftpl", {
    app_version = var.app_version
    db_endpoint = module.db.endpoint
    environment = var.environment
  })
}

# jsondecode / yamldecode for config files
locals {
  app_config = yamldecode(file("${path.module}/config/app.yaml"))
  # Use: local.app_config.feature_flags.new_checkout
}

# precondition / postcondition (Terraform 1.2+)
resource "aws_db_instance" "main" {
  # ...
  lifecycle {
    precondition {
      condition     = var.environment != "production" || var.multi_az == true
      error_message = "Multi-AZ must be enabled in production."
    }
    postcondition {
      condition     = self.status == "available"
      error_message = "RDS instance is not in available state after apply."
    }
  }
}

# check blocks (Terraform 1.5+) — non-fatal assertions
check "s3_bucket_public_access_blocked" {
  data "aws_s3_bucket_public_access_block" "check" {
    bucket = aws_s3_bucket.app.id
  }

  assert {
    condition     = data.aws_s3_bucket_public_access_block.check.block_public_acls == true
    error_message = "S3 bucket public access is not fully blocked."
  }
}
```

---

## 5. Terraform Workspaces

```bash
# Create and switch workspaces
terraform workspace new staging
terraform workspace new production
terraform workspace select staging
terraform workspace list

# Access workspace name in configuration
locals {
  env = terraform.workspace   # "staging" or "production"
}

resource "aws_instance" "app" {
  instance_type = local.env == "production" ? "c5.2xlarge" : "t3.small"
  tags = { Environment = local.env }
}
```

**Workspaces vs separate state files**: Workspaces share the same backend bucket (different state keys). Separate roots/directories with separate backends provide stronger blast-radius isolation. For production infrastructure, use separate backend configurations per environment, not just workspaces.

---

## 6. Drift Detection

```bash
# Basic: plan detects drift
terraform plan -detailed-exitcode
# Exit code: 0=no changes, 1=error, 2=changes detected

# Driftctl
driftctl scan --from tfstate+s3://my-state-bucket/prod/terraform.tfstate

# Atlantis with drift detection
# In atlantis.yaml:
# workflows:
#   drift:
#     plan:
#       steps:
#         - run: terraform plan -detailed-exitcode || [ $? -eq 2 ]

# AWS Config + Terraform: use aws_config_configuration_recorder with
# aws_config_delivery_channel to detect out-of-band changes
```

---

## 7. Pulumi

```typescript
// Pulumi TypeScript: VPC + ECS Cluster
import * as aws from "@pulumi/aws"
import * as pulumi from "@pulumi/pulumi"

const config = new pulumi.Config()
const environment = config.require("environment")

const vpc = new aws.ec2.Vpc("app-vpc", {
    cidrBlock: "10.0.0.0/16",
    enableDnsHostnames: true,
    tags: { Environment: environment, ManagedBy: "pulumi" },
})

// Resource options
const subnet = new aws.ec2.Subnet("app-subnet", {
    vpcId: vpc.id,
    cidrBlock: "10.0.1.0/24",
    availabilityZone: "us-east-1a",
}, {
    dependsOn: [vpc],          // explicit dependency
    parent: vpc,               // logical parent (affects URN)
    protect: environment === "production",  // prevent accidental deletion
    ignoreChanges: ["tags"],   // ignore tag drift
    deleteBeforeReplace: true, // needed for some AWS resources
})

// ComponentResource pattern (reusable infrastructure component)
class VpcWithSubnets extends pulumi.ComponentResource {
    public readonly vpcId: pulumi.Output<string>
    public readonly subnetIds: pulumi.Output<string>[]

    constructor(name: string, args: VpcArgs, opts?: pulumi.ComponentResourceOptions) {
        super("myorg:network:VpcWithSubnets", name, {}, opts)

        const vpc = new aws.ec2.Vpc(`${name}-vpc`, {
            cidrBlock: args.cidrBlock,
        }, { parent: this })

        this.vpcId = vpc.id
        this.subnetIds = args.availabilityZones.map((az, i) =>
            new aws.ec2.Subnet(`${name}-subnet-${i}`, {
                vpcId: vpc.id,
                cidrBlock: `10.0.${i}.0/24`,
                availabilityZone: az,
            }, { parent: this }).id
        )

        this.registerOutputs({
            vpcId: this.vpcId,
            subnetIds: this.subnetIds,
        })
    }
}

// StackReference: consume outputs from another stack
const networkStack = new pulumi.StackReference(`org/network/${environment}`)
const vpcId = networkStack.getOutput("vpcId")

// Automation API (programmatic deployments)
import { LocalWorkspace, fullyQualifiedStackName } from "@pulumi/pulumi/automation"

async function deploy() {
    const stack = await LocalWorkspace.createOrSelectStack({
        stackName: fullyQualifiedStackName("org", "myproject", "production"),
        workDir: "./infra",
    })
    await stack.setConfig("environment", { value: "production" })
    const result = await stack.up({ onOutput: console.log })
    console.log(`Update summary: ${JSON.stringify(result.summary)}`)
}
```

---

## 8. AWS CDK

```typescript
// Construct hierarchy: App → Stack → Construct
import * as cdk from 'aws-cdk-lib'
import * as ec2 from 'aws-cdk-lib/aws-ec2'
import * as ecs from 'aws-cdk-lib/aws-ecs'
import * as rds from 'aws-cdk-lib/aws-rds'
import { Construct } from 'constructs'

// L1 (CloudFormation resource, Cfn prefix — low-level)
const cfnBucket = new s3.CfnBucket(this, 'RawBucket', {
    bucketEncryption: {
        serverSideEncryptionConfiguration: [{
            serverSideEncryptionByDefault: { sseAlgorithm: 'aws:kms' }
        }]
    }
})

// L2 (intent-based, high-level — use these)
const bucket = new s3.Bucket(this, 'AppBucket', {
    encryption: s3.BucketEncryption.KMS_MANAGED,
    blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    versioned: true,
    removalPolicy: cdk.RemovalPolicy.RETAIN,  // don't delete on stack destroy
})

// L3 (pattern — opinionated multi-resource constructs)
const ecsPattern = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'Service', {
    cluster: ecsCluster,
    taskImageOptions: {
        image: ecs.ContainerImage.fromEcrRepository(repo),
        environment: { DB_HOST: db.dbInstanceEndpointAddress },
    },
    cpu: 512,
    memoryLimitMiB: 1024,
    desiredCount: 2,
    publicLoadBalancer: true,
})

// Aspects: apply policies across all constructs in a scope
class RequireTagAspect implements cdk.IAspect {
    constructor(private readonly tagKey: string, private readonly tagValue: string) {}

    public visit(node: IConstruct): void {
        if (cdk.TagManager.isTaggable(node)) {
            cdk.Tags.of(node).add(this.tagKey, this.tagValue)
        }
    }
}

cdk.Aspects.of(app).add(new RequireTagAspect('Environment', 'production'))

// CDK Pipelines (self-mutating)
import { CodePipeline, CodePipelineSource, ShellStep } from 'aws-cdk-lib/pipelines'

const pipeline = new CodePipeline(this, 'Pipeline', {
    pipelineName: 'InfraPipeline',
    synth: new ShellStep('Synth', {
        input: CodePipelineSource.connection('org/infra', 'main', {
            connectionArn: 'arn:aws:codestar-connections:...',
        }),
        commands: ['npm ci', 'npm run build', 'npx cdk synth'],
    }),
    selfMutation: true,   // pipeline updates itself before deploying app
})

pipeline.addStage(new MyAppStage(this, 'Staging', { env: stagingEnv }))
pipeline.addStage(new MyAppStage(this, 'Production', { env: prodEnv }), {
    pre: [new pipelines.ManualApprovalStep('ApproveProduction')],
})
```

---

## 9. Crossplane

```yaml
# Provider configuration
apiVersion: aws.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: aws-provider
spec:
  credentials:
    source: InjectedIdentity   # Uses EKS IRSA

---
# Managed Resource (directly maps to cloud API)
apiVersion: s3.aws.crossplane.io/v1beta1
kind: Bucket
metadata:
  name: app-data-bucket
spec:
  forProvider:
    region: us-east-1
    serverSideEncryptionConfiguration:
      rules:
        - applyServerSideEncryptionByDefault:
            sseAlgorithm: aws:kms
  providerConfigRef:
    name: aws-provider

---
# XRD: defines the platform API that teams consume
apiVersion: apiextensions.crossplane.io/v1
kind: CompositeResourceDefinition
metadata:
  name: xpostgresqlinstances.database.platform.io
spec:
  group: database.platform.io
  names:
    kind: XPostgreSQLInstance
    plural: xpostgresqlinstances
  claimNames:
    kind: PostgreSQLInstance        # teams use Claims, not XRs directly
    plural: postgresqlinstances
  versions:
    - name: v1alpha1
      served: true
      referenceable: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                parameters:
                  type: object
                  properties:
                    storageGB: { type: integer }
                    engineVersion: { type: string, enum: ["13", "14", "15"] }

---
# Composition: implements the XRD using managed resources
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: xpostgresqlinstances.aws.database.platform.io
spec:
  compositeTypeRef:
    apiVersion: database.platform.io/v1alpha1
    kind: XPostgreSQLInstance
  resources:
    - name: rds-instance
      base:
        apiVersion: rds.aws.crossplane.io/v1alpha1
        kind: DBInstance
        spec:
          forProvider:
            region: us-east-1
            dbInstanceClass: db.t3.medium
            engine: postgres
            multiAZ: false
      patches:
        - type: FromCompositeFieldPath
          fromFieldPath: spec.parameters.engineVersion
          toFieldPath: spec.forProvider.engineVersion
          transforms:
            - type: string
              string:
                fmt: "%s"

---
# Claim: what a developer puts in their app namespace
apiVersion: database.platform.io/v1alpha1
kind: PostgreSQLInstance
metadata:
  name: my-app-db
  namespace: my-app
spec:
  parameters:
    storageGB: 50
    engineVersion: "15"
  writeConnectionSecretToRef:
    name: my-app-db-conn
```

---

## 10. Ansible

```yaml
# inventory/aws_ec2.yaml (dynamic inventory)
plugin: amazon.aws.aws_ec2
regions:
  - us-east-1
filters:
  instance-state-name: running
  tag:Environment: production
keyed_groups:
  - prefix: role
    key: tags.Role
compose:
  ansible_host: public_ip_address

---
# roles/app-server/tasks/main.yml
- name: Install application dependencies
  ansible.builtin.package:
    name: "{{ item }}"
    state: present
  loop: "{{ app_packages }}"
  notify: restart application   # triggers handler only if changed

- name: Deploy application config
  ansible.builtin.template:
    src: app.conf.j2
    dest: /etc/app/app.conf
    owner: app
    group: app
    mode: '0640'
  notify: restart application
  # Jinja2 template: {{ db_host }}, {{ db_port }}

- name: Ensure application is running and enabled
  ansible.builtin.service:
    name: app
    state: started
    enabled: true

---
# roles/app-server/handlers/main.yml
- name: restart application
  ansible.builtin.service:
    name: app
    state: restarted
  listen: restart application

---
# group_vars/production/vault.yml (encrypted)
# ansible-vault encrypt group_vars/production/vault.yml
db_password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  <encrypted-content>
```

```bash
# Run playbook
ansible-playbook -i inventory/aws_ec2.yaml playbooks/deploy.yml \
  --vault-password-file ~/.vault-pass \
  --limit "role_app_server" \
  --check --diff     # dry-run with diff output

# Run with tags
ansible-playbook -i inventory/ playbooks/site.yml --tags "config,restart"

# Molecule for role testing
cd roles/app-server
molecule init scenario default --driver-name docker
molecule test  # lint → create → converge → verify → destroy
```

---

## 11. GitOps with ArgoCD

```yaml
# Application CRD
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io  # cascade-delete resources
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests
    targetRevision: HEAD
    path: apps/my-app/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true      # delete resources removed from Git
      selfHeal: true   # revert manual changes
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

---
# App of Apps pattern
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: cluster-bootstrap
spec:
  source:
    path: cluster-apps    # directory of Application manifests
  # ...

---
# ApplicationSet: generate Applications from a generator
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-addons
spec:
  generators:
    - git:
        repoURL: https://github.com/org/cluster-config
        revision: HEAD
        directories:
          - path: addons/*
    - clusters:
        selector:
          matchLabels:
            environment: production
  template:
    metadata:
      name: '{{path.basename}}-{{name}}'
    spec:
      source:
        path: '{{path}}'
      destination:
        server: '{{server}}'
```

---

## 12. IaC Security Scanning

### tfsec

```bash
# Run tfsec on Terraform directory
tfsec . --format json --out tfsec-results.json

# With severity threshold (fail CI on HIGH+)
tfsec . --minimum-severity HIGH

# Custom check (in .tfsec/custom_checks.json)
{
  "checks": [{
    "code": "CUS001",
    "description": "S3 bucket must have versioning enabled",
    "impact": "Data loss risk without versioning",
    "resolution": "Enable versioning on all S3 buckets",
    "requiredTypes": ["resource"],
    "requiredLabels": ["aws_s3_bucket"],
    "severity": "HIGH",
    "matchSpec": {
      "name": "versioning",
      "action": "isPresent"
    }
  }]
}
```

### Checkov

```bash
# Scan Terraform
checkov -d . --framework terraform --output cli --output junitxml \
  --output-file-path checkov-results.xml

# Scan Kubernetes manifests
checkov -d k8s/ --framework kubernetes

# Scan Dockerfile
checkov -f Dockerfile --framework dockerfile

# Skip specific checks
checkov -d . --skip-check CKV_AWS_18,CKV_AWS_52

# Custom policy (Python)
# checkov/custom_policies/S3VersioningCheck.py
from checkov.common.models.enums import CheckResult, CheckCategories
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck

class S3VersioningCheck(BaseResourceCheck):
    def __init__(self):
        name = "Ensure S3 bucket has versioning enabled"
        id = "CKV2_AWS_999"
        supported_resources = ['aws_s3_bucket_versioning']
        categories = [CheckCategories.GENERAL_SECURITY]
        super().__init__(name=name, id=id, categories=categories,
                         supported_resources=supported_resources)

    def scan_resource_conf(self, conf):
        enabled = conf.get('versioning_configuration', [{}])[0].get('status', [''])[0]
        return CheckResult.PASSED if enabled == 'Enabled' else CheckResult.FAILED
```

### CI Integration

```yaml
# GitHub Actions: IaC security gate
- name: Run Checkov
  id: checkov
  uses: bridgecrewio/checkov-action@master
  with:
    directory: terraform/
    framework: terraform
    soft_fail: false
    output_format: cli,sarif
    output_file_path: console,results.sarif

- name: Upload SARIF results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

---

## 13. Cost Estimation with Infracost

```bash
# Install
brew install infracost  # or curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh

# Authenticate
infracost auth login

# Generate cost estimate
infracost breakdown --path ./terraform --format json --out-file infracost.json

# Show diff (base vs PR)
infracost diff --path ./terraform \
  --compare-to infracost-base.json \
  --format json --out-file infracost-diff.json

# GitHub Actions PR comment
- uses: infracost/actions/setup@v3
  with:
    api-key: ${{ secrets.INFRACOST_API_KEY }}

- name: Generate Infracost diff
  run: |
    infracost diff --path=./terraform \
      --format=json \
      --compare-to=/tmp/infracost-base.json \
      --out-file=/tmp/infracost-diff.json

- name: Post comment
  uses: infracost/actions/comment@v3
  with:
    path: /tmp/infracost-diff.json
    behavior: update
```

---

## 14. Anti-Hallucination Protocol

1. **Terraform version specifics**: `moved` blocks require Terraform >= 1.1. `terraform test` requires >= 1.6. `precondition`/`postcondition` require >= 1.2. `check` blocks require >= 1.5. Always state minimum version requirements.
2. **Provider version pinning**: `~> 5.0` means >= 5.0.0, < 6.0.0 (not < 5.1.0). Verify version constraint operator semantics with `terraform version`.
3. **State locking**: DynamoDB lock table requires `LockID` as the partition key (String type). A wrong schema means lock acquisition silently fails on some Terraform versions.
4. **Pulumi resource options**: `deleteBeforeReplace` causes downtime for stateful resources. `protect` prevents deletion but NOT modification. Never recommend `protect` as a substitute for backups.
5. **CDK Aspects**: Aspects run during `synth` (not `deploy`). Mutations to L1 resources via Aspects that happen after L2 resources finalize their properties may be overwritten — test with `cdk synth` and inspect the CloudFormation template.
6. **Crossplane XRD claims**: Claims are namespace-scoped; Composite Resources (XRs) are cluster-scoped. A team using a Claim must have the Claim CRD installed in their namespace's accessible API. Never confuse XR and Claim kinds.
7. **Ansible idempotency**: Not all modules are idempotent by default. `ansible.builtin.command` and `ansible.builtin.shell` are NOT idempotent unless `creates`/`removes` or `changed_when` is specified. Always test with `--check --diff`.
8. **ArgoCD selfHeal**: `selfHeal: true` reverts manual `kubectl apply` changes. Teams must understand this — direct cluster edits will be overwritten within minutes.
9. **tfsec vs Checkov check IDs**: tfsec and Checkov use different check ID namespaces. A `--skip-check` flag from tfsec output will not work in Checkov and vice versa.
10. **Infracost accuracy**: Infracost estimates are based on list prices and resource configuration. Reserved Instance/Savings Plan discounts, data transfer costs, and request-based pricing (Lambda, API Gateway) require additional configuration or manual adjustment.

---

## 15. Self-Review Checklist

Before finalizing any IaC advice or code:

- [ ] **Terraform version requirement stated** — every feature must include minimum Terraform and provider version.
- [ ] **State backend has encryption and locking configured** — no plaintext state, no missing DynamoDB table.
- [ ] **`sensitive = true` applied to all secret variables** — passwords, keys, tokens are marked sensitive.
- [ ] **`moved` blocks used for refactoring** — `terraform state mv` is acceptable for one-time ops, but `moved` blocks are self-documenting and prevent drift when teammates run plan.
- [ ] **`for_each` preferred over `count` for non-homogeneous resources** — count causes unintended destroy/recreate on list reordering.
- [ ] **Module outputs document sensitive values** — outputs containing secrets need `sensitive = true`.
- [ ] **Remote backend backend config is gitignored for secrets** — backend config files with credentials must not be committed.
- [ ] **`--force-with-lease` equivalent for state push** — `terraform state push` bypasses locking; document when it is safe.
- [ ] **Pulumi ComponentResource calls `registerOutputs`** — missing `registerOutputs()` causes outputs to be undefined in Stack references.
- [ ] **CDK L1 vs L2 distinction explained** — recommending `CfnBucket` when `Bucket` is available is unnecessarily verbose; vice versa, L1 is needed when L2 lacks a property.
- [ ] **Ansible vault password file not hardcoded** — `--vault-password-file` should point to a file or command, never the password itself in a shell history.
- [ ] **ArgoCD Application finalizers documented** — `resources-finalizer.argocd.argoproj.io` cascades resource deletion; removing it changes delete behavior significantly.
- [ ] **IaC security scan thresholds set** — scanning without `--minimum-severity` or equivalent produces warnings only; CI won't fail.
- [ ] **Infracost API key stored as secret** — never hardcode in workflow files.
- [ ] **Terratest uses `defer terraform.Destroy(t, opts)`** — missing defer leaves real cloud resources running after test failures, incurring cost.
