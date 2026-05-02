"""
AutoDeploy — Environment Variable Detection Service

Scans repository code for environment variable usage, identifies required
secrets, and flags missing variables — without ever logging secret values.
"""

import re
from dataclasses import dataclass, field, asdict


# ─── Known env var purposes ───────────────────────────────

ENV_PURPOSES = {
    "DATABASE_URL": "Database connection string (PostgreSQL, MySQL, etc.)",
    "MONGO_URI": "MongoDB connection URI",
    "MONGODB_URI": "MongoDB connection URI",
    "REDIS_URL": "Redis connection string",
    "SUPABASE_URL": "Supabase project URL",
    "SUPABASE_KEY": "Supabase anonymous/public API key",
    "SUPABASE_ANON_KEY": "Supabase anonymous API key",
    "SUPABASE_SERVICE_KEY": "Supabase service role key (sensitive)",
    "PORT": "Server listen port",
    "HOST": "Server bind host address",
    "SECRET_KEY": "Application secret key for sessions/JWT",
    "JWT_SECRET": "JSON Web Token signing secret",
    "API_KEY": "External API key",
    "OPENAI_API_KEY": "OpenAI API key for LLM integration",
    "GITHUB_TOKEN": "GitHub personal access token",
    "AWS_ACCESS_KEY_ID": "AWS access key",
    "AWS_SECRET_ACCESS_KEY": "AWS secret key",
    "AWS_REGION": "AWS region identifier",
    "GOOGLE_APPLICATION_CREDENTIALS": "Google Cloud service account credentials",
    "STRIPE_SECRET_KEY": "Stripe payment secret key",
    "STRIPE_PUBLISHABLE_KEY": "Stripe publishable key",
    "SENDGRID_API_KEY": "SendGrid email API key",
    "NEXT_PUBLIC_API_URL": "Public API URL for Next.js frontend",
    "VITE_API_URL": "API URL for Vite frontend",
    "REACT_APP_API_URL": "API URL for Create React App",
    "NODE_ENV": "Node.js environment (production/development)",
    "PYTHON_ENV": "Python environment mode",
    "DEBUG": "Debug mode flag",
    "CORS_ORIGINS": "Allowed CORS origins",
    "ALLOWED_HOSTS": "Django allowed hosts",
    "SMTP_HOST": "Email SMTP server",
    "SMTP_PORT": "Email SMTP port",
    "S3_BUCKET": "AWS S3 bucket name",
    "CLOUDINARY_URL": "Cloudinary media URL",
}

# Patterns for env var detection
JS_PATTERNS = [
    re.compile(r'process\.env\.([A-Z_][A-Z0-9_]+)'),
    re.compile(r'process\.env\[[\'\"]([A-Z_][A-Z0-9_]+)[\'\"]\]'),
    re.compile(r'import\.meta\.env\.([A-Z_][A-Z0-9_]+)'),
]

PY_PATTERNS = [
    re.compile(r'os\.environ\[[\'\"]([A-Z_][A-Z0-9_]+)[\'\"]\]'),
    re.compile(r'os\.environ\.get\([\'\"]([A-Z_][A-Z0-9_]+)[\'\"]'),
    re.compile(r'os\.getenv\([\'\"]([A-Z_][A-Z0-9_]+)[\'\"]'),
    re.compile(r'environ\[[\'\"]([A-Z_][A-Z0-9_]+)[\'\"]\]'),
]

DOTENV_PATTERN = re.compile(r'^([A-Z_][A-Z0-9_]+)\s*=', re.MULTILINE)


@dataclass
class EnvVar:
    name: str
    purpose: str = ""
    source_files: list[str] = field(default_factory=list)
    is_secret: bool = False
    priority: str = "medium"  # high, medium, low

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EnvScanResult:
    required_vars: list[dict] = field(default_factory=list)
    detected_in_env_example: list[str] = field(default_factory=list)
    missing_vars: list[str] = field(default_factory=list)
    detected_sources: dict[str, list[str]] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    total_vars: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def scan_env_vars(file_contents: dict[str, str]) -> EnvScanResult:
    """
    Scan repository files for environment variable usage.

    Args:
        file_contents: Dict of filepath -> content

    Returns:
        EnvScanResult with required vars, missing vars, and recommendations
    """
    result = EnvScanResult()
    found_vars: dict[str, EnvVar] = {}

    # Parse .env.example if present
    env_example_vars = set()
    for key in [".env.example", ".env.sample", ".env.template"]:
        content = file_contents.get(key, "")
        if content:
            for match in DOTENV_PATTERN.finditer(content):
                var_name = match.group(1)
                env_example_vars.add(var_name)
                result.detected_in_env_example.append(var_name)

    # Scan all files
    for filepath, content in file_contents.items():
        if not content:
            continue

        ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
        detected = set()

        # JavaScript/TypeScript patterns
        if ext in ("js", "jsx", "ts", "tsx", "mjs", "cjs"):
            for pattern in JS_PATTERNS:
                for match in pattern.finditer(content):
                    detected.add(match.group(1))

        # Python patterns
        if ext in ("py",):
            for pattern in PY_PATTERNS:
                for match in pattern.finditer(content):
                    detected.add(match.group(1))

        # Config files
        if filepath.endswith((".env.example", ".env.sample", ".env.template")):
            for match in DOTENV_PATTERN.finditer(content):
                detected.add(match.group(1))

        # Register found vars
        for var_name in detected:
            if var_name not in found_vars:
                found_vars[var_name] = EnvVar(
                    name=var_name,
                    purpose=ENV_PURPOSES.get(var_name, "Application configuration"),
                    is_secret=_is_secret(var_name),
                    priority=_get_priority(var_name),
                )
            found_vars[var_name].source_files.append(filepath)

    # Build result
    for var in sorted(found_vars.values(), key=lambda v: {"high": 0, "medium": 1, "low": 2}[v.priority]):
        result.required_vars.append(var.to_dict())
        result.detected_sources[var.name] = var.source_files
        if var.name not in env_example_vars and var.is_secret:
            result.missing_vars.append(var.name)

    result.total_vars = len(found_vars)

    # Recommendations
    if result.missing_vars:
        result.recommendations.append(
            f"Found {len(result.missing_vars)} potentially missing secret(s): {', '.join(result.missing_vars[:5])}"
        )
    if not env_example_vars and found_vars:
        result.recommendations.append("Consider adding a .env.example file to document required variables")
    for var in found_vars.values():
        if var.priority == "high" and var.is_secret:
            result.recommendations.append(f"⚠️ {var.name} — {var.purpose} — must be set before deployment")

    return result


def _is_secret(name: str) -> bool:
    """Determine if a variable name likely holds a secret value."""
    secret_words = ("key", "secret", "token", "password", "credential", "auth", "private")
    name_lower = name.lower()
    return any(w in name_lower for w in secret_words) or name in (
        "DATABASE_URL", "MONGO_URI", "MONGODB_URI", "REDIS_URL",
        "SUPABASE_URL", "SUPABASE_KEY", "CLOUDINARY_URL",
    )


def _get_priority(name: str) -> str:
    """Assign priority level to an env var."""
    high = ("DATABASE_URL", "MONGO_URI", "SECRET_KEY", "JWT_SECRET", "OPENAI_API_KEY",
            "SUPABASE_URL", "SUPABASE_KEY", "PORT", "AWS_ACCESS_KEY_ID")
    low = ("DEBUG", "NODE_ENV", "PYTHON_ENV", "HOST", "CORS_ORIGINS")
    if name in high:
        return "high"
    if name in low:
        return "low"
    return "medium"
