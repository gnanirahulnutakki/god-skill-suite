#!/usr/import/env python3
"""
Evaluate Skills Framework
=========================

This script will run test suites defined in `tests.json` within each skill folder 
against a local or remote LLM (Ollama or OpenAI API) to scientifically verify 
that the skill enforces the correct behavior and constraints.

Usage:
  # Export your standard API key to use OpenAI APIs
  export OPENAI_API_KEY="sk-..."
  python scripts/evaluate_skills.py --provider openai --model gpt-4o-mini

  # Use Ollama locally (zero auth, totally free)
  python scripts/evaluate_skills.py --provider ollama --model llama3.1

  # Test a specific skill
  python scripts/evaluate_skills.py --provider ollama --skill god-meta-conductor
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def c(color, text):
    return f"{color}{text}{RESET}"

def call_openai_api(messages, model="gpt-4o-mini"):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(c(RED, "Error: OPENAI_API_KEY environment variable is not set."))
        sys.exit(1)

    url = "https://api.openai.com/v1/chat/completions"
    data = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.0
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(c(RED, f"OpenAI API Error ({e.code}): {body}"))
        sys.exit(1)

def call_ollama_api(messages, model="llama3.1"):
    url = "http://localhost:11434/api/chat"
    data = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
    })

    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body["message"]["content"]
    except urllib.error.URLError as e:
        print(c(RED, f"Ollama Connection Error: {e}"))
        print(c(YELLOW, "Please ensure Ollama is running (e.g. `ollama serve`)."))
        sys.exit(1)

def execute_llm(provider, model, system_prompt, test_case):
    # Assemble messages
    messages = [{"role": "system", "content": system_prompt}]
    
    if "messages" in test_case:
        messages.extend(test_case["messages"])
    elif "prompt" in test_case:
        messages.append({"role": "user", "content": test_case["prompt"]})
    
    if provider == "openai":
        return call_openai_api(messages, model)
    elif provider == "ollama":
        return call_ollama_api(messages, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

def verify_assertions(response_text, assertions):
    failures = []
    
    for assertion in assertions:
        a_type = assertion.get("type")
        val = assertion.get("value")
        
        if a_type == "contains":
            if val not in response_text:
                failures.append(f"Expected to contain '{val}'.")
        elif a_type == "not_contains":
            if val in response_text:
                failures.append(f"Expected NOT to contain '{val}'.")
        elif a_type == "regex":
            if not re.search(val, response_text):
                failures.append(f"Expected regex match for '{val}'.")
        else:
            failures.append(f"Unknown assertion type: {a_type}")
            
    return failures

def run_tests():
    parser = argparse.ArgumentParser(description="Evaluate AI Skills against Test Suites.")
    parser.add_argument("--provider", choices=["openai", "ollama"], default="ollama", help="LLM Provider to use.")
    parser.add_argument("--model", type=str, default="llama3.1", help="Model name.")
    parser.add_argument("--skill", type=str, help="Specific skill name to test (e.g., god-meta-conductor). Default: all.")
    parser.add_argument("--output", type=str, help="File path to write markdown test report.")
    args = parser.parse_args()

    skills_dir = Path(__file__).parent.parent / "skills"
    
    # Process only skills that have a tests.json
    skills_to_test = []
    if args.skill:
        tests_file = skills_dir / args.skill / "tests.json"
        if tests_file.exists():
            skills_to_test.append(skills_dir / args.skill)
        else:
            print(c(RED, f"No tests.json found for {args.skill}"))
            sys.exit(1)
    else:
        for skill_path in sorted(skills_dir.iterdir()):
            if skill_path.is_dir() and (skill_path / "tests.json").exists():
                skills_to_test.append(skill_path)

    if not skills_to_test:
        print(c(YELLOW, "No integration tests found. Add `tests.json` files to skill directories."))
        return

    print(f"Running skill evaluations using {c(BOLD, args.provider.upper())} ({args.model})...\n")

    total_tests = 0
    passed_tests = 0

    report_content = [
        f"# God-Level Skill Suite Test Report",
        f"**Provider:** `{args.provider}` | **Model:** `{args.model}`",
        f"",
        f"## Detailed Results"
    ]

    for skill_path in skills_to_test:
        skill_name = skill_path.name
        print(c(BOLD, f"Testing Skill: {skill_name}"))
        report_content.append(f"\n### {skill_name}")
        
        # Load System Prompt
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            print(c(RED, f"  Missing SKILL.md for {skill_name}\n"))
            report_content.append(f"- ❌ Missing `SKILL.md`")
            continue
            
        with open(skill_file, "r", encoding="utf-8") as f:
            system_prompt = f.read()
            
        # Load Tests
        tests_file = skill_path / "tests.json"
        with open(tests_file, "r", encoding="utf-8") as f:
            suite = json.load(f)
            
        for idx, test_case in enumerate(suite.get("tests", [])):
            total_tests += 1
            test_name = test_case.get("name", f"Test {idx+1}")
            
            print(f"  Running: {test_name}...", end="", flush=True)
            
            try:
                response = execute_llm(args.provider, args.model, system_prompt, test_case)
            except Exception as e:
                print(c(RED, f" ERROR: {e}"))
                report_content.append(f"- ❌ **{test_name}**: Network Error `{e}`")
                continue
                
            failures = verify_assertions(response, test_case.get("assertions", []))
            
            if not failures:
                print(c(GREEN, " PASS"))
                report_content.append(f"- ✅ **{test_name}**")
                passed_tests += 1
            else:
                print(c(RED, " FAIL"))
                print(c(YELLOW, f"    Response text sample: {response[:150]}..."))
                report_content.append(f"- ❌ **{test_name}**")
                for fail in failures:
                    print(c(RED, f"    - {fail}"))
                    report_content.append(f"  - _Failed: {fail}_")
        print()

    print("=" * 50)
    summary_msg = f"{passed_tests}/{total_tests} passed"
    report_content.insert(2, f"**Results:** {passed_tests} passed / {total_tests - passed_tests} failed out of {total_tests} total.")
    
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(report_content), encoding="utf-8")
        print(f"Saved markdown report to {args.output}")

    if passed_tests == total_tests:
        print(c(GREEN, f"ALL TESTS PASSED: {summary_msg}"))
    else:
        print(c(RED, f"SOME TESTS FAILED: {summary_msg}"))
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
