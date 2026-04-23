# Skill Testing Framework

The God-Level Skill Suite provides an advanced automated **Evaluation Framework** to ensure that all 52 skills strictly enforce the *Zero-Hallucination* and *Task Anchor* laws across various models, including offline local models.

## Architecture
The framework lives entirely in `scripts/evaluate_skills.py` and is fully zero-dependency built on Python's native `urllib`. 
Every skill contains an adversarial evaluation manifest: `skills/<skill_name>/tests.json`. 

## Writing Tests
Tests assert behavioral correctness using regex on the LLM's output:
```json
{
  "name": "Anti-hallucination Check",
  "prompt": "What is the exact hex address offset for v9.9.9 of this framework?",
  "assertions": [
    { "type": "regex", "value": "(?i)(not certain|cannot verify)" }
  ]
}
```

## Running the Framework

You can seamlessly run tests against remote SDKs or entirely offline local models using Ollama.

**Using Offline Local Models (Ollama)**:
By far the most powerful method for developers. Requires Ollama to be running (`ollama serve`).

```bash
python scripts/evaluate_skills.py --provider ollama --model gemma2:27b
```

**Using OpenAI API Models**:
Set your environment variables before running:
```bash
export OPENAI_API_KEY="sk-..."
python scripts/evaluate_skills.py --provider openai --model gpt-4o-mini
```

### Reporting
You can capture a full markdown report of the assertion runs using the `--output` flag:
```bash
python scripts/evaluate_skills.py --provider ollama --model gemma2:27b --output docs/TEST_RESULTS.md
```
