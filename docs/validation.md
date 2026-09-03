# Validation

Run the complete repository gate from the Agentbot checkout:

```bash
env -u NO_COLOR bash tests/run.sh
```

The gate runs available Python quality checks, Python and shell suites, Bash
syntax, production ShellCheck when installed, and `git diff --check`.

To match CI's Ruff and coverage checks, install development tools locally:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
PATH="$PWD/.venv/bin:$PATH" env -u NO_COLOR bash tests/run.sh
```

Useful focused checks are:

```bash
python3 -m unittest discover -s tests
bash tests/shell/test_cli.sh
./install.sh doctor
```

Suite names under `tests/shell/` are authoritative. Doctor is a runtime
diagnostic and does not replace the repository gate.
