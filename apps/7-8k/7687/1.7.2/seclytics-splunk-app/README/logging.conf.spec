# General sections
[loggers]
keys = <string>

[handlers]
keys = <string>

[formatters]
keys = <string>

# Logger stanzas
[logger_root]
level = <string>
handlers = <string>

[logger_splunklib]
qualname = <string>
level = <string>
handlers = <string>
propagate = <bool>

[logger_GetAugurDataCommand]
qualname = <string>
level = <string>
handlers = <string>
propagate = <bool>

[logger_FeedbackCommand]
qualname = <string>
level = <string>
handlers = <string>
propagate = <bool>

[logger_AugurStatusCommand]
qualname = <string>
level = <string>
handlers = <string>
propagate = <bool>

# Handler stanzas
[handler_app]
class = <string>
level = <string>
args = <string>
formatter = <string>

[handler_splunklib]
class = <string>
level = <string>
args = <string>
formatter = <string>

[handler_stderr]
class = <string>
level = <string>
args = <string>
formatter = <string>

# Formatter stanzas
[formatter_seclytics_app]
format = <string>

