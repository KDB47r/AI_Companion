import json


def parse_sse(text: str) -> list[dict]:
    """Parse the subset of SSE used by this service into dicts."""

    events: list[dict] = []
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return events

    for block in normalized.split("\n\n"):
        if not block.strip():
            continue

        event = None
        event_id = None
        data_lines: list[str] = []

        for line in block.split("\n"):
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
            elif line.startswith("id:"):
                event_id = int(line[len("id:") :].strip())

        if event is None:
            continue

        events.append(
            {
                "event": event,
                "data": json.loads("\n".join(data_lines)) if data_lines else None,
                "id": event_id,
            }
        )

    return events
