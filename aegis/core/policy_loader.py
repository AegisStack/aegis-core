"""
Policy Loader - Multi-tenant policy loading with caching support.

Loads policies from various backends: filesystem, S3, GCS, or custom stores.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional, Protocol

import yaml

from ..exceptions import AegisPolicyLoadError


class PolicyStore(Protocol):
    """Protocol for custom policy storage backends."""

    def load_policy(self, customer_id: str) -> dict[str, Any]:
        """Load policy for a customer. Returns parsed policy dict."""
        ...


class FilesystemPolicyStore:
    """Load policies from local filesystem."""

    def __init__(self, base_path: str = "./policies"):
        """
        Initialize filesystem policy store.

        Args:
            base_path: Base directory containing policy files
        """
        self.base_path = Path(base_path)

    def load_policy(self, customer_id: str) -> dict[str, Any]:
        """
        Load policy from filesystem.

        Looks for {customer_id}.yaml or {customer_id}.yml

        Args:
            customer_id: Customer identifier

        Returns:
            Parsed policy dictionary

        Raises:
            AegisPolicyLoadError: If policy file not found or invalid
        """
        # Try both .yaml and .yml extensions
        for ext in [".yaml", ".yml"]:
            policy_path = self.base_path / f"{customer_id}{ext}"
            if policy_path.exists():
                try:
                    with open(policy_path) as f:
                        policy = yaml.safe_load(f)
                        if not isinstance(policy, dict):
                            raise AegisPolicyLoadError(
                                "Policy file must contain a YAML dictionary", str(policy_path)
                            )
                        return policy
                except yaml.YAMLError as e:
                    raise AegisPolicyLoadError(
                        f"Invalid YAML in policy file: {e}", str(policy_path)
                    )
                except Exception as e:
                    raise AegisPolicyLoadError(f"Error reading policy file: {e}", str(policy_path))

        raise AegisPolicyLoadError(
            f"Policy file not found for customer '{customer_id}'",
            str(self.base_path / f"{customer_id}.yaml"),
        )


class S3PolicyStore:
    """Load policies from AWS S3."""

    def __init__(self, bucket: str, prefix: str = "policies/"):
        """
        Initialize S3 policy store.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix for policy files
        """
        self.bucket = bucket
        self.prefix = prefix
        self._s3_client = None

    def _get_s3_client(self):
        """Lazy-load boto3 S3 client."""
        if self._s3_client is None:
            try:
                import boto3

                self._s3_client = boto3.client("s3")
            except ImportError:
                raise AegisPolicyLoadError(
                    "boto3 not installed. Install with: pip install aegis-sdk[s3]"
                )
        return self._s3_client

    def load_policy(self, customer_id: str) -> dict[str, Any]:
        """
        Load policy from S3.

        Args:
            customer_id: Customer identifier

        Returns:
            Parsed policy dictionary

        Raises:
            AegisPolicyLoadError: If policy not found or invalid
        """
        s3 = self._get_s3_client()
        key = f"{self.prefix}{customer_id}.yaml"

        try:
            response = s3.get_object(Bucket=self.bucket, Key=key)
            policy_yaml = response["Body"].read().decode("utf-8")
            policy = yaml.safe_load(policy_yaml)

            if not isinstance(policy, dict):
                raise AegisPolicyLoadError(
                    "Policy must be a YAML dictionary", f"s3://{self.bucket}/{key}"
                )

            return policy

        except s3.exceptions.NoSuchKey:
            raise AegisPolicyLoadError(
                f"Policy not found for customer '{customer_id}'", f"s3://{self.bucket}/{key}"
            )
        except yaml.YAMLError as e:
            raise AegisPolicyLoadError(f"Invalid YAML in policy: {e}", f"s3://{self.bucket}/{key}")
        except Exception as e:
            raise AegisPolicyLoadError(
                f"Error loading policy from S3: {e}", f"s3://{self.bucket}/{key}"
            )


class DashboardPolicyStore:
    """
    Load policies from the Aegis Dashboard API.

    This is the canonical way to keep the SDK in sync with policies
    managed through the dashboard UI.  Whenever a policy is created,
    updated, or rolled back in the dashboard the next call to
    load_policy() (after the cache TTL expires) will pick up the
    new active version automatically.

    Usage::

        store = DashboardPolicyStore(
            base_url="http://localhost:8000",
            api_key="ak_your_key",
            agent_id="billing-agent",
        )
        tools = aegis.wrap(
            tools=[...],
            policy=store.load_policy("acme-corp"),
            agent_id="billing-agent",
            customer_id="acme-corp",
        )

    Or via register_policy_store()::

        aegis.register_policy_store(
            backend="dashboard",
            base_url="http://localhost:8000",
            api_key="ak_your_key",
            agent_id="billing-agent",
        )
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = "",
        agent_id: str = "",
        timeout: int = 10,
    ):
        """
        Initialize Dashboard policy store.

        Args:
            base_url: Base URL of the Aegis Dashboard API
            api_key:  API key (``X-API-Key`` header)
            agent_id: Agent ID whose active policy should be loaded.
                      Must be provided — policies are scoped per agent.
            timeout:  HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id
        self.timeout = timeout

    def load_policy(self, customer_id: str) -> dict[str, Any]:
        """
        Fetch the active policy for *customer_id* + *agent_id* from the
        dashboard and return it as a parsed dictionary.

        Args:
            customer_id: Customer identifier

        Returns:
            Parsed policy dictionary

        Raises:
            AegisPolicyLoadError: If the policy cannot be fetched or parsed
        """
        try:
            import requests as _requests
        except ImportError:
            raise AegisPolicyLoadError(
                "requests library is required for DashboardPolicyStore. "
                "Install with: pip install requests"
            )

        if not self.agent_id:
            raise AegisPolicyLoadError(
                "DashboardPolicyStore requires agent_id to be set",
                self.base_url,
            )

        url = f"{self.base_url}/api/v1/policies"
        try:
            response = _requests.get(
                url,
                params={
                    "customer_id": customer_id,
                    "agent_id": self.agent_id,
                    "include_inactive": "false",
                },
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
            response.raise_for_status()
            policies = response.json()
        except Exception as e:
            raise AegisPolicyLoadError(
                f"Error fetching policy from dashboard: {e}",
                url,
            )

        if not policies:
            raise AegisPolicyLoadError(
                f"No active policy found in dashboard for customer='{customer_id}' "
                f"agent='{self.agent_id}'. Create one via the Policies page.",
                url,
            )

        # API returns most-recent first; take the active one
        active_policy_record = policies[0]
        policy_yaml = active_policy_record.get("policy_yaml", "")
        if not policy_yaml:
            raise AegisPolicyLoadError(
                "Dashboard returned a policy record with empty policy_yaml",
                url,
            )

        try:
            policy = yaml.safe_load(policy_yaml)
        except yaml.YAMLError as e:
            raise AegisPolicyLoadError(
                f"Invalid YAML in dashboard policy: {e}",
                url,
            )

        if not isinstance(policy, dict):
            raise AegisPolicyLoadError(
                "Policy must be a YAML dictionary",
                url,
            )

        return policy


class GCSPolicyStore:
    """Load policies from Google Cloud Storage."""

    def __init__(self, bucket: str, prefix: str = "policies/"):
        """
        Initialize GCS policy store.

        Args:
            bucket: GCS bucket name
            prefix: Blob prefix for policy files
        """
        self.bucket_name = bucket
        self.prefix = prefix
        self._gcs_client = None

    def _get_gcs_client(self):
        """Lazy-load GCS client."""
        if self._gcs_client is None:
            try:
                from google.cloud import storage

                self._gcs_client = storage.Client()
            except ImportError:
                raise AegisPolicyLoadError(
                    "google-cloud-storage not installed. Install with: pip install aegis-sdk[gcs]"
                )
        return self._gcs_client

    def load_policy(self, customer_id: str) -> dict[str, Any]:
        """
        Load policy from GCS.

        Args:
            customer_id: Customer identifier

        Returns:
            Parsed policy dictionary

        Raises:
            AegisPolicyLoadError: If policy not found or invalid
        """
        client = self._get_gcs_client()
        bucket = client.bucket(self.bucket_name)
        blob_name = f"{self.prefix}{customer_id}.yaml"
        blob = bucket.blob(blob_name)

        try:
            policy_yaml = blob.download_as_text()
            policy = yaml.safe_load(policy_yaml)

            if not isinstance(policy, dict):
                raise AegisPolicyLoadError(
                    "Policy must be a YAML dictionary", f"gs://{self.bucket_name}/{blob_name}"
                )

            return policy

        except Exception as e:
            if "404" in str(e):
                raise AegisPolicyLoadError(
                    f"Policy not found for customer '{customer_id}'",
                    f"gs://{self.bucket_name}/{blob_name}",
                )
            raise AegisPolicyLoadError(
                f"Error loading policy from GCS: {e}", f"gs://{self.bucket_name}/{blob_name}"
            )


class PolicyCache:
    """In-memory cache for policies with TTL support."""

    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize policy cache.

        Args:
            ttl_seconds: Time-to-live for cached policies
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}

    def get(self, customer_id: str) -> Optional[dict[str, Any]]:
        """
        Get cached policy if not expired.

        Args:
            customer_id: Customer identifier

        Returns:
            Cached policy or None if not found/expired
        """
        if customer_id in self._cache:
            policy, timestamp = self._cache[customer_id]
            if time.time() - timestamp < self.ttl_seconds:
                return policy
            else:
                # Expired - remove from cache
                del self._cache[customer_id]
        return None

    def set(self, customer_id: str, policy: dict[str, Any]) -> None:
        """
        Cache a policy.

        Args:
            customer_id: Customer identifier
            policy: Policy dictionary to cache
        """
        self._cache[customer_id] = (policy, time.time())

    def invalidate(self, customer_id: Optional[str] = None) -> None:
        """
        Invalidate cached policies.

        Args:
            customer_id: If provided, invalidate only this customer.
                        If None, invalidate all.
        """
        if customer_id:
            self._cache.pop(customer_id, None)
        else:
            self._cache.clear()


class PolicyLoader:
    """
    Multi-tenant policy loader with caching.

    Loads policies from configured backend and caches them in memory.
    """

    def __init__(
        self, store: Optional[PolicyStore] = None, cache_ttl: int = 60, enable_cache: bool = True
    ):
        """
        Initialize policy loader.

        Args:
            store: Policy storage backend (defaults to filesystem)
            cache_ttl: Cache time-to-live in seconds
            enable_cache: Whether to enable caching
        """
        self.store = store or FilesystemPolicyStore()
        self.cache = PolicyCache(ttl_seconds=cache_ttl) if enable_cache else None

    def load(self, customer_id: str) -> dict[str, Any]:
        """
        Load policy for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            Parsed policy dictionary

        Raises:
            AegisPolicyLoadError: If policy cannot be loaded
        """
        # Try cache first
        if self.cache:
            cached_policy = self.cache.get(customer_id)
            if cached_policy is not None:
                return cached_policy

        # Load from store
        policy = self.store.load_policy(customer_id)

        # Validate basic structure
        if "version" not in policy:
            raise AegisPolicyLoadError("Policy missing required 'version' field", customer_id)

        if "rules" not in policy:
            raise AegisPolicyLoadError("Policy missing required 'rules' field", customer_id)

        # Cache and return
        if self.cache:
            self.cache.set(customer_id, policy)

        return policy

    def invalidate_cache(self, customer_id: Optional[str] = None) -> None:
        """
        Invalidate policy cache.

        Args:
            customer_id: If provided, invalidate only this customer.
                        If None, invalidate all.
        """
        if self.cache:
            self.cache.invalidate(customer_id)


# Global policy store registry for convenience
_policy_loader: Optional[PolicyLoader] = None


def register_policy_store(backend: str = "filesystem", **kwargs) -> PolicyLoader:
    """
    Register a global policy store for use with load_customer_policy().

    Args:
        backend: Backend type ('filesystem', 's3', 'gcs')
        **kwargs: Backend-specific configuration

    Returns:
        Configured PolicyLoader instance

    Example:
        >>> register_policy_store(backend='s3', bucket='aegis-policies')
        >>> policy = load_customer_policy('acme-corp')
    """
    global _policy_loader

    if backend == "filesystem":
        base_path = kwargs.get("base_path", "./policies")
        store = FilesystemPolicyStore(base_path=base_path)
    elif backend == "s3":
        bucket = kwargs.get("bucket")
        if not bucket:
            raise ValueError("S3 backend requires 'bucket' parameter")
        prefix = kwargs.get("prefix", "policies/")
        store = S3PolicyStore(bucket=bucket, prefix=prefix)
    elif backend == "gcs":
        bucket = kwargs.get("bucket")
        if not bucket:
            raise ValueError("GCS backend requires 'bucket' parameter")
        prefix = kwargs.get("prefix", "policies/")
        store = GCSPolicyStore(bucket=bucket, prefix=prefix)
    elif backend == "dashboard":
        base_url = kwargs.get("base_url", "http://localhost:8000")
        api_key = kwargs.get("api_key", "")
        agent_id = kwargs.get("agent_id", "")
        if not agent_id:
            raise ValueError("Dashboard backend requires 'agent_id' parameter")
        timeout = kwargs.get("timeout", 10)
        store = DashboardPolicyStore(
            base_url=base_url,
            api_key=api_key,
            agent_id=agent_id,
            timeout=timeout,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")

    cache_ttl = kwargs.get("cache_ttl", 60)
    enable_cache = kwargs.get("enable_cache", True)

    _policy_loader = PolicyLoader(store=store, cache_ttl=cache_ttl, enable_cache=enable_cache)

    return _policy_loader


def load_customer_policy(customer_id: str) -> dict[str, Any]:
    """
    Load policy for a customer using the registered policy store.

    Must call register_policy_store() first to configure the backend.

    Args:
        customer_id: Customer identifier

    Returns:
        Parsed policy dictionary

    Raises:
        RuntimeError: If no policy store is registered
        AegisPolicyLoadError: If policy cannot be loaded
    """
    global _policy_loader

    if _policy_loader is None:
        # Auto-register filesystem backend as default
        register_policy_store(backend="filesystem")

    return _policy_loader.load(customer_id)
