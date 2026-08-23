from app.schemas.intelligence import ResponseContext, ResponseRecommendation


def _priority(risk_score: float) -> str:
    if risk_score >= 85:
        return "critical"
    if risk_score >= 65:
        return "high"
    if risk_score >= 35:
        return "medium"
    return "low"


def recommend_actions(context: ResponseContext) -> list[ResponseRecommendation]:
    priority = _priority(context.risk_score)
    recommendations: list[ResponseRecommendation] = []

    if context.malicious_ip_confirmed and context.source_ip:
        recommendations.append(
            ResponseRecommendation(
                action="block_ip",
                target=str(context.source_ip),
                priority=priority,
                rationale="The source address is confirmed malicious and appears in this event.",
            )
        )
    if context.host and context.risk_score >= 85:
        recommendations.append(
            ResponseRecommendation(
                action="isolate_host",
                target=context.host,
                priority="critical",
                rationale="Critical calculated risk warrants analyst review for host isolation.",
            )
        )
    if context.user and any(
        marker in context.event_type.lower()
        for marker in ("credential", "authentication", "login", "account")
    ):
        recommendations.append(
            ResponseRecommendation(
                action="reset_credentials",
                target=context.user,
                priority=priority,
                rationale="The event concerns account or authentication activity.",
            )
        )
    if context.vulnerability_id:
        recommendations.append(
            ResponseRecommendation(
                action="patch_vulnerability",
                target=context.vulnerability_id,
                priority=priority,
                rationale="A specific vulnerability is associated with the observed risk.",
            )
        )
    if context.host and context.confidence >= 0.7:
        recommendations.append(
            ResponseRecommendation(
                action="investigate_endpoint",
                target=context.host,
                priority=priority,
                rationale="Detection confidence is high enough for endpoint investigation.",
            )
        )
    if not recommendations:
        recommendations.append(
            ResponseRecommendation(
                action="monitor",
                target=context.host or str(context.source_ip or "environment"),
                priority=priority,
                rationale="Current evidence does not justify a more disruptive recommendation.",
            )
        )

    order = {
        "block_ip": 0,
        "isolate_host": 1,
        "reset_credentials": 2,
        "patch_vulnerability": 3,
        "investigate_endpoint": 4,
        "monitor": 5,
    }
    return sorted(recommendations, key=lambda item: (order[item.action], item.target))
