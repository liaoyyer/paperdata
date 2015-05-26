#!/usr/bin/python
# -*- coding: utf-8 -*-
# Create paperdata table

import paperdata_dbi
import sys

### Script to create paperdata database
### Instantiates tables

### Author: Immanuel Washington
### Date: 5-06-15

def create_table(table=None):
	dbi = paperdata_dbi.DataBaseInterface()
	if table is None:
		sys.exit()
	#table = dbi.Final_Product
	dbi.create_table(table)

if __name__ == '__main__':
	create_table()
