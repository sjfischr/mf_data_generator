from aws_cdk import (
    Stack,
    Duration,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_lambda as _lambda,
    aws_sns as sns,
)
from constructs import Construct


class StepFunctionsStack(Stack):
    """Stack for the Step Functions state machine orchestrating the appraisal pipeline."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        input_validator: _lambda.IFunction,
        crosswalk_generator: _lambda.IFunction,
        image_generator: _lambda.IFunction,
        qc_validator: _lambda.IFunction,
        assembler: _lambda.IFunction,
        t12_generator: _lambda.IFunction,
        lender_narrative_generator: _lambda.IFunction,
        section_lambdas: dict[str, _lambda.IFunction],
        topic: sns.ITopic,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Standard retry configuration for Lambda tasks
        retry_config = {
            "errors": [
                "TransientError",
                "Lambda.ServiceException",
                "Lambda.AWSLambdaException",
                "Lambda.SdkClientException",
                "Lambda.TooManyRequestsException",
            ],
            "interval": Duration.seconds(5),
            "max_attempts": 3,
            "backoff_rate": 2.0,
        }

        # --- SNS error notification task ---
        notify_error = tasks.SnsPublish(
            self,
            "NotifyError",
            topic=topic,
            message=sfn.TaskInput.from_json_path_at("$"),
            subject="Appraisal Generation Failed",
            result_path=sfn.JsonPath.DISCARD,
        )
        notify_error_state = notify_error.next(
            sfn.Fail(self, "PipelineFailed", cause="Appraisal generation failed", error="AppraisalError")
        )

        # --- Step 1: Input Validation ---
        validate_input = tasks.LambdaInvoke(
            self,
            "ValidateInput",
            lambda_function=input_validator,
            output_path="$.Payload",
        )
        validate_input.add_retry(**retry_config)
        validate_input.add_catch(notify_error_state, result_path="$.error")

        # --- Step 2: Crosswalk Generation ---
        generate_crosswalk = tasks.LambdaInvoke(
            self,
            "GenerateCrosswalk",
            lambda_function=crosswalk_generator,
            output_path="$.Payload",
        )
        generate_crosswalk.add_retry(**retry_config)
        generate_crosswalk.add_catch(notify_error_state, result_path="$.error")

        # --- Step 3: Parallel section generation + T12 ---
        parallel_sections = sfn.Parallel(
            self,
            "GenerateAllSections",
            result_path="$.sections_output",
        )

        for section_name, section_fn in section_lambdas.items():
            construct_name = f"Generate_{section_name}"
            section_task = tasks.LambdaInvoke(
                self,
                construct_name,
                lambda_function=section_fn,
                output_path="$.Payload",
            )
            section_task.add_retry(**retry_config)
            parallel_sections.branch(section_task)

        # T12 generator runs in parallel with sections
        generate_t12 = tasks.LambdaInvoke(
            self,
            "GenerateT12",
            lambda_function=t12_generator,
            output_path="$.Payload",
        )
        generate_t12.add_retry(**retry_config)
        parallel_sections.branch(generate_t12)

        generate_lender_narrative = tasks.LambdaInvoke(
            self,
            "GenerateLenderNarrative",
            lambda_function=lender_narrative_generator,
            output_path="$.Payload",
        )
        generate_lender_narrative.add_retry(**retry_config)
        parallel_sections.branch(generate_lender_narrative)

        parallel_sections.add_catch(notify_error_state, result_path="$.error")

        # --- Step 4: Image Generation ---
        generate_images = tasks.LambdaInvoke(
            self,
            "GenerateImages",
            lambda_function=image_generator,
            output_path="$.Payload",
        )
        generate_images.add_retry(**retry_config)
        parallel_sections.branch(generate_images)

        # --- Step 5: QC Validation ---
        run_qc = tasks.LambdaInvoke(
            self,
            "RunQCValidation",
            lambda_function=qc_validator,
            output_path="$.Payload",
        )
        run_qc.add_retry(**retry_config)
        run_qc.add_catch(notify_error_state, result_path="$.error")

        # --- Step 6: Choice — QC pass or fail ---
        qc_choice = sfn.Choice(self, "QCPassOrFail")

        # --- Step 7: Assembler (on QC pass) ---
        assemble_report = tasks.LambdaInvoke(
            self,
            "AssembleReport",
            lambda_function=assembler,
            output_path="$.Payload",
        )
        assemble_report.add_retry(**retry_config)
        assemble_report.add_catch(notify_error_state, result_path="$.error")

        # --- Step 8: SNS publish with download links ---
        notify_success = tasks.SnsPublish(
            self,
            "NotifySuccess",
            topic=topic,
            message=sfn.TaskInput.from_json_path_at("$"),
            subject="Appraisal Generation Complete",
            result_path=sfn.JsonPath.DISCARD,
        )

        succeed_state = sfn.Succeed(self, "PipelineSucceeded")

        # Wire up the QC choice
        qc_choice.when(
            sfn.Condition.string_equals("$.qc_status", "PASS"),
            assemble_report.next(notify_success).next(succeed_state),
        )
        qc_choice.otherwise(notify_error_state)

        # --- Build the chain ---
        definition = (
            validate_input
            .next(generate_crosswalk)
            .next(parallel_sections)
            .next(run_qc)
            .next(qc_choice)
        )

        # --- State Machine ---
        self.state_machine = sfn.StateMachine(
            self,
            "AppraisalPipelineStateMachine",
            state_machine_name="AppraisalPipelineStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(45),
        )


