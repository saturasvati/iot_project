from flask import Flask, render_template, request, Response
from classes import *
import datetime
import env

# Prepare

db = DatabaseLink(database=env.DB_DATABASE, host=env.DB_HOST,
                  username=env.DB_USERNAME, password=env.DB_PASSWORD)

tokens_catch = db.get_tokens()
rooms: list[Room] = {}

# Make room "Main"
room = Room("main", db)

room.set_temperature_sensor("temperature",
                            env.SENSOR_TEMPERATURE_TOKEN)
room.set_humidity_sensor("humidity",
                         env.SENSOR_HUMIDITY_TOKEN)
room.set_temperature_sensor_outer("temperature_outer",
                                  env.SENSOR_TEMPERATURE_OUTER_TOKEN)
room.set_humidity_sensor_outer("humidity_outer",
                               env.SENSOR_HUMIDITY_OUTER_TOKEN)
room.set_co2_sensor("carbondioxide",
                    env.SENSOR_CO2_TOKEN)

room.set_ac_devices("battery_relay",
                    env.EXECUTOR_HEATER_ADDRESS,
                    env.EXECUTOR_HEATER_TOKEN)
room.set_heater_device("conditioner",
                       env.EXECUTOR_AC_ADDRESS,
                       env.EXECUTOR_AC_TOKEN)
room.set_vent_device("window_opener",
                     env.EXECUTOR_VENT_ADDRESS,
                     env.EXECUTOR_VENT_TOKEN)
room.set_humidifier_device("GARLYN_AirWash_V30",
                           env.EXECUTOR_HUMIDIFIER_ADDRESS,
                           env.EXECUTOR_HUMIDIFIER_TOKEN)

room.set_autocontrol(True,True,True,True)

rooms.append(room)

# Flask functions

app = Flask(__name__)


@app.route("/api/<request_room>", methods=["POST"])
def api_main(request_room):
    try:
        rooms[request_room]
    except KeyError:
        return Response("Request room not exist", status=404)
    try:
        rooms[request_room]
    except KeyError:
        return Response("Request room not exist", status=404)
    body = request.json()
    token = body["Auth"]
    area: Room = rooms[request_room]
    if token == (None or ""):
        return Response("Token is necessary", status=401)
    auth_success = area.precessing_request(token, body["value"])
    if not auth_success:
        return Response("Token not accepted", status=403)


@app.route("/")
def main_page():
    pass
