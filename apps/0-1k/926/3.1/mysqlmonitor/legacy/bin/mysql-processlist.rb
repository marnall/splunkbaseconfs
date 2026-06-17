#!/usr/bin/env ruby
#
# Retrieves information from the processlist table of a MySQL database and dumps in multi k/v format to stdout
#
# Estimated index usage: 100b per running process per invocation
#
Dir.chdir File.dirname(__FILE__)
require "database"
include Database

cols = []
cols << "USER"
cols << "HOST"
cols << "DB"
cols << "COMMAND"
cols << "TIME"
cols << "STATE"

puts cols.join("\t")
with_connection("INFORMATION_SCHEMA") do |db|
	res = db.query("SELECT #{cols.join(",")} FROM PROCESSLIST")
	res.each { |row| puts row.join("\t") }
end
