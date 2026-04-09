from grok_x_lead_monitor.models import QuerySpec


QUERY_PACKS: dict[str, list[QuerySpec]] = {
    "v1": [
        QuerySpec(query="feet hurt standing all day", intent_theme="standing_pain"),
        QuerySpec(query="need comfortable shoes recommendations", intent_theme="comfort_recommendation"),
        QuerySpec(query="best shoes for plantar fasciitis", intent_theme="plantar_fasciitis"),
        QuerySpec(query="my feet are killing me at work need better shoes", intent_theme="work_pain"),
        QuerySpec(query="walking all day shoes recommendation", intent_theme="replacement_intent"),
    ]
}


def build_query_pack(version: str) -> list[QuerySpec]:
    try:
        return list(QUERY_PACKS[version])
    except KeyError as exc:
        raise ValueError(f"Unsupported query pack version: {version}") from exc

