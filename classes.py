import pymongo
import datetime
import numpy as np
import abc
import requests
import env
from typing import Literal, TypeAlias


def quick_lstsq(values: list, dates: list[datetime.datetime]):
    try:
        len(values) == len(dates)
    except:
        return IndexError
    A = np.vstack([[x.timestamp() for x in dates], np.ones(len(dates))]).T
    tg, shift = np.linalg.lstsq(A, values, rcond=None)[0]
    return (tg, shift)


class DatabaseLink:
    """Класс интерфейса базы данных"""

    def __init__(self, host: str, username: str, password: str, database: str) -> None:
        self.client = pymongo.MongoClient(
            host=host, username=username, password=password, authSource=database, authMechanism="SCRAM-SHA-256")
        self.db = self.client[database]
        print(f"Connected to database {host}/{database}")

    def send(self, collection: str, value: dict):
        """Создать запись в БД"""
        value |= {"date": datetime.datetime.now(
        )}  # Время записи добавляется автоматически
        self.db[collection].insert_one(value)

    def update(self, collection: str, record: dict, subs: dict):
        self.db[collection].update_one(record, {"$set": subs})

    def get(self, collection: str):
        """Получить записи в БД"""
        return list(self.db[collection].find().sort({"date": 1}))

    def check_exist(self, collection, field, value):
        cursor = self.db[collection].find_one({field: value})
        if cursor == None:
            return False
        if len(cursor) == 0:
            return False
        return True

    def get_for_period(self, collection: str, begin: datetime.datetime, end: datetime.datetime = datetime.datetime.now()):
        """Получить записи в БД за данный промежуток времени"""
        return list(self.db[collection].find({"date": {"$gt": begin, "$lt": end}}).sort({"date": 1}))


class Sensor(abc.ABC):
    """АБК датчика"""

    pragma: str = None

    @abc.abstractmethod
    def __init__(self, name, token, db: DatabaseLink):
        self.name = name
        self._token = token
        self.db = db
        if not (db.check_exist("device", "name", name) and db.check_exist("device", "token", token)):
            self.db.send("device", {"name": name,
                                    "token": token, "pragma": self.pragma})

    @abc.abstractmethod
    def redefinition_token(self, token):
        """Изменить токен авторизации"""
        self.db.update("device", {"name": self.name}, {"token": token})
        self._token = token

    @abc.abstractmethod
    def remove_token(self):
        """Отозвать токен авторизации"""
        self.db.update("device", {"name": self.name}, {"token": None})
        self._token = None

    @abc.abstractmethod
    def validate(self, data) -> bool:
        """Утвердить данные"""

    @abc.abstractmethod
    def save(self, data):
        """Сохранить данные в БД"""

    @abc.abstractmethod
    def get_average(self) -> float:
        """Получить последнее значение за период"""

    @abc.abstractmethod
    def get_trend(self, period) -> float:
        """Получить производную по времени"""

    @abc.abstractmethod
    def get_forecast(self, period, period_forecast):
        """Получить прогноз на заданный промежуток времени"""


class Executor:
    """Класс исполнительного устройства"""
    _power_status = False
    settings = None

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        self.name = name
        self.address = address
        self.token = _token
        self._db = _db

    def redefinition_token(self, token):
        """Изменить токен авторизации"""
        self.token = token
        print(f"Token of {self.name} changed")

    def redefinition_address(self, address):
        """Изменить сетевой адрес"""
        self.address = address
        print(f"Net address of {self.name} changed to {address}")

    def log_event(self, value: dict):
        self._db.send("log", {"executor": self.name,
                      "address": self.address} | value)

    def send_command(self, value: dict):
        """Отправить команду на ИУ"""
        try:
            res = requests.post(self.address, json=value,
                                headers={"Auth": self.token}, timeout=1.5)
            res = res.json()
        except:
            res = {"error": "timeout"}
        return res

    def switch_power(self, power: bool):
        res = self.send_command({"switch_power": power})
        self._power_status = power
        self.log_event({"command": {"switch_power": power}, "answer": res})

    def get_power_status(self):
        return self._power_status

    def get_settings(self):
        return self.settings


class TemperatureSensor(Sensor):
    """Класс датчика температуры"""

    pragma = "temperature"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        if data == None:
            return False
        return data < 100 and data > -60

    def save(self, data):
        if self.validate(data):
            self.db.send("temperature", {
                         "temperature": data, "sensor": self.name})

    def get_average(self, period: datetime.timedelta):
        records = self.db.get_for_period(
            "temperature", datetime.datetime.now() - period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["temperature"]) for x in records]
        try:
            average = sum(values)/len(values)
        except:
            ZeroDivisionError
            average = None
        return average

    def get_trend(self, period: datetime.timedelta):
        records = self.db.get_for_period(
            "temperature", datetime.datetime.now() - period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["temperature"]) for x in records]
        dates = [x["date"] for x in records]
        return quick_lstsq(values, dates)[0]

    def get_forecast(self, period: datetime.datetime, period_forecast: datetime.timedelta):
        average = self.get_average(period)
        trend = self.get_trend(period)
        forecast = trend * period_forecast.seconds + average
        return forecast

    def redefinition_token(self, token):
        return super().redefinition_token(token)

    def remove_token(self):
        return super().remove_token()


class HumiditySensor(Sensor):
    """Класс датчика влажности"""
    pragma = "humidity"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        if data == None:
            return False
        return data < 100 and data > 0

    def save(self, data):
        if self.validate(data):
            self.db.send("humidity", {"humidity": data, "sensor": self.name})

    def get_average(self, period: datetime.datetime):
        records = self.db.get_for_period(
            "humidity", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["humidity"]) for x in records]
        try:
            average = sum(values)/len(values)
        except:
            ZeroDivisionError
            average = None
        return average

    def get_trend(self, period: datetime.datetime):
        records = self.db.get_for_period(
            "humidity", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["humidity"]) for x in records]
        dates = [x["date"] for x in records]
        return quick_lstsq(values, dates)[0]

    def get_forecast(self, period: datetime.datetime, period_forecast: datetime.timedelta):
        average = self.get_average(period)
        trend = self.get_trend(period)
        forecast = trend * period_forecast.seconds + average
        return forecast

    def redefinition_token(self, token):
        return super().redefinition_token(token)

    def remove_token(self):
        return super().remove_token()


class TemperatureSensorOuter(Sensor):
    """Класс датчика температуры"""

    pragma = "temperature_outer"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        if data == None:
            return False
        return data < 100 and data > -60

    def save(self, data):
        if self.validate(data):
            self.db.send("temperature_outer", {
                "temperature_outer": data, "sensor": self.name})

    def get_average(self, period):
        records = self.db.get_for_period(
            "temperature_outer", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["temperature_outer"]) for x in records]
        try:
            average = sum(values)/len(values)
        except:
            ZeroDivisionError
            average = None
        return average

    def get_trend(self, period):
        records = self.db.get_for_period(
            "temperature_outer", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["temperature_outer"]) for x in records]
        dates = [x["date"] for x in records]
        return quick_lstsq(values, dates)[0]

    def get_forecast(self, period: datetime.datetime, period_forecast: datetime.timedelta):
        average = self.get_average(period)
        trend = self.get_trend(period)
        forecast = trend * period_forecast.seconds + average
        return forecast

    def redefinition_token(self, token):
        return super().redefinition_token(token)

    def remove_token(self):
        return super().remove_token()


class HumiditySensorOuter(Sensor):
    """Класс датчика влажности"""
    pragma = "humidity_outer"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        if data == None:
            return False
        return data < 100 and data > 0

    def save(self, data):
        if self.validate(data):
            self.db.send("humidity_outer", {
                "humidity_outer": data, "sensor": self.name})

    def get_average(self, period: datetime.datetime):
        records = self.db.get_for_period(
            "humidity_outer", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["humidity_outer"]) for x in records]
        try:
            average = sum(values)/len(values)
        except:
            ZeroDivisionError
            average = None
        return average

    def get_trend(self, period: datetime.datetime):
        records = self.db.get_for_period(
            "humidity_outer", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["humidity_outer"]) for x in records]
        dates = [x["date"] for x in records]
        return quick_lstsq(values, dates)[0]

    def get_forecast(self, period: datetime.datetime, period_forecast: datetime.timedelta):
        average = self.get_average(period)
        trend = self.get_trend(period)
        forecast = trend * period_forecast.seconds + average
        return forecast

    def redefinition_token(self, token):
        return super().redefinition_token(token)

    def remove_token(self):
        return super().remove_token()


class CO2Sensor(Sensor):
    """Класс датчика давления"""
    pragma = "co2"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        if data == None:
            return False
        return data < 100e3 and data > 0

    def save(self, data):
        if self.validate(data):
            self.db.send("co2", {"co2": data, "sensor": self.name})

    def get_average(self, period):
        records = self.db.get_for_period(
            "co2", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["co2"]) for x in records]
        try:
            average = sum(values)/len(values)
        except:
            ZeroDivisionError
            average = None
        return average

    def get_trend(self, period):
        records = self.db.get_for_period(
            "co2", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [float(x["co2"]) for x in records]
        dates = [x["date"] for x in records]
        return quick_lstsq(values, dates)[0]

    def get_forecast(self, period: datetime.datetime, period_forecast: datetime.timedelta):
        average = self.get_average(period)
        trend = self.get_trend(period)
        forecast = trend * period_forecast.seconds + average
        return forecast

    def redefinition_token(self, token):
        return super().redefinition_token(token)

    def remove_token(self):
        return super().remove_token()


class HeaterDevice(Executor):
    """Класс обогревателя"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def set_heating_power(self, heating_power: int):
        self.settings = heating_power
        res = self.send_command({"heating_power": heating_power})
        self.log_event(
            {"command": {"heating_power": heating_power}, "answer": res})


class ACDevice(Executor):
    """Класс кондиционера"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def set_temperature(self, temperature: int):
        self.settings = temperature
        res = self.send_command({"set_temperature": temperature})
        self.log_event(
            {"command": {"set_temperature": temperature}, "answer": res})


class VentDevice(Executor):
    """Класс вентилирующего агрегата"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def set_speed(self, speed: int):
        self.settings = speed
        res = self.send_command({"set_speed": speed})
        self.log_event({"command": {"set_speed": speed}, "answer": res})


class Humidifier(Executor):
    """Класс увлажнителя воздуха"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def set_volume(self, volume: int):
        self.settings = volume
        res = self.send_command({"set_volume": volume})
        self.log_event({"command": {"set_volume": volume}, "answer": res})


class Room:
    """Класс помещения"""
    autocontrol_heater: bool = False
    autocontrol_ac: bool = False
    autocontrol_vent: bool = False
    autocontrol_humidifier: bool = False
    temperature_requirement_inf = env.TEMPERATURE_LEVEL_INF
    temperature_requirement_sup = env.TEMPERATURE_LEVEL_SUP
    humidity_requirement_inf = env.HUMIDITY_LEVEL_INF
    humidity_requirement_sup = env.HUMIDITY_LEVEL_SUP
    co2_requirement_acceptable = env.CO2_LEVEL_ACCEPTABLE
    co2_requirement_harmful = env.CO2_LEVEL_HARMFUL
    co2_requirement_danger = env.CO2_LEVEL_DANGER
    _tokens = []
    report = {}
    report_period = datetime.timedelta(minutes=env.PERIOD_REPORT)
    forecast_period = datetime.timedelta(minutes=env.PERIOD_FORECAST)

    FuzzyAssessment: TypeAlias = Literal['tooLow', 'optimum', 'tooHigh']
    DangerAssessment: TypeAlias = Literal['optimum', 'acceptable',
                                          'harmful', 'danger']

    def __init__(self, name: str, db):
        self.name = name
        self.db: DatabaseLink = db
        print(f"Created new room named {name}")

    def make_token_list(self):
        records = self.db.get("device")
        pragma = {"temperature": self.temperature_sensor,
                  "humidity": self.humidity_sensor, "co2": self.co2_sensor, "temperature_outer": self.temperature_sensor_outer, "humidity_outer": self.humidity_sensor_outer}
        self._tokens = {record["token"]: pragma[record["pragma"]]
                        for record in records}

    def is_in_tokens_list(self, token):
        return (token is not (None or "")) and token in self._tokens

    def processing_request(self, token, data):
        if token == ("" or None):
            return 403
        if not self.is_in_tokens_list(token):
            return 401
        if data == ("" or None):
            return 400
        sensor: Sensor = self._tokens[token]
        sensor.save(data)
        return 201

    def get_history(self, period: datetime.timedelta =
                    datetime.timedelta(hours=6)):
        history = {}
        collections = ["temperature", "humidity", "temperature_outer",
                       "humidity_outer", "co2", "device", "log"]
        for table in collections:
            records = self.db.get_for_period(table,
                                             datetime.datetime.now() - period,
                                             datetime.datetime.now())
            records = [{x: d[x] for x in d if x != '_id'} for d in records]
            history |= {table: records}
        return history

    def set_report_period(self, period: datetime.timedelta = datetime.timedelta(minutes=5)):
        self.report_period = period

    def set_forecast_period(self, period: datetime.timedelta = datetime.timedelta(minutes=5)):
        self.forecast_period = period

    def set_temperature_sensor(self, name, token):
        sensor = TemperatureSensor(name, token, self.db)
        self.temperature_sensor = sensor

    def set_humidity_sensor(self, name, token):
        sensor = HumiditySensor(name, token, self.db)
        self.humidity_sensor = sensor

    def set_temperature_sensor_outer(self, name, token):
        sensor = TemperatureSensorOuter(name, token, self.db)
        self.temperature_sensor_outer = sensor

    def set_humidity_sensor_outer(self, name, token):
        sensor = HumiditySensorOuter(name, token, self.db)
        self.humidity_sensor_outer = sensor

    def set_co2_sensor(self, name, token):
        sensor = CO2Sensor(name, token, self.db)
        self.co2_sensor = sensor

    def set_ac_devices(self, name, address, token):
        device = ACDevice(name, address, token, self.db)
        self.ac_device = device

    def set_heater_device(self, name, address, token):
        device = HeaterDevice(name, address, token, self.db)
        self.heater_device = device

    def set_vent_device(self, name, address, token):
        device = VentDevice(name, address, token, self.db)
        self.vent_device = device

    def set_humidifier_device(self, name, address, token):
        device = Humidifier(name, address, token, self.db)
        self.humidifier_device = device

    def set_heater_power(self, setting):
        self.heater_device.set_heating_power(setting)
        pass

    def set_ac_temperature(self, setting):
        self.ac_device.set_temperature(setting)
        pass

    def set_vent_speed(self, setting):
        self.vent_device.set_speed(setting)
        pass

    def set_humidifier_volume(self, setting):
        self.humidifier_device.set_volume(setting)
        pass

    def make_temperature_assessment(self, temperature: float) -> FuzzyAssessment:
        assessment: self.FuzzyAssessment = "optimum"
        if temperature > self.temperature_requirement_sup:
            assessment = "tooHigh"
        if temperature < self.temperature_requirement_inf:
            assessment = "tooLow"
        return assessment

    def make_humidity_assessment(self, humidity: float) -> FuzzyAssessment:
        assessment: self.FuzzyAssessment = "optimum"
        if humidity > self.humidity_requirement_sup:
            assessment = "tooHigh"
        if humidity < self.humidity_requirement_inf:
            assessment = "tooLow"
        return assessment

    def make_co2_assessment(self, co2: float) -> FuzzyAssessment:
        assessment: self.FuzzyAssessment = "danger"
        if co2 < self.co2_requirement_danger:
            assessment = "harmful"
        if co2 < self.co2_requirement_harmful:
            assessment = "acceptable"
        if co2 < self.co2_requirement_acceptable:
            assessment = "optimum"
        return assessment

    def make_report(self, period: datetime.timedelta = report_period):
        """Составить оценку атмосферных параметров"""

        if not self.temperature_sensor:
            print("Temperature sensor not set!")
            return None
        if not self.humidity_sensor:
            print("Humidity sensor not set!")
            return None
        if not self.co2_sensor:
            print("CO2 sensor not set!")
            return None

        temperature = self.temperature_sensor.get_average(period)
        humidity = self.humidity_sensor.get_average(period)
        co2 = self.co2_sensor.get_average(period)
        temperature_outer = self.temperature_sensor_outer.get_average(period)
        humidity_outer = self.humidity_sensor_outer.get_average(period)

        if not self.temperature_sensor.validate(temperature) or not self.humidity_sensor.validate(humidity) or not self.co2_sensor.validate(co2):
            return None

        temperature_assessment: self.FuzzyAssessment =\
            self.make_temperature_assessment(temperature)
        humidity_assessment: self.FuzzyAssessment =\
            self.make_humidity_assessment(humidity)
        co2_assessment: self.DangerAssessment =\
            self.make_co2_assessment(co2)
        temperature_outer_assessment: self.FuzzyAssessment =\
            self.make_temperature_assessment(temperature_outer)
        humidity_outer_assessment: self.FuzzyAssessment =\
            self.make_humidity_assessment(humidity_outer)

        temperature_trend = self.temperature_sensor.get_trend(period)
        humidity_trend = self.humidity_sensor.get_trend(period)
        co2_trend = self.co2_sensor.get_trend(period)

        temperature_forecast = self.temperature_sensor.get_forecast(
            period, self.forecast_period)
        humidity_forecast = self.humidity_sensor.get_forecast(
            period, self.forecast_period)
        co2_forecast = self.co2_sensor.get_forecast(
            period, self.forecast_period)

        temperature_forecast_assessment =\
            self.make_temperature_assessment(temperature_forecast)
        humidity_forecast_assessment =\
            self.make_humidity_assessment(humidity_forecast)
        co2_forecast_assessment =\
            self.make_co2_assessment(co2_forecast)

        vent_power = self.vent_device.get_power_status()
        ac_power = self.ac_device.get_power_status()
        heater_power = self.heater_device.get_power_status()
        humidifier_power = self.humidifier_device.get_power_status()
        report = {
            "value": {
                "temperature": np.round(temperature, 1),
                "humidity": np.round(humidity, 0),
                "co2": np.round(co2, 0),
                "temperature_outer": np.round(temperature_outer, 1),
                "humidity_outer": np.round(humidity_outer, 0),
            },
            "assessment": {
                "temperature": temperature_assessment,
                "humidity": humidity_assessment,
                "co2": co2_assessment,
                "temperature_outer": temperature_outer_assessment,
                "humidity_outer": humidity_outer_assessment,
            },
            "trend": {
                "temperature": temperature_trend,
                "humidity": humidity_trend,
                "co2": co2_trend,
            },
            "forecast": {
                "temperature": temperature_forecast,
                "humidity": humidity_forecast,
                "co2": co2_forecast,
            },
            "forecast_assessment": {
                "temperature": temperature_forecast_assessment,
                "humidity": humidity_forecast_assessment,
                "co2": co2_forecast_assessment,
            },
            "devices_status": {
                "vent": vent_power,
                "ac": ac_power,
                "heater": heater_power,
                "humidifier": humidifier_power,
            },
            "forecast_for_period": int(self.forecast_period.seconds),
            "for_moment": datetime.datetime.now().isoformat(),
            "for_period": int(period.seconds),
        }

        self.report = report

        return report

    def autocontrol(self, report):
        """Использовать ИУ для повышения атмосферных качеств"""
        temperature_forecast = report["forecast_assessment"]["temperature"]
        humidity_forecast = report["forecast_assessment"]["humidity"]
        temperature_outer = report["assessment"]["temperature_outer"]
        humidity_outer = report["assessment"]["humidity_outer"]
        co2_forecast = report["forecast_assessment"]["co2"]
        co2 = report["assessment"]["co2"]

        ac_power: bool = False
        heater_power: bool = False
        humidifier_power: bool = False
        vent_power: bool = False

        match temperature_forecast:
            case "tooLow":
                match humidity_forecast:
                    case "tooLow":
                        if temperature_outer != "tooLow" and \
                                humidity_outer != "tooLow":
                            vent_power = True
                        else:
                            heater_power = True
                            humidifier_power = True
                    case "optimum":
                        if temperature_outer != "tooLow" and \
                                humidity_outer == "optimum":
                            vent_power = True
                        else:
                            heater_power = True
                    case "tooHigh":
                        if temperature_outer != "tooLow" and \
                                humidity_outer != "tooHigh":
                            vent_power = True
                        else:
                            heater_power = True
            case "optimum":
                match humidity_forecast:
                    case "tooLow":
                        if temperature_outer == "optimum" and \
                                humidity_outer != "tooLow":
                            vent_power = True
                        else:
                            humidifier_power = True
                    case "optimum":
                        pass
                    case "tooHigh":
                        if temperature_outer == "optimum" and \
                                humidity_outer != "tooHigh":
                            vent_power = True
                        else:
                            pass
            case "tooHigh":
                match humidity_forecast:
                    case "tooLow":
                        if temperature_outer != "tooHigh" and \
                                humidity_outer != "tooHigh":
                            vent_power = True
                        else:
                            ac_power = True
                    case "optimum":
                        if temperature_outer != "tooHigh" and \
                                humidity_outer == "optimum":
                            vent_power = True
                        else:
                            ac_power = True
                    case "tooHigh":
                        if temperature_outer != "tooHigh" and \
                                humidity_outer != "tooHigh":
                            vent_power = True
                        else:
                            ac_power = True

        if co2_forecast == "danger" or co2 == "danger":
            vent_power = True
            if not self._autocontrol_vent:
                self.vent_device.switch_power(vent_power)
        if (co2_forecast == "harmful" or co2 == "harmful") and \
                temperature_forecast == "optimum":
            vent_power = True

        if self.autocontrol_vent and vent_power:
            self.vent_device.switch_power(vent_power)
        if self.autocontrol_ac and ac_power:
            self.ac_device.switch_power(ac_power)
        if self.autocontrol_heater and heater_power:
            self.heater_device.switch_power(heater_power)
        if self.autocontrol_humidifier and humidifier_power:
            self.humidifier_device.switch_power(humidifier_power)
