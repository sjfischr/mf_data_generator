#!/usr/bin/env python3
import aws_cdk as cdk

from stacks.storage_stack import StorageStack
from stacks.lambda_stack import LambdaStack
from stacks.stepfunctions_stack import StepFunctionsStack
from stacks.api_stack import ApiStack


app = cdk.App()

# Stack 1: Storage (S3 + SNS)
storage_stack = StorageStack(app, "StorageStack")

# Stack 2: Lambda functions
lambda_stack = LambdaStack(
    app,
    "LambdaStack",
    bucket=storage_stack.bucket,
    topic=storage_stack.topic,
)
lambda_stack.add_dependency(storage_stack)

# Stack 3: Step Functions state machine
stepfunctions_stack = StepFunctionsStack(
    app,
    "StepFunctionsStack",
    input_validator=lambda_stack.input_validator,
    crosswalk_generator=lambda_stack.crosswalk_generator,
    image_generator=lambda_stack.image_generator,
    qc_validator=lambda_stack.qc_validator,
    assembler=lambda_stack.assembler,
    t12_generator=lambda_stack.t12_generator,
    section_lambdas=lambda_stack.section_lambdas,
    topic=storage_stack.topic,
)
stepfunctions_stack.add_dependency(lambda_stack)

# Stack 4: API Gateway
api_stack = ApiStack(
    app,
    "ApiStack",
    input_validator=lambda_stack.input_validator,
    status_checker=lambda_stack.status_checker,
    download_handler=lambda_stack.download_handler,
    lucky_generator=lambda_stack.lucky_generator,
)
api_stack.add_dependency(lambda_stack)

app.synth()
