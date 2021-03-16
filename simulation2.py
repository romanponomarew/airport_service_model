import pygame
import simpy
from environment import (PyGameEnvironment, FrameRenderer)
import time
import itertools
import random
import json
import sys

import time

AIRPLANE_ARRIVING_TIME = [3000, 7000]  # Прибытие самолета каждые [min, max] секунд
# Define constants for the screen width and height
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SIMULATION_SPEED = 0.0001  # 0.001 - NORMAL_speed, 0.0001 - FAST_speed, 0.0000000001 - MAX_speed
# Airplane_Settings####################
AIRPLANE_SPEED_X = 3
AIRPLANE_SPEED_Y = 10
# Loader_Settings######################
LOADER_SPEED_X = 3
LOADER_SPEED_Y = 2
NUMBER_OF_LOADERS = 3
# Truck_Settings######################
TRUCK_SPEED_X = 2
TRUCK_SPEED_Y = 3

"""Вспомогательные переменные для отображения количества агентов, координат"""
############################################################
stoyanka_counts = 0  # Кол-во самолетов на стоянке
warehouse_loaders = 0  # Кол-во команд грузчиков на складе

WAREHOSE_STATION_SIZE = 50  # Максимальное(изначальное) количество деталей на складе
THRESHOLD = 20  # Порог имеющихся деталей для заказа новых запчастей (в %)
number_station = 2

iteration = 0
WAREHOSE_MAX = 50
WAREHOSE_STATION_SIZE2 = WAREHOSE_MAX  # Максимальное(изначальное) количество деталей на складе


class Station:
    def __init__(self, number_of_station):
        self.number_of_station = number_of_station

        if self.number_of_station == 1:
            self.x = 285
            self.y = 280
            self.x_loaders = 0
            self.y_loaders = 230
        elif self.number_of_station == 2:
            self.x = 285
            self.y = 465
            self.x_loaders = 0
            self.y_loaders = 410
        elif self.number_of_station == 3:
            self.x = 0
            self.y = 0
            self.x_loaders = 0
            self.y_loaders = 0

        self.station_status = 0  # Занята или свободна(самолетом)
        self.stoyanka_to_station = 0  # Находится ли какой-нибудь самолет в пути от стоянки к станции
        self.station_repair = ""  # Статус ремонта самолета на станции - "repair"/"ready"
        self.repairing = ""  # Ведется ли сейчас ремонт на 1 станции? (now/done)-ожидание грузчиком и самолетом ремонта
        self.details_required = 0  # Сколько деталей требуются для починки самолета на станции

        self.loader_to_station = 0  # Находится ли кто-то из грузчиков в пути от склада к станции
        self.loaders_count_on_station = 0

    def change_station_status_to_busy(self, station_number, airplane_number):
        """
        При прибытии самолета на станцию обслуживания
        изменить ее статус на занятый ремонтом
        """
        global event, event_time

        self.station_status = 1
        if station_number == 1:
            self.stoyanka_to_station = 0

        elif station_number == 2:
            self.stoyanka_to_station = 0
        self.station_repair = "repair"
        self.details_required = random.randint(1, 30)
        event = f"Самолет{airplane_number} на ремонте(1)"
        event_time = round(env.now / 1000)


class Airplane:
    """
    Самолет - либо на стоянке, либо на станции тех.обслуживания(№1 или №2), либо покаидает аэропорт.
    Случайным образом выбирается количество запчастей, которые необходимо заменить.
    Методы перемещения и перерисовки самолета вызываются внутри метода RUN с бесконечным циклом.

    Описание методов самолета:
    1)перемещение на стоянку
    2)перемещение со стоянки на станцию тех.обслуживания
    3)перемещение со станции тех.обслуживания на взлетную полосу и вылет с аэропорта
    """

    def __init__(self, env, name):
        IMG_size = 60
        self.image = pygame.image.load("airplane4.png")  # Загрузка в pygame картинки
        self.image = pygame.transform.scale(self.image, (IMG_size, IMG_size))  # Изменение размера картинки
        self.x = 0  # Изначальное положение центра картинки
        self.y = 0
        self.env = env
        self.status_now = ""  # "on_parking", "on_station{№}", "to_station{№}", "from_station{№}"
        self.status = "arrived_on_airport"  # "on_parking", "on_service_station", "moving"
        self.name = name
        self.time_parking = 0  # Время прибытия на стоянку
        self.time_station = 0  # Время прибытия на станцию на ремонт
        self.time_leave = 0  # Самолет готов, покидает аэропорт
        self.time_result = 0  # Итоговое время пребывания самолета в аэропорту
        self.monitoring = ""  # Текущее событие самолета
        self.time_now = 0  # Время текущего события

        self.selected_station = 0  # Станция выбранная для обслуживания

    def arriving(self):
        """Прибытие самолета в аэропорт и перемещение на стоянку"""
        current_x_stoyanka = SCREEN_HEIGHT - 80  # Текущая координата Y для стоянки
        global stoyanka_counts
        global event, event_time
        # Движение по вертикали(Конечная координата зависит от того, сколько самолетов уже на стоянке):
        self.y += 5
        if self.y >= current_x_stoyanka - 60 * stoyanka_counts:
            self.y = current_x_stoyanka - 60 * stoyanka_counts
            # Движение по горизонтиали:
            self.x += 10
            # Удержание игрока в рамках окна
            if self.x > 56:
                self.x = 56
                self.status = "on_parking"
        # Увеличиваем количество самолетов на стоянке
        if self.status == "on_parking":
            stoyanka_counts = stoyanka_counts + 1
            self.time_parking = round(env.now / 1000)
            event = f"Самолет{self.name} на парковке"
            event_time = round(env.now / 1000)

    def go_to_free_station(self, selected_station):
        """Перемещение самолета от стоянки на СВОБОДНУЮ станцию обслуживания"""
        global stoyanka_counts
        global event_time, event

        station_number = selected_station.number_of_station
        # Движение по горизонтиали:
        self.x += AIRPLANE_SPEED_X
        if 150 < self.x < 154:
            self.x = 150  # Промежуточная координата м/у станциями - для смены движения
        #############################
        # Движение по вертикали(до станции обслуживания №2):
        self.y -= AIRPLANE_SPEED_Y
        if self.y <= selected_station.y:
            self.y = selected_station.y
            ###############################
            # Движение по горизонтиали:
            if self.x == 150:
                self.x = self.x + 5
            if self.x >= selected_station.x:
                self.x = selected_station.x
                self.status = "on_service_station"
            # Увеличиваем количество самолетов на стоянке
            if self.status == "on_service_station":
                selected_station.change_station_status_to_busy(station_number=int(station_number),
                                                               airplane_number=self.name)
                self.status_now = "on_station" + str(station_number)

    def checking_stations(self):
        """
        Выбор свободной станции обслуживания
        Уменьшаем кол-во самолетов на стоянке на 1 при отправлении к свободной станции обслжуивания
        """
        global stoyanka_counts
        for station_object in stations_objects:
            if self.status == "on_parking" and station_object.station_status == 0 and station_object.stoyanka_to_station == 0:
                if "to_station" not in self.status_now:
                    self.status_now = "to_station" + str(station_object.number_of_station)
                    station_object.stoyanka_to_station = 1
                if stoyanka_counts != 0:
                    stoyanka_counts -= 1
                    return station_object

    def counting_required_details(self):
        """
        При нахождении самолета на станции обслуживания происходит подсчет необходимых для ремонта деталей
        """
        for station_object in stations_objects:
            station_number = str(station_object.number_of_station)
            if self.status_now == ("on_station" + station_number) and station_object.station_repair == "ready":
                self.status_now = "from_station" + station_number
                station_object.station_status = 0
                station_object.details_required = 0

    def leaving_airport(self):
        """Самолеты покидают аэропорт со станций обслуживания"""
        # Движение по горизонтиали:
        self.x += 2
        if self.x > 440 and self.y != 600:
            self.x = 440
            # Движение по вертикали(до станции обслуживания №1):
            self.y += 3
            if self.y > 600:
                self.y = 600
        if self.x == 440 and self.y == 600:
            self.x += 3

    def stopping_simulation(self):
        """
        Останавливаем программу, когда последний самолет покидает АТБ
        """
        global event_time, event
        # self.monitoring = "Самолет1 улетает"
        # self.time_now = round(env.now / 1000)
        self.time_result = self.time_leave - self.time_parking
        print(f"Общее время нахождения самолета{self.name} в аэропорту ={self.time_result}")
        results.append(self.time_result)
        event = f"Самолет{self.name} улетает"
        event_time = round(env.now / 1000)
        if len(results) == 10:  # Когда покинет последний самолет
            with open('file.txt', 'w+') as fw:
                # записываем
                json.dump(results, fw)
            raise SystemExit

    def stopping_simulation_by_time(self):
        """
        Остановить симуляцию по истечению отведенного времени
        """
        environment_time = str(round(env.now / 1000))
        if int(environment_time) > 160:
            print(environment_time)
            raise SystemExit

    def run(self):
        simulation_run = True  # Переменная для остановки симуляции
        while True:
            # selected_station = 0
            # Прибытие самолета в аэропорт:
            if self.status == "arrived_on_airport":
                self.arriving()

            # Станция обслуживания выбирается только один раз для каждого из самолетов
            if not self.selected_station:
                self.selected_station = self.checking_stations()  # Выбор свободной станции обслуживания

            # # Перемещение самолета со стоянки на свободную станцию тех.обслуживания:
            if self.status == "on_parking":
                if ("to_station" in self.status_now) and self.selected_station:
                    yield self.env.timeout(100)
                    self.go_to_free_station(selected_station=self.selected_station)

            if self.status == "on_service_station":
                self.counting_required_details()
                # После ремонта(станция тех.обслуживания) самолет покидает аэропорт:
                if "from_station" in self.status_now:
                    self.leaving_airport()
                    if simulation_run:
                        self.time_leave = round(env.now / 1000)
                        simulation_run = False
                        self.stopping_simulation()
            yield self.env.timeout(20)

    def __call__(self, screen):
        # screen.blit(self.image, (self.x, self.y))  # Расположить картинку по координатам
        self.image1 = self.image.get_rect(topleft=(self.x, self.y))
        screen.blit(self.image, self.image1)


class Loader:
    """Команда грузчиков"""

    def __init__(self, env, number):
        self.number = number
        self.IMG_size = 45
        self.image = pygame.image.load("loader.png")  # Загрузка в pygame картинки
        self.image = pygame.transform.scale(self.image, (self.IMG_size, self.IMG_size))  # Изменение размера картинки
        self.x = 650  # Изначальное положение центра картинки(На складе)
        self.y = 380
        self.env = env
        self.status_now = ""  # "on_parking", "on_service_station", "moving"
        self.status = "in_warehouse"  # "on_service_station", "moving"
        self.repair_time = random.randint(1200, 2000)  # Среднее время ремонта на станции тех.обслуживания

        # self.search_time = random.randint(150, 300)   # Среднее время поиска 1 детали на складе(стандартные технологии)
        self.search_time = random.randint(33, 67)  # Среднее время поиска 1 детали на складе(технологии IoT)

        self.search_status = "search"
        self.warehose_status = "empty"  # "empty", "full"
        self.loader_details = 0  # Запчасти которые несет с собой грузчик от склада к станции

        self.requesting_station = 0  # Выбор станции, к которой нужно перенести детали со склада

    def to_service_station1(self):
        global env
        global WAREHOSE_STATION_SIZE2
        """Перемещение грузчиков от склада к станции тех.обслуживания №1"""
        self.x -= LOADER_SPEED_X
        if self.x < 450 and self.y != 410 and self.y != 230:
            self.x = 450

            """К станции тех.обслуживания №1:"""
            self.y -= LOADER_SPEED_Y
            if self.y < 230:
                self.y = 230

        if self.y == 230 or self.y == 410:
            self.x -= LOADER_SPEED_X
            if self.x < 400:
                self.x = 400
                self.status = "on_service_station1"
                self.image = pygame.image.load("loader_empty1.png")  # Загрузка в pygame картинки
                self.image = pygame.transform.scale(self.image,
                                                    (self.IMG_size, self.IMG_size))  # Изменение размера картинки
                station1.loaders_count_on_station = 1
                station1.loader_to_station = 0
                station1.repairing = "now"
        yield self.env.timeout(10)  ###### Для того чтобы можно было вызвать как генератор

    def to_service_station2(self):
        """Перемещение грузчиков от склада к станции тех.обслуживания №1"""
        self.x -= LOADER_SPEED_X
        if self.x < 450 and self.y != 410 and self.y != 230:
            self.x = 450
            """К станции тех.обслуживания №2:"""
            self.y += LOADER_SPEED_Y
            if self.y > 410:
                self.y = 410

        if self.y == 230 or self.y == 410:
            self.x -= (LOADER_SPEED_X - 1)
            if self.x < 400:
                self.x = 400
                self.status = "on_service_station2"
                self.image = pygame.image.load("loader_empty1.png")  # Загрузка в pygame картинки
                self.image = pygame.transform.scale(self.image,
                                                    (self.IMG_size, self.IMG_size))  # Изменение размера картинки
                station2.loaders_count_on_station = 1
                station2.loader_to_station = 0
                station2.repairing = "now"
        yield self.env.timeout(10)  ###### Для того чтобы можно было вызвать как генератор

    def go_to_requesting_details_station(self, requesting_station):  # TODO: safaf
        """
        Перемещение грузчиков от склада к станции тех.обслуживания,
        которой нужны запчасти со склада
        """
        number_of_station = requesting_station.number_of_station
        self.x -= LOADER_SPEED_X
        if self.x < 450 and self.y != 410 and self.y != 230:
            self.x = 450
            """К станции тех.обслуживания №2:"""
            self.y += LOADER_SPEED_Y
            if self.y > requesting_station.y_loaders:
                self.y = requesting_station.y_loaders

        if self.y == 230 or self.y == 410:
            self.x -= (LOADER_SPEED_X - 1)
            if self.x < 400:
                self.x = 400
                self.status = "on_service_station" + str(number_of_station)
                self.image = pygame.image.load("loader_empty1.png")  # Загрузка в pygame картинки
                self.image = pygame.transform.scale(self.image,
                                                    (self.IMG_size, self.IMG_size))  # Изменение размера картинки
                requesting_station.loaders_count_on_station = 1
                requesting_station.loader_to_station = 0
                requesting_station.repairing = "now"
                self.requesting_station = 0

        yield self.env.timeout(10)  ###### Для того чтобы можно было вызвать как генератор

    def to_warehouse(self):
        """Перемещение грузчиков от станции тех.обслуживания(1 или 2) к складу"""
        global warehouse_loaders
        self.x += LOADER_SPEED_X
        if self.x > 450 and self.y != 380:
            self.x = 450
            """От станции тех.обслуживания №2:"""
            # self.y -= 2
            # if self.y < 380:
            #     self.y = 380
            """От станции тех.обслуживания №1:"""
            self.y += LOADER_SPEED_Y
            if self.y > 380:
                self.y = 380

        if self.y == 380:
            self.x += LOADER_SPEED_X
            if self.x > 650:
                self.x = 650
                self.status = "in_warehouse"
                self.search_status = "search"
                self.image = pygame.image.load("loader.png")  # Загрузка в pygame картинки
                self.image = pygame.transform.scale(self.image,
                                                    (self.IMG_size, self.IMG_size))  # Изменение размера картинки
                warehouse_loaders += 1
                self.warehose_status = "empty"

    def checking_stations(self):
        """
        Проверка станций - выбор станции, к которой нужно перенсти детали со склада
        """
        for station_object in stations_objects:
            if self.status == "in_warehouse" and not station_object.loaders_count_on_station:
                if station_object.station_status and not station_object.loader_to_station:
                    station_object.loader_to_station = 1
                    return station_object

    def departure_from_warehouse_to_station(self, WAREHOSE_STATION_SIZE2, station_object):
        """
        Если грузчиком получен запрос станции о ремонте, он проверяет:
         1.находится ли кто-то из грузчиков уже в пути
         2.есть ли на складе нужные запчасти
        Забирает детали со склада и отправляется к нужной станции
        """
        global warehouse_loaders
        station_number = station_object.number_of_station
        # self.departure_from_warehouse_to_station(requesting_station=station_object)
        if "to_station" not in self.status_now:
            self.status_now = "to_station" + str(station_object.number_of_station)
        if warehouse_loaders != 0:
            warehouse_loaders -= 1
        if station_object.loader_to_station and self.status_now == f"to_station{station_number}" and WAREHOSE_STATION_SIZE2 > station_object.details_required:
            self.take_details_from_warehouse(details_required=station_object.details_required)

            if self.loader_details != 0:
                if self.search_status == "search":
                    yield self.env.timeout(
                        self.search_time * station_object.details_required)  # Время поиска запчастей для ст.тех.обсл.1 на складе
                    self.search_status = "done"
                if self.search_status == "done":
                    yield env.process(self.go_to_requesting_details_station(requesting_station=station_object))

    def take_details_from_warehouse(self, details_required):
        """
        Забрать необходимое кол-во деталей(для станции тех.обслуживания №1 или №2) со склада:
        Уменьшить кол-во деталей на складе
        """
        global WAREHOSE_STATION_SIZE2
        if self.warehose_status == "empty":
            WAREHOSE_STATION_SIZE2 -= details_required
            self.loader_details = details_required
            self.warehose_status = "full"

    def ordering_new_details(self):
        """
        Грузчики ищут на складе нужные для ремонта детали.
        Если деталей недостаточно, они сообщают грузовику отправится на производство за новыми запчастями
        """
        global WAREHOSE_STATION_SIZE2
        for station_object in stations_objects:
            if WAREHOSE_STATION_SIZE2 < station_object.details_required:
                # Ждем грузовик с новыми запчастями и пополняем запас склада
                if truck.status == "in_warehouse":
                    yield env.process(truck.to_production())
                # Грузовик находится на производстве:
                if truck.status == "on_production":
                    if truck.loading_status == "now":
                        yield env.process(truck.loading())
                        truck.loading_status = "done"
                    if truck.loading_status == "done":
                        yield env.process(truck.to_warehouse())
                        if truck.y == 240 and truck.x == 600:
                            WAREHOSE_STATION_SIZE2 = WAREHOSE_MAX

    def return_to_warehouse(self):
        """
        Если грузчик на станции обслуживания и там находится самолет, требующий ремонта -
        происходит ремонт, по завершению которого грузчик возвращается на склад
        """
        if "on_service_station" in self.status:
            self.status_now = "to_warehouse"
            for station_object in stations_objects:
                if station_object.repairing == "now" and self.status == "on_service_station" + str(
                        station_object.number_of_station):
                    yield self.env.timeout(self.repair_time)  # Время ремонта
                    self.loader_details = 0
                    if self.status == "on_service_station" + str(station_object.number_of_station):
                        station_object.repairing = "done"
                        station_object.station_repair = "ready"

                if self.status == "on_service_station" + str(station_object.number_of_station):
                    station_object.loaders_count_on_station = 0
            self.to_warehouse()

    def run(self):
        while True:
            # Станция обслуживания выбирается только один раз для каждого из самолетов
            if self.requesting_station:
                print(f"Грузчик №{self.number}, его requesting_station={self.requesting_station.number_of_station}")
            else:
                print(f"Грузчик №{self.number}, его requesting_station={self.requesting_station}")
            if not self.requesting_station:
                self.requesting_station = self.checking_stations()  # Выбор свободной станции обслуживания
            station_object = self.requesting_station

            # Грузчик отпраляется на запросившую ремонт станцию обслуживания
            if station_object:
                yield from self.departure_from_warehouse_to_station(WAREHOSE_STATION_SIZE2, station_object)

            # Говорим грузовику отпрваится на склад за новыми запчастями:
            yield from self.ordering_new_details()

            # Отправление грузчика при завершении ремонта со станции обратно на склад:
            yield from self.return_to_warehouse()
            yield self.env.timeout(50)

    def __call__(self, screen):
        self.image1 = self.image.get_rect(topleft=(self.x, self.y))
        screen.blit(self.image, self.image1)  # Расположить картинку по координатам


class Truck:
    """
    Грузовик:
        При количестве деталей на складе меньше допустимого предела - перемещается на производство,
        загружает детали и везет обратно на склад
    """

    def __init__(self, env):
        self.IMG_size = 70
        self.image = pygame.image.load("truck.png")  # Загрузка в pygame картинки
        self.image = pygame.transform.scale(self.image,
                                            (self.IMG_size + 20, self.IMG_size))  # Изменение размера картинки
        self.x = 600  # Изначальное положение центра картинки(Склад)
        self.y = 240
        # self.x = 660  # На производстве
        # self.y = 50
        self.env = env
        self.status_prev = ""  # "on_parking", "on_service_station", "moving"
        self.status = "in_warehouse"  # "on_production"
        # self.status = "on_production"
        self.loading_status = ""  # Загружается ли сейчас грузовик? ("now"/"done")

    def loading(self):
        yield self.env.timeout(1500)

    def to_production(self):
        """Перемещение грузовика от склада к производству/заводу"""
        global iteration
        global event_time, event
        self.y -= TRUCK_SPEED_Y
        if self.y < 50:
            self.y = 50

            self.x += TRUCK_SPEED_X
            if self.x > 660:
                self.x = 660
                self.status = "on_production"
                self.image = pygame.image.load("truck.png")  # Загрузка в pygame картинки
                self.image = pygame.transform.scale(self.image,
                                                    (self.IMG_size + 20, self.IMG_size))  # Изменение размера картинки
                iteration += 1
                self.loading_status = "now"
                event = "Грузовик на заводе"
                event_time = round(env.now / 1000)

        yield self.env.timeout(10)  # # Для того чтобы можно было вызвать как генератор

    def to_warehouse(self):
        """Перемещение грузовика от завода к складу"""
        global iteration
        global WAREHOSE_STATION_SIZE2
        global event, event_time
        self.x -= TRUCK_SPEED_X
        if self.x < 600:
            self.x = 600

            self.y += TRUCK_SPEED_Y
            if self.y > 240:
                self.y = 240
                self.status = "in_warehouse"
                self.image = pygame.image.load("truck.png")  # Загрузка в pygame картинки
                self.image = pygame.transform.scale(self.image,
                                                    (self.IMG_size + 20, self.IMG_size))  # Изменение размера картинки
                iteration += 1
                event = "Грузовик на складе"
                event_time = round(env.now / 1000)
        yield self.env.timeout(10)  # Для того чтобы можно было вызвать как генератор

    def __call__(self, screen):
        self.image1 = self.image.get_rect(topleft=(self.x, self.y))
        screen.blit(self.image, self.image1)  # Расположить картинку по координатам


class Monitoring:
    """Класс для отображения текста и состояния переменных"""

    def __init__(self, stoyanka_counts):
        self.stoyanka_counts = stoyanka_counts
        self.font = pygame.font.Font(None, 20)

    def parameter_displaying(self, text: str, parameter, x, y, indent=0):
        """
        Отображение текста и параметра на экране по переданным координатам
        params:
            indent - Отступ параметра от текста
        """
        display_text = self.font.render(text, True, (0, 0, 255))
        screen.blit(display_text, [x, y])
        display_parametr = self.font.render(str(parameter), True, (0, 0, 255))
        screen.blit(display_parametr, [x + 130 + indent, y])

    def __call__(self, screen):
        # Отображение текста на экране:
        airplanes_counts_text = "Кол-во самолетов:"
        loaders_counts_text = "Кол-во грузчиков:"
        details_required_text = "Требуется деталей:"

        # ################### Отображение кол-ва самолетов на стоянке: ###################
        self.parameter_displaying(text=airplanes_counts_text, parameter=stoyanka_counts, x=10, y=230)

        # ################### Отображение кол-ва самолетов на станции тех.обслуживания №1: ###################
        self.parameter_displaying(text=airplanes_counts_text, parameter=station1.station_status, x=250, y=215)
        # ################### Отображение кол-ва деталей на станции тех.обслуживания №1: ###################
        self.parameter_displaying(text=details_required_text, parameter=station1.details_required, x=240, y=165)
        # ################### Отображение кол-ва команд механиков на станции тех.обслуживания №1: ###################
        self.parameter_displaying(text=loaders_counts_text, parameter=station1.loaders_count_on_station, x=250, y=190)

        # ################### Отображение кол-ва самолетов на станции тех.обслуживания №2: ###################
        self.parameter_displaying(text=airplanes_counts_text, parameter=station2.station_status, x=250, y=390)
        # ################### Отображение кол-ва деталей на станции тех.обслуживания №2: ###################
        self.parameter_displaying(text=details_required_text, parameter=station2.details_required, x=240, y=340)
        # ################### Отображение кол-ва команд механиков на станции тех.обслуживания №2: ###################
        self.parameter_displaying(text=loaders_counts_text, parameter=station2.loaders_count_on_station, x=250, y=365)

        # ################### Отображение кол-ва команд грузчиков на складе: ###################
        self.parameter_displaying(text=loaders_counts_text, parameter=warehouse_loaders, x=778, y=300)
        # ################### Отображение кол-ва деталей на складе(2): ###################
        self.parameter_displaying(text="Кол-во деталей на складе:", parameter=WAREHOSE_STATION_SIZE2, x=778, y=325,
                                  indent=50)
        # From Monitoring1(Для отладки)
        # Отображение события:
        self.parameter_displaying(text="Событие:", parameter=event, x=550, y=440, indent=-50)
        # Время события:
        self.parameter_displaying(text="Время:", parameter=event_time, x=550, y=470, indent=-70)
        # Время в симуляции:
        self.parameter_displaying(text="Время симуляции:", parameter=round(env.now / 1000), x=550, y=620)


###########################################################
def airplane_generator(env, cars):
    """Генерируем новые самолеты, которые прибывают на обслуживание"""
    for i in itertools.count():
        yield env.timeout(random.randint(AIRPLANE_ARRIVING_TIME[0], AIRPLANE_ARRIVING_TIME[1]))
        if len(cars) != 0:
            a = cars.pop(0)
            renderer.add(a)
            env.process(a.run())


###########################################################


"""Описание игры"""
pygame.init()

event = ""  # Глобальное событие в системе
event_time = 0  # Время глобального события

##############################################################
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
renderer = FrameRenderer(screen)
env = PyGameEnvironment(renderer, factor=SIMULATION_SPEED, strict=False)  # factor - Для скорости воспроизведения модели
renderer.add(Monitoring(stoyanka_counts))

station1 = Station(number_of_station=1)
station2 = Station(number_of_station=2)
stations_objects = [station1, station2]

airplanes = [Airplane(env, i) for i in range(1, 11)]

mechanics = [Loader(env, number=i) for i in range(1, NUMBER_OF_LOADERS + 1)]
for mechanic in mechanics:
    renderer.add(mechanic)
    env.process(mechanic.run())

truck = Truck(env)
renderer.add(truck)

service_station = simpy.Resource(env, number_station)  # Общий ресурс - станции обслуживания
warehose = simpy.Container(env, WAREHOSE_STATION_SIZE, init=WAREHOSE_STATION_SIZE)  # Склад(контейнер) - механики /
# забирают/ детали, грузовик привозит новые

env.process(airplane_generator(env, airplanes))

results = []
print(results)

env.run()
print(results)
