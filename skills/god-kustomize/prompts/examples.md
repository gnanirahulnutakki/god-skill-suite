# Prompt Library: god-kustomize

To get the absolute best out of this skill, load the `SKILL.md` system prompt and use these specialized prompts.

## 1. Deep Code Review
> "Acting under the principles of `god-kustomize`, review this Kustomize overlay structure. Check for: duplicated base content in overlays, use of deprecated fields (patchesStrategicMerge, vars), missing hash suffixes on ConfigMaps, hardcoded namespaces in base, and selector label mutations."

## 2. Technical System Design
> "I am designing a multi-environment Kustomize structure for 5 microservices across dev/staging/prod. Apply the `god-kustomize` mindset to propose a directory layout using bases, overlays, and components. Identify where components should replace duplicated patches."

## 3. High-Stakes Troubleshooting
> "A `kustomize build` is producing unexpected output — resources are missing or duplicated. Using the `god-kustomize` protocol, analyze the kustomization.yaml chain and identify resource resolution, patch targeting, or generator issues."
