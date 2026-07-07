
# encoding = utf-8

import os
import sys
import time
import datetime

from yahoo_weather.weather import YahooWeather
from yahoo_weather.config.units import Unit

def validate_input(helper, definition):
    city = definition.parameters.get('city', None)
    temperature_scale = definition.parameters.get('temperature_scale', None)

def collect_events(helper, ew):
    weather = YahooWeather(APP_ID=helper.get_global_setting("app_id"),
                       api_key=helper.get_global_setting("consumer_key"),
                       api_secret=helper.get_global_setting("consumer_secret"))

    opt_city = helper.get_arg('city')
    opt_temperature_scale = helper.get_arg('temperature_scale')
    
    if opt_temperature_scale == "F":
        unit = Unit.fahrenheit
    else:
        unit = Unit.celsius

    # LOGICA
    weather.get_yahoo_weather_by_city(opt_city, unit)

    curr_date = str(weather.current_observation.pubDate)
    curr_temp = str(weather.current_observation.condition.temperature)
    curr_desc = weather.current_observation.condition.text
    title = weather.location.city
    latitude = str(weather.location.lat)
    longitude = str(weather.location.long)
    
    for fcast in weather.forecasts:
        fore_date = fcast.date.strftime("%d-%m-%Y %H:%M:%S")
        fore_max_temp = str(fcast.high)
        fore_min_temp = str(fcast.low)
        fore_desc = fcast.text
        
        data =  curr_date + "|" + title + "|" + curr_temp + "|" + curr_desc + "|" + latitude + "|" + longitude + "|" + fore_date + "|" + fore_max_temp + "|" + fore_min_temp + "|" + fore_desc
        
        event = helper.new_event(data, host=None, source='yahooweather', sourcetype='csv', done=True, unbroken=True)
        
        try:
            ew.write_event(event)
        except Exception as e:
            raise e