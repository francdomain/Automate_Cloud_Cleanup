# Create OIDC Provider for GitHub
resource "aws_iam_openid_connect_provider" "github" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = var.thumbprint_list # GitHub's OIDC thumbprint
  url             = var.url
}

# Create IAM Role
resource "aws_iam_role" "github_actions_role" {
  name = "github-actions-cleanup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" : "sts.amazonaws.com",
            "token.actions.githubusercontent.com:sub" : "repo:francdomain/Automate_Cloud_Cleanup:ref:refs/heads/main"
          }
        }
      }
    ]
  })
}

# Attach Policies to the Role
resource "aws_iam_policy" "cloud_cleanup_policy" {
  name = "github-actions-cloud-cleanup-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ec2:DescribeInstances",
          "ec2:StopInstances",
          "ec2:DescribeVolumes",
          "ec2:DeleteVolume",
          "cloudwatch:GetMetricStatistics"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cloud_cleanup_policy_attachment" {
  role       = aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.cloud_cleanup_policy.arn
}
