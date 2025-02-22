import json
import os
import subprocess

def lambda_handler(event, context):
    try:
        # Parse the Slack request body
        body = json.loads(event.get("body", "{}"))

        # Handle Slack URL verification challenge
        if body.get("type") == "url_verification":
            return {
                "statusCode": 200,
                "body": body["challenge"]
            }

        # Handle interactive message actions
        if body.get("type") == "interactive_message":
            action = body["actions"][0]["value"]
            if action == "approve":
                # Start cleanup process
                cleanup_result = perform_cleanup()

                return {
                    "statusCode": 200,
                    "body": json.dumps({"text": "Cleanup process started.", "result": cleanup_result})
                }
            else:
                return {
                    "statusCode": 200,
                    "body": json.dumps({"text": "Cleanup declined. No action taken."})
                }

        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid request."})
        }

    except Exception as e:
        print(f"Error processing event: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error."})
        }

def perform_cleanup():
    try:
        # Run the cleanup script (ensure `cloud_cleanup.py` is in Lambda)
        result = subprocess.run(["python3", "/var/task/cloud_cleanup.py", "--dry-run=False"], capture_output=True, text=True)

        print("Cleanup Output:", result.stdout)
        print("Cleanup Error:", result.stderr)

        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            return {"status": "failed", "error": result.stderr}

    except Exception as e:
        print(f"Cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}