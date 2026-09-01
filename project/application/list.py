from flet import *
from project.configuration.config_manager import ConfigManager
from project.station.camera.camera_manager import CameraManager
from project.station.robot.robot_controller import RobotController
from project.application.layers.workspace import create_workspace_layer
from project.application.layers.calibration import create_calibration_layer
from project.application.layers.measurement import create_measurements_layer
from project.application.layers.picture import create_picture_layer
# from project.application.layers.post_check import create_post_check_layer
from project.application.layers.guide import create_guide_layer
from project.application.layers.statistics import create_statistics_layer

def create_layers_list(config: 'ConfigManager',
                       robot: 'RobotController',
                       camera_manager: 'CameraManager') -> Tabs.tabs:
    """
    Создаёт и возвращает список слоёв (вкладок) приложения.
    Возвращает список объектов слоёв приложения.

    Args:
        config: Класс Конфигураций
        robot: Класс Манипулятора
        camera_manager: Класс-менеджер камер

    Returns:
        Tabs: Лист с вкладками приложения
    """
    tabs_list = [
        create_workspace_layer(config, camera_manager, robot),  # Проверка годности изделий
        create_calibration_layer(config, camera_manager, robot),  # Калибровка системы
        create_statistics_layer(config), # Статистика 
        create_picture_layer(config, camera_manager),  # Калибровка камеры и применение к ней фильтров
        create_measurements_layer(config, camera_manager),  # Измерение объектов на изображении
        create_guide_layer(config),  # Гид по программе
    ]

    return tabs_list
