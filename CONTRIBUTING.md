# Contributing to revibe

revibe is a multi-provider CLI coding agent. Contributions welcome!

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/revibe.git
cd revibe
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
python -m revibe
```

## How to Help
- **Bug reports**: Open an issue with reproduction steps
- **New providers**: PR adding a new AI provider integration
- **CLI improvements**: Better UX, flags, output formatting

## Style
- PEP 8, type hints, Google-style docstrings
- Test your changes with `pytest`

## Structure
```
revibe/
├── revibe/         # Main package
│   ├── providers/  # AI provider adapters
│   └── cli/        # CLI interface
├── tests/          # Tests
└── docs/           # Documentation
```

Open an issue or PR — let's build something great! 🎵
