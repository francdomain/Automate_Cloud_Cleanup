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
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            # Check if monitoring is disabled
            if 'Monitoring' in instance and instance['Monitoring']['State'] == 'disabled':
                idle_instances.append(instance_id)
            else:
                # Check CPU utilization
                avg_cpu = get_instance_cpu_utilization(cloudwatch_client, instance_id)
                if avg_cpu < CPU_THRESHOLD:
                    idle_instances.append(instance_id)
    return idle_instances

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
    return [volume['VolumeId'] for volume in volumes['Volumes']]

def cleanup_resources(ec2_client, cloudwatch_client, dry_run=True):
    """Identify and optionally clean up resources."""
    idle_instances = find_idle_instances(ec2_client, cloudwatch_client)
    unattached_volumes = find_unattached_volumes(ec2_client)

    if not dry_run:
        # Stop idle instances
        for instance in idle_instances:
            ec2_client.stop_instances(InstanceIds=[instance])

        # Delete unattached volumes
        for volume in unattached_volumes:
            ec2_client.delete_volume(VolumeId=volume)

    return idle_instances, unattached_volumes

def generate_report(idle_instances, unattached_volumes):
    """Generate a CSV report of identified resources."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f"cloud_cleanup_report_{timestamp}.csv"
    with open(report_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Resource Type', 'Resource ID'])
        writer.writerows([['Idle Instance', instance] for instance in idle_instances])
        writer.writerows([['Unattached Volume', volume] for volume in unattached_volumes])
    return report_filename

def main():
    """Main execution logic."""
    ec2_client = boto3.client('ec2')
    cloudwatch_client = boto3.client('cloudwatch')
    dry_run = os.getenv('DRY_RUN', 'True').lower() == 'true'

    idle_instances, unattached_volumes = cleanup_resources(ec2_client, cloudwatch_client, dry_run)

    report_filename = generate_report(idle_instances, unattached_volumes)
    print(f"Report generated: {report_filename}")

if __name__ == "__main__":
    main()