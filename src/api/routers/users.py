from fastapi import APIRouter, Query
from typing import List
from src.api.services.data_loader import data_loader
from src.api.schemas.responses import UserRiskProfile

router = APIRouter()


@router.get("/users/risk", response_model=List[UserRiskProfile])
def get_risky_users(
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of users to return"),
    sort: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction for risk score"),
):
    """
    Return the riskiest users, ranked by total risk score.

    Each user includes their aggregated risk score, organisational role,
    department, and a categorical risk level.
    """
    users = data_loader.get_users_risk_data(limit=limit, sort_desc=(sort == "desc"))

    for u in users:
        u.setdefault("role", "Employee")
        u.setdefault("department", "General")
        if "risk_level" not in u:
            score = u.get("total_risk_score", 0)
            u["risk_level"] = (
                "Critical" if score > 80
                else "High" if score > 50
                else "Medium" if score > 25
                else "Low"
            )
    return users


@router.get("/users/{user_id}/profile")
def get_user_profile(user_id: str):
    """
    Return the full risk profile for a single user.

    Includes risk score, rank, role, department, and categorical risk level.
    Returns 404 if the user is not found.
    """
    from fastapi import HTTPException

    profile = data_loader.get_user_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")
    return profile
