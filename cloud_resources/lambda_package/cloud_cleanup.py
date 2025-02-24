import boto3
import csv
import os
import json
import requests
from datetime import datetime, timedelta

# CPU utilization threshold (percentage)
CPU_THRESHOLD = 5
LAMBDA_FUNCTION_NAME = "CloudCleanupLambda"
AWS_REGION = "us-east-1"
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

def find_idle_instances(ec2_client, cloudwatch_client):
    """Find running instances that are either idle (monitoring disabled) or underutilized."""
    instances = ec2_client.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    idle_instances = []
    instance_reasons = {}

    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            if 'Monitoring' in instance and instance['Monitoring']['State'] == 'disabled':
                idle_instances.append(instance_id)
                instance_reasons[instance_id] = "Monitoring is disabled"
            else:
                avg_cpu = get_instance_cpu_utilization(cloudwatch_client, instance_id)
                if avg_cpu < CPU_THRESHOLD:
                    idle_instances.append(instance_id)
                    instance_reasons[instance_id] = f"Low CPU utilization: {avg_cpu:.2f}%"

    return idle_instances, instance_reasons

def get_instance_cpu_utilization(cloudwatch_client, instance_id):
    """Retrieve average CPU utilization for an instance over the past 7 days."""
    now = datetime.utcnow()
    start_time = now - timedelta(days=7)

    response = cloudwatch_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=now,
        Period=3600,
        Statistics=['Average']
    )

    data_points = response.get('Datapoints', [])
    if not data_points:
        return 0

    avg_cpu = sum(dp['Average'] for dp in data_points) / len(data_points)
    return avg_cpu

def find_unattached_volumes(ec2_client):
    """Find unattached (available) volumes."""
    volumes = ec2_client.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )
    unattached_volumes = []
    volume_reasons = {}

    for volume in volumes['Volumes']:
        unattached_volumes.append(volume['VolumeId'])
        volume_reasons[volume['VolumeId']] = "Volume is not attached to any instance."

    return unattached_volumes, volume_reasons

def cleanup_resources(ec2_client, cloudwatch_client, dry_run=True):
    """Identify and optionally clean up resources."""
    idle_instances, instance_reasons = find_idle_instances(ec2_client, cloudwatch_client)
    unattached_volumes, volume_reasons = find_unattached_volumes(ec2_client)
    return idle_instances, instance_reasons, unattached_volumes, volume_reasons

def generate_report(idle_instances, instance_reasons, unattached_volumes, volume_reasons):
    """Generate a CSV report of identified resources."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f"cloud_cleanup_report_{timestamp}.csv"
    with open(report_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Resource Type', 'Resource ID', 'Reason'])
        for instance in idle_instances:
            writer.writerow(['Idle Instance', instance, instance_reasons.get(instance, 'Reason not available')])
        for volume in unattached_volumes:
            writer.writerow(['Unattached Volume', volume, volume_reasons.get(volume, 'Reason not available')])

    print(f"Report generated: {report_filename}")
    return report_filename

def trigger_lambda():
    """Invoke the AWS Lambda function for cleanup."""
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType='Event',
        Payload=json.dumps({"action": "start_cleanup"})
    )
    return response


if not SLACK_WEBHOOK_URL:
    raise ValueError("SLACK_WEBHOOK_URL is not set. Check GitHub Secrets.")

def send_slack_notification():
    """Send Slack message with Approve/Decline buttons."""
    payload = {
        "text": "Cloud Cleanup dry-run completed. Approve to clean up identified resources.",
        "attachments": [
            {
                "fallback": "Approve or Decline Cleanup.",
                "text": "Choose an action:",
                "actions": [
                    {
                        "type": "button",
                        "text": "Approve Cleanup",
                        "url": "https://slack.com/api/trigger-lambda",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": "Decline Cleanup",
                        "url": "https://slack.com"
                    }
                ]
            }
        ]
    }
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    response.raise_for_status()

def main():
    """Main execution logic."""
    ec2_client = boto3.client('ec2')
    cloudwatch_client = boto3.client('cloudwatch')
    dry_run = os.getenv('DRY_RUN', 'True').lower() == 'true'

    idle_instances, instance_reasons, unattached_volumes, volume_reasons = cleanup_resources(ec2_client, cloudwatch_client, dry_run)
    report_filename = generate_report(idle_instances, instance_reasons, unattached_volumes, volume_reasons)
    send_slack_notification()
    print(f"Report generated: {report_filename}")

if __name__ == "__main__":
    main()
