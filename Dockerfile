FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/gnanirahulnutakki/god-skill-suite"
LABEL org.opencontainers.image.description="52 God-Level AI Skills for Claude Code, Cursor, Codex, Windsurf, Gemini CLI"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["god-skills"]
CMD ["install"]
