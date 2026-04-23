---
name: god-llm-sdk
description: "God-level skill for working with LLM SDKs and AI frameworks: Anthropic Claude SDK (Python/TypeScript), OpenAI SDK (Python/TypeScript), AWS Bedrock SDK, Google Vertex AI SDK, LangChain (chains, agents, tools, memory, callbacks), LlamaIndex (document loaders, index types, query engines, retrievers), DSPy (signatures, modules, optimizers), Hugging Face transformers and datasets, Ollama for local models, LiteLLM for provider-agnostic calls, and the patterns for building production-grade AI applications. Covers API error handling, rate limiting, retry strategies, streaming, token counting, cost management, and async patterns. Never fabricates SDK method signatures — always provides verification path."
metadata:
  version: "1.0.0"
---

# God-Level LLM SDK Mastery

## Researcher-Warrior Mindset

You are an engineer who ships production AI systems, not a notebook experimenter. You understand that LLM APIs change fast — model names are deprecated, parameter names shift, SDK versions break. Every method signature you write must be verifiable. Every API call must handle failure. Every token costs money. Every latency matters to a user.

**Anti-hallucination mandate — CRITICAL**: LLM SDK method signatures, model names, and parameter names are high-hallucination risk. Always:
1. State which SDK version the code targets (e.g., `anthropic>=0.40.0`).
2. Recommend `pip show anthropic` / `pip show openai` to verify installed version before trusting any code here.
3. When uncertain about a specific parameter name, say so explicitly and direct to the official docs.
4. Never invent a method that sounds plausible. Real verification path: official API docs, SDK changelog, GitHub source.

**Verification URLs** (check these when unsure):
- Anthropic: https://docs.anthropic.com/en/api/
- OpenAI: https://platform.openai.com/docs/api-reference
- AWS Bedrock: https://docs.aws.amazon.com/bedrock/
- LangChain: https://python.langchain.com/docs/
- LlamaIndex: https://docs.llamaindex.ai/
- DSPy: https://dspy.ai/

**Cross-domain mandate**: Lessons from distributed systems (retry budgets, circuit breakers), databases (connection pooling, query planning), and web servers (graceful degradation, backpressure) all apply directly to LLM API clients. Treat LLM APIs like any other I/O-bound, rate-limited, expensive external service.

---

## Anthropic Claude SDK

**Install**: `pip install anthropic`
**Verify version**: `pip show anthropic`
**Docs**: https://docs.anthropic.com/en/api/

### Basic Usage
```python
import anthropic

client = anthropic.Anthropic(api_key="sk-ant-...")
# api_key defaults to ANTHROPIC_API_KEY env var — prefer env var in production

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",  # Verify current model names at docs
    max_tokens=1024,                      # REQUIRED — no default
    system="You are a helpful assistant.",  # System prompt is a top-level parameter
    messages=[
        {"role": "user", "content": "Explain gradient descent."}
    ]
)

print(message.content[0].text)
print(f"Input tokens: {message.usage.input_tokens}")
print(f"Output tokens: {message.usage.output_tokens}")
```

**Current model names (as of training cutoff — always verify)**:
- `claude-3-5-sonnet-20241022` — best balance of intelligence and speed
- `claude-3-5-haiku-20241022` — fastest, most economical
- `claude-3-opus-20240229` — most intelligent, highest cost
- Model names include date stamps — check https://docs.anthropic.com/en/docs/about-claude/models for the latest.

### Streaming
```python
# Context manager approach — recommended
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a story."}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    # Access final message after stream completes
    final_message = stream.get_final_message()
    print(f"\nTotal tokens: {final_message.usage.output_tokens}")
```

### Tool Use (Function Calling)
```python
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["city"]
        }
    }
]

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}]
)

# Check if model wants to use a tool
if response.stop_reason == "tool_use":
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    tool_name = tool_use_block.name
    tool_input = tool_use_block.input
    tool_use_id = tool_use_block.id

    # Execute tool, get result
    weather_result = get_weather(**tool_input)  # Your implementation

    # Continue conversation with tool result
    final_response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=tools,
        messages=[
            {"role": "user", "content": "What's the weather in Tokyo?"},
            {"role": "assistant", "content": response.content},  # Full content block
            {"role": "user", "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(weather_result)
                }
            ]}
        ]
    )
```

### Vision (Image Input)
```python
import base64
from pathlib import Path

image_data = base64.standard_b64encode(Path("image.jpg").read_bytes()).decode()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data,
                }
            },
            {"type": "text", "text": "What's in this image?"}
        ]
    }]
)
```

### Token Counting (Before Calling)
```python
# Count tokens without making a real API call
token_count = client.messages.count_tokens(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Hello world"}],
    system="You are a helpful assistant."
)
print(f"Input tokens: {token_count.input_tokens}")
```

---

## OpenAI SDK

**Install**: `pip install openai`
**Verify version**: `pip show openai`
**Docs**: https://platform.openai.com/docs/api-reference

### Basic Usage
```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")  # Defaults to OPENAI_API_KEY env var

response = client.chat.completions.create(
    model="gpt-4o",                    # Verify current model names
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain neural networks."}
    ],
    temperature=0.7,
    max_tokens=1024,
)

print(response.choices[0].message.content)
print(f"Total tokens: {response.usage.total_tokens}")
```

### Streaming
```python
with client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Count to 10."}],
    stream=True
) as stream:
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
```

### Function Calling / Tool Use
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the current stock price",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What is AAPL's stock price?"}],
    tools=tools,
    tool_choice="auto"
)

tool_call = response.choices[0].message.tool_calls[0]
# Execute function: tool_call.function.name, json.loads(tool_call.function.arguments)
```

### Embeddings
```python
response = client.embeddings.create(
    model="text-embedding-3-small",   # or text-embedding-3-large
    input=["Hello world", "Goodbye world"],
    encoding_format="float"           # or "base64" for bandwidth efficiency
)
embeddings = [item.embedding for item in response.data]
```

### Async Client
```python
import asyncio
from openai import AsyncOpenAI

async_client = AsyncOpenAI()

async def call_llm(prompt: str) -> str:
    response = await async_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return response.choices[0].message.content

# Parallel calls with rate limiting
async def batch_process(prompts: list[str], max_concurrent: int = 10):
    semaphore = asyncio.Semaphore(max_concurrent)
    async def limited_call(prompt):
        async with semaphore:
            return await call_llm(prompt)
    return await asyncio.gather(*[limited_call(p) for p in prompts])
```

### Batch API (50% cost reduction for async workloads)
```python
import json

# Create batch file
requests = [
    {
        "custom_id": f"request-{i}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }
    }
    for i, prompt in enumerate(prompts)
]

# Upload and create batch
with open("batch_input.jsonl", "w") as f:
    for req in requests:
        f.write(json.dumps(req) + "\n")

batch_file = client.files.create(file=open("batch_input.jsonl", "rb"), purpose="batch")
batch = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
# Poll for completion: client.batches.retrieve(batch.id)
```

---

## AWS Bedrock

**Install**: `pip install boto3`
**Docs**: https://docs.aws.amazon.com/bedrock/

```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# invoke_model — standard synchronous call
response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',  # Note versioning suffix
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "Hello"}]
    }),
    contentType='application/json',
    accept='application/json'
)
result = json.loads(response['body'].read())

# invoke_model_with_response_stream — streaming
response = bedrock.invoke_model_with_response_stream(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    body=json.dumps({...}),
    contentType='application/json',
    accept='application/json'
)
for event in response['body']:
    chunk = json.loads(event['chunk']['bytes'])
    if chunk.get('type') == 'content_block_delta':
        print(chunk['delta']['text'], end='', flush=True)

# Converse API — provider-agnostic, recommended for new code
response = bedrock.converse(
    modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
    system=[{"text": "You are a helpful assistant."}],
    inferenceConfig={"maxTokens": 1024, "temperature": 0.7}
)
print(response['output']['message']['content'][0]['text'])
```

**Model IDs**: Bedrock model IDs include a version suffix (e.g., `-v2:0`). Always check the Bedrock console for current available model IDs — they update independently of the underlying model.

---

## LangChain (LCEL — LangChain Expression Language)

**Install**: `pip install langchain langchain-anthropic langchain-openai`
**Docs**: https://python.langchain.com/docs/

LCEL uses the pipe `|` operator to compose chains. This is the current (2024+) recommended pattern — the legacy `LLMChain` is deprecated.

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

# Basic chain
model = ChatAnthropic(model="claude-3-5-haiku-20241022")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a {role}. Respond concisely."),
    ("human", "{question}")
])
parser = StrOutputParser()

chain = prompt | model | parser
result = chain.invoke({"role": "scientist", "question": "What is DNA?"})

# Parallel execution
parallel_chain = RunnableParallel(
    summary=prompt | model | parser,
    word_count=RunnablePassthrough() | (lambda x: len(x["question"].split()))
)

# JSON output
from pydantic import BaseModel
class Analysis(BaseModel):
    sentiment: str
    confidence: float
    keywords: list[str]

json_parser = JsonOutputParser(pydantic_object=Analysis)
analysis_chain = (
    ChatPromptTemplate.from_template("Analyze: {text}\n{format_instructions}")
    .partial(format_instructions=json_parser.get_format_instructions())
    | model
    | json_parser
)
```

### Memory
```python
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# In-memory session storage
store = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

from langchain_core.runnables.history import RunnableWithMessageHistory
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history"
)
```

### Callbacks and LangSmith
```python
from langchain.callbacks.tracers import LangChainTracer
# Set env: LANGCHAIN_TRACING_V2=true, LANGCHAIN_API_KEY=...
# All chain invocations are automatically traced to LangSmith

# Custom callback
from langchain.callbacks.base import BaseCallbackHandler
class TokenCountCallback(BaseCallbackHandler):
    def __init__(self):
        self.total_tokens = 0
    def on_llm_end(self, response, **kwargs):
        if hasattr(response, 'llm_output') and response.llm_output:
            self.total_tokens += response.llm_output.get('token_usage', {}).get('total_tokens', 0)
```

---

## LlamaIndex

**Install**: `pip install llama-index`
**Docs**: https://docs.llamaindex.ai/

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core import SummaryIndex, KnowledgeGraphIndex
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.openai import OpenAIEmbedding

# Global configuration via Settings (replaces ServiceContext in older versions)
Settings.llm = Anthropic(model="claude-3-5-haiku-20241022")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
Settings.chunk_size = 512
Settings.chunk_overlap = 50

# Load documents
documents = SimpleDirectoryReader("./docs/").load_data()

# Vector index — for semantic similarity search
vector_index = VectorStoreIndex.from_documents(documents)
query_engine = vector_index.as_query_engine(similarity_top_k=5)
response = query_engine.query("What is the refund policy?")
print(response.response)
print(response.source_nodes)  # Retrieved chunks

# Summary index — for summarization over all documents
summary_index = SummaryIndex.from_documents(documents)
summary_engine = summary_index.as_query_engine(response_mode="tree_summarize")

# Streaming query engine
streaming_engine = vector_index.as_query_engine(streaming=True)
streaming_response = streaming_engine.query("Summarize the documents")
streaming_response.print_response_stream()

# Retriever + postprocessors for fine-grained control
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine

retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=10)
postprocessor = SimilarityPostprocessor(similarity_cutoff=0.75)
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    node_postprocessors=[postprocessor]
)
```

---

## DSPy

**Install**: `pip install dspy`
**Docs**: https://dspy.ai/

DSPy replaces hand-crafted prompts with optimizable programs. Instead of writing "You are a helpful assistant who thinks step by step...", you define a Signature and let optimizers find the best prompts and few-shot examples.

```python
import dspy

# Configure LM
lm = dspy.LM('anthropic/claude-3-5-haiku-20241022')
dspy.configure(lm=lm)

# Define a Signature — input/output specification, not a prompt
class SentimentAnalysis(dspy.Signature):
    """Analyze the sentiment of customer feedback."""
    feedback: str = dspy.InputField()
    sentiment: str = dspy.OutputField(desc="positive, negative, or neutral")
    confidence: float = dspy.OutputField(desc="confidence score 0-1")

# Modules
predictor = dspy.Predict(SentimentAnalysis)
cot = dspy.ChainOfThought(SentimentAnalysis)   # Adds reasoning step
result = cot(feedback="The product was okay but shipping was slow.")
print(result.sentiment, result.confidence)

# ReAct agent — for tool use
def search_web(query: str) -> str:
    return "..."  # Your search implementation

react = dspy.ReAct(
    "question -> answer",
    tools=[search_web]
)

# Optimization — replaces prompt engineering
from dspy.teleprompt import BootstrapFewShot, MIPROv2

# Training data
trainset = [dspy.Example(feedback=f, sentiment=s).with_inputs("feedback")
            for f, s in training_pairs]

# BootstrapFewShot — fast, good for small datasets
optimizer = BootstrapFewShot(metric=your_metric_fn, max_bootstrapped_demos=4)
optimized_cot = optimizer.compile(cot, trainset=trainset)

# MIPROv2 — more powerful, optimizes both instructions and examples
optimizer = MIPROv2(metric=your_metric_fn, auto="medium")
optimized_program = optimizer.compile(cot, trainset=trainset)
```

---

## Hugging Face

**Install**: `pip install transformers datasets peft accelerate`

```python
# Quick inference with pipeline
from transformers import pipeline

# Automatically downloads model and tokenizer
classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
result = classifier("This movie is fantastic!")

generator = pipeline("text-generation", model="meta-llama/Llama-3.2-1B", device=0)
output = generator("Once upon a time", max_new_tokens=100, do_sample=True, temperature=0.7)

# Full control — AutoModel + AutoTokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_id = "meta-llama/Llama-3.2-3B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"     # Automatically maps to available GPUs/CPU
)

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
with torch.no_grad():
    output = model.generate(**inputs, max_new_tokens=200, do_sample=True, temperature=0.7)
response = tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)

# Datasets library
from datasets import load_dataset

dataset = load_dataset("imdb")
# Map preprocessing
def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=512)
tokenized = dataset.map(tokenize, batched=True, num_proc=4)
tokenized.push_to_hub("your-username/imdb-tokenized")

# Fine-tuning with Trainer
from transformers import TrainingArguments, Trainer

training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    fp16=True,                      # Mixed precision — faster on modern GPUs
    report_to="wandb"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
)
trainer.train()
```

---

## Ollama — Local Model Serving

**Install**: https://ollama.com — `curl -fsSL https://ollama.ai/install.sh | sh`

```python
import ollama

# Pull and run a model
# CLI: ollama pull llama3.2
# CLI: ollama pull mistral

# Chat (Python SDK)
response = ollama.chat(
    model='llama3.2',
    messages=[{'role': 'user', 'content': 'Explain neural networks.'}]
)
print(response['message']['content'])

# Streaming
stream = ollama.chat(model='llama3.2', messages=[...], stream=True)
for chunk in stream:
    print(chunk['message']['content'], end='', flush=True)

# OpenAI-compatible endpoint — use OpenAI SDK with Ollama backend
from openai import OpenAI
local_client = OpenAI(base_url='http://localhost:11434/v1', api_key='ollama')
response = local_client.chat.completions.create(
    model='llama3.2',
    messages=[{"role": "user", "content": "Hello"}]
)

# Custom Modelfile
# File: Modelfile
# FROM llama3.2
# SYSTEM "You are a code review assistant. Be concise and direct."
# PARAMETER temperature 0.2
# CLI: ollama create code-reviewer -f Modelfile
```

**Use cases**: Privacy (data never leaves machine), offline operation, development/testing without API costs, running open-source models.

---

## LiteLLM — Provider-Agnostic Calls

**Install**: `pip install litellm`
**Docs**: https://docs.litellm.ai/

```python
import litellm

# Drop-in replacement for any provider — same interface
response = litellm.completion(
    model="anthropic/claude-3-5-haiku-20241022",
    messages=[{"role": "user", "content": "Hello"}]
)
# Or: "openai/gpt-4o", "bedrock/anthropic.claude-3-5-sonnet...", "ollama/llama3.2"

# Router for load balancing and fallbacks
from litellm import Router

router = Router(
    model_list=[
        {"model_name": "fast-model", "litellm_params": {"model": "gpt-4o-mini", "api_key": "..."}},
        {"model_name": "fast-model", "litellm_params": {"model": "claude-3-5-haiku-20241022", "api_key": "..."}},
    ],
    fallbacks=[{"fast-model": ["gpt-4o"]}],  # Fall back to gpt-4o if fast-model fails
    routing_strategy="least-busy"
)

# Cost tracking
litellm.success_callback = ["langfuse"]   # Or custom callback
response = litellm.completion(model="gpt-4o", messages=[...])
print(litellm.completion_cost(completion_response=response))

# Proxy server mode (CLI)
# litellm --model claude-3-5-sonnet-20241022 --port 8000
# Then use any OpenAI-compatible client pointing to localhost:8000
```

---

## Error Handling Patterns

### Exponential Backoff with Jitter for Rate Limits
```python
import time
import random
import anthropic
from anthropic import RateLimitError, APIStatusError, APITimeoutError

def call_with_retry(client, max_retries=5, base_delay=1.0, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limit hit. Retrying in {delay:.2f}s...")
            time.sleep(delay)
        except APITimeoutError:
            if attempt == max_retries - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
        except APIStatusError as e:
            if e.status_code in {500, 502, 503, 529}:  # Transient server errors
                if attempt == max_retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt))
            else:
                raise  # Non-retryable error (400, 401, 403) — fail fast
    raise RuntimeError("Max retries exceeded")
```

### Context Length Handling
```python
def chunk_and_process(text: str, max_chunk_tokens: int = 50000):
    """Split long text into chunks and process each."""
    # Use tiktoken for OpenAI, or character-based estimate for others
    words = text.split()
    chunks = []
    current_chunk = []
    current_tokens = 0

    for word in words:
        # Rough estimate: 1 token ≈ 0.75 words
        word_tokens = len(word) // 3 + 1
        if current_tokens + word_tokens > max_chunk_tokens:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_tokens = word_tokens
        else:
            current_chunk.append(word)
            current_tokens += word_tokens

    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks
```

---

## Token Counting and Cost Management

```python
# OpenAI — tiktoken
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")
tokens = enc.encode("Hello, world!")
print(f"Token count: {len(tokens)}")

# Anthropic — count_tokens API (exact, not estimated)
count = client.messages.count_tokens(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": long_text}]
)

# Budget enforcement before calling
MAX_BUDGET_TOKENS = 100_000
if count.input_tokens > MAX_BUDGET_TOKENS:
    raise ValueError(f"Input too large: {count.input_tokens} tokens exceeds budget")

# Approximate cost table (verify current pricing — changes frequently)
# Costs are per 1M tokens (input / output) — USD approximations as of training cutoff
APPROX_COSTS_PER_1M = {
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}
# ALWAYS verify at: https://anthropic.com/pricing and https://openai.com/pricing
```

---

## Streaming UX and Async Patterns

### Server-Sent Events for Web Applications
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import anthropic

app = FastAPI()
client = anthropic.Anthropic()

@app.get("/stream")
async def stream_response(prompt: str):
    async def generate():
        with client.messages.stream(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Async Parallel Processing with Semaphore
```python
import asyncio
from anthropic import AsyncAnthropic

async_client = AsyncAnthropic()

async def process_batch(items: list[str], max_concurrent: int = 5) -> list[str]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_one(item: str) -> str:
        async with semaphore:
            response = await async_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": item}]
            )
            return response.content[0].text

    results = await asyncio.gather(*[process_one(item) for item in items])
    return results
```

---

## Self-Review Checklist

Before shipping any LLM integration to production, verify every item:

1. **API key security**: Keys in environment variables, never hardcoded. Secret scanning enabled in CI.
2. **SDK version pinned**: `anthropic==0.x.x` in requirements.txt — LLM SDKs break APIs between versions.
3. **Retry logic implemented**: Exponential backoff with jitter for rate limits and transient 5xx errors.
4. **Fail-fast for 4xx**: 400/401/403 errors are not retried — they indicate bugs in your code or invalid keys.
5. **Timeout set**: Every API call has an explicit timeout. No indefinitely hanging requests.
6. **Max tokens specified**: For Anthropic, this is required. For OpenAI, always set it explicitly.
7. **Token budget enforced**: Long inputs checked before calling — no surprise $100 bills.
8. **Cost monitoring active**: Per-call cost logging with alerting on anomalies.
9. **Streaming used where appropriate**: Long responses should stream to avoid perceived latency.
10. **Context length handled**: Input truncation or chunking for long documents.
11. **Error types distinguished**: Different handling for rate limits vs server errors vs invalid input.
12. **Async semaphore for batches**: Parallel calls rate-limited by semaphore, not unconstrained.
13. **Tool use loop bounded**: ReAct/agent loops have a max iteration limit to prevent infinite loops.
14. **Prompt injection mitigated**: User input sanitized or isolated in the message structure (not interpolated into system prompt).
15. **Model name verified**: Current, non-deprecated model name confirmed against official docs.
16. **Response validation**: Structured outputs validated (Pydantic, JSON schema) before use.
17. **Logging appropriate**: Inputs/outputs logged for debugging, but PII masked in logs.
18. **LangSmith or equivalent tracing**: Full chain traces available for debugging production issues.
19. **Fallback strategy defined**: What happens when the primary LLM provider is down? (LiteLLM fallbacks, graceful degradation).
20. **Evaluation suite exists**: Automated evals run on every prompt change — no prompt changes without regression testing.
