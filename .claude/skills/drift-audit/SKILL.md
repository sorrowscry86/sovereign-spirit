---
name: drift-audit
description: >
  Run a coherence audit on the Sovereign Spirit codebase. Checks for broken
  imports, datetime violations, debug print statements, hardcoded secrets,
  and other drift patterns identified in the 2026-02-26 audit.
  Invoke with /drift-audit before committing or after major changes.
---

# Drift Audit — Sovereign Spirit

Run these checks and report any hits. A clean system produces zero output on each.

## 1. Broken Imports (deleted files still referenced)

```bash
python -c "
import ast, os, sys
errors = []
for root, dirs, files in os.walk('src'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'): continue
        path = os.path.join(root, f)
        try:
            with open(path) as fh:
                ast.parse(fh.read())
        except SyntaxError as e:
            errors.append(f'{path}: SyntaxError: {e}')
for e in errors: print(e)
print(f'{len(errors)} syntax errors found')
"
```

## 2. Datetime Violations (Law of Time)

```bash
grep -rn "datetime\.now()" src/ --include="*.py"
grep -rn "utcnow()" src/ --include="*.py"
```

Both should return nothing. Any hit is a violation.

## 3. Debug Print Statements (VOID-DIR-004)

```bash
grep -rn "^\s*print(" src/ --include="*.py"
```

Should return nothing. Use `logger.*` instead.

## 4. Hardcoded Secrets

```bash
grep -rn "sk-[a-zA-Z0-9_\-]\{20,\}" . --include="*.py" --include="*.yaml" --include="*.yml" --include="*.json"
grep -rn "api_key: [^$\"'\n{]" config/ --include="*.yaml"
```

Should return nothing. All secrets via `${ENV_VAR}` or env vars.

## 5. Stale `os.sys` Pattern

```bash
grep -rn "os\.sys\." src/ --include="*.py"
```

Should return nothing. Use `import sys` + `sys.executable`.

## 6. Missing Top-Level Imports (late imports inside functions)

```bash
grep -rn "^\s\+import " src/ --include="*.py" | grep -v "^.*:from\|^.*:#"
```

## 7. Wrong DB Abstraction

```bash
grep -rn "db\.pool" src/ --include="*.py"
```

Should return nothing. Use `db.session()`.

## 8. Docker Port Consistency

```bash
grep -n "8000" docker-compose.yml config/docker-compose.yml .voidcat/CONTEXT.md 2>/dev/null
```

Should only appear in the deprecation notice in `config/docker-compose.yml`.

## Reporting

After running each check, report:
- **CLEAN** if no hits
- **DRIFT DETECTED** with file:line for any hits, severity (critical/medium/low), and recommended fix

A fully coherent system reports CLEAN on all 8 checks.
