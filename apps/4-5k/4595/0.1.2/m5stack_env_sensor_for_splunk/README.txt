# M5Stack ENV sensor

This app enable to receive and visualize sensor data
from toy IoT device [M5Stack](https://m5stack.com/).

  * Splunk
    - HTTP Event Collector
    - Metric type index
  * M5Stack
    - M5Cloud (MicroPython)
    - ENV sensor

## Configuration

### Splunk

This app create a metric index `m5stack_env`.

1. Enable HTTP Event Collector (HEC) on your Splunk.
2. Install the app.
3. Create HTTP Event Collector input
  and also set default sourcetype.
4. Note a generated token of the HEC input.

### M5Stack

1. Enable the MicroPython environment on your box.
2. Connect an ENV sensor to the box.
3. Get [python codes](https://github.com/ryumei/m5stack_env_monitor_with_splunk).
4. Conpy `cofig.json.sample` to `config.json` and edit config.json.
3. Upload python codes and config.json to your M5Stack using [ampy](https://github.com/pycampers/ampy).
4. Enable WiFi connection.

