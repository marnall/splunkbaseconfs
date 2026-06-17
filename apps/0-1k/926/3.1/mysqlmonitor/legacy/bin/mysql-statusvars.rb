#!/usr/bin/env ruby
#
# Retrieves information from the global_status table of a MySQL database and dumps in k/v pairs to stdout
#
# Estimated index usage: 1kb per invocation
#
Dir.chdir File.dirname(__FILE__)
require "database"
include Database

# Stats to retrieve from the session_status table
stats = []
stats << "Aborted_clients"				# Number of clients which closed without closing the connection properly
stats << "Aborted_connects"				# Number of connections which were unsuccessful
stats << "Com_commit"					# Number of transactions committed
stats << "Com_rollback"					# Number of transactions rolled back
stats << "Com_select"					# Number of select statements executed
stats << "Com_insert"					# Number of insert statements executed
stats << "Com_update"					# Number of update statements executed
stats << "Com_delete"					# Number of delete statements executed
stats << "Connections"					# Total number of connection attempts to the server
stats << "Created_tmp_disk_tables"			# Number of internal temporary tables that were written to disk
stats << "Created_tmp_tables"				# Number of internal temporary tables created (total)
stats << "Handler_read_rnd_next"			# A high number here indicates a lot of table scans being performed
stats << "Innodb_buffer_pool_pages_data"		# The number of pages containing data (dirty or clean)
stats << "Innodb_buffer_pool_pages_dirty"		# Number of dirty pages
stats << "Innodb_buffer_pool_pages_flushed"		# Number of flushed pages
stats << "Innodb_buffer_pool_pages_free"		# Number of free pages
stats << "Innodb_buffer_pool_pages_total"		# Total number of pages
stats << "Innodb_buffer_pool_read_requests"		# The number of logical read requests InnoDB has done
stats << "Innodb_buffer_pool_write_requests"		# The number of logical write requests InnoDB has done
stats << "Innodb_buffer_pool_reads"			# Number of reads from InnoDB not from the buffer pool (i.e. read from disk)
stats << "Innodb_buffer_pool_wait_free"			# Number of times InnoDB had to wait for a page to be flushed before writing to the buffer pool
stats << "Innodb_data_pending_fsyncs"			# The current number of pending fsync() operations
stats << "Innodb_data_pending_reads"			# The current number of pending read operations
stats << "Innodb_data_pending_writes"			# The current number of pending write operations
stats << "Innodb_log_waits"				# The number of times that the log buffer was too small and a wait was required
stats << "Innodb_os_log_pending_fsyncs"			# The number of pending log file fsync() operations
stats << "Innodb_os_log_pending_writes"			# The number of pending log file writes
stats << "Innodb_row_lock_time"				# The total time spent in acquiring row locks, in milliseconds
stats << "Innodb_row_lock_waits"			# The number of times a row lock had to be waited for
stats << "Opened_tables"				# The number of tables opened in total since the server was started
stats << "Qcache_hits"					# Total number of query results served from the query cache
stats << "Qcache_lowmem_prunes"				# Cache entries pruned due to low memory
stats << "Qcache_free_memory"				# Free memory in the query cache
stats << "Select_full_join"				# The number of joins that perform table scans because they do not use indexes
stats << "Select_range_check"				# The number of joins without keys that check for key usage after each row
stats << "Select_scan"					# The number of joins that did a full scan of the first table
stats << "Slow_queries"					# The number of queries that have taken longer than long_query_time
stats << "Sort_merge_passes"				# The number of merge passes that the sort algorithm has had to do
stats << "Sort_scan"					# The number of sorts that were done by scanning the table
stats << "Table_locks_immediate"			# The number of times that a request for a table lock could be granted immediately
stats << "Table_locks_waited"				# The number of times that a request for a table lock could not be granted immediately and a wait was needed	
stats << "Threads_cached"				# The number of threads in the thread cache
stats << "Threads_connected"				# The number of currently open connections
stats << "Threads_created"				# The number of threads created to handle connections since server startup
stats << "Threads_running"				# The number of threads that are not sleeping
stats << "Key_reads"					# Reads from the MyISAM key buffer	
stats << "Key_read_requests"				# Requests to read from the MyISAM key buffer	
stats << "Uptime"					# Server uptime
vars = []
vars << "Max_connections"
vars << "Auto_increment_increment"

print "[#{Time.new}] "
with_connection("INFORMATION_SCHEMA") do |db|
	stats = stats.map { |s| "'#{db.escape_string(s)}'" }
	res = db.query("SELECT VARIABLE_NAME, VARIABLE_VALUE FROM GLOBAL_STATUS WHERE VARIABLE_NAME IN (#{stats.join(",")})")
	res.each_hash { |row| print "#{row["VARIABLE_NAME"]}=#{row["VARIABLE_VALUE"]}," }
	vars = vars.map { |s| "'#{db.escape_string(s)}'" }
	res = db.query("SELECT VARIABLE_NAME, VARIABLE_VALUE FROM GLOBAL_VARIABLES WHERE VARIABLE_NAME IN (#{vars.join(",")})")
	res.each_hash { |row| print "#{row["VARIABLE_NAME"]}=#{row["VARIABLE_VALUE"]}," }
end
print "\n"
