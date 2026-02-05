from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/agents")
def demo_agents(payload: dict) -> dict:
    ak = payload.get("ak")
    sk = payload.get("sk")
    if ak != "demo-ak" or sk != "demo-sk":
        raise HTTPException(status_code=401, detail="Invalid demo credentials")

    return {
        "items": [
            {
                "name": "Customer Success Agent",
                "status": "active",
                "owner": "CS",
                "last_run": "2026-02-04T10:00:00Z",
                "description": "Handles onboarding and routine check-ins.",
                "groups": ["customer-success", "onboarding"],
                "url": "https://example.com/agents/cs",
            },
            {
                "name": "Ops Triage Agent",
                "status": "active",
                "owner": "Operations",
                "last_run": "2026-02-04T09:20:00Z",
                "description": "Monitors SLA breaches and escalations.",
                "groups": ["operations"],
                "url": "https://example.com/agents/ops",
            },
            {
                "name": "Growth Research Agent",
                "status": "paused",
                "owner": "Growth",
                "last_run": "2026-02-03T16:45:00Z",
                "description": "Summarizes experiment results and insights.",
                "groups": ["growth", "analysis"],
                "url": "https://example.com/agents/growth",
            },
        ]
    }
