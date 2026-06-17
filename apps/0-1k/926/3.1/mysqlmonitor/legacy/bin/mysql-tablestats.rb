#!/usr/bin/env ruby
#
# Retrieves information from the tables table of a MySQL database and dumps in multi k/v format to stdout
#
# Estimated index usage: 50b per table in the schema each invocation
#
Dir.chdir File.dirname(__FILE__)
require "database"
include Database

# Columns to retrive for each table
cols = []
cols << "t.TABLE_SCHEMA"
cols << "t.TABLE_NAME"
cols << "t.DATA_LENGTH"
cols << "t.INDEX_LENGTH"
cols << "t.DATA_FREE"
cols << "t.AUTO_INCREMENT"
cols << "c.DATA_TYPE"
cols << "c.COLUMN_TYPE"
cols << "c.NUMERIC_PRECISION"
cols << "c.NUMERIC_SCALE"

nicecols = cols.map { |col| col.gsub(/[tc]\./,"") }

puts nicecols.join("\t")
with_connection("INFORMATION_SCHEMA") do |db|
	res = db.query("SELECT #{cols.join(",")} FROM TABLES t " +
					"LEFT JOIN COLUMNS c ON " +
					"t.TABLE_NAME = c.TABLE_NAME AND " +
					"t.TABLE_SCHEMA = c.TABLE_SCHEMA AND " +
					"c.COLUMN_KEY = 'PRI' AND " +
					"c.EXTRA = 'auto_increment' " +
					"WHERE t.TABLE_SCHEMA NOT IN ('mysql', 'information_schema')")
	res.each { |row| puts row.map { |val| val.nil? ? 0 : val }.join("\t") }
end
