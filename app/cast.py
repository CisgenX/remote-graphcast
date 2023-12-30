import os
import json
import boto3
from cdsutils import save_cds_rcfile
import logging
logging.basicConfig(level=logging.INFO)
from ai_models_graphcast.model import GraphcastModel
from datetime import datetime
from botocore.exceptions import NoCredentialsError
from constants import *

def validate_date_list(date_list):
	# make sure all data is available
	# make sure start times start at 0600 or 1800
	pass

def parse_date_list(date_list):
	date_list = json.loads(date_list)

	for start in date_list:
		start['start_time'] = datetime.strptime(start['start_time'], "%Y%m%d%H")

	return date_list

def cast_all(
		aws_access_key_id, 
		aws_secret_access_key, 
		bucket_name,
		cds_url,
		cds_key,
		date_list,	
		cast_id
	):

	save_cds_rcfile(cds_key=cds_key, cds_url=cds_url)
	print('cds credentials file created')
	date_list = parse_date_list(date_list)
	s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
	print('s3 client set up')

	dir_path = f'/tmp/{cast_id}/'
	for start_point in date_list:
		date = start_point['start_time'].strftime("%Y%m%d")
		time = int(start_point['start_time'].strftime("%H"))
		dt = datetime.now().strftime("%Y%m%d%H")
		hours_to_forcast = start_point['hours_to_forcast']

		gc = GraphcastModel(
			input="cds", 
			output="file", 
			download_assets=True, 
			path=f'{dir_path}{dt}-output', 
			metadata={}, 
			model_args={}, 
			assets_sub_directory=dir_path,
			assets=dir_path,
			date=date, # just the date part 
			time=time, # just the time part
			staging_dates = None, # alternatively, a list of dates, as opposed to the single date/time
			debug=True,
			lead_time=hours_to_forcast, # the number of hours to forcast 
			only_gpu=True,
			archive_requests=f"{dir_path}archive",
			hindcast_reference_year=None,
		)

		gc.run()

		print(f"forcast complete for {start_point['start_time']}")

	print(f"all forcasts complete for {cast_id}, uploading to s3")

	for subdir, _, files in os.walk(dir_path):
		for file in files:
			full_path = os.path.join(subdir, file)
			with open(full_path, 'rb') as data:
				try:
					s3_client.upload_fileobj(data, bucket_name, full_path[len(dir_path)+1:])
					print(f"File {file} uploaded successfully")
				except NoCredentialsError:
					print("Credentials not available")

	print(f"upload complete for {cast_id}")

if __name__ == "__main__":

	required_variables = [
		AWS_ACCESS_KEY_ID,
		AWS_SECRET_ACCESS_KEY,
		AWS_BUCKET,
		AWS_REGION,
		CDS_URL,
		CDS_KEY,
		DATE_LIST,
		CAST_ID
	]

	print('Checking environment variables are set')
	for var in required_variables:
		if var not in os.environ:
			raise Exception(f"Missing required environment variable {var}")
		else:
			print(f"{var}: {os.environ[var]}")


	cast_all(
		aws_access_key_id=os.environ[AWS_ACCESS_KEY_ID], 
		aws_secret_access_key=os.environ[AWS_SECRET_ACCESS_KEY], 
		bucket_name=os.environ[AWS_BUCKET],
		cds_url=os.environ[CDS_URL],
		cds_key=os.environ[CDS_KEY],
		date_list=os.environ[DATE_LIST],
		cast_id=os.environ[CAST_ID],
	)