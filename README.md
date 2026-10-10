# App: production-grade full-stack template

FastAPI (DDD + hexagonal + event-driven) · MySQL 8.4 · Next.js 16 / React 19 · complete test pyramid · CI/CD · Claude Code-native.

## Quick start
```bash
make setup          # deps, browsers, git hooks, .env
make up migrate     # MySQL in Docker + schema
make dev-api        # terminal 1 → http://localhost:8000/docs
make dev-web        # terminal 2 → http://localhost:3000/products
make seed           # demo data
```

## Everyday commands
`make help` lists everything. The important ones are `check-fast`, `test-all`, `security`, `perf-load`, `build`.

## Working with Claude Code
Open the folder in VSCode, start `claude`, and use:
- `/feature <description or issue #>` for the full autonomous SDLC (plan → design → TDD → tests → security → perf → review → PR)
- `/plan`, `/design`, `/adr`, `/tdd`, `/test-all`, `/review`, `/security-scan`, `/perf-test`, `/debug`, `/ship`

See `CLAUDE.md` for the project rules every agent follows, and `docs/` for architecture and ADRs.
