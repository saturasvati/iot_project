import pymongo
import datetime
import numpy as np
import abc
import requests


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

    def get(self, collection: str):
        """Получить записи в БД"""
        return list(self.db[collection].find().sort({"date": 1}))

    def get_for_period(self, collection: str, begin: datetime.datetime, end: datetime.datetime = datetime.datetime.now()):
        """Получить записи в БД за данный промежуток времени"""
        return list(self.db[collection].find({"date": {"$gt": begin, "$lt": end}}).sort({"date": 1}))


class Sensor(abc.ABC):
    """АБК датчика"""
    _tokens = []

    @abc.abstractmethod
    def add_token(self, token):
        """Изменить токен авторизации"""
        self._tokens.append(token)

    @abc.abstractmethod
    def remove_token(self, token):
        """Отозвать токен авторизации"""
        self._tokens.remove(token)

    @abc.abstractmethod
    def check_token(self, token):
        """Проверить токен"""
        return token in self._tokens

    @abc.abstractmethod
    def validate():
        """Утвердить данные"""

    @abc.abstractmethod
    def save():
        """Сохранить данные в БД"""

    @abc.abstractmethod
    def get_tail():
        """Получить последние записи из БД"""

    @abc.abstractmethod
    def get_last():
        """Получить последнее значение за период"""

    @abc.abstractmethod
    def get_trend():
        """Получить производную по времени"""


class Executor:
    """Класс исполнительного устройства"""

    def __init__(self, name, address: str, token) -> None:
        self.name = name
        self.address = address
        self.token = token

    def redefinition_token(self, token):
        """Изменить токен авторизации"""
        self.token = token
        print(f"Token of {self.name} changed")

    def redefinition_address(self, address):
        """Изменить сетевой адрес"""
        self.address = address
        print(f"Net address of {self.name} changed to {address}")

    def send_command(self, value: dict):
        """Отправить команду на ИУ"""
        res = requests.post(f"http://{self.address}", json=value, headers={"Auth": self.token})
        return res


class TemperatureSensor(Sensor):
    """Класс датчика температуры"""
    pass


class HumiditySensor(Sensor):
    """Класс датчика влажности"""
    pass


class PressureSensor(Sensor):
    """Класс датчика давления"""
    pass


class HeaterDevice(Executor):
    """Класс обогревателя"""
    pass


class ACDevice(Executor):
    """Класс кондиционера"""
    pass


class VentDevice(Executor):
    """Класс вентилирующего агрегата"""
    pass


class Room:
    """Класс помещения"""
    _ac_devices: list[ACDevice] = []
    _heater_device: list[HeaterDevice] = []
    _vent_device: list[VentDevice] = []

    def __init__(self, name: str, db) -> None:
        self.name = name
        self.db = db
        temperature_sensor = TemperatureSensor()
        humidity_sensor = HumiditySensor()
        pressure_sensor = PressureSensor()
        print(f"Created new room named {name}")

    def redefine_temperature_requirements(self, inf: float = 20, sup: float = 25, inf_cutoff: float = 21, sup_cutoff: float = 24):
        """Установить требования температурного режима"""
        # Оптимальные значения температуры
        self._temperature_requirement_inf = inf  # минимальное
        self._temperature_requirement_sup = sup  # максимальное
        # Параметры управления гистерезисом
        self._temperature_requirement_inf_cutoff = inf_cutoff  # минимальное отсечки
        self._temperature_requirement_sup_cutoff = sup_cutoff  # максимальное отсечки
        print(f"Set temperature optimum:\ninf = {inf}\nsup = {
              sup}\nHysteresis:\ninf = {inf_cutoff}\nsup = {sup_cutoff}")

    def redefine_humidity_requirements(self, inf: float = 40, sup: float = 80, inf_cutoff: float = 50, sup_cutoff: float = 70):
        """Установить требования режима влажности воздуха"""
        # Оптимальные значения влажности
        self._humidity_requirement_inf = inf  # минимальное
        self._humidity_requirement_sup = sup  # максимальное
        # Параметры управления гистерезисом
        self._humidity_requirement_inf_cutoff = inf_cutoff  # минимальное отсечки
        self._humidity_requirement_sup_cutoff = sup_cutoff  # максимальное отсечки
        print(f"Set humidity optimum:\ninf = {inf}\nsup = {
              sup}\nHysteresis:\ninf = {inf_cutoff}\nsup = {sup_cutoff}")

    def add_ac_devices(self, device: ACDevice):
        self._ac_devices.append(device)

    def add_heater_device(self, device: HeaterDevice):
        self._heater_device.append(device)

    def add_vent_device(self, device: VentDevice):
        self._vent_device.append(device)

    def update_atmosphere_parameters(self):
        pass
