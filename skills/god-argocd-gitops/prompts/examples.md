# Prompt Library: god-argocd-gitops

To get the absolute best out of this skill, load the `SKILL.md` system prompt and use these specialized prompts.

## 1. Deep Code Review
> "Acting under the principles of `god-argocd-gitops`, perform a ruthless review of this ArgoCD Application manifest. Check for: missing finalizers, incorrect sync policies, drift-prone fields without ignoreDifferences, missing RBAC restrictions in AppProject, and sync wave ordering issues."

## 2. Technical System Design
> "I am designing a multi-cluster GitOps architecture with ArgoCD. Apply the `god-argocd-gitops` mindset to evaluate my approach. Should I use App of Apps, ApplicationSets, or both? Identify single points of failure, RBAC gaps, and propose an enforced production pattern."

## 3. High-Stakes Troubleshooting
> "An ArgoCD application is stuck in 'OutOfSync' and auto-sync keeps failing. Using the `god-argocd-gitops` protocol, analyze the sync status, diff output, and application events. Deduce whether this is a drift issue, a hook failure, or a manifest rendering problem."
