from sqlalchemy import Table, Column, String, Integer, ForeignKey, Float, func, Boolean, DateTime, Enum, BigInteger, Numeric, Text
from sqlalchemy import event, DDL, UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import os, sys, logging
import paper as ppdata

Base = ppdata.Base
logger = logging.getLogger('ganglia')

#############
#
#   The basic definition of our database
#
#############

class Filesystem(Base, ppdata.DictFix):
	__tablename__ = 'filesystem'
	__table_args__ = (PrimaryKeyConstraint('host', 'system', 'timestamp', name='host_system_time'),)
	host = Column(String(100)) #folio
	system = Column(String(100)) #/data4
	total_space = Column(BigInteger)
	used_space = Column(BigInteger)
	free_space = Column(BigInteger)
	percent_space = Column(Numeric(4,1))
	timestamp = Column(BigInteger) #seconds since 1970

class Monitor(Base, ppdata.DictFix):
	__tablename__ = 'monitor'
	host = Column(String(100))
	path = Column(String(100))
	filename = Column(String(100))
	full_path = Column(String(200))
	status = Column(String(100))
	full_stats = Column(String(200), primary_key=True)
	del_time = Column(BigInteger)
	time_start = Column(BigInteger)
	time_end = Column(BigInteger)
	timestamp = Column(BigInteger)

class Ram(Base, ppdata.DictFix):
	__tablename__ = 'ram'
	__table_args__ = (PrimaryKeyConstraint('host', 'timestamp', name='host_time'),)
	host = Column(String(100))
	total = Column(BigInteger)
	used = Column(BigInteger)
	free = Column(BigInteger)
	shared = Column(BigInteger)
	buffers = Column(BigInteger)
	cached = Column(BigInteger)
	bc_used = Column(BigInteger)
	bc_free = Column(BigInteger)
	swap_total = Column(BigInteger)
	swap_used = Column(BigInteger)
	swap_free = Column(BigInteger)
	timestamp = Column(BigInteger)

class Iostat(Base, ppdata.DictFix):
	__tablename__ = 'iostat'
	__table_args__ = (PrimaryKeyConstraint('host', 'timestamp', name='host_time'),)
	host = Column(String(100))
	device = Column(String(100))
	tps = Column(Numeric(7,2))
	read_s = Column(Numeric(7,2))
	write_s = Column(Numeric(7,2))
	bl_reads = Column(BigInteger)
	bl_writes = Column(BigInteger)
	timestamp = Column(BigInteger)

class Cpu(Base, ppdata.DictFix):
	__tablename__ = 'cpu'
	__table_args__ = (PrimaryKeyConstraint('host', 'timestamp', name='host_time'),)
	host = Column(String(100))
	cpu = Column(Integer)
	user_perc = Column(Numeric(5,2))
	sys_perc = Column(Numeric(5,2))
	iowait_perc = Column(Numeric(5,2))
	idle_perc = Column(Numeric(5,2))
	intr_s = Column(Integer)
	timestamp = Column(BigInteger)

class DataBaseInterface(ppdata.DataBaseInterface):
	def __init__(self, configfile='~/ganglia.cfg'):
		'''
		Unique Interface for the ganglia database

		Args:
			configfile (str): ganglia database configuration file --defaults to ~/ganglia.cfg
		'''
		super(ppdata.DataBaseInterface, self).__init__(configfile=configfile)
		self.main_fields = ('filesystem', 'monitor', 'ram', 'iostat', 'cpu')

	def create_db(self):
		'''
		creates the tables in the database.
		'''
		Base.metadata.bind = self.engine
		table_name = getattr(sys.modules[__name__], 'Monitor')
		table = getattr(table_name, '__table__')
		insert_update_trigger = DDL('''CREATE TRIGGER insert_update_trigger \
										after INSERT or UPDATE on Monitor \
										FOR EACH ROW \
										SET NEW.full_path = concat(NEW.host, ':', NEW.path, '/', NEW.filename)''')
		event.listen(table, 'after_create', insert_update_trigger)
		insert_update_trigger_2 = DDL('''CREATE TRIGGER insert_update_trigger_2 \
										after INSERT or UPDATE on Monitor \
										FOR EACH ROW \
										SET NEW.full_stats = concat(NEW.full_path, '+', NEW.status)''')
		event.listen(table, 'after_create', insert_update_trigger_2)
		Base.metadata.create_all()

	def drop_db(self, Base):
		'''
		drops tables in the database

		Args:
			object: Base database object
		'''
		super(ppdata.DataBaseInterface, self).drop_db(Base)

	def add_entry_dict(self, s, TABLE, entry_dict):
		'''
		create a new entry.

		Args:
			s (object): session object
			TABLE (str): table name
			entry_dict (dict): dict of attributes for object
		'''
		super(ppdata.DataBaseInterface, self).add_entry_dict(__name__, s, TABLE, entry_dict)

	def get_entry(self, s, TABLE, unique_value):
		'''
		retrieves any object.
		Errors if there are more than one of the same object in the db. This is bad and should
		never happen

		Args:
			s (object): session object
			TABLE (str): table name
			unique_value (int/float/str): primary key value of row

		Returns:
			object: table object
		'''
		super(ppdata.DataBaseInterface, self).get_entry(__name__, s, TABLE, unique_value)
