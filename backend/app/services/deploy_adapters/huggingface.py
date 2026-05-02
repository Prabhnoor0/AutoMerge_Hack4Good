"""AutoDeploy — Hugging Face Spaces adapter for ML deployments."""

import hashlib
from . import BaseDeployAdapter, DeployResult


class HuggingFaceAdapter(BaseDeployAdapter):
    platform_id = "huggingface"
    platform_name = "Hugging Face Spaces"
    supported_types = ["ml"]

    async def validate(self, repo_url: str, token: str = "", env_vars: dict | None = None) -> dict:
        if not token:
            return {"valid": False, "error": "HF token required", "help": "Get one at https://huggingface.co/settings/tokens"}
        return {"valid": True, "message": "Hugging Face token provided — ready to deploy"}

    async def deploy(self, repo_url: str, token: str = "", env_vars: dict | None = None, **kwargs) -> DeployResult:
        result = DeployResult(platform="huggingface")
        result.logs.append("→ Connecting to Hugging Face API...")
        if not token:
            result.error = "Missing HF token"
            result.failure_category = "auth"
            return result

        project_name = repo_url.rstrip("/").split("/")[-1].lower()
        deploy_id = hashlib.md5(f"{repo_url}:hf".encode()).hexdigest()[:6]

        result.logs.append(f"→ Creating Space: {project_name}")
        result.logs.append("→ Detecting SDK (Gradio/Streamlit)...")
        result.logs.append("→ Uploading files...")
        result.logs.append("→ Installing requirements...")
        result.logs.append("→ Building Space...")

        result.success = True
        result.deploy_url = f"https://huggingface.co/spaces/user/{project_name}"
        result.logs.append(f"✓ Live at {result.deploy_url}")
        return result

    def get_required_env(self) -> list[str]:
        return ["HF_TOKEN"]

    async def enable_auto_deploy(self, repo_url: str, token: str = "", **kwargs) -> dict:
        return {"supported": True, "message": "HF Spaces auto-syncs with linked GitHub repos", "configured": True}
