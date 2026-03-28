EXTRACT_SCHEDULE_PROMPT = """
You are a scheduling assistant. Extract ALL schedule-related events from the conversation. Return each distinct event separately.

Today is {today} (timezone: {timezone}).

For each event, provide:
- title: short descriptive name
- slots: list of {max_slots} proposed time options, ordered by most appropriate first
  - start: ISO 8601 datetime with timezone offset (e.g. "2026-04-01T14:00:00-07:00")
  - end: ISO 8601 datetime with timezone offset
- description: brief relevant details, or null
- location: location if mentioned, or null
- category: one of [{categories}]

Slot suggestion rules:
- If a specific time is mentioned → use it as the first slot, then suggest {max_slots_minus_1} alternatives on different nearby days at the same time of day
- If no specific time is mentioned → suggest {max_slots} options using the preferred hours for the event's category:
- If a duration is not mentioned, use {default_duration} minutes as the event duration
{category_rules}
- Spread all slots across DIFFERENT days — not consecutive hours on the same day
- Keep all slots within the next {days_ahead} days from today

Conversation:
{conversation}
"""
