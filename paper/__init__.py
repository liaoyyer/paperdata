import os
import sys
import paramiko
import logging
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
try:
	import configparser
except:
	import ConfigParser as configparser

def login_ssh(host, username=None):
	'''
	SSH/SFTP connection to remote host

	input: remote host and username
	output: ssh connection to be used to run commands to remote host
	'''
	ssh = paramiko.SSHClient()
	ssh.load_system_host_keys()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	key_filename = os.path.expanduser('~/.ssh/id_rsa')
	try:
		ssh.connect(host, username=username, key_filename=key_filename)
	except:
		try:
			ssh.connect(host, key_filename=key_filename)
		except:
			return None

	return ssh

logger = logging.getLogger('paper')
Base = declarative_base()

class DictFix(object):
	'''
	superclass for all SQLAlchemy Table objects
	allows access to object row dictionary

	output: dict of table attributes
	'''
	def to_dict(self):
		try:
			new_dict = {}
			for column in self.__table__.columns:
				new_dict[column.name] = getattr(self, column.name)
			return new_dict
		except(exc.InvalidRequestError):
			return None

class DataBaseInterface(object):
	def __init__(self, configfile='~/paperdata.cfg'):
		'''
		Connect to the database and initiate a session creator.
		superclass of DBI for paperdata, paperdev, and ganglia databases

		input: configuration file -- defaults to paperdata.cfg, can be changed on initiation
		'''
		if not configfile is None:
			config = configparser.ConfigParser()
			configfile = os.path.expanduser(configfile)
			if os.path.exists(configfile):
				logger.info(' '.join(('loading file', configfile)))
				config.read(configfile)
				try:
					self.dbinfo = config._sections['dbinfo']
				except:
					self.dbinfo = config['dbinfo']
				try:
					self.dbinfo['password'] = self.dbinfo['password'].decode('string-escape')
				except:
					try:
						self.dbinfo['password'] = bytes(self.dbinfo['password'], 'ascii').decode('unicode_escape')
					except:
						self.dbinfo['password'] = self.dbinfo['password']
			else:
				logging.info(' '.join((configfile, 'Not Found')))
		try:
			connect_string = 'mysql://{username}:{password}@{hostip}:{port}/{dbname}'
			self.engine = create_engine(connect_string.format(**self.dbinfo), pool_size=20, max_overflow=40)
		except:
			connect_string = 'mysql+mysqldb://{username}:{password}@{hostip}:{port}/{dbname}'
			self.engine = create_engine(connect_string.format(**self.dbinfo), pool_size=20, max_overflow=40)

		self.Session = sessionmaker(bind=self.engine)

	def create_table(Table):
		'''
		creates a table in the database.
		input: table object
		'''
		Table.__table__.create(bind=self.engine)

	def get_entry(self, s=None, TABLE, unique_value):
		'''
		retrieves any object.
		Errors if there are more than one of the same object in the db. This is bad and should
		never happen

		input: session object(optional), table name, primary key value of row
		output: table object
		'''
		open_sess = False
		if s is None:
			s = self.Session()
			open_sess = True
		table = getattr(sys.modules[__name__], TABLE.title())
		try:
			ENTRY = s.query(table).get(unique_value)
		except:
			return None
		if open_sess:
			s.close()
		return ENTRY

	def set_entry(self, ENTRY, field, new_value):
		'''
		sets the value of any entry
		input: ENTRY object, field to be changed, new value
		'''
		setattr(ENTRY, field, new_value)
		yay = self.add_entry(ENTRY)
		return yay

	def add_entry(self, s=None, ENTRY):
		'''
		adds entry to database and commits
		does not add if duplicate found

		input: session object(optional), table object
		'''
		open_sess = False
		if s is None:
			s = self.Session()
			open_sess = True
		try:
			s.add(ENTRY)
			s.commit()
		except (exc.IntegrityError):
			s.rollback()
			print('Duplicate entry found ... skipping entry')
		if open_sess:
			s.close()
		return None
