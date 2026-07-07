import json
import random
from datetime import datetime, timedelta

random.seed(123456)

def apply_variation(original_value: float|int, variation_min: float|int, variation_max: float|int, limit_min: float|int, limit_max: float|int, circle: bool = False, force_int: int = False) -> float|int:
    """Applying variation to an int or float values.

    Args:
        original_value (float | int): Actual value
        variation_min (float | int): Minimal variation
        variation_max (float | int): Maximum variation
        limit_min (float | int): Lower range of the value
        limit_max (float | int): Upper range of the value
        circle (bool, optional): If the value need to be circular (e.g Wind orientation). Defaults to False.
        force_int (bool, optional): The returned value is an int. Defaults to False.

    Returns:
        float|int : Value of the variation (not the new value)
    """    
    if force_int:
        variation = random.triangular(variation_min, variation_max)
    else:
        variation = round(random.triangular(variation_min, variation_max))

    if original_value + variation > limit_max:
        if circle:
            resultat = limit_min + abs(variation)
        else:
            if original_value + variation > 0:
                resultat = original_value - variation
            else:
                resultat = original_value + variation
    elif original_value + variation < limit_min:
        if circle:
            resultat = limit_max - abs(variation)
        else:
            if original_value + variation > 0:
                resultat = original_value + variation
            else:
                resultat = original_value - variation
    else:
        resultat = original_value + variation

    if force_int:
        return round(resultat)
    else:
        return round(resultat,2)


def generate_weather_event(sensor_name, previous_values, timestamp):

    if previous_values is None:
        temperature = round(random.uniform(-5, 40), 2)
        humidity = round(random.uniform(30, 70), 2)
        wind_speed = round(random.uniform(0, 20), 2)
        wind_orientation = round(random.uniform(0, 360), 2)
        uv_index = 0
    else:
        temperature = apply_variation(previous_values["temperature"],-0.7,0.7,-1,40)
        humidity = apply_variation(previous_values["humidity"],-1.2,1.2,30,50)
        wind_speed = apply_variation(previous_values["wind_speed"],-1,1,0,20)
        wind_orientation = apply_variation(previous_values["wind_orientation"],-5,5,0,360, circle=True)
        uv_index = apply_variation(previous_values["uv_index"],-1,1,0,10, force_int=True)

    event = {
        "timestamp": timestamp,
        "sensor_name": sensor_name,
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "wind_orientation": wind_orientation,
        "uv_index": uv_index
    }
    
    return event

def generate_weather_log(num_events: int, filename: str) -> None:
    """Generate weather logs

    Args:
        num_events (int): Number of event to generate
        filename (str): Path for the JSON file
    """    
    sensors = ["Site_A", "Site_B"]

    time = datetime.now() - timedelta(days=1)

    with open(filename, "w") as file:
        previous_values = {sensor: None for sensor in sensors}
        for _ in range(num_events):
            for sensor_name in sensors:
                time += timedelta(seconds=1)
                new_values = generate_weather_event(sensor_name, previous_values[sensor_name], time.strftime("%Y-%m-%dT%H:%M:%S"))

                json.dump(new_values, file)
                file.write('\n')

                previous_values[sensor_name] = new_values

if __name__ == "__main__":
    generate_weather_log(num_events=10000, filename="climate_sensors.sample")