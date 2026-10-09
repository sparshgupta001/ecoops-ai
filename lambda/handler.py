import json

from backend.main import analyze_environmental_data


def handler(event, context):
    if isinstance(event, dict) and "body" in event and event["body"]:
        body = json.loads(event["body"])
        return analyze_environmental_data(body)
    return analyze_environmental_data(event)
