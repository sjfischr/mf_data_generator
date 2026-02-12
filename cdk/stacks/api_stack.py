from aws_cdk import (
    Stack,
    CfnOutput,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
)
from constructs import Construct


class ApiStack(Stack):
    """Stack for the API Gateway REST API."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        input_validator: _lambda.IFunction,
        status_checker: _lambda.IFunction,
        download_handler: _lambda.IFunction,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # REST API
        self.api = apigw.RestApi(
            self,
            "SyntheticAppraisalAPI",
            rest_api_name="SyntheticAppraisalAPI",
            description="API for generating synthetic multifamily appraisals",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "X-Amz-Date",
                    "Authorization",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        # /api resource
        api_resource = self.api.root.add_resource("api")

        # POST /api/generate -> input_validator Lambda (proxy integration)
        generate_resource = api_resource.add_resource("generate")
        generate_integration = apigw.LambdaIntegration(
            input_validator,
            proxy=True,
        )
        generate_resource.add_method("POST", generate_integration)

        # GET /api/status/{job_id} -> status_checker Lambda
        status_resource = api_resource.add_resource("status")
        status_job_resource = status_resource.add_resource("{job_id}")
        status_integration = apigw.LambdaIntegration(
            status_checker,
            proxy=True,
        )
        status_job_resource.add_method("GET", status_integration)

        # GET /api/download/{job_id} -> download_handler Lambda
        download_resource = api_resource.add_resource("download")
        download_job_resource = download_resource.add_resource("{job_id}")
        download_integration = apigw.LambdaIntegration(
            download_handler,
            proxy=True,
        )
        download_job_resource.add_method("GET", download_integration)

        # Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="URL of the Synthetic Appraisal API",
        )

        CfnOutput(
            self,
            "GenerateEndpoint",
            value=f"{self.api.url}api/generate",
            description="POST endpoint to generate a new appraisal",
        )

        CfnOutput(
            self,
            "StatusEndpoint",
            value=f"{self.api.url}api/status/{{job_id}}",
            description="GET endpoint to check appraisal generation status",
        )

        CfnOutput(
            self,
            "DownloadEndpoint",
            value=f"{self.api.url}api/download/{{job_id}}",
            description="GET endpoint to download completed appraisal",
        )
