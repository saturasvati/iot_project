import pymongo
import datetime
import numpy as np
import abc


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
    @abc.abstractmethod
    def redefinition_token():
        """Изменить токен авторизации"""
        pass

    @abc.abstractmethod
    def redefinition_address():
        """Изменить сетевой адрес"""
        pass

    @abc.abstractmethod
    def deactivate():
        """Удалить токен авторизации"""
        pass

    @abc.abstractmethod
    def measurement():
        """Провести измерения"""
        pass

    @abc.abstractmethod
    def validate():
        """Утвердить данные"""
        pass

    @abc.abstractmethod
    def save():
        """Сохранить данные в БД"""
        pass


class Executor(abc.ABC):
    """АБК исполнительного устройства"""
    @abc.abstractmethod
    def redefinition_token():
        """Изменить токен авторизации"""
        pass

    @abc.abstractmethod
    def redefinition_address():
        """Изменить сетевой адрес"""
        pass

    @abc.abstractmethod
    def send_command():
        """Отправить команду на ИУ"""
        pass

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

class Room:
    """Класс помещения"""
    _temperature_sensors:list[Sensor] = []
    _humidity_sensors:list[Sensor] = []
    _outer_temperature_sensors:list[Sensor] = []
    _outer_humidity_sensors:list[Sensor] = []

    def __init__(self, name: str, db) -> None:
        self.name = name
        self.db = db
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

    def add_temperature_sensor(self, sensor:TemperatureSensor):
        pass

    def add_humidity_sensor(self, sensor):
        pass

    def add_outer_temperature_sensor(self, sensor:TemperatureSensor):
        pass

    def add_outer_humidity_sensor(self, sensor):
        pass



    def update_atmosphere_parameters(self):
        pass