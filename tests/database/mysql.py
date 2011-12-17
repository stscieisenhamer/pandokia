import os

import pandokia.db_mysqldb as dbx

f = open("access_mysql")
hostname,username,password,dbname = f.readline().strip().split(';')

dbx = dbx.PandokiaDB( {
    'host' : hostname, 
    'user' : username, 
    'passwd' : password, 
    'db' : dbname   
    } )

dbx.execute('drop table if exists test_table')

import shared
shared.dbx = dbx

from shared import *

import csv_t
csv_t.dbx = dbx

from csv_t import *
