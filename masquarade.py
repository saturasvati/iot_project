import datetime
import requests
import env
import random

"""Скрипт имитирует отправку данных с блока датчика в целях тестирования"""

url = "http://localhost:5000/api/device/send"
timeout = 1.5

m_t = 23
m_phi = 50
m_co2 = 700
m_o_t = 17
m_o_phi = 50


def make_request(url, m, devi, token):
    val = m + random.randint(-devi, devi)
    data = {"Auth": token, "value": val}
    try:
        res = requests.post(url=url, json=data, timeout=timeout, headers={
                            "Content-Type": "application/json"})
        print(f"{res.request.body}")
    except:
        res = {"error": "timeout"}

make_request(url, m_t, 1, env.SENSOR_TEMPERATURE_TOKEN)
make_request(url, m_phi, 4, env.SENSOR_HUMIDITY_TOKEN)
make_request(url, m_o_t, 1, env.SENSOR_TEMPERATURE_OUTER_TOKEN)
make_request(url, m_o_phi, 3, env.SENSOR_HUMIDITY_OUTER_TOKEN)
make_request(url, m_co2, 100, env.SENSOR_CO2_TOKEN)

while True:
    if int(datetime.datetime.now().timestamp()) % 45 == 0:
        make_request(url, m_t, 1, env.SENSOR_TEMPERATURE_TOKEN)
        make_request(url, m_phi, 4, env.SENSOR_HUMIDITY_TOKEN)
        make_request(url, m_o_t, 1, env.SENSOR_TEMPERATURE_OUTER_TOKEN)
        make_request(url, m_o_phi, 3, env.SENSOR_HUMIDITY_OUTER_TOKEN)
        make_request(url, m_co2, 100, env.SENSOR_CO2_TOKEN)
        print()
