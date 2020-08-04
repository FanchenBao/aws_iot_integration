# coding: utf-8

from shutil import copy, make_archive, rmtree

import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from script_config import CLIENT, ScriptSettings
from typing import Dict

# set up logger
logger = logging.getLogger()
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# CONSTANT
ROOT_DIR: Path = Path(__file__).parent.parent.absolute()
TEMP: Path = ROOT_DIR.joinpath('temp')
ZIP_NAME: str = 'function.zip'


def clean_up() -> None:
    """Remove the temp folder and function zip file."""
    rmtree(TEMP)
    Path.unlink(ROOT_DIR.joinpath(ZIP_NAME))


def get_argument_parser() -> ArgumentParser:  # pragma no cover
    """Set up a parser to parse command line arguments.

    :return: A fresh, unused, ArgumentParser.
    """
    parser = ArgumentParser(
        description=(
            'Update lambda code and configuration for AWS Lambda '
            'This script can ONLY be '
            'used when env is set to test, because the dev and prod '
            'environment must be published from the test version, not '
            'directly updated from the code base. '
            'Usage: env=test python3 '
            'update_lambda_code.py --func_name {some_name} '
            '--description {some_description}.'
        ),
    )
    parser.add_argument(
        '--func_name',
        dest='func_name',
        type=str,
        required=True,
        help=(
            'REQUIRED. The name of the lambda function as shown on AWS.'
        ),
    )
    parser.add_argument(
        '--description',
        dest='description',
        type=str,
        required=True,
        help=(
            'REQUIRED. The description of the lambda function.'
        ),
    )
    return parser


def exception_handler(error_msg: str) -> None:
    """Log exception and error message, and clean up the procedure.

    :param error_msg: The error message to log.
    """
    logger.exception(error_msg)
    logger.error(f'\033[30;41mUpdate {args.func_name} FAILED!\033[0m')
    clean_up()


def prep_files(func_name: str) -> None:
    """Prepare a temp folder to hold all the files to be uploaded to Lambda.

    :param func_name: Name of the lambda function as shown on AWS Lambda.
    """
    # prepare temp folder
    if Path.exists(TEMP):  # clean up any previous upload
        rmtree(TEMP)
    Path.mkdir(TEMP)
    # copy files to temp
    copy(
        str(
            ROOT_DIR.joinpath(
                f'src/lambda_func/{func_name}/lambda_function.py',
            ),
        ),
        str(TEMP),
    )
    # create zip file
    make_archive(ZIP_NAME.split('.')[0], 'zip', str(TEMP))


def upload_code(args, env_variables: Dict) -> None:
    """Upload lambda code base (as a zip file) to its associated AWS Lambda.

    :param args: Parsed command line arguments.
    :param env_variables: Environment variables for the given lambda function
    """
    with open(ZIP_NAME, 'rb') as f_obj:  # upload
        zip_bytes = f_obj.read()
        try:
            resp1 = CLIENT.update_function_code(
                FunctionName=args.func_name,
                ZipFile=zip_bytes,
            )
        except Exception:
            exception_handler('Update lambda function code FAILED.')
            sys.exit(1)
        logger.info(resp1)

    try:  # config
        resp2 = CLIENT.update_function_configuration(
            FunctionName=args.func_name,
            Description=args.description,
            Environment={
                'Variables': env_variables,
            },
            Timeout=70,  # 70 seconds
        )
    except Exception:
        exception_handler('Update lambda function configuration FAILED.')
        sys.exit(1)
    logger.info(resp2)


if __name__ == '__main__':
    # Parse command line arguments
    parser: ArgumentParser = get_argument_parser()
    args = parser.parse_args()
    script_settings = ScriptSettings(args.func_name)

    logger.info(f'\033[30;43mUpdating code in {args.func_name}...\033[0m')

    if script_settings.env != 'test':
        logger.error('Must use this script when "env=test"!')
        sys.exit(1)
    prep_files(args.func_name)
    upload_code(args, script_settings.env_variables)
    clean_up()
    logger.info(f'\033[30;42mUpdate {args.func_name} SUCCESS!\033[0m')
