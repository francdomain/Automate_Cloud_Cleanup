# 1. Create OIDC Provider for GitHub
resource "aws_iam_openid_connect_provider" "github" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = var.thumbprint_list # GitHub's OIDC thumbprint
  url             = var.url
}

# 2. Create IAM Role
# resource "aws_iam_role" "github_actions_role" {
#   name = "github-actions-cleanup-role"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Effect = "Allow",
#         Principal = {
#           Federated = aws_iam_openid_connect_provider.github.arn
#         },
#         Action = "sts:AssumeRoleWithWebIdentity",
#         Condition = {
#           StringEquals = {
#             "token.actions.githubusercontent.com:sub" : "francdomain/Automate_Cloud_Cleanup:ref:refs/heads/main"
#           }
#         }
#       }
#     ]
#   })
# }

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
            "token.actions.githubusercontent.com:sub" : "repo:Automate_Cloud_Cleanup:ref:refs/heads/main"
          }
        }
      }
    ]
  })
}

# 3. Attach Policies to the Role
resource "aws_iam_role_policy" "cleanup_policy" {
  name = "cleanup-policy"
  role = aws_iam_role.github_actions_role.name

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
          "s3:PutObject"
        ],
        Resource = "*"
      }
    ]
  })
}
