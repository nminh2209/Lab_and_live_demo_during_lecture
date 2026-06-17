"""
Production Readiness Checker

Run: python check_production_ready.py
"""
import os
import sys


def check(name: str, passed: bool, detail: str = "") -> dict:
    icon = "[OK]" if passed else "[FAIL]"
    print(f"  {icon} {name}" + (f" -- {detail}" if detail else ""))
    return {"name": name, "passed": passed}


def run_checks():
    results = []
    base = os.path.dirname(__file__)

    print("\n" + "=" * 55)
    print("  Production Readiness Check — Day 12 Lab")
    print("=" * 55)

    print("\nRequired Files")
    required_files = [
        "Dockerfile",
        "docker-compose.yml",
        ".dockerignore",
        ".env.example",
        "requirements.txt",
        "app/main.py",
        "app/config.py",
        "app/auth.py",
        "app/rate_limiter.py",
        "app/cost_guard.py",
        "utils/mock_llm.py",
        "nginx.conf",
    ]
    for fname in required_files:
        results.append(check(f"{fname} exists", os.path.exists(os.path.join(base, fname))))

    results.append(check(
        "render.yaml exists",
        os.path.exists(os.path.join(base, "render.yaml")),
    ))

    print("\nSecurity")
    root_gitignore = os.path.join(base, "..", ".gitignore")
    env_ignored = os.path.exists(root_gitignore) and ".env" in open(root_gitignore).read()
    results.append(check(".env in .gitignore", env_ignored))

    secrets_found = []
    for rel in ["app/main.py", "app/config.py", "app/auth.py"]:
        fpath = os.path.join(base, rel)
        if os.path.exists(fpath):
            content = open(fpath).read()
            for bad in ["sk-hardcoded", "password123", "never-do-this"]:
                if bad in content:
                    secrets_found.append(f"{rel}:{bad}")
    results.append(check(
        "No hardcoded secrets in code",
        len(secrets_found) == 0,
        str(secrets_found) if secrets_found else "",
    ))

    print("\nAPI Endpoints (code check)")
    main_py = os.path.join(base, "app", "main.py")
    if os.path.exists(main_py):
        content = open(main_py).read()
        results.append(check("/health endpoint defined", '"/health"' in content))
        results.append(check("/ready endpoint defined", '"/ready"' in content))
        results.append(check("Authentication implemented", "verify_api_key" in content))
        results.append(check("Rate limiting implemented", "check_rate_limit" in content))
        results.append(check("Cost guard implemented", "check_budget" in content))
        results.append(check("Conversation history (Redis)", "get_history" in content))
        results.append(check("Graceful shutdown (SIGTERM)", "SIGTERM" in content))
        results.append(check("Structured logging (JSON)", "json.dumps" in content))
        results.append(check("OpenAI integration", "openai_api_key" in content))

    print("\nDocker")
    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        content = open(dockerfile).read()
        results.append(check("Multi-stage build", "AS builder" in content or "AS runtime" in content))
        results.append(check("Non-root user", "useradd" in content or "USER " in content))
        results.append(check("HEALTHCHECK instruction", "HEALTHCHECK" in content))
        results.append(check("Slim base image", "slim" in content or "alpine" in content))

    compose = os.path.join(base, "docker-compose.yml")
    if os.path.exists(compose):
        content = open(compose).read()
        results.append(check("docker-compose has redis", "redis:" in content))
        results.append(check("docker-compose has nginx", "nginx:" in content))

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = round(passed / total * 100)

    print("\n" + "=" * 55)
    print(f"  Result: {passed}/{total} checks passed ({pct}%)")
    if pct == 100:
        print("  PRODUCTION READY! Deploy when ready.")
    elif pct >= 80:
        print("  Almost there! Fix the [FAIL] items above.")
    else:
        print("  Not ready. Review the checklist carefully.")
    print("=" * 55 + "\n")
    return pct == 100


if __name__ == "__main__":
    ready = run_checks()
    sys.exit(0 if ready else 1)
