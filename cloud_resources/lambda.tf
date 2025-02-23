data "archive_file" "lambda_function_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.py" # For single file
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "slack_interaction_handler" {
  filename         = data.archive_file.lambda_function_zip.output_path
  function_name    = "SlackInteractionHandler"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("${data.archive_file.lambda_function_zip.output_path}") # Ensures updates trigger a redeploy

  environment {
    variables = {
      GITHUB_TOKEN = var.github_token
      REPO_OWNER   = var.repo_owner
      REPO_NAME    = var.repo_name
    }
  }
}

resource "aws_lambda_permission" "allow_apigateway" {
  statement_id = "AllowExecutionFromAPIGateway"
  action       = "lambda:InvokeFunction"
  # function_name = aws_lambda_function.slack_interaction_handler.arn
  function_name = aws_lambda_function.slack_interaction_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
