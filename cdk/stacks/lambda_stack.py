from aws_cdk import (
    Stack,
    Duration,
    BundlingOptions,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_sns as sns,
    aws_iam as iam,
)
from constructs import Construct


class LambdaStack(Stack):
    """Stack for all Lambda functions used in the appraisal generation pipeline."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        bucket: s3.IBucket,
        topic: sns.ITopic,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = bucket
        self.topic = topic

        # Shared environment variables for all Lambdas
        self.shared_env = {
            "S3_BUCKET": bucket.bucket_name,
            "SNS_TOPIC_ARN": topic.topic_arn,
        }

        # Bedrock invoke policy (includes Marketplace permissions for inference profiles)
        self.bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "aws-marketplace:ViewSubscriptions",
                "aws-marketplace:Subscribe",
            ],
            resources=["*"],
        )

        # Shared Lambda layer for dependencies + shared code
        self.shared_layer = _lambda.LayerVersion(
            self,
            "SharedLayer",
            code=_lambda.Code.from_asset(
                ".",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r lambdas/requirements-runtime.txt -t /asset-output/python "
                        "&& mkdir -p /asset-output/python/lambdas "
                        "&& cp -r lambdas/shared /asset-output/python/lambdas/",
                    ],
                ),
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Shared dependencies and utilities for appraisal generator Lambdas",
        )

        # --- Core pipeline Lambdas ---

        self.input_validator = self._create_lambda(
            "InputValidator",
            handler_path="lambdas/input_validator",
            memory_size=512,
            timeout_minutes=5,
        )

        self.crosswalk_generator = self._create_lambda(
            "CrosswalkGenerator",
            handler_path="lambdas/crosswalk_generator",
            memory_size=1024,
            timeout_minutes=10,
        )

        self.image_generator = self._create_lambda(
            "ImageGenerator",
            handler_path="lambdas/image_generator",
            memory_size=512,
            timeout_minutes=5,
        )

        self.qc_validator = self._create_lambda(
            "QcValidator",
            handler_path="lambdas/qc_validator",
            memory_size=512,
            timeout_minutes=5,
        )

        self.assembler = self._create_lambda(
            "Assembler",
            handler_path="lambdas/assembler",
            memory_size=512,
            timeout_minutes=15,
        )

        self.t12_generator = self._create_lambda(
            "T12Generator",
            handler_path="lambdas/t12_generator",
            memory_size=512,
            timeout_minutes=5,
        )

        # --- Section generator Lambdas (section_01 through section_12) ---
        # Opus-powered sections get 1024MB memory; others get 512MB.

        self.section_lambdas: dict[str, _lambda.Function] = {}

        for i in range(1, 13):
            section_name = f"section_{i:02d}"
            construct_name = f"Section{i:02d}Generator"
            memory = 1024  # All section agents get 1024MB
            fn = self._create_lambda(
                construct_name,
                handler_path=f"lambdas/section_generators/{section_name}",
                memory_size=memory,
                timeout_minutes=10,
            )
            self.section_lambdas[section_name] = fn

        # --- API-facing Lambdas ---

        self.status_checker = self._create_lambda(
            "StatusChecker",
            handler_path="lambdas/status_checker",
            memory_size=512,
            timeout_minutes=5,
        )

        self.download_handler = self._create_lambda(
            "DownloadHandler",
            handler_path="lambdas/download_handler",
            memory_size=512,
            timeout_minutes=5,
        )

        self.lucky_generator = self._create_lambda(
            "LuckyGenerator",
            handler_path="lambdas/lucky_generator",
            memory_size=512,
            timeout_minutes=2,
        )

        # Wire Step Functions ARN and permissions using the known state machine name.
        # This avoids cyclic cross-stack references.
        sfn_arn = f"arn:aws:states:{self.region}:{self.account}:stateMachine:AppraisalPipelineStateMachine"

        self.input_validator.add_environment("STEP_FUNCTION_ARN", sfn_arn)
        self.status_checker.add_environment("STEP_FUNCTION_ARN", sfn_arn)

        self.input_validator.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["states:StartExecution"],
                resources=[sfn_arn],
            )
        )
        self.status_checker.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "states:DescribeExecution",
                    "states:ListExecutions",
                    "states:GetExecutionHistory",
                    "states:DescribeStateMachine",
                ],
                resources=[sfn_arn, f"{sfn_arn}:*", f"arn:aws:states:{self.region}:{self.account}:execution:AppraisalPipelineStateMachine:*"],
            )
        )

    def _create_lambda(
        self,
        construct_id: str,
        handler_path: str,
        memory_size: int = 512,
        timeout_minutes: int = 5,
        extra_env: dict | None = None,
    ) -> _lambda.Function:
        """Create a Lambda function with standard configuration."""
        environment = {**self.shared_env}
        if extra_env:
            environment.update(extra_env)

        fn = _lambda.Function(
            self,
            construct_id,
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset(handler_path),
            memory_size=memory_size,
            timeout=Duration.minutes(timeout_minutes),
            environment=environment,
            layers=[self.shared_layer],
        )

        # Grant S3 read/write access
        self.bucket.grant_read_write(fn)

        # Grant Bedrock invoke permissions
        fn.add_to_role_policy(self.bedrock_policy)

        return fn
