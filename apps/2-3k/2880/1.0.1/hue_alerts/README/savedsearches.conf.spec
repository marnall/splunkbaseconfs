# Hue action params

action.hue.param.lights = <string>
* Comma separated list of light names, supports wildcards. The value is matched 
* against the light ID as well as the light name.

action.hue.param.on = [0|1]
* Control the on-state of the lights.
* 1 to turn the light on
* 0 to turn the light off

action.hue.param.color = <string>
* Set the color of the lights. The value has to be a hex color (including 
* leading #, eg. #ff0000) or one of the supported color names.
* Supported color names are: white, red, green, blue and yellow

action.hue.param.bri = <int>
* Set the brightness of the light. This is a value between 0 and 255.

action.hue.param.flash = [none|once|long]
* Control whether to flash the light when changing the state
* Possible value:
*   none - do not flash the light
*   once - flash the light once
*   long - flash the light for 15 seconds
