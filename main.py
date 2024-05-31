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
room.autocontrol_vent = True
room.autocontrol_ac = True
room.autocontrol_heater = True
room.autocontrol_humidifier = True

# Flask functions

app = Flask(__name__, static_folder="static")

# Errors


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", error=404, comment="Ложки не существует")

# API


@app.route("/api/device/send", methods=["POST"])
def api_device_send():
    token = request.json["Auth"]
    value = request.json["value"]
    code = room.processing_request(token, value)
    report = room.make_report()
    room.autocontrol(report)
    return Response(status=code)


@app.route("/api/device/settings", methods=["POST"])
def api_device_settings():
    settings: dict[dict] = request.json
    if ("executor_on" in settings and len(settings["executor_on"])):
        for exe, val in settings["executor_on"].items():
            match exe:
                case "ac":
                    room.ac_device.switch_power(val)
                case "vent":
                    room.vent_device.switch_power(val)
                case "heater":
                    room.heater_device.switch_power(val)
                case "humidifier":
                    room.humidifier_device.switch_power(val)
    if ("executor_setting" in settings and len(settings["executor_setting"])):
        for exe, val in settings["executor_setting"].items():
            val = int(val)
            match exe:
                case "ac":
                    room.ac_device.set_temperature(val)
                case "vent":
                    room.vent_device.set_speed(val)
                case "heater":
                    room.heater_device.set_heating_power(val)
                case "humidifier":
                    room.humidifier_device.set_volume(val)
    if ("executor_address" in settings and len(settings["executor_address"])):
        for exe, val in settings["executor_address"].items():
            match exe:
                case "ac":
                    room.ac_device.redefinition_address(val)
                case "vent":
                    room.vent_device.redefinition_address(val)
                case "heater":
                    room.heater_device.redefinition_address(val)
                case "humidifier":
                    room.humidifier_device.redefinition_address(val)
    if ("executor_autocontrol" in settings and len(settings["executor_autocontrol"])):
        for exe, val in settings["executor_autocontrol"].items():
            match exe:
                case "ac":
                    print(exe, val)
                    room.autocontrol_ac=val
                case "vent":
                    print(exe, val)
                    room.autocontrol_vent=val
                case "heater":
                    print(exe, val)
                    room.autocontrol_heater=val
                case "humidifier":
                    print(exe, val)
                    room.autocontrol_humidifier=val
        print(room.autocontrol_ac,room.autocontrol_heater,room.autocontrol_humidifier,room.autocontrol_vent)
    if ("executor_token" in settings and len(settings["executor_token"])):
        for exe, val in settings["executor_token"].items():
            match exe:
                case "ac":
                    room.ac_device.redefinition_token(val)
                case "vent":
                    room.vent_device.redefinition_token(val)
                case "heater":
                    room.heater_device.redefinition_token(val)
                case "humidifier":
                    room.humidifier_device.redefinition_token(val)
        room.make_token_list()
    if ("sensor_new_token" in settings and len(settings["sensor_new_token"])):
        for sensor, val in settings["sensor_new_token"].items():
            match sensor:
                case "temperature":
                    room.temperature_sensor.redefinition_token(val)
                case "temperature_outer":
                    room.temperature_sensor_outer.redefinition_token(val)
                case "humidity":
                    room.humidity_sensor.redefinition_token(val)
                case "humidity_outer":
                    room.humidity_sensor_outer.redefinition_token(val)
                case "co2":
                    room.co2_sensor.redefinition_token(val)
        room.make_token_list()
    if ("sensor_remove" in settings and len(settings["sensor_remove"])):
        for sensor, val in settings["sensor_remove"].items():
            match sensor:
                case "temperature":
                    room.temperature_sensor.remove_token()
                case "temperature_outer":
                    room.temperature_sensor_outer.remove_token()
                case "humidity":
                    room.humidity_sensor.remove_token()
                case "humidity_outer":
                    room.humidity_sensor_outer.remove_token()
                case "co2":
                    room.co2_sensor.remove_token()
        room.make_token_list()
    return Response(status=200)


@app.route("/api/common/settings", methods=["POST"])
def api_get_settings():
    settings = request.json
    settings["co2"]["acceptable"] = float(settings["co2"]["acceptable"])
    settings["co2"]["harmful"] = float(settings["co2"]["harmful"])
    settings["co2"]["danger"] = float(settings["co2"]["danger"])
    settings["temperature"]["inf"] = float(settings["temperature"]["inf"])
    settings["temperature"]["sup"] = float(settings["temperature"]["sup"])
    settings["humidity"]["inf"] = float(settings["humidity"]["inf"])
    settings["humidity"]["sup"] = float(settings["humidity"]["sup"])
    settings["period"]["forecast"] = int(settings["period"]["forecast"])
    settings["period"]["report"] = int(settings["period"]["report"])

    if room.co2_sensor.validate(settings["co2"]["acceptable"]):
        room.co2_requirement_acceptable = settings["co2"]["acceptable"]
    if room.co2_sensor.validate(settings["co2"]["harmful"]):
        room.co2_requirement_harmful = settings["co2"]["harmful"]
    if room.co2_sensor.validate(settings["co2"]["danger"]):
        room.co2_requirement_danger = settings["co2"]["danger"]
    if room.temperature_sensor.validate(settings["temperature"]["inf"]):
        room.temperature_requirement_inf = settings["temperature"]["inf"]
    if room.temperature_sensor.validate(settings["temperature"]["sup"]):
        room.temperature_requirement_sup = settings["temperature"]["sup"]
    if room.humidity_sensor.validate(settings["humidity"]["inf"]):
        room.humidity_requirement_inf = settings["humidity"]["inf"]
    if room.humidity_sensor.validate(settings["humidity"]["sup"]):
        room.humidity_requirement_sup = settings["humidity"]["sup"]
    if settings["period"]["forecast"] > 10 and settings["period"]["forecast"] < 3600:
        room.forecast_period = datetime.timedelta(seconds=settings["period"]["report"])
    if settings["period"]["report"] > 10 and settings["period"]["report"] < 3600:
        room.report_period = datetime.timedelta(seconds=settings["period"]["forecast"])

    return Response(status=201)


@app.route("/api/get/settings")
def api_send_settings():
    answer = {
        "co2": {"acceptable": room.co2_requirement_acceptable,
                "harmful": room.co2_requirement_harmful,
                "danger": room.co2_requirement_danger},
        "temperature": {"inf": room.temperature_requirement_inf,
                        "sup": room.temperature_requirement_sup},
        "humidity": {"inf": room.humidity_requirement_inf,
                     "sup": room.humidity_requirement_sup},
        "period": {"forecast": room.forecast_period.seconds,
                   "report": room.report_period.seconds}
    }
    return answer


@app.route("/api/get/device_status")
def api_get_devices_statistic():
    answer = {"executor_on": {},
              "executor_setting": {},
              "executor_address": {},
              "executor_autocontrol": {}, }
    report = room.make_report()
    answer["executor_on"] = report["devices_status"]

    answer["executor_setting"]["ac"] = room.ac_device.settings
    answer["executor_setting"]["vent"] = room.vent_device.settings
    answer["executor_setting"]["heater"] = room.heater_device.settings
    answer["executor_setting"]["humidifier"] = room.humidifier_device.settings

    answer["executor_address"]["ac"] = room.ac_device.address
    answer["executor_address"]["vent"] = room.vent_device.address
    answer["executor_address"]["heater"] = room.heater_device.address
    answer["executor_address"]["humidifier"] = room.humidifier_device.address

    answer["executor_autocontrol"]["ac"] = room.autocontrol_ac
    answer["executor_autocontrol"]["vent"] = room.autocontrol_vent
    answer["executor_autocontrol"]["heater"] = room.autocontrol_heater
    answer["executor_autocontrol"]["humidifier"] = room.autocontrol_humidifier

    return answer


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
