#!/usr/bin/env ruby
#
# Retrieves slave status of a MySQL database and dumps in k/v format to stdout
#
# Estimated index usage: 150b per invocation
#
Dir.chdir File.dirname(__FILE__)
require "database"
include Database

# Columns to output
cols = []
cols << "Slave_IO_Running"
cols << "Slave_SQL_Running"
cols << "Last_IO_Errno"
cols << "Last_IO_Error"
cols << "Last_SQL_Errno"
cols << "Last_SQL_Error"
cols << "Seconds_Behind_Master"

print "[#{Time.new}] "
with_connection do |db|
	res = db.query("SHOW SLAVE STATUS")
	res.each_hash { |row| cols.each { |col| print "#{col}=#{row[col]}," if row.has_key?(col) } }
end
print "\n"
