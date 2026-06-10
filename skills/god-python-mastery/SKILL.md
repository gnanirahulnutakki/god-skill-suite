---
name: god-python-mastery
description: "God-level Python mastery. Deep dive into Python internals (GIL, memory model, bytecode), type annotations and mypy, asyncio and concurrent programming, packaging (pyproject.toml, uv, pip, setuptools), virtual environments, debugging (pdb, pudb, debugpy), profiling (cProfile, py-spy, memory_profiler), dataclasses and attrs, decorators and metaclasses, context managers, generators and iterators, pathlib, testing (pytest fixtures, parametrize, mocking), and production patterns. Never fabricate stdlib module names or function signatures — verify against docs.python.org. Covers Python 3.10+."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Python Mastery

## Anti-Hallucination Rules

- NEVER invent Python stdlib module names or functions — verify against docs.python.org.
- NEVER claim a feature exists in a Python version without checking the changelog (e.g., match/case is 3.10+, `type` keyword is 3.12+).
- NEVER fabricate pip/uv command flags — verify against tool documentation.
- NEVER claim the GIL has been removed in CPython — PEP 703 (free-threaded) is experimental in 3.13+.
- ALWAYS specify minimum Python version when using newer syntax (walrus operator 3.8+, union types `X | Y` 3.10+, `type` aliases 3.12+).

---

## 1. Type Annotations (Modern Python)

### 1.1 Core Typing (Python 3.10+)

```python
# Use built-in types directly (no need for typing.List, typing.Dict in 3.10+)
def process_items(items: list[str], config: dict[str, int]) -> tuple[int, str]:
    ...

# Union types with | (3.10+)
def fetch(url: str, timeout: int | float | None = None) -> str | bytes:
    ...

# Optional is just X | None
def find_user(user_id: int) -> User | None:
    ...

# TypeAlias (3.10+)
type Vector = list[float]                    # 3.12+ syntax
Vector: TypeAlias = list[float]              # 3.10-3.11 syntax

# Literal types
from typing import Literal
def set_log_level(level: Literal["debug", "info", "warn", "error"]) -> None:
    ...

# TypedDict
from typing import TypedDict
class UserDict(TypedDict):
    name: str
    email: str
    age: int
    is_active: bool  # Not NotRequired — all keys required

class PartialUser(TypedDict, total=False):
    name: str        # All keys optional
    email: str

# Protocol (structural subtyping — duck typing with type safety)
from typing import Protocol, runtime_checkable

@runtime_checkable
class Serializable(Protocol):
    def serialize(self) -> bytes: ...
    def deserialize(self, data: bytes) -> None: ...

# Generic types
from typing import Generic, TypeVar
T = TypeVar("T")

class Repository(Generic[T]):
    def get(self, id: int) -> T: ...
    def save(self, entity: T) -> None: ...
```

### 1.2 mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true                    # Enable all strict checks
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false    # Relax in tests

[[tool.mypy.overrides]]
module = ["third_party_lib.*"]
ignore_missing_imports = true
```

---

## 2. Asyncio

```python
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

# Basic async/await
async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Concurrent execution
async def fetch_all(urls: list[str]) -> list[dict]:
    tasks = [fetch_data(url) for url in urls]
    return await asyncio.gather(*tasks, return_exceptions=True)

# TaskGroup (Python 3.11+) — structured concurrency
async def process_batch(items: list[str]) -> list[str]:
    results = []
    async with asyncio.TaskGroup() as tg:
        for item in items:
            tg.create_task(process_item(item))
    return results

# Async generator
async def stream_events(topic: str) -> AsyncIterator[dict]:
    async with connect_to_kafka(topic) as consumer:
        async for message in consumer:
            yield message.value()

# Async context manager
@asynccontextmanager
async def database_transaction() -> AsyncIterator[Connection]:
    conn = await pool.acquire()
    try:
        await conn.execute("BEGIN")
        yield conn
        await conn.execute("COMMIT")
    except Exception:
        await conn.execute("ROLLBACK")
        raise
    finally:
        await pool.release(conn)

# Semaphore for rate limiting
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

async def rate_limited_fetch(url: str) -> dict:
    async with semaphore:
        return await fetch_data(url)
```

---

## 3. Packaging (Modern)

### pyproject.toml (PEP 621)

```toml
[project]
name = "my-package"
version = "1.2.3"
description = "A well-packaged Python library"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [{ name = "Team", email = "team@example.com" }]
dependencies = [
    "httpx>=0.25",
    "pydantic>=2.0",
    "structlog>=23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.5",
    "ruff>=0.1",
    "pre-commit>=3.0",
]

[project.scripts]
my-cli = "my_package.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py310"
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "PTH", "RUF"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q --strict-markers"
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
]
```

### Virtual Environment Management

```bash
# uv (fastest — recommended)
uv venv                           # Create .venv
uv pip install -e ".[dev]"        # Install with dev deps
uv pip compile requirements.in -o requirements.txt  # Lock deps
uv run pytest                     # Run in venv without activating

# Standard venv
python -m venv .venv
source .venv/bin/activate         # macOS/Linux
.venv\Scripts\activate            # Windows
pip install -e ".[dev]"
```

---

## 4. Dataclasses and Pydantic

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True, slots=True)  # frozen=immutable, slots=memory efficient
class User:
    id: int
    name: str
    email: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Validation in frozen dataclass requires object.__setattr__
        if not self.email or "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")

# Pydantic v2 — runtime validation
from pydantic import BaseModel, Field, field_validator, EmailStr

class UserCreate(BaseModel):
    model_config = {"strict": True}
    
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=0, le=150)
    
    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()
```

---

## 5. Decorators and Context Managers

```python
import functools
import time
import logging
from contextlib import contextmanager
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

# Type-safe decorator
def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    logging.warning(f"Attempt {attempt} failed: {e}, retrying in {delay}s")
                    time.sleep(delay * attempt)
            raise RuntimeError("Unreachable")
        return wrapper
    return decorator

@retry(max_attempts=3, delay=0.5)
def fetch_from_api(url: str) -> dict:
    ...

# Context manager for resource management
@contextmanager
def timer(label: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logging.info(f"{label}: {elapsed:.3f}s")

with timer("database_query"):
    result = db.execute(query)
```

---

## 6. Debugging and Profiling

```python
# pdb — built-in debugger
import pdb; pdb.set_trace()        # Classic breakpoint
breakpoint()                        # Python 3.7+ — uses PYTHONBREAKPOINT env var

# PYTHONBREAKPOINT=pudb.set_trace python script.py  # Use pudb instead
# PYTHONBREAKPOINT=0 python script.py               # Disable breakpoints

# cProfile — CPU profiling
python -m cProfile -s cumulative my_script.py
python -m cProfile -o profile.pstats my_script.py
# Visualize: pip install snakeviz && snakeviz profile.pstats

# py-spy — sampling profiler (no code changes, low overhead)
py-spy record -o profile.svg -- python my_script.py   # Flamegraph
py-spy top --pid <PID>                                  # Live view

# memory_profiler
from memory_profiler import profile as mem_profile

@mem_profile
def memory_intensive_function():
    data = [i ** 2 for i in range(10_000_000)]
    return sum(data)
```

---

## 7. Testing with pytest

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Fixtures
@pytest.fixture
def db_session():
    session = create_test_session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Parametrize
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
    ("123", "123"),
])
def test_uppercase(input: str, expected: str):
    assert input.upper() == expected

# Mocking
def test_fetch_user(db_session):
    with patch("myapp.services.user_repo.get") as mock_get:
        mock_get.return_value = User(id=1, name="Alice")
        result = fetch_user(1)
        assert result.name == "Alice"
        mock_get.assert_called_once_with(1)

# Async testing
@pytest.mark.anyio
async def test_async_endpoint(async_client):
    response = await async_client.get("/api/users")
    assert response.status_code == 200

# Custom markers
@pytest.mark.slow
@pytest.mark.integration
def test_full_pipeline():
    ...
```

---

## Cross-Domain Connections

**Python ↔ DevOps:** Python scripts for infrastructure automation (Ansible modules, custom Terraform providers, K8s operators with kopf). Use `subprocess.run()` with `check=True` — never `os.system()`.

**Python ↔ Data:** pandas, polars for data processing. SQLAlchemy for database access. Pydantic for data validation at boundaries.

**Python ↔ ML/AI:** PyTorch, TensorFlow for training. FastAPI for model serving. structlog for structured logging in ML pipelines.

---

## Self-Review Checklist

- [ ] Type annotations on all public functions (mypy --strict passes)
- [ ] `pyproject.toml` used for packaging (not setup.py/setup.cfg)
- [ ] Virtual environment used (never `pip install` globally)
- [ ] `ruff` configured for linting and formatting
- [ ] All exceptions caught specifically (never bare `except:`)
- [ ] f-strings used for string formatting (not `%` or `.format()`)
- [ ] `pathlib.Path` used instead of `os.path` string manipulation
- [ ] Dataclasses/Pydantic used instead of raw dicts for structured data
- [ ] Context managers used for resource cleanup
- [ ] `functools.wraps` applied to all decorators
- [ ] Tests use pytest fixtures and parametrize (not unittest.TestCase)
- [ ] Async code uses `asyncio.TaskGroup` (3.11+) or `gather` for concurrency
