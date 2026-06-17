#
# Mixin for common functions relating to finding and using a database connection
#
module Database
	# Modify for location of hosts file on system
	hosts_file = "/splunk/splunk/etc/apps/mysql/hosts.yaml"

	require "mysql"
	require "yaml"

	unless ARGV.length == 1 then
		puts "Usage: #{File.basename($0)} <host record>, where <host record> is the name of a MySQL host in #{hosts_file}"
		exit(1)
	end

	begin 
		hosts = YAML.load_file(hosts_file)
		host = hosts["Databases"][ARGV[0]]
		@@hostname = host["host"]
		@@username = host["username"]
		@@password = host["password"]
	rescue Exception => e
		puts "Error: unable load or parse #{hosts_file}"
		exit(1)
	end

	if @@hostname.nil? || @@hostname.empty? || @@username.nil? || @@username.empty? || @@password.nil? then
		puts "Error: No valid definition found for provided host."
		exit(1)
	end

	def with_connection(schema = "")
		begin
			db = Mysql.real_connect(@@hostname, @@username, @@password, schema)
			yield db
		rescue Mysql::Error => e
			puts "Error: #{e.errno} - #{e.error}"
		ensure
			db.close if db
		end
	end
end 
