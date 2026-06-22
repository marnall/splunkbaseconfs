// __author__ = 'Michael Uschmann / MuS'
// __date__ = 'Copyright $Oct 25, 2018 11:00:00 AM$'
// __version__ = '0.1.1'

// get config arguments
var remote_user = process.argv[2],
    locale = 'en-GB',
    proxy_port = process.argv[3],
    connect_from = process.argv[4],
    splunk_port = '8000',
    splunk_host = process.env.SPLUNK_WEB_HOST || '127.0.0.1',
    request_timeout_ms = parseInt(process.env.USERFUL_PROXY_TIMEOUT_MS || '30000', 10),
    splunk_admin_user = process.env.SPLUNK_ADMIN_USER || 'admin',
    splunk_admin_pass = process.env.SPLUNK_ADMIN_PASS || 'Sh37wubatu.';

if (isNaN(request_timeout_ms) || request_timeout_ms < 1000) {
  request_timeout_ms = 30000;
}

var http = require('http'),
    https = require('https'),
    url = require('url'),
    querystring = require('querystring'),
    httpProxy = require('http-proxy');

if (!/^\d+$/.test(String(proxy_port || ''))) {
  proxy_port = '9902';
}

if (!remote_user) {
  remote_user = 'admin';
}

// Create a proxy server with custom application logic
var proxy = httpProxy.createProxyServer({
    target: 'http://' + splunk_host + ':' + splunk_port,
    timeout: request_timeout_ms,
    proxyTimeout: request_timeout_ms * 2,
    xfwd: true
});

var shutting_down = false;

function nowEpoch() {
  return (new Date).getTime();
}

function safeHost(req) {
  if (req && req.headers && req.headers.host) {
    return req.headers.host;
  }
  return '';
}

function normalizeClientIp(value) {
  if (!value) {
    return '';
  }
  var ip = String(value).trim();
  if (ip.indexOf(',') !== -1) {
    ip = ip.split(',')[0].trim();
  }
  ip = ip.replace(/^::ffff:/, '');
  ip = ip.replace(/^::/, '');
  if (ip === '1') {
    return '127.0.0.1';
  }
  if (ip === 'localhost') {
    return '127.0.0.1';
  }
  return ip;
}

function getRemoteAddress(req) {
  return (req && req.socket && req.socket.remoteAddress) ||
    (req && req.connection && req.connection.remoteAddress) ||
    '';
}

function isIPv4(ip) {
  if (!/^\d+\.\d+\.\d+\.\d+$/.test(ip)) {
    return false;
  }
  var parts = ip.split('.');
  for (var i = 0; i < parts.length; i++) {
    var value = parseInt(parts[i], 10);
    if (isNaN(value) || value < 0 || value > 255) {
      return false;
    }
  }
  return true;
}

function ipToInt(ip) {
  var parts = ip.split('.').map(function(part) {
    return parseInt(part, 10);
  });
  return (((parts[0] << 24) >>> 0) +
    ((parts[1] << 16) >>> 0) +
    ((parts[2] << 8) >>> 0) +
    (parts[3] >>> 0)) >>> 0;
}

function isCidrMatch(ip, cidr) {
  if (!isIPv4(ip)) {
    return false;
  }
  var cidrParts = String(cidr || '').split('/');
  if (cidrParts.length !== 2 || !isIPv4(cidrParts[0])) {
    return false;
  }

  var prefix = parseInt(cidrParts[1], 10);
  if (isNaN(prefix) || prefix < 0 || prefix > 32) {
    return false;
  }

  var mask = prefix === 0 ? 0 : ((0xffffffff << (32 - prefix)) >>> 0);
  var ipInt = ipToInt(ip);
  var netInt = ipToInt(cidrParts[0]);
  return (ipInt & mask) === (netInt & mask);
}

function isAllowedClient(clientIp) {
  var allowAll = (
    connect_from === '*' ||
    connect_from === '0.0.0.0' ||
    connect_from === '0.0.0.0/0'
  );
  if (allowAll) {
    return true;
  }

  var allowedList = (connect_from || '')
    .split(',')
    .map(function(ip) { return ip.trim(); })
    .filter(function(ip) { return ip; });

  for (var i = 0; i < allowedList.length; i++) {
    var allowed = normalizeClientIp(allowedList[i]);
    if (!allowed) {
      continue;
    }
    if (allowed === clientIp) {
      return true;
    }
    if (allowed.indexOf('/') !== -1 && isCidrMatch(clientIp, allowed)) {
      return true;
    }
  }

  return false;
}

function extractClientContext(req) {
  var remoteAddress = getRemoteAddress(req);
  var clientIp = normalizeClientIp(remoteAddress);
  return {
    clientIp: clientIp,
    host: safeHost(req),
    reqUrl: (req && req.url) ? req.url : ''
  };
}

function base64EncodeAscii(input) {
  var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  var str = String(input);
  var output = '';
  var i = 0;
  while (i < str.length) {
    var chr1 = str.charCodeAt(i++);
    var chr2 = str.charCodeAt(i++);
    var chr3 = str.charCodeAt(i++);
    var enc1 = chr1 >> 2;
    var enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
    var enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
    var enc4 = chr3 & 63;
    if (isNaN(chr2)) {
      enc3 = 64;
      enc4 = 64;
    } else if (isNaN(chr3)) {
      enc4 = 64;
    }
    output += chars.charAt(enc1);
    output += chars.charAt(enc2);
    output += enc3 === 64 ? '=' : chars.charAt(enc3);
    output += enc4 === 64 ? '=' : chars.charAt(enc4);
  }
  return output;
}

function proxyEmbeds(req, res) {
  var parsed = url.parse(req.url, true);
  var query = parsed.query || {};
  if (!query.output_mode) {
    query.output_mode = 'json';
  }
  if (!query.embed_host && req.headers && req.headers.host) {
    query.embed_host = req.headers.host.split(':')[0];
  }
  var path = '/services/userful/embeds?' + querystring.stringify(query);
  var auth = null;
  try {
    var user = (splunk_admin_user || '').toString();
    var pass = (splunk_admin_pass || '').toString();
    if (!user || !pass) {
      throw new Error('Missing splunk admin credentials');
    }
    auth = base64EncodeAscii(user + ':' + pass);
  } catch (err) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: String(err), message: 'Invalid splunk admin credentials' }));
    return;
  }

  var options = {
    hostname: splunk_host,
    port: 8089,
    method: 'GET',
    path: path,
    headers: {
      'Authorization': 'Basic ' + auth,
      'Accept': 'application/json'
    },
    timeout: request_timeout_ms,
    rejectUnauthorized: false
  };

  var splunkReq = https.request(options, function(splunkRes) {
    res.writeHead(splunkRes.statusCode || 500, {
      'Content-Type': splunkRes.headers['content-type'] || 'application/json'
    });
    splunkRes.pipe(res);
  });

  splunkReq.on('error', function(err) {
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: String(err), message: 'Failed to reach splunkd' }));
      return;
    }
    try {
      res.end();
    } catch (endErr) {}
  });

  splunkReq.on('timeout', function() {
    splunkReq.destroy();
    if (!res.headersSent) {
      res.writeHead(504, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ message: 'Timeout reaching splunkd' }));
    }
  });

  splunkReq.end();
}

// Modify the header to allow the user to login
proxy.on('proxyReq', function(proxyReq, req, res, options) {
  proxyReq.setHeader('Accept-Language', locale);
  proxyReq.setHeader('REMOTE_USER', remote_user);
  // also send the canonical hyphenated form in case remoteUserMatchExact is enforced
  proxyReq.setHeader('Remote-User', remote_user);
});

proxy.on('proxyReqWs', function(proxyReq, req, socket, options, head) {
  proxyReq.setHeader('Accept-Language', locale);
  proxyReq.setHeader('REMOTE_USER', remote_user);
  proxyReq.setHeader('Remote-User', remote_user);
});

// Keep the proxy process alive when Splunk Web is temporarily unavailable.
// Without this handler, http-proxy emits an error event that crashes Node.
proxy.on('error', function(err, req, res) {
  var epoch = nowEpoch();
  var req_url = (req && req.url) ? req.url : '';
  var err_code = (err && err.code) ? String(err.code) : '';
  var status_code = (err_code === 'ECONNREFUSED' || err_code === 'ETIMEDOUT') ? 503 : 502;
  console.log(
    "_time=\"" + epoch + "\" level=\"error\" proxy_port=\"" + proxy_port +
    "\" message=\"Upstream Splunk Web unavailable\" url=\"" + req_url +
    "\" error=\"" + String(err) + "\""
  );

  if (!res || typeof res.writeHead !== 'function') {
    return;
  }
  if (res.headersSent) {
    try {
      res.end();
    } catch (endErr) {}
    return;
  }
  try {
    res.writeHead(status_code, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        error: String(err),
        message: 'Failed to reach Splunk Web upstream'
      })
    );
  } catch (writeErr) {}
});

var server = http.createServer(function(req, res) {
  req.setTimeout(request_timeout_ms, function() {
    if (res && !res.headersSent) {
      res.writeHead(504, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ message: 'Request timed out in Userful proxy' }));
    }
    try {
      req.destroy();
    } catch (destroyErr) {}
  });

  // allow relaxed access; support wildcard and comma-separated allow list
  var epoch = nowEpoch();
  var context = extractClientContext(req);
  var client_ip = context.clientIp;
  var allowed = isAllowedClient(client_ip);
  if (!allowed) {
     console.log("_time=\"" + epoch + "\" level=\"warn\" clientIp=\"" + client_ip + "\" proxy=\"" + context.host + "\" message=\"Client IP blocked by allow list\" url=\"" + context.reqUrl + "\"");
     res.writeHead(403);
     res.end();
     return;
  }

  if (req.method === 'GET' && req.url === '/_userful/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'ok',
      port: proxy_port,
      upstream: splunk_host + ':' + splunk_port
    }));
    return;
  }

  if (req.method === 'GET' && req.url.indexOf('/services/userful/embeds') !== -1) {
     proxyEmbeds(req, res);
     return;
  }

  // If the environment already enforces SSO at the reverse proxy,
  // do not block any methods here. We rely on IP allowlist + Splunk auth.

  // allow connection and proxy it to Splunk
  console.log("_time=\"" + epoch + "\" user=\"" + remote_user + "\" clientIp=\"" + client_ip + "\" proxy=\"" + context.host + "\" url=\"" + context.reqUrl + "\"" );
  proxy.web(req, res);
});

server.on('upgrade', function(req, socket, head) {
  var epoch = nowEpoch();
  var context = extractClientContext(req);
  if (!isAllowedClient(context.clientIp)) {
    console.log("_time=\"" + epoch + "\" level=\"warn\" clientIp=\"" + context.clientIp + "\" proxy=\"" + context.host + "\" message=\"Websocket client blocked by allow list\" url=\"" + context.reqUrl + "\"");
    try {
      socket.destroy();
    } catch (socketErr) {}
    return;
  }
  proxy.ws(req, socket, head);
});

if (typeof server.keepAliveTimeout !== 'undefined') {
  server.keepAliveTimeout = request_timeout_ms;
}

if (typeof server.headersTimeout !== 'undefined') {
  server.headersTimeout = request_timeout_ms + 5000;
}

var start_epoch = nowEpoch();
console.log("_time=" + start_epoch + " message=\"Starting Dashboard proxy on port " + proxy_port + "\"")
server.listen(proxy_port);

server.on('clientError', function(err, socket) {
  var epoch = nowEpoch();
  console.log("_time=\"" + epoch + "\" level=\"warn\" message=\"Client socket error\" error=\"" + String(err) + "\"");
  if (socket && socket.writable) {
    try {
      socket.end('HTTP/1.1 400 Bad Request\\r\\n\\r\\n');
    } catch (socketErr) {}
  }
});

server.on('error', function(err) {
  var epoch = nowEpoch();
  console.log("_time=\"" + epoch + "\" level=\"error\" message=\"Userful proxy server error\" error=\"" + String(err) + "\"");
});

function gracefulShutdown(signalName) {
  if (shutting_down) {
    return;
  }
  shutting_down = true;
  var epoch = nowEpoch();
  console.log("_time=\"" + epoch + "\" level=\"info\" message=\"Received " + signalName + ", shutting down proxy\" port=\"" + proxy_port + "\"");
  try {
    server.close(function() {
      process.exit(0);
    });
  } catch (err) {
    process.exit(0);
  }

  setTimeout(function() {
    process.exit(0);
  }, 5000).unref();
}

process.on('SIGTERM', function() {
  gracefulShutdown('SIGTERM');
});

process.on('SIGINT', function() {
  gracefulShutdown('SIGINT');
});

process.on('uncaughtException', function(err) {
  var epoch = nowEpoch();
  console.log("_time=\"" + epoch + "\" level=\"error\" message=\"Uncaught exception in dash-proxy\" error=\"" + String(err) + "\"");
});

process.on('unhandledRejection', function(reason) {
  var epoch = nowEpoch();
  console.log("_time=\"" + epoch + "\" level=\"error\" message=\"Unhandled rejection in dash-proxy\" error=\"" + String(reason) + "\"");
});
