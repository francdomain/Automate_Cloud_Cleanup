import boto3
import csv
import os
from datetime import datetime, timedelta

# CPU utilization threshold (percentage)
CPU_THRESHOLD = 5

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
            # Check if monitoring is disabled
            if 'Monitoring' in instance and instance['Monitoring']['State'] == 'disabled':
                idle_instances.append(instance_id)
                instance_reasons[instance_id] = "Monitoring is disabled"
            else:
                # Check CPU utilization
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
        Period=3600,  # Hourly intervals
        Statistics=['Average']
    )

    data_points = response.get('Datapoints', [])
    if not data_points:
        return 0  # No data indicates low utilization

    # Calculate average CPU utilization
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

    instance_actions = {}
    volume_actions = {}

    if not dry_run:
        # Stop idle instances
        for instance in idle_instances:
            ec2_client.stop_instances(InstanceIds=[instance])
            instance_actions[instance] = "Instance stopped"

        # Delete unattached volumes
        for volume in unattached_volumes:
            try:
                ec2_client.delete_volume(VolumeId=volume)
                volume_actions[volume] = "Volume deleted"
            except ec2_client.exceptions.ClientError as e:
                if "InvalidVolume.NotFound" in str(e):
                    volume_actions[volume] = "Volume already deleted"
                else:
                    raise e  # Re-raise for unexpected errors
    else:
        # For dry run, no actions are performed
        instance_actions = {instance: "No action (dry run)" for instance in idle_instances}
        volume_actions = {volume: "No action (dry run)" for volume in unattached_volumes}

    return idle_instances, instance_reasons, instance_actions, unattached_volumes, volume_reasons, volume_actions

def generate_report(idle_instances, instance_reasons, instance_actions, unattached_volumes, volume_reasons, volume_actions):
    """Generate a CSV report of identified resources and actions taken."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f"cloud_cleanup_report_{timestamp}.csv"
    with open(report_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['Resource Type', 'Resource ID', 'Reason', 'Action Taken'])
        # Write idle instances with reasons and actions
        for instance in idle_instances:
            writer.writerow(['Idle Instance', instance, instance_reasons.get(instance, 'Reason not available'), instance_actions.get(instance, 'Action not available')])
        # Write unattached volumes with reasons and actions
        for volume in unattached_volumes:
            writer.writerow(['Unattached Volume', volume, volume_reasons.get(volume, 'Reason not available'), volume_actions.get(volume, 'Action not available')])

    print(f"Report generated: {report_filename}")
    return report_filename

def main():
    """Main execution logic."""
    ec2_client = boto3.client('ec2')
    cloudwatch_client = boto3.client('cloudwatch')
    dry_run = os.getenv('DRY_RUN', 'True').lower() == 'true'

    (idle_instances, instance_reasons, instance_actions,
     unattached_volumes, volume_reasons, volume_actions) = cleanup_resources(ec2_client, cloudwatch_client, dry_run)

    report_filename = generate_report(idle_instances, instance_reasons, instance_actions,
                                       unattached_volumes, volume_reasons, volume_actions)
    print(f"Report generated: {report_filename}")

if __name__ == "__main__":
    main()