"""AutoDeploy — Base adapter interface for deployment platforms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict


@dataclass
class DeployResult:
    success: bool = False
    platform: str = ""
    deploy_url: str = ""
    logs: list[str] = field(default_factory=list)
    error: str = ""
    failure_category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class BaseDeployAdapter(ABC):
    """Abstract base for all deployment platform adapters."""

    platform_id: str = ""
    platform_name: str = ""
    supported_types: list[str] = []

    @abstractmethod
    async def validate(self, repo_url: str, token: str = "", env_vars: dict | None = None) -> dict:
        """Validate that the repo can be deployed to this platform."""
        ...

    @abstractmethod
    async def deploy(self, repo_url: str, token: str = "", env_vars: dict | None = None, **kwargs) -> DeployResult:
        """Execute the deployment."""
        ...

    @abstractmethod
    def get_required_env(self) -> list[str]:
        """Return platform-specific required env vars (API tokens etc)."""
        ...

    async def enable_auto_deploy(self, repo_url: str, token: str = "", **kwargs) -> dict:
        """Enable auto-deploy on push. Override in subclasses that support it."""
        return {"supported": False, "message": f"{self.platform_name} auto-deploy not yet implemented"}
