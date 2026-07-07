#!/usr/bin/python

import psycopg2
import csv
import sys
import ConfigParser 
import os
import os.path

if len(sys.argv) == 3:
  profile = sys.argv[2]
elif len(sys.argv) == 2:
  profile = 'default'
else:
  print "syntax: " + sys.argv[0] + " <view_name> [<dbprofile>]"
  sys.exit(1)

def xstr(s):
  if s is None:
    return ''
  return str(s)

def write_csv(columns, data):
  for datum in data:
    datum = [ xstr(value) for value in datum ]
  csvout = csv.writer(sys.stdout, delimiter='|')
  csvout.writerows(data)

def write_kv(columns, data):
  for datum in data:
    line = ''
    i = 0
    for value in datum:
      if len(line) > 0:
        line = line + ' '
      line = line + columns[i] + '="' + xstr(value) + '"'
      i = i + 1
    print line
    
def write_data(columns, data, mode):
  if mode == 'csv':
    write_csv(columns, data)
  elif mode == 'kv':
    write_kv(columns, data)
  else:
    print data

def connect_string(database, host, port, user, password):
  result = "dbname=" + str(database)
  if host != None:
    result = result + " host=" + str(host)
  if port != None:
    result = result + " port=" + str(port)
  if user != None:
    result = result + " user=" + str(user)
  if password != None:
    result = result + " password=" + str(password)
  return result

view = sys.argv[1]
defaultdb = None
dbhost = None
dbport = None
dbuser = None
dbpassword = None
outputmode = None

config = ConfigParser.ConfigParser()

try:
  config_path_default = os.path.join(os.path.dirname(os.path.join(os.getcwd(), __file__)), '../default/postgrestats.conf')
  config_path_local = os.path.join(os.path.dirname(os.path.join(os.getcwd(), __file__)), '../local/postgrestats.conf')
  config.read([config_path_default, config_path_local])
except:
  raise

if config.has_option(profile, 'defaultdb'):
  defaultdb = config.get(profile, 'defaultdb')
  print defaultdb + '\n'
if config.has_option(profile, 'host'):
  dbhost = config.get(profile, 'host')
if config.has_option(profile, 'port'):
  dbport = config.get(profile, 'port')
if config.has_option(profile, 'user'):
  dbuser = config.get(profile, 'user')
  print dbuser
if config.has_option(profile, 'password'):
  dbpassword = config.get(profile, 'password')
if config.has_option(profile, 'output'):
  outputmode = config.get(profile, 'output')

if defaultdb == None:
  defaultdb = 'postgres'
if dbport == None:
  dbport = 5432
if outputmode == None:
  outputmode = 'kv'

if view in [ 'pg_stat_all_tables', 'pg_stat_all_indexes', 'pg_statio_all_tables', 'pg_statio_all_indexes', 'pg_statio_all_sequences' ]:
  databases = []
  try:
    dbc = psycopg2.connect(connect_string(defaultdb, dbhost, dbport, dbuser, dbpassword)) 
    c = dbc.cursor()
    c.execute("""SELECT datname FROM pg_database""")
    databases = c.fetchall()
    dbc.close()
  except:
    pass
  for database in databases:
    try:
      dbc = psycopg2.connect(connect_string(database[0], dbhost, dbport, dbuser, dbpassword))
      c = dbc.cursor()
      c.execute("""SELECT now() as src_time,'""" + database[0] + """' as datname,* FROM """ + view)
      columns = [desc[0] for desc in c.description]
      stats = c.fetchall()
      dbc.close()
      write_data(columns, stats, outputmode)
    except Exception, e:
      print e
      pass
else:
  try:
    dbc = psycopg2.connect(connect_string(defaultdb, dbhost, dbport, dbuser, dbpassword))
    c = dbc.cursor()
    c.execute("""SELECT now() as src_time,* FROM """ + view)
    columns = [desc[0] for desc in c.description]
    stats = c.fetchall()
    dbc.close()
    write_data(columns, stats, outputmode)
  except Exception, e:
    print e
    pass

