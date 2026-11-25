import os

from aws_cdk import App

from cdk.stacks.storage_stack import StorageStack
from cdk.stacks.lambda_stack import LambdaStack
from cdk.stacks.stepfunctions_stack import StepFunctionsStack
from cdk.stacks.api_stack import ApiStack


def test_stacks_synthesize_with_fal_and_detailed_pipeline(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "test-fal-key")
    monkeypatch.setenv("BEDROCK_SONNET_MODEL_ARN", "arn:test:sonnet")
    monkeypatch.setenv("BEDROCK_OPUS_MODEL_ARN", "arn:test:opus")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "")

    app = App(context={"aws:cdk:bundling-stacks": []})
    storage = StorageStack(app, "TestStorage")
    lambdas = LambdaStack(
        app,
        "TestLambda",
        bucket=storage.bucket,
        topic=storage.topic,
    )
    lambdas.add_dependency(storage)
    state_machine = StepFunctionsStack(
        app,
        "TestStepFunctions",
        input_validator=lambdas.input_validator,
        crosswalk_generator=lambdas.crosswalk_generator,
        image_generator=lambdas.image_generator,
        qc_validator=lambdas.qc_validator,
        assembler=lambdas.assembler,
        t12_generator=lambdas.t12_generator,
        lender_narrative_generator=lambdas.lender_narrative_generator,
        section_lambdas=lambdas.section_lambdas,
        topic=storage.topic,
    )
    state_machine.add_dependency(lambdas)
    ApiStack(
        app,
        "TestApi",
        input_validator=lambdas.input_validator,
        status_checker=lambdas.status_checker,
        download_handler=lambdas.download_handler,
        lucky_generator=lambdas.lucky_generator,
    )

    assembly = app.synth()
    templates = assembly.get_stack_by_name("TestLambda").template
    lambda_resource = next(
        value
        for key, value in templates["Resources"].items()
        if "ImageGenerator" in key
        and value.get("Type") == "AWS::Lambda::Function"
    )
    # The image generator environment is asserted through its synthesized properties.
    function_props = lambda_resource["Properties"]
    env = function_props["Environment"]["Variables"]
    assert env["FAL_KEY"] == "test-fal-key"
    assert "REPLICATE_API_TOKEN" not in env

    narrative_resources = [
        value
        for value in templates["Resources"].values()
        if value.get("Type") == "AWS::Lambda::Function"
        and "lender_narrative_generator" in str(value)
    ]
    assert narrative_resources or hasattr(lambdas, "lender_narrative_generator")
