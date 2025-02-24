resource "time_sleep" "wait_for_cluster" {
  create_duration = "30s"
}

resource "null_resource" "package_lambda" {
  provisioner "local-exec" {
    command = <<EOT
      rm -rf ${path.module}/lambda_package
      mkdir -p ${path.module}/lambda_package
      cp -r ${path.module}/lambda_src/* ${path.module}/lambda_package/
      pip install -r ${path.module}/lambda_src/requirements.txt -t ${path.module}/lambda_package
    EOT
  }

  triggers = {
    always_run = "${timestamp()}"
  }
}

data "archive_file" "lambda_function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_package"
  output_path = "${path.module}/lambda_function.zip"

  depends_on = [null_resource.package_lambda, time_sleep.wait_for_cluster]
}

# data "archive_file" "lambda_function_zip" {
#   type        = "zip"
#   source_dir  = "${path.module}/lambda_src" # Include multiple files from a directory
#   output_path = "${path.module}/lambda_function.zip"

#   depends_on = [null_resource.package_lambda, time_sleep.wait_for_cluster]
# }

resource "aws_lambda_function" "slack_interaction_handler" {
  function_name    = "CloudCleanupLambda"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  filename         = data.archive_file.lambda_function_zip.output_path
  source_code_hash = data.archive_file.lambda_function_zip.output_base64sha256

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
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
