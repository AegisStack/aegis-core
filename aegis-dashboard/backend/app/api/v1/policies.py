"""
Policies API - CRUD operations for policies.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel
from typing import List, Optional
import hashlib
import yaml

from ...database import get_db
from ...models import Policy

router = APIRouter()


class PolicyCreate(BaseModel):
    """Schema for creating a new policy."""

    customer_id: str
    agent_id: str
    policy_yaml: str
    description: Optional[str] = None
    created_by: Optional[str] = None


class PolicyResponse(BaseModel):
    """Schema for policy responses."""

    policy_id: str
    customer_id: str
    agent_id: str
    policy_yaml: str
    version: int
    is_active: bool
    created_at: str
    created_by: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True


def validate_policy_yaml(policy_yaml: str) -> dict:
    """Validate YAML syntax and basic policy structure."""
    try:
        policy = yaml.safe_load(policy_yaml)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

    if not isinstance(policy, dict):
        raise HTTPException(status_code=400, detail="Policy must be a YAML dictionary")

    if "version" not in policy:
        raise HTTPException(status_code=400, detail="Policy missing 'version' field")

    if "rules" not in policy:
        raise HTTPException(status_code=400, detail="Policy missing 'rules' field")

    return policy


@router.get("/policies", response_model=List[PolicyResponse])
async def list_policies(
    customer_id: str = Query(...),
    agent_id: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """List policies for a customer."""
    query = select(Policy).where(Policy.customer_id == customer_id)

    if agent_id:
        query = query.where(Policy.agent_id == agent_id)

    if not include_inactive:
        query = query.where(Policy.is_active == True)

    query = query.order_by(desc(Policy.created_at))

    result = await db.execute(query)
    policies = result.scalars().all()

    return [PolicyResponse(**p.to_dict()) for p in policies]


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific policy by ID."""
    result = await db.execute(select(Policy).where(Policy.policy_id == policy_id))
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return PolicyResponse(**policy.to_dict())


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_policy(policy_data: PolicyCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new policy version.

    Validates YAML, deactivates previous versions, and creates new active policy.
    """
    # Validate YAML
    validate_policy_yaml(policy_data.policy_yaml)

    # Compute hash
    policy_hash = hashlib.sha256(policy_data.policy_yaml.encode()).hexdigest()

    # Check if identical policy already exists
    existing_query = select(Policy).where(
        and_(
            Policy.customer_id == policy_data.customer_id,
            Policy.agent_id == policy_data.agent_id,
            Policy.policy_hash == policy_hash,
            Policy.is_active == True,
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Identical policy already exists")

    # Get current version number
    version_query = (
        select(func.max(Policy.version))
        .where(
            and_(
                Policy.customer_id == policy_data.customer_id,
                Policy.agent_id == policy_data.agent_id,
            )
        )
    )
    version_result = await db.execute(version_query)
    current_version = version_result.scalar() or 0

    # Deactivate all previous versions
    deactivate_query = (
        select(Policy)
        .where(
            and_(
                Policy.customer_id == policy_data.customer_id,
                Policy.agent_id == policy_data.agent_id,
                Policy.is_active == True,
            )
        )
    )
    deactivate_result = await db.execute(deactivate_query)
    for old_policy in deactivate_result.scalars():
        old_policy.is_active = False

    # Create new policy
    new_policy = Policy(
        customer_id=policy_data.customer_id,
        agent_id=policy_data.agent_id,
        policy_yaml=policy_data.policy_yaml,
        policy_hash=policy_hash,
        version=current_version + 1,
        is_active=True,
        created_by=policy_data.created_by,
        description=policy_data.description,
    )

    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)

    return PolicyResponse(**new_policy.to_dict())


@router.post("/policies/{policy_id}/activate", response_model=PolicyResponse)
async def activate_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    """Activate a specific policy version (rollback)."""
    # Get the policy
    result = await db.execute(select(Policy).where(Policy.policy_id == policy_id))
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Deactivate all other versions
    deactivate_query = select(Policy).where(
        and_(
            Policy.customer_id == policy.customer_id,
            Policy.agent_id == policy.agent_id,
            Policy.is_active == True,
        )
    )
    deactivate_result = await db.execute(deactivate_query)
    for old_policy in deactivate_result.scalars():
        old_policy.is_active = False

    # Activate this policy
    policy.is_active = True

    await db.commit()
    await db.refresh(policy)

    return PolicyResponse(**policy.to_dict())
