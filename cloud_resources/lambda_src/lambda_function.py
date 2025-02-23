import json
import os
import logging
import urllib.parse
import boto3
from cloud_cleanup import cleanup_resources, generate_report, send_slack_notification

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        ec2_client = boto3.client('ec2')
        cloudwatch_client = boto3.client('cloudwatch')
        dry_run = os.getenv('DRY_RUN', 'True').lower() == 'true'

        # Log incoming request
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract and parse Slack request payload
        body = event.get("body", "")
        if not body:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing request body"})}

        parsed_body = urllib.parse.parse_qs(body)
        payload = json.loads(parsed_body.get("payload", ["{}"])[0])

        # Handle Slack URL verification
        if payload.get("type") == "url_verification":
            return {"statusCode": 200, "body": payload["challenge"]}

        # Handle Slack interactive message actions
        if payload.get("type") == "interactive_message":
            actions = payload.get("actions", [])
            if not actions:
                return {"statusCode": 400, "body": json.dumps({"error": "No action received"})}

            action = actions[0].get("value")
            if action == "approve":
                # Perform cleanup operations
                idle_instances, instance_reasons, unattached_volumes, volume_reasons = cleanup_resources(ec2_client, cloudwatch_client, dry_run)
                report_filename = generate_report(idle_instances, instance_reasons, unattached_volumes, volume_reasons)
                send_slack_notification()

                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Cleanup executed",
                        "report": report_filename,
                        "request_id": context.aws_request_id
                    })
                }
            elif action == "decline":
                return {"statusCode": 200, "body": json.dumps({"text": "Cleanup declined. No action taken."})}

        return {"statusCode": 400, "body": json.dumps({"error": "Invalid request format"})}

    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal Server Error",
                "message": str(e),
                "request_id": context.aws_request_id
            })
        }
