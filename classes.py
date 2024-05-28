import pymongo
import datetime
import numpy as np
import abc
import requests
import env
from typing import Literal, TypeAlias


def quick_lstsq(x: list, y: list):
    try:
        len(x) == len(y)
    except:
        return IndexError
    x = np.array(x)
    y = np.array(y)
    A = np.vstack([x, np.ones(len(x))]).T
    k, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return k


class DatabaseLink:
    """Класс интерфейса базы данных"""

    def __init__(self, host: str, username: str, password: str, database: str) -> None:
        self.client = pymongo.MongoClient(
            host=host, username=username, password=password, authSource=database, authMechanism="SCRAM-SHA-256")
        self.db = self.client[database]
        print(f"Connected to database {host}/{database}")

    def send(self, collection: str, value: dict):
        """Создать запись в БД"""
        value += {"timestamp": datetime.datetime.now()
                  }  # Время записи добавляется автоматически
        self.db[collection].insert_one(value)

    def update(self, collection: str, record: dict, subs: dict):
        self.db[collection].update_one(record, subs)

    def get(self, collection: str):
        """Получить записи в БД"""
        return list(self.db[collection].find().sort({"date": 1}))

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
        self.db.send(
            "sensor", {"name": name, "token": token, "pragma": self.pragma})

    @abc.abstractmethod
    def redefinition_token(self, token):
        """Изменить токен авторизации"""
        self.db.update("sensor", {"name": self.name}, {"token": token})
        self._token = token

    @abc.abstractmethod
    def remove_token(self):
        """Отозвать токен авторизации"""
        self.db.update("sensor", {"name": self.name}, {"token": None})
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


class Executor:
    """Класс исполнительного устройства"""

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
                      "address": self.address}+value)

    def send_command(self, value: dict):
        """Отправить команду на ИУ"""
        res = requests.post(
            f"http://{self.address}", json=value, headers={"Auth": self.token})
        return res


class TemperatureSensor(Sensor):
    """Класс датчика температуры"""

    pragma = "temperature"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        return data < 100 and data > -60

    def save(self, data):
        self.db.send("temperature", {"temperature": data, "sensor": self.name})

    def get_average(self, period):
        records = self.db.get_for_period(
            "temperature", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [x["temperature"] for x in records]
        average = sum(values)/len(values)
        return average

    def get_trend(self, period):
        records = self.db.get_for_period(
            "temperature", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [x["temperature"] for x in records]
        dates = [x["date"].timestamp() for x in records]
        return quick_lstsq(values, dates)


class HumiditySensor(Sensor):
    """Класс датчика влажности"""
    pragma = "humidity"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        return data < 100 and data > 0

    def save(self, data):
        self.db.send("humidity", {"humidity": data, "sensor": self.name})

    def get_average(self, period):
        records = self.db.get_for_period(
            "humidity", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [x["humidity"] for x in records]
        average = sum(values)/len(values)
        return average

    def get_trend(self, period):
        records = self.db.get_for_period(
            "humidity", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [x["humidity"] for x in records]
        dates = [x["date"].timestamp() for x in records]
        return quick_lstsq(values, dates)


class CO2Sensor(Sensor):
    """Класс датчика давления"""
    pragma = "co2"

    def __init__(self, name, token, db: DatabaseLink):
        super().__init__(name, token, db)

    def validate(self, data) -> bool:
        return data < 30e3 and data > 0

    def save(self, data):
        self.db.send("co2", {"co2": data, "sensor": self.name})

    def get_average(self, period):
        records = self.db.get_for_period(
            "co2", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [x["co2"] for x in records]
        average = sum(values)/len(values)
        return average

    def get_trend(self, period):
        records = self.db.get_for_period(
            "co2", datetime.datetime.now()-period, datetime.datetime.now())
        try:
            len(records) > 0
        except:
            IndexError
        values = [x["co2"] for x in records]
        dates = [x["date"].timestamp() for x in records]
        return quick_lstsq(values, dates)


class HeaterDevice(Executor):
    """Класс обогревателя"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def switch_power(self, power: bool):
        res = self.send_command({"switch_power": power})
        self.log_event({"command": {"switch_power": power}, "answer": res})

    def set_heating_power(self, heating_power: int):
        res = self.send_command({"heating_power": heating_power})
        self.log_event(
            {"command": {"heating_power": heating_power}, "answer": res})


class ACDevice(Executor):
    """Класс кондиционера"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def switch_power(self, power: bool):
        res = self.send_command({"switch_power": power})
        self.log_event({"command": {"switch_power": power}, "answer": res})

    def set_temperature(self, temperature: int):
        res = self.send_command({"set_temperature": temperature})
        self.log_event(
            {"command": {"set_temperature": temperature}, "answer": res})


class VentDevice(Executor):
    """Класс вентилирующего агрегата"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def switch_power(self, power: bool):
        res = self.send_command({"switch_power": power})
        self.log_event({"command": {"switch_power": power}, "answer": res})

    def set_speed(self, speed: int):
        res = self.send_command({"set_speed": speed})
        self.log_event({"command": {"set_speed": speed}, "answer": res})


class Humidifier(Executor):
    """Класс увлажнителя воздуха"""

    def __init__(self, name, address: str, _token, _db: DatabaseLink) -> None:
        super().__init__(name, address, _token, _db)

    def switch_power(self, power: bool):
        res = self.send_command({"switch_power": power})
        self.log_event({"command": {"switch_power": power}, "answer": res})

    def set_volume(self, volume: int):
        res = self.send_command({"set_volume": volume})
        self.log_event({"command": {"set_volume": volume}, "answer": res})


class Room:
    """Класс помещения"""
    _autocontrol_heater: bool = False
    _autocontrol_ac: bool = False
    _autocontrol_vent: bool = False
    _autocontrol_humidifier: bool = False

    report = {}

    FuzzyAssessment: TypeAlias = Literal['tooLow', 'infBorder', 'optimum',
                                         'supBorder', 'tooHigh']
    DangerAssessment: TypeAlias = Literal['optimum', 'acceptable',
                                          'harmful', 'danger']
    TrendAssessment: TypeAlias = Literal['falling', 'constant', 'rising']

    def redefine_temperature_requirements(self,
                                          inf: float = env.TEMPERATURE_LEVEL_INF,
                                          sup: float = env.TEMPERATURE_LEVEL_SUP,
                                          inf_cutoff: float = env.TEMPERATURE_LEVEL_INF_CUTOFF,
                                          sup_cutoff: float = env.TEMPERATURE_LEVEL_SUP_CUTOFF,
                                          rising: float = env.TEMPERATURE_TREND_RISING,
                                          falling: float = env.TEMPERATURE_TREND_FALLING):
        """Установить требования температурного режима"""
        # Оптимальные значения температуры
        self._temperature_requirement_inf = inf  # минимальное
        self._temperature_requirement_sup = sup  # максимальное
        # Параметры управления гистерезисом
        self._temperature_requirement_inf_cutoff = inf_cutoff  # минимальное отсечки
        self._temperature_requirement_sup_cutoff = sup_cutoff  # максимальное отсечки
        # Параметры границ производных
        self._temperature_requirement_rising = rising
        self._temperature_requirement_falling = falling
        print(f"Set temperature optimum:\ninf = {inf}\nsup = {sup}\n" +
              f"Hysteresis:\ninf = {inf_cutoff}\nsup = {sup_cutoff}" +
              f"Trends:\nrising = {rising*3600}\nfalling = {falling*3600}")

    def redefine_humidity_requirements(self,
                                       inf: float = env.HUMIDITY_LEVEL_INF,
                                       sup: float = env.HUMIDITY_LEVEL_SUP,
                                       inf_cutoff: float = env.HUMIDITY_LEVEL_INF_CUTOFF,
                                       sup_cutoff: float = env.HUMIDITY_LEVEL_SUP_CUTOFF,
                                       rising: float = env.HUMIDITY_TREND_RISING,
                                       falling: float = env.HUMIDITY_TREND_FALLING):
        """Установить требования режима влажности воздуха"""
        # Оптимальные значения влажности
        self._humidity_requirement_inf = inf  # минимальное
        self._humidity_requirement_sup = sup  # максимальное
        # Параметры управления гистерезисом
        self._humidity_requirement_inf_cutoff = inf_cutoff  # минимальное отсечки
        self._humidity_requirement_sup_cutoff = sup_cutoff  # максимальное отсечки
        # Параметры границ производных
        self._humidity_requirement_rising = rising
        self._humidity_requirement_falling = falling
        print(f"Set humidity optimum:\ninf = {inf}\nsup = {sup}\n" +
              f"Hysteresis:\ninf = {inf_cutoff}\nsup = {sup_cutoff}" +
              f"Trends:\nrising = {rising*3600}\nfalling = {falling*3600}")

    def redefine_co2_requirements(self,
                                  acceptable: float = env.CO2_LEVEL_ACCEPTABLE,
                                  harmful: float = env.CO2_LEVEL_HARMFUL,
                                  danger: float = env.CO2_LEVEL_DANGER,
                                  rising: float = env.CO2_TREND_RISING,
                                  falling: float = env.CO2_TREND_FALLING):
        """Установить требования режима концентрации углекислоты"""
        self._co2_requirement_acceptable = acceptable  # допустимое
        self._co2_requirement_harmful = harmful  # вредное
        self._co2_requirement_danger = danger  # опасное
        self._co2_requirement_rising = rising
        self._co2_requirement_falling = falling
        print(f"Set CO2 requirements:\nacceptable = {acceptable}\n" +
              f"harmful = {harmful}\ndanger = {danger}\n" +
              f"Trends:\nrising = {rising*3600}\nfalling = {falling*3600}")

    def __init__(self, name: str, db):
        self.name = name
        self.db: DatabaseLink = db
        self.redefine_temperature_requirements()
        self.redefine_humidity_requirements()
        self.redefine_co2_requirements()
        print(f"Created new room named {name}")

    def is_in_tokens_list(self, token):
        _tokens = []
        _tokens += [x._token for x in self._temperature_sensor]
        _tokens += [x._token for x in self._humidity_sensor]
        return (token is not (None or "")) and token in _tokens

    def set_temperature_sensor(self, sensor: TemperatureSensor):
        self.temperature_sensor = sensor

    def set_humidity_sensor(self, sensor: HumiditySensor):
        self.humidity_sensor = sensor

    def set_temperature_sensor_outer(self, sensor: TemperatureSensor):
        self.temperature_sensor_outer = sensor

    def set_humidity_sensor_outer(self, sensor: HumiditySensor):
        self.humidity_sensor_outer = sensor

    def set_co2_sensor(self, sensor: CO2Sensor):
        self.co2_sensor = sensor

    def set_ac_devices(self, device: ACDevice):
        self.ac_device = device

    def set_heater_device(self, device: HeaterDevice):
        self.heater_device = device

    def set_vent_device(self, device: VentDevice):
        self.vent_device = device

    def set_humidifier_device(self, device: Humidifier):
        self.humidifier_device = device

    def set_autocontrol(self, heater: bool = False, ac: bool = False, vent: bool = False, humidifier: bool = False):
        self._autocontrol_heater = heater
        self._autocontrol_ac = ac
        self._autocontrol_vent = vent
        self._autocontrol_humidifier = humidifier

    def make_temperature_assessment(self, temperature: float) -> FuzzyAssessment:
        assessment: self.FuzzyAssessment = None
        if temperature > self._temperature_requirement_sup:
            assessment = "tooHigh"
        if temperature < self._temperature_requirement_sup and \
                temperature > self._temperature_requirement_sup_cutoff:
            assessment = "supBorder"
        if temperature < self._temperature_requirement_sup_cutoff and \
                temperature > self._temperature_requirement_inf_cutoff:
            assessment = "optimum"
        if temperature < self._temperature_requirement_inf_cutoff and \
                temperature > self._temperature_requirement_inf:
            assessment = "infBorder"
        if temperature < self._temperature_requirement_sup:
            assessment = "tooLow"
        return assessment

    def make_humidity_assessment(self, humidity: float) -> FuzzyAssessment:
        assessment: self.FuzzyAssessment = None
        if humidity > self._humidity_requirement_sup:
            assessment = "tooHigh"
        if humidity < self._humidity_requirement_sup and \
                humidity > self._humidity_requirement_sup_cutoff:
            assessment = "supBorder"
        if humidity < self._humidity_requirement_sup_cutoff and \
                humidity > self._humidity_requirement_inf_cutoff:
            assessment = "optimum"
        if humidity < self._humidity_requirement_inf_cutoff and \
                humidity > self._humidity_requirement_inf:
            assessment = "infBorder"
        if humidity < self._humidity_requirement_sup:
            assessment = "tooLow"
        return assessment

    def make_co2_assessment(self, co2: float) -> FuzzyAssessment:
        assessment: self.FuzzyAssessment = "danger"
        if co2 < self._co2_requirement_danger:
            assessment = "harmful"
        if co2 < self._co2_requirement_harmful:
            assessment = "acceptable"
        if co2 < self._co2_requirement_acceptable:
            assessment = "optimum"
        return assessment

    def make_temperature_trend_assessment(self, trend: float) -> TrendAssessment:
        assessment = "constant"
        if trend > self._temperature_requirement_rising:
            assessment = "rising"
        if trend > self._temperature_requirement_falling:
            assessment = "falling"
        return assessment

    def make_humidity_trend_assessment(self, trend: float) -> TrendAssessment:
        assessment = "constant"
        if trend > self._humidity_requirement_rising:
            assessment = "rising"
        if trend > self._humidity_requirement_falling:
            assessment = "falling"
        return assessment

    def make_co2_trend_assessment(self, trend: float) -> TrendAssessment:
        assessment = "constant"
        if trend > self._co2_requirement_rising:
            assessment = "rising"
        if trend > self._co2_requirement_falling:
            assessment = "falling"
        return assessment

    def make_report(self, period: datetime = datetime.time(minute=10)):
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

        temperature_trend_assessment: self.TrendAssessment =\
            self.make_temperature_trend_assessment(temperature_trend)
        humidity_trend_assessment: self.TrendAssessment =\
            self.make_humidity_trend_assessment(humidity_trend)
        co2_trend_assessment: self.TrendAssessment =\
            self.make_co2_trend_assessment(co2_trend)

        report = {
            "assessment": {
                "temperature": temperature_assessment,
                "humidity": humidity_assessment,
                "co2": co2_assessment,
                "temperature_outer": temperature_outer_assessment,
                "humidity_outer": humidity_outer_assessment,
            },
            "trend": {
                "temperature": temperature_trend_assessment,
                "humidity": humidity_trend_assessment,
                "co2": co2_trend_assessment,
            },
            "for_moment": datetime.datetime.now(),
            "for_period": period,
        }

        self.report = report

        return report

    def autocontrol(self, report):
        """Использовать ИУ для повышения атмосферных качеств"""

        temperature = report["assessment"]["temperature"]
        humidity = report["assessment"]["humidity"]
        co2 = report["assessment"]["co2"]
        temperature_outer = report["assessment"]["temperature_outer"]
        humidity_outer = report["assessment"]["humidity_outer"]

        temperature_trend = report["trend"]["temperature"]
        humidity_trend = report["trend"]["humidity"]
        co2_trend = report["trend"]["co2"]

        if co2 == "danger":
            self.vent_device.switch_power(True)
        if co2 == "harmful" and temperature == ("infBorder" or "supBorder"):
            self.vent_device.switch_power(True)

        pass
