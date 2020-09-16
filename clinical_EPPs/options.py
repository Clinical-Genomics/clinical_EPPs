import click

OPTION_PROCESS = click.option(
    "-p", "--process", required=True, help="Lims id for current Process"
)

OPTION_WORKFLOW_ID = click.option("-w", "--workflow", required=True, help="Destination workflow id.")
OPTION_STAGE_ID = click.option("-s", "--stage", required=True, help="Destination stage id.")
OPTION_UDF = click.option(
    "-u", "--udf", required=True, help="UDF that will tell wich artifacts to move."
)
OPTION_INPUT_OUTPUT = click.option(
    "-i",
    "--inputs",
    default=False,
    is_flag=True,
    help="Use this flag if you run the script from a QC step.",
)
OPTION_STEP_NAME = click.option(
    "-n", "--step-name", required=True, multiple=True, help="Name of the step before the rerun step."
)