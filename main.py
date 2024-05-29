from flask import Flask, render_template, request, Response
from classes import *
import datetime
import env

# Prepare

db = DatabaseLink(database=env.DB_DATABASE, host=env.DB_HOST,
                  username=env.DB_USERNAME, password=env.DB_PASSWORD)

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
                    env.EXECUTOR_AC_ADDRESS,
                    env.EXECUTOR_AC_TOKEN)
room.set_heater_device("conditioner",
                       env.EXECUTOR_HEATER_ADDRESS,
                       env.EXECUTOR_HEATER_TOKEN)
room.set_vent_device("window_opener",
                     env.EXECUTOR_VENT_ADDRESS,
                     env.EXECUTOR_VENT_TOKEN)
room.set_humidifier_device("GARLYN_AirWash_V30",
                           env.EXECUTOR_HUMIDIFIER_ADDRESS,
                           env.EXECUTOR_HUMIDIFIER_TOKEN)

room.set_heater_power(400)      # [W]
room.set_ac_temperature(16)     # [degC]
room.set_vent_speed(100)        # [%]
room.set_humidifier_volume(80)  # [%]

room.make_token_list()
room.set_autocontrol(True, True, True, True)

# Flask functions

app = Flask(__name__, static_folder="static")

# Errors


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", error=404, comment="Ложки не существует")

# API


@app.route("/api/device", methods=["POST"])
def api_device():
    token = request.form.get("Auth")
    if token == (None or ""):
        return Response("Token is necessary", status=401)
    auth_success = room.precessing_request(token, request.form.get("value"))
    if not auth_success:
        return Response("Token not accepted", status=403)
    return Response("Created", 201)


@app.route("/api/get/report", methods=["GET"])
def api_get_report():
    if request.args.get("period"):
        period = datetime.timedelta(seconds=int(request.args.get("period")))
        report = room.make_report(period)
    else:
        report = room.make_report()
    return report

@app.route("/api/get/data", methods=["GET"])
def api_get_data():
    if request.args.get("period"):
        period = datetime.timedelta(seconds=int(request.args.get("period")))
        history = room.get_history(period)
    else:
        history = room.get_history(datetime.timedelta(hours=6))
    return history

# UI
@app.route("/")
def main_page():
    return render_template("index.html")


@app.route("/report")
def report_page():
    report = room.make_report()
    return render_template("report.html", report=report)


@app.route("/devices")
def devices_page():
    return render_template("devices.html")


@app.route("/settings")
def settings_page():
    return render_template("settings.html")


if __name__ == '__main__':
    app.debug = True
    app.run()
