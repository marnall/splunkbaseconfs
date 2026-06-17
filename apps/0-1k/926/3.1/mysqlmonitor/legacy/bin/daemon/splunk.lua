local tokenizer = require("proxy.tokenizer")
local auto_config = require("proxy.auto-config")
local commands = require("proxy.commands")
 
math.randomseed(os.time())

-- Config
if not proxy.global.config.splunk then 
	proxy.global.config.splunk = {
		-- This percent of queries will be Splunk'd, default to 100% (all queries)
		samplerate = 100,
		
		-- This many seconds of delay on the TCP socket  will result in Splunk
		-- being regarded as failed, and all logging to Splunk will be abandoned
		-- until a manual correction is issued
		timeout = 1.0,

		-- Will auto switch to 0 if Splunk goes away for timeout seconds
		-- Can be manually switched with: "PROXY SET GLOBAL splunk.splunk_active = [0|1]"
		active = 1,

		-- Splunk host as a string
		host = "127.0.0.1",

		-- Splunk TCP port as a number
		port = 9332
	}
end

function read_query(packet)
	local cmd = commands.parse(packet)

	local r = auto_config.handle(cmd)
	if r then return r end
	
	if proxy.global.config.splunk.active == 0 or proxy.global.config.splunk.samplerate < 1 then
		return
	elseif cmd.type == proxy.COM_QUERY and
		(proxy.global.config.splunk.samplerate >= 100 or math.random(0,100) < proxy.global.config.splunk.samplerate) then
		query = packet:sub(2)
		proxy.queries:append(1, packet)
		return proxy.PROXY_SEND_QUERY
	end
end

function read_query_result(inj)
	local cmd = commands.parse(inj.query)

	if cmd.type == proxy.COM_QUERY then
		local tokens = tokenizer.tokenize(inj.query)
		query = tokenizer.normalize(tokens)
		print("[" .. os.date("%Y-%m-%d %X") .. "] " .. "query=\"" .. trim(query) .. "\",query_time=" .. inj.query_time .. ",response_time=" .. inj.response_time)
	end
end

-- Remove 3 leading and 2 trailing chars,
-- the extra space that the tokenizer seems to insert when normalizing
function trim(s)
	return s:sub(3, -2)
end
