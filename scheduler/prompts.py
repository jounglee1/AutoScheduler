EXTRACT_SCHEDULE_PROMPT = """
You are a scheduling assistant. Extract all schedule-related information from the conversation below.

For each schedule found, provide:
- title: a short descriptive name
- start: start datetime in ISO 8601 format (e.g. "2024-03-10T14:00:00")
- end: end datetime in ISO 8601 format
- description: optional extra details
- location: optional location

If no specific year is mentioned, assume the current year.
If no end time is mentioned, assume 1 hour after start.

Conversation:
{conversation}
"""
