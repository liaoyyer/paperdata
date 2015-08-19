#!/flask/bin/python3.4

import psycopg2
import os
import glob
import requests
from datetime import datetime
from app import models
from app.flask_app import db
from app import db_utils
import time

profiling_mark = None

def write_to_log(msg):
	print(msg)

def profile():
	global profiling_mark
	result = datetime.now() - profiling_mark
	profiling_mark = datetime.now()
	return result.total_seconds()

def log_query_time(var_name):
	write_to_log('{var_name} query ran in {profile_time} seconds'.format(var_name=var_name, profile_time=profile())
	return None

def update():
	utc_now = datetime.utcnow().isoformat()

	baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='

	gps_now = int(requests.get(baseUTCToGPSURL + utc_now).text)

	profiling_mark = datetime.now()

	#total hours in SADB
	total_sadb_hours = sum(db_utils.get_query_results(data_source=None, database='sadb', table='observation',
									field_tuples=(('length', '!=', None),), field_sort_tuple=None, output_vars=('length',))) / 3600.0

	log_query_time('total_sadb_hours')

	#total hours in paperdata
	total_paperdata_hours = sum(db_utils.get_query_results(data_source=None, database='paperdata', table='observation',
									field_tuples=(('length', '!=', None),), field_sort_tuple=None, output_vars=('length',))) / 3600.0


	log_query_time('total_paperdata_hours')

	#total that has data in observations
	sadb_obs_rows = db_utils.get_query_results(data_source=None, database='sadb', table='observation',
												field_tuples=(('files', '!=', None),), field_sort_tuple=(('obsnum', 'asc'),),
												output_vars=('length', 'obsnum', 'files'))

	#make tuple of length and file_count for sadb_obs_rows
	sadb_obs_rows = tuple((length, obsnum, len(files)) for length, obsnum, files in sadb_obs_rows)

	log_query_time('sadb_obs_rows')

	paperdata_files_rows = db_utils.get_query_results(data_source=None, database='paperdata', table='file',
												field_tuples=None, field_sort_tuple=(('obsnum', 'asc'),),
												output_vars=('obsnum',))

	log_query_time('paperdata_files_rows')

	write_to_log('preparing for the giant iteration where sadb_obs_rows = {sadb_count} and paperdata_files_rows = {paper_count}'\
					.format(len(sadb_obs_rows), paper_count=len(paperdata_files_rows)))

	total_data_hours = 0
	no_more_paperdata_files = False
	match = 0
	no_match = 0
	weird = 0
	not_weird = 0

	#get all the unique observations
	sadb_unique_obs = {sadb_obsnum for _, sadb_obsnum, _ in sadb_obs_rows if sadb_obsnum}
	paperdata_unique_obs = {paper_obsnum for paper_obsnum in paperdata_files_rows if paper_obsnum}
	shared_obs = sadb_unique_obs & paperdata_unique_obs

	#count every file that has a 'shared_obsnum'
	num_paperdata_files = sum(1 for paper_obsnum in paperdata_files_rows if paper_obsnum in shared_obs and paper_obsnum is not None)
	match = num_paperdata_files
	no_match = sum(1 for paper_obsnum in paperdata_files_rows if paper_obsnum is None)

	for length, sadb_obsnum, sadb_files in sadb_obs_rows:
		num_sadb_files = len(sadb_files)

		if num_paperdata_files > num_sadb_files:
			print('what the hell! More files in paperdata! obsid = {obsnum} num_sadb_files = {sadb_num} num_paperdata_files = {paper_num}'\
							.format(obsnum=sadb_obsnum, sadb_num=num_sadb_files, paper_num=num_paperdata_files))
			weird += 1
		else:
			not_weird += 1

		total_data_hours += (float(num_paperdata_files) / float(num_sadb_files)) * length / 3600.0

	print('match = {match} no_match = {no_match}'.format(match=match, no_match=no_match))
	print('weird = {weird} not_weird = {not_weird}'.format(weird=weird, not_weird=not_weird))

	write_to_log('The giant iteration ran in {profile_time} seconds'.format(profile_time=profile()))

	#amount of hours back to check
	time_span = 4
	time_secs = time_span * 3600.0

	#data transfer rate XXXX need to add table or check fields to generate
	#total filesize from rtp_files that have been transferred in the past 4 hours / 4 hours
	data_transfer_total = sum(db_utils.get_query_results(data_source=None, database='paperdata', table='rtp_file',
													field_tuples=(('timestamp', '>=', time.time() - time_secs), ('transferred', '==', True)),
													field_sort_tuple=None, output_vars=('filesize',)))
	#in MB per second
	data_transfer_rate = data_transfer_total / time_secs

	log_query_time('data_transfer_rate')

	write_to_log('\nTotal Scheduled Hours = {time}'.format(time=round(total_sadb_hours), 6))
	write_to_log('Total Observed Hours = {time}'.format(time=round(total_paperdata_hours), 6))
	write_to_log('Total Hours that have data = {time}'.format(time=round(total_data_hours), 6))
	write_to_log('Data transfer rate = {time}'.format(time=round(data_transfer_rate), 6))

	graph_datum = getattr(models, 'Data_Amount')(hours_scheduled=total_sadb_hours, hours_observed=total_paperdata_hours,
												hours_with_data=total_data_hours, data_transfer_rate=data_transfer_rate)

	db.session.add(graph_datum)
	db.session.commit()

if __name__ == '__main__':

	write_to_log('\n-- {timestamp} -- \n' .format(timestamp=datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z')))

	# Establish the database connection
	profiling_mark = datetime.now()

	try:
		update()
	except:
		except Exception as e:	
			write_to_log('Cannot connect to some database - {e}'.format(e=e))
			exit(1)