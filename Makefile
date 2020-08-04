# path to virtualenv
VENV=/home/pi/.local/share/virtualenvs/aws_iot_integration-p2VuOyv1
PYTHON3=$(VENV)/bin/python3

update_remote_control_api:
	python3 scripts/update_lambda_code.py --func_name remote_control_api --description 'Handle REST API for remote command-and-response with a specific AWS IoT thing.'
