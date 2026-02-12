from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    Duration,
    aws_s3 as s3,
    aws_sns as sns,
)
from constructs import Construct


class StorageStack(Stack):
    """Stack for S3 storage and SNS notification resources."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for appraisal data
        self.bucket = s3.Bucket(
            self,
            "AppraisalDataBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(30),
                ),
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.DELETE,
                        s3.HttpMethods.HEAD,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3600,
                ),
            ],
        )

        # SNS topic for appraisal completion notifications
        self.topic = sns.Topic(
            self,
            "AppraisalCompletionTopic",
            topic_name="AppraisalCompletionTopic",
        )

        # Outputs
        CfnOutput(
            self,
            "BucketName",
            value=self.bucket.bucket_name,
            description="S3 bucket name for appraisal data",
        )

        CfnOutput(
            self,
            "SnsTopicArn",
            value=self.topic.topic_arn,
            description="SNS topic ARN for appraisal completion notifications",
        )
