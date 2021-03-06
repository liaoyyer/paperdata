#!/usr/bin/python
# -*- coding: utf-8 -*-
# Create paper tables

from __future__ import print_function
import sys
import json
import glob
from paper.data import dbi as pdbi, data_db as pdb
import add_files
import sqlalchemy.exc

### Script to create paper database
### Instantiates tables

### Author: Immanuel Washington
### Date: 5-06-15

def load_backup(dbi, backup_file=None, table=None):
	'''
	loads backups from json into database

	Args:
		dbi (object): database interface object,
		backup_file (str): name of backup file --defaults to None
		table (str): table name --defaults to None
	'''
	if table is None:
		return None
	if backup_file is None:
		backup_list = sorted(glob.glob('/data4/paper/paperdata_backup/[0-9]*'), reverse=True)
		timestamp = int(backup_list[0].split('/')[-1])
		backup_file = '/data4/paper/paperdata_backup/{timestamp}/{table}_{timestamp}.json'.format(table=table, timestamp=timestamp)

	with dbi.session_scope() as s, open(backup, 'r') as backup_db:
		entry_list = json.load(backup_db)
		for entry_dict in entry_list:
			print(entry_dict.items())
			try:
				dbi.add_entry_dict(s, table, entry_dict)
			except KeyboardInterrupt:
				raise
			except:
				print('Failed to load in entry')

	return None

if __name__ == '__main__':
	dbi = pdbi.DataBaseInterface()
	if len(sys.argv) == 3:
		backup_table = sys.argv[1]
		backup_file = sys.argv[2]
		load_backup(dbi, backup_file, table=backup_table)
	else:
		#load_backup(dbi, table='Observation')
		load_backup(dbi, table='File')
		#load_backup(dbi, table='Feed')
		#load_backup(dbi, table='Log')
		#load_backup(dbi, table='RTPFile')
	add_files.update_obsnums(dbi)
	add_files.connect_observations(dbi)
