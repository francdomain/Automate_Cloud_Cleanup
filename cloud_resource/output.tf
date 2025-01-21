output "github_role_arn" {
  value       = aws_iam_role.github_actions_role.arn
  description = "ARN of the GitHub Actions IAM Role"
}

output "instance_ids" {
  value = [for instance in aws_instance.instances : instance.id]
}

output "volume_ids" {
  value = [for volume in aws_ebs_volume.unattached_volumes : volume.id]
}

output "cleanup_role_arn" {
  value = aws_iam_role.cleanup_role.arn
}
