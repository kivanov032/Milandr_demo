from flet import *
import threading
import os
import time
from pathlib import Path
from typing import Optional

from project.algorithms.core import main_algorithm
from project.algorithms.disk_space_monitor import detect_inspection_disk, DiskSpaceMonitor
from project.application.addition.colors import color_mode
from project.application.addition.dialogs import (show_error, show_warning, show_success, show_confirmation,
                                                  select_file, select_directory)
from project.application.addition.loadings import get_path
from project.application.layers.guide import admin_required
from project.configuration.config_manager import ConfigManager
from project.station.camera.camera_manager import CameraManager
from project.station.robot.robot_controller import RobotController
from project.application.data_work.wafer_visual import WaferMapVisual
from project.application.data_work.wafer_map_factory import WaferMapFactory
from project.application.data_work.wafer_map_bin_parser import WaferMapBinParser
from project.application.data_work.wafer_data import DieStatus
from project.application.data_work.protocol import Protocol
from project.application.addition.logger import logger
from project.application.tab_manager import tab_manager
from project.application.addition.exceptions import RobotException, CameraException, ValidationException, \
    ProtocolException, KnownSystemException


def create_workspace_layer(config: 'ConfigManager', camera_manager: 'CameraManager', robot: 'RobotController'):
    """
     Функция-конструктор вкладки "Инспекция кристаллов".

    :param config: Класс конфигураций
    :param camera_manager: Класс-менеджер камер
    :param robot: Экземпляр класса робота
    :return: flet.Tab вкладка "Проверка годности изделий"
    """
    wafer_map_visual: Optional['WaferMapVisual'] = None

    application_colors = color_mode(config)
    strict_validation = True  # Состояние чекбокса (метка строгой валидации в парсинге бинарного файла карты годности)
    buttons_state_cache = {}

    # === БАЗОВЫЕ ГРАФИЧЕСКИЕ ЭЛЕМЕНТЫ С ПОДДЕРЖКОЙ СОСТОЯНИЙ ===
    def create_button(active: bool = True, **kwargs) -> ElevatedButton:
        """
        Создает кнопку с поддержкой состояний (активная/неактивная)

        :param active: True - активная кнопка, False - неактивная
        :param kwargs: дополнительные параметры для переопределения (включая text_style, text_align и др.)
        :return: настроенная кнопка
        """
        # Извлекаем специфичные для текста параметры
        custom_text_style = kwargs.pop('text_style', None)
        custom_text_align = kwargs.pop('text_align', TextAlign.CENTER)

        if active:
            base_text_style = custom_text_style if custom_text_style else TextStyle(
                size=22, weight=FontWeight.BOLD
            )
            text_color = application_colors["text"]
            bg_color = application_colors["inactive"]
            disabled = False
        else:
            base_text_style = custom_text_style if custom_text_style else TextStyle(
                size=22, weight=FontWeight.BOLD
            )
            text_color = application_colors["unclickable"]
            bg_color = application_colors["top_bar"]
            disabled = True

        # Создаём внутренний Text, чтобы потом можно было менять его цвет
        inner_text = Text(
            value=kwargs.get("text", ""),
            text_align=custom_text_align,
            style=base_text_style,
            color=text_color,
        )

        base_style = ButtonStyle(
            shape=RoundedRectangleBorder(radius=20),
            overlay_color=application_colors["hover"],
            bgcolor=bg_color,
            animation_duration=300
        )

        # Убираем text из kwargs, он уже использован
        kwargs.pop('text', None)

        btn = ElevatedButton(
            width=kwargs.pop('width', 120),
            height=kwargs.pop('height', 54),
            style=base_style,
            disabled=disabled,
            content=Container(
                content=inner_text,
                alignment=alignment.center,
            ),
            **kwargs
        )

        # Сохраняем ссылки на важные объекты
        btn._inner_text = inner_text
        btn._bg_color = bg_color
        btn._text_color = text_color

        return btn

    def set_button_active(button: ElevatedButton, active: bool = True):
        """
        Устанавливает состояние кнопки (активная/неактивная)

        :param button: кнопка для изменения состояния
        :param active: True - активная, False - неактивная
        """
        if active:
            button.bgcolor = application_colors["inactive"]
            button.color = application_colors["text"]
            button.disabled = False
        else:
            button.bgcolor = application_colors["top_bar"]
            button.color = application_colors["unclickable"]
            button.disabled = True

        # Если у кнопки есть кастомный внутренний текст, обновим его цвет
        if hasattr(button, '_inner_text'):
            button._inner_text.color = button.color
            button._inner_text.update()
        # В любом случае обновляем саму кнопку
        button.update()

    def create_text_field(active: bool = False, **kwargs) -> TextField:
        """
        Создает поле ввода с поддержкой состояний (активное/неактивное)

        :param active: True - активное поле, False - неактивное (по умолчанию)
        :param kwargs: дополнительные параметры для переопределения (включая text_size, label_size)
        :return: настроенное поле ввода
        """
        # Извлекаем размеры текста из kwargs
        text_size = kwargs.pop('text_size', 14)  # Размер вводимого текста
        label_size = kwargs.pop('label_size', 12)  # Размер текста label

        if active:
            color = application_colors["text"]
            label_style_color = application_colors["text"]
            disabled = False
        else:
            color = application_colors["unclickable"]
            label_style_color = application_colors["unclickable"]
            disabled = True

        base_style = {
            "color": color,
            "bgcolor": application_colors["top_bar"],
            "border_color": application_colors["text"],
            "focused_border_color": application_colors["active"],
            "label_style": TextStyle(color=label_style_color, size=label_size),
            "text_style": TextStyle(color=color, size=text_size),
            "disabled": disabled
        }

        base_params = {
            "width": 120,
            "height": 48,
        }
        base_params.update(base_style)
        base_params.update(kwargs)

        return TextField(**base_params)

    def set_text_field_active(text_field: TextField, active: bool = True):
        """
        Устанавливает состояние поля ввода (активное/неактивное)

        :param text_field: поле ввода для изменения состояния
        :param active: True - активное, False - неактивное
        """
        if active:
            text_field.color = application_colors["text"]
            text_field.label_style = TextStyle(color=application_colors["text"])
            text_field.disabled = False
        else:
            text_field.color = application_colors["unclickable"]
            text_field.label_style = TextStyle(color=application_colors["unclickable"])
            text_field.disabled = True

        text_field.update()

    def create_scale_button(text, position):
        """
        Создает кнопку шага в стиле второго слоя

        :param text: Текст на кнопке
        :param position: Позиция ("first", "middle", "last")
        :return: ElevatedButton
        """
        step_button_configs = {
            "first": {"radius": border_radius.only(12, 0, 12, 0)},
            "middle": {"radius": 0},
            "last": {"radius": border_radius.only(0, 12, 0, 12)},
        }

        config = step_button_configs[position]

        # Изначально кнопки неактивными
        return ElevatedButton(
            text=text,
            width=104,
            height=40,
            style=ButtonStyle(
                shape=RoundedRectangleBorder(radius=config["radius"]),
                overlay_color=application_colors["hover"],
                bgcolor=application_colors["top_bar"],
                color=application_colors["unclickable"],
                text_style=TextStyle(size=22, weight=FontWeight.BOLD),
                animation_duration=300,
            ),
            disabled=True,
        )

    # === ГРАФИЧЕСКИЕ ЭЛЕМЕНТЫ ===

    # === Текстовые поля для ввода значений ===

    # Заголовок над группой параметров
    grid_params_title = Container(
        content=Text(
            "Расстояние между центрами кристаллов:",
            size=22,
            weight=FontWeight.BOLD,
            color=application_colors["text"],
            text_align=TextAlign.CENTER,
        ),
        alignment=alignment.center,
    )

    # Поле для ввода расстояния по горизонтали
    grid_width_input = create_text_field(
        active=False,
        label="По X (мм)",
        value=str(config.wafer_params["x_distance"]),
        text_size=22,
        label_size=22,
        width=110,
        height=50,
    )

    # Поле для ввода расстояния по вертикали
    grid_height_input = create_text_field(
        active=False,
        label="По Y (мм)",
        value=str(config.wafer_params["y_distance"]),
        text_size=22,
        label_size=22,
        width=110,
        height=50,
    )

    # Кнопка активации полей для ввода новых параметров пластины (активная по умолчанию)
    change_wafer_params_btn = create_button(
        active=True,
        text="Изменить",
        width=150
    )

    # Кнопка сохранения введённых параметров визуализации пластины (неактивная по умолчанию)
    update_wafer_params_btn = create_button(
        active=False,
        text="Сохранить",
        width=150
    )

    # Строка с кнопками и полями
    grid_controls_row = Row(
        controls=[
            change_wafer_params_btn,
            grid_width_input,
            grid_height_input,
            update_wafer_params_btn,
        ],
        alignment=MainAxisAlignment.CENTER,
        spacing=15,
    )

    height_image = 800
    width_image = 580

    # Левый контейнер для изображений с камеры
    left_image_container = Container(
        content=Image(src=get_path(False), fit=ImageFit.FILL, height=height_image, width=width_image),
        height=height_image,
        width=width_image,
        bgcolor=application_colors["background"],
        border_radius=10,
        alignment=alignment.center,
    )

    # Правый контейнер для изображений с камеры
    right_image_container = Container(
        content=Image(src=get_path(False), fit=ImageFit.FILL, height=height_image, width=width_image),
        height=height_image,
        width=width_image,
        bgcolor=application_colors["background"],
        border_radius=10,
        alignment=alignment.center,
    )

    # Начальное состояние - просьба выбрать файл
    initial_container = Container(
        content=Column(
            controls=[
                Icon(Icons.FILE_UPLOAD_OUTLINED, size=80, color=application_colors["unclickable"]),
                Container(height=20),
                Text("Выберите файл карты годности\n(.bin или без расширения)\nили json-отчет",
                     size=30,
                     text_align=TextAlign.CENTER,
                     color=application_colors["unclickable"])
            ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
        ),
        width=600,
        height=600,
        alignment=alignment.center,
        bgcolor=application_colors["background"]
    )

    # Контейнер для загрузочного экрана
    loading_container = Container(
        content=Column(
            controls=[
                ProgressRing(width=100, height=100, color=application_colors["active"]),
                Container(height=30),
                Text("Загрузка карты...", size=30, color=application_colors["text"])
            ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
        ),
        width=600,
        height=600,
        alignment=alignment.center,
        bgcolor=application_colors["background"],
    )

    # Контейнер для сетки (изначально скрыт)
    button_grid = Container(
        width=600,
        height=600,
        clip_behavior=ClipBehavior.HARD_EDGE,
        bgcolor=application_colors["background"],
        alignment=alignment.center
    )

    # Основной контейнер, который будет меняться
    dynamic_grid_container = Container(
        alignment=alignment.center,
        content=initial_container  # Начинаем с просьбы выбрать файл
    )

    # Кнопка, активирующая поля для ввода новых характеристик пластины (активная по умолчанию)
    download_wafer_map_btn = create_button(
        active=True,
        text="Загрузить файл карты годности",
        width=370
    )

    # Флаг строгой валидации (по умолчанию включен)
    strict_validation_checkbox = Container(
        content=Row(
            controls=[
                # Контейнер для самого чекбокса
                Container(
                    content=Icon(
                        name=Icons.CHECK if strict_validation else "",
                        size=42,
                        color=application_colors["text"],
                    ),
                    width=50,
                    height=50,
                    border_radius=12,
                    border=border.all(3, application_colors["text"]),
                    bgcolor=application_colors["background"],
                    alignment=alignment.center
                ),
                # Текст с переносом
                Container(
                    content=Column(
                        controls=[
                            Text("Строгая",
                                 size=21,
                                 weight=FontWeight.BOLD,
                                 color=application_colors["text"]),
                            Text("валидация",
                                 size=21,
                                 weight=FontWeight.BOLD,
                                 color=application_colors["text"]),
                        ],
                        spacing=0,
                    ),
                    padding=padding.only(left=10),
                )
            ],
            alignment=MainAxisAlignment.START,
            vertical_alignment=CrossAxisAlignment.CENTER,
        ),
        bgcolor=application_colors["background"],
        border_radius=5,
        padding=padding.all(5),
    )

    # Контейнер с кнопками управления загрузки данных с пластины
    download_wafer_map_controls_container = Row(
        controls=[
            download_wafer_map_btn,
            Container(width=5),
            strict_validation_checkbox
        ],
        alignment=MainAxisAlignment.CENTER,
        spacing=10,
    )

    # Группа: заголовок НАД строкой с кнопками и полями
    grid_controls_container = Column(
        controls=[
            grid_params_title,
            Container(height=2),
            grid_controls_row,
        ],
        alignment=MainAxisAlignment.CENTER,
        horizontal_alignment=CrossAxisAlignment.CENTER,
    )

    # Выбор масштаба кнопок, визуализирующих кристаллы
    scale_crystal_buttons = Row(
        controls=[
            Text(
                value="Масштаб кнопок: ",
                size=22,
                weight=FontWeight.BOLD,
                color=application_colors["text"]
            ),
            Container(width=12),
            create_scale_button("1x", "first"),
            create_scale_button("1,5x", "middle"),
            create_scale_button("2x", "last"),
        ],
        alignment=MainAxisAlignment.CENTER,
        spacing=5
    )

    # Собираем ссылки на кнопки масштаба
    scale_buttons = []
    for control in scale_crystal_buttons.controls[2:]:
        scale_buttons.append(control)

    # Контейнер c визуализацией пластины и кнопками взаимодействия с ней
    center_column = Column(
        controls=[
            Container(height=1),
            Row(
                controls=[
                    Text("Визуализация пластины", size=26, weight=FontWeight.BOLD,
                         color=application_colors["text"]),
                ],
                alignment=MainAxisAlignment.CENTER,
            ),
            scale_crystal_buttons,
            Container(height=4),
            dynamic_grid_container,
            download_wafer_map_controls_container,
            grid_controls_container,
            Container(height=60),
        ],
        alignment=MainAxisAlignment.CENTER,
        horizontal_alignment=CrossAxisAlignment.CENTER,
    )

    # Кнопка "Определить типы детектируемых кристаллов"
    change_detectable_dice_btn = create_button(
        active=False,
        text="Определить типы\nдетектируемых кристаллов",
        width=340,
        height=70,
    )

    # Кнопка "Обновить протокол"
    update_protocol_btn = create_button(
        active=False,
        text="Обновить\nпротокол",
        width=150,
        height=70
    )

    change_detectable_dice_container = Row(
        controls=[
            update_protocol_btn,
            change_detectable_dice_btn,
        ],
        alignment=MainAxisAlignment.CENTER,
        spacing=40,
    )

    # Кнопка "Запуск" (активная по умолчанию)
    start_AOI_btn = create_button(
        active=True,
        text="Запуск"
    )

    # Кнопка "Пауза" (неактивная по умолчанию)
    pause_AOI_btn = create_button(
        active=False,
        text="Пауза"
    )

    # Кнопка "Продолжить" (неактивная по умолчанию)
    continue_AOI_btn = create_button(
        active=False,
        text="Продолжить",
        width=170
    )

    # Кнопка "Стоп" (неактивная по умолчанию)
    stop_AOI_btn = create_button(
        active=False,
        text="Стоп"
    )

    # Контейнер правых кнопок
    inspection_buttons = Row(
        controls=[
            start_AOI_btn,
            pause_AOI_btn,
            continue_AOI_btn,
            stop_AOI_btn,
        ],
        alignment=MainAxisAlignment.CENTER,
        spacing=15,
    )

    # Левый контейнер
    left_column = Column(
        controls=[
            Text("Оригинальное изображение", size=26, weight=FontWeight.BOLD, color=application_colors["text"]),
            left_image_container,
            change_detectable_dice_container,
            Container(height=50),
        ],
        alignment=MainAxisAlignment.CENTER,
        horizontal_alignment=CrossAxisAlignment.CENTER,
    )

    # Правый контейнер
    right_column = Column(
        controls=[
            Text("Изображение с дефектами", size=26, weight=FontWeight.BOLD, color=application_colors["text"]),
            right_image_container,
            Container(height=1),
            inspection_buttons,
            Container(height=50),
        ],
        alignment=MainAxisAlignment.CENTER,
        horizontal_alignment=CrossAxisAlignment.CENTER,
    )

    workspace_tab = Tab(
        text="Инспекция кристаллов",
        content=Container(
            content=Row(
                controls=[
                    left_column,
                    Container(expand=0),
                    center_column,
                    Container(expand=0),
                    right_column,
                ],
                alignment=MainAxisAlignment.CENTER,
                vertical_alignment=CrossAxisAlignment.CENTER,
            ),
            padding=10,
            bgcolor=application_colors["background"],
        ),
    )

    def validate_input_file_path(file_path_wafer_map: str) -> str:
        """
        Проверяет, является ли файл бинарным или json

        Args:
            file_path_wafer_map: Путь к файлу с бинарником

        Returns:
            str: Тип файла в случае принадлежности файла к допустимым, иначе ""
        """
        if not file_path_wafer_map or not os.path.exists(file_path_wafer_map):
            return ""

        file_name = os.path.basename(file_path_wafer_map)

        if '.' not in file_name:
            return "bin"

        extension = os.path.splitext(file_name)[1].lower()
        if extension == '.bin':
            return "bin"
        elif extension == '.json':
            return "json"

        return ""

    def download_wafer_map_handler(_e):
        """
        Обработчик нажатия на кнопку "Загрузить файл с картой годности".
        Показывает загрузку, затем генерирует сетку на основе загруженных данных.
        """
        page = _e.page

        # Открытие диалога выбора файла
        input_file_path = select_file(
            initial_dir=config.input_file_path,
            title="Выберите бинарный файл карты годности или json-отчет",
            filetypes=[
                ("Все файлы", "*"),
                ("Бинарные файлы (.bin)", "*.bin"),
                ("JSON-файлы (.json)", "*.json"),
            ]
        )

        if not input_file_path:
            return

        # Определение типа файла
        extension_file = validate_input_file_path(input_file_path)
        if extension_file == "":
            show_error("Некорректный формат файла",
                       "Выберите файл с расширением .bin, .json или файл без расширения",
                       page, config)
            logger.warning(f"Выбран файл некорректного формата: {input_file_path}")
            return

        config.input_file_path = str(Path(input_file_path).parent.as_posix())

        try:
            if extension_file == 'bin':

                # Открытие диалога выбора папки для сохранения протокола
                protocol_path = select_directory(
                    initial_dir=config.protocol_path,
                    title="Выберите папку, в которой будет протокол текущей пластины",
                )

                if not protocol_path:
                    return

                if not os.path.exists(protocol_path):
                    show_error("Неправильный путь к папке",
                               f"Папки {protocol_path} не существует выберете другой путь",
                               page, config)
                    logger.warning(f"Выбрана несуществующая папка: {protocol_path}")
                    return

        except Exception as e:
            logger.error(f"Ошибка при обработки входных данных: {e}")
            show_error("Ошибка при обработки входных данных",
                       "Точная причина неизвестна", page, config)

        protocol: Optional['Protocol'] = Protocol()

        active_all_buttons(False)
        deactivate_scale_buttons()
        dynamic_grid_container.content = loading_container
        page.update()

        # Запускаем асинхронную загрузку
        async def load_wafer_map_async():
            try:
                if extension_file == 'bin':
                    parser = WaferMapBinParser(
                        file_path=input_file_path,
                        strict_validation_check=strict_validation
                    )
                    parser.parse()

                    wafer_map = WaferMapFactory.from_bin_parser(parser, config)

                    config.protocol_path = protocol.create_protocol(
                        protocol_path=protocol_path,
                        wafer_map_bin_file_path=input_file_path,
                        wafer_map=wafer_map
                    ).parent.as_posix()

                else:
                    wafer_map = WaferMapFactory.from_json_protocol(input_file_path)

                    config.protocol_path = (
                        protocol.load_config_from_json(json_file_path=input_file_path)
                    ).parent.as_posix()

                wafer_map.protocol = protocol
                wafer_map.protocol.update_protocol(wafer_map)

                nonlocal wafer_map_visual
                wafer_map_visual = WaferMapVisual(application_colors, config)
                grid_view = wafer_map_visual.generate_visual(
                    wafer_map=wafer_map,
                    scale_value=config.scale_buttons_panel
                )

                button_grid.content = grid_view
                dynamic_grid_container.content = button_grid

                await page.update_async()

                if not (wafer_map_visual and wafer_map_visual.wafer_map):
                    show_error("Ошибка генерации карты годности",
                               "Модель карты годности не была сгенерирована",
                               page, config)
                    return

                show_success("Успешная загрузка карты годности",
                             "Произведён парсинг входного бинарного файла.\nCгенерированы папки протоколов.",
                             page, config)
                logger.info(f"Карта годности успешно загружена из файла: {input_file_path}")

                return

            except (ProtocolException, KnownSystemException) as e:
                show_error("Ошибка при обработке входных данных", str(e), page, config)

            except ValidationException as e:
                show_error("Ошибка валидации бинарного файла карты годности", str(e), page, config)

            except Exception as e:
                logger.error(f"Ошибка при обработке входных данных: {e}")
                show_error("Ошибка при обработке входных данных",
                           "Точная причина неизвестна", page, config)

            finally:
                active_all_buttons(True)
                if dynamic_grid_container.content != button_grid:
                    dynamic_grid_container.content = initial_container
                else:
                    set_button_active(change_detectable_dice_btn, True)
                    set_button_active(update_protocol_btn, True)
                    activate_scale_buttons()
                await page.update_async()

        time.sleep(0.1)
        page.run_task(load_wafer_map_async)

    def toggle_strict_validation_handler(_e):
        """Функция переключения состояния метки строгой валидации парсинга бинарника"""
        nonlocal strict_validation
        strict_validation = not strict_validation

        checkbox_icon = strict_validation_checkbox.content.controls[0].content
        checkbox_icon.name = Icons.CHECK if strict_validation else ""
        strict_validation_checkbox.update()

    @admin_required(config)
    def change_wafer_params_handler(_e):
        """Только для админа"""
        set_button_active(download_wafer_map_btn, False)
        set_button_active(change_wafer_params_btn, False)
        set_button_active(update_wafer_params_btn, True)
        set_text_field_active(grid_width_input, True)
        set_text_field_active(grid_height_input, True)

    def update_wafer_params_handler(_e):
        """
        Меняет данные параметры кристаллов, введённые в соответствующие.
        Обновляет основную модель данных WaferMap, если она уже есть.
        """
        try:
            # Изъятие данных из полей ввода и их валидация
            cell_size_x_mm = max(1.0, min(10.0, float(grid_width_input.value)))
            cell_size_y_mm = max(1.0, min(10.0, float(grid_height_input.value)))

            if not (config.wafer_params["x_distance"] == cell_size_x_mm
                    and config.wafer_params["y_distance"] == cell_size_y_mm):

                nonlocal wafer_map_visual
                if wafer_map_visual is not None and wafer_map_visual.wafer_map is not None:
                    wafer_map = wafer_map_visual.wafer_map
                    if wafer_map is not None:
                        active_all_buttons(False)
                        wafer_map.cell_size_x_mm = cell_size_x_mm
                        wafer_map.cell_size_y_mm = cell_size_y_mm
                        wafer_map.update_die_coordinates(is_need_update=True)
                        active_all_buttons(True)

                config.wafer_params = {"x_distance": cell_size_x_mm, "y_distance": cell_size_y_mm}

                # Обновление полей
                grid_width_input.value = str(cell_size_x_mm)
                grid_height_input.value = str(cell_size_y_mm)

                grid_width_input.update()
                grid_height_input.update()

                logger.info(f"Новые параметры с кристалла ({cell_size_x_mm}x{cell_size_y_mm}) мм сохранены")

            # Восстанавливаем состояния элементов
            set_button_active(change_wafer_params_btn, True)
            set_button_active(download_wafer_map_btn, True)
            set_button_active(update_wafer_params_btn, False)
            set_text_field_active(grid_width_input, False)
            set_text_field_active(grid_height_input, False)

        except ValueError as e:
            show_error("Ошибка при изменении параметров кристаллов",
                       "Введены некорректные значения. Должны быть положительные числа.",
                       _e.page, config)
            logger.warning(f"Ошибка в вводе новых значений пластины: {e}")

        except Exception as e:
            show_error("Ошибка в изменении данных пластины",
                       "Точная причина не известна",
                       _e.page, config)
            logger.warning(f"Ошибка в вводе новых значений пластины: {e}")

    algorithm_thread = None
    stop_event = threading.Event()
    pause_event = threading.Event()

    def run_AOI_algorithm():
        """Работа главного алгоритма (режим инспекции)."""
        page = config.page
        try:
            while not stop_event.is_set():
                if pause_event.is_set():
                    logger.debug("Алгоритм на паузе, ожидание...")
                    pause_event.wait(timeout=0.5)
                    continue

                wafer_map = wafer_map_visual.wafer_map
                wafer_map.update_stats()

                count_need_check_dice = wafer_map.get_count_dice_of_status(status=DieStatus.NEED_CHECK)
                count_checked_dice = main_algorithm(
                    wafer_map_visual=wafer_map_visual,
                    robot=robot,
                    camera_manager=camera_manager,
                    config=config,
                    left_image_container=left_image_container,
                    right_image_container=right_image_container,
                    stop_event=stop_event,
                    pause_event=pause_event,
                    on_pause_request=pause_AOI_handler,
                )

                success = True
                wafer_map.update_stats()
                error_message_protocols = wafer_map.protocol.check_flag_update_files_success()
                if error_message_protocols is not None:
                    show_error("Ошибка обновления протоколов",
                               error_message_protocols,
                               page, config)
                    success = False

                if count_need_check_dice != count_checked_dice:
                    comparison = "МЕНЬШЕ" if count_checked_dice < count_need_check_dice else "БОЛЬШЕ"
                    error_message = (f"Количество проверенных кристаллов ({count_checked_dice}) {comparison}"
                                     f" заявленного ({count_need_check_dice})")
                    show_warning("Предупреждение", error_message, page, config)
                    logger.warning(error_message)
                    success = False

                if success:
                    success_message = (f"Корректно проинспектировано {count_checked_dice} кристаллов "
                                       f"из {count_need_check_dice} запланированных.")
                    show_success("Инспекция успешно выполнена!",
                                 success_message,
                                 page, config)
                    logger.info(success_message)

                stop_AOI_handler()
                break

        except RobotException as e:
            show_error("Ошибка Манипулятора в режиме инспекции", e, page, config)
            stop_AOI_handler()

        except CameraException as e:
            show_error("Ошибка Камеры в режиме инспекции", e, page, config)
            stop_AOI_handler()

        except KnownSystemException as e:
            show_error("Системная ошибка в режиме инспекции", e, page, config)
            stop_AOI_handler()

        except Exception as e:
            show_error("Системная ошибка в режиме инспекции",
                       "Неизвестная ошибка",
                       page, config)
            logger.error(f"Ошибка в режиме инспекции: {e}")
            stop_AOI_handler()

    def start_AOI_handler(_e):
        """Событие на нажатие кнопки "Запуск"."""
        page = _e.page

        if config.sharpness_ideal <= 0 or wafer_map_visual.wafer_map.orientation.z_coord_of_first_reference_die is None:
            show_error("Ошибка настройки автофокуса",
                       "Эталонное значение резкости неизвестно, поскольку автофокус ни разу не был произведен",
                       page, config)
            logger.warning(f"Автофокус перед инспекцией не был произведен")
            return

        if not (wafer_map_visual and wafer_map_visual.wafer_map):
            show_error("Ошибка моделей данных",
                       "Отсутствуют данные по пластине или её визуальная модель",
                       page, config)
            logger.warning("Отсутствуют данные по пластине или её визуальная модель")
            return

        ret, error_message = wafer_map_visual.wafer_map.validate()
        if not ret:
            show_error("Ошибка калибровочных данных", error_message, page, config)
            logger.warning(f"Ошибка калибровочных данных:  {error_message}")
            return

        if not DiskSpaceMonitor(disk_path=detect_inspection_disk(), config=config).check_before_inspection():
            return

        wafer_map_visual.reset_all_reference_visualization()  # Удаление визуальной детекции референсных кристаллов
        wafer_map_visual.inspection_active = True  # Блокировка нажатия на Canvas
        wafer_map_visual.wafer_map.update_stats()  # Обновление статистики у программной модели пластины

        nonlocal algorithm_thread
        if algorithm_thread is None or (algorithm_thread is not None and not algorithm_thread.is_alive()):
            # Сбрасываем события
            stop_event.clear()
            pause_event.clear()

            disconnect_all_cams(_e)  # Останавливаем трансляции с камер
            tab_manager.block_tabs(["Инспекция кристаллов", "Руководство оператора"])  # Блокировка табов

            # Устанавливаем состояния кнопок
            active_all_buttons(False)
            deactivate_scale_buttons()
            set_button_active(start_AOI_btn, False)
            set_button_active(pause_AOI_btn, True)
            set_button_active(continue_AOI_btn, False)
            set_button_active(stop_AOI_btn, True)

            time.sleep(0.5)
            algorithm_thread = threading.Thread(target=run_AOI_algorithm, daemon=True)
            algorithm_thread.start()

            # Начинаем сессию инспекции (без записи времени начала в JSON)
            wafer_map_visual.wafer_map.protocol.start_timer()
            logger.info("Инспекция запущена")

    def pause_AOI_handler(_e=None):
        """Событие на нажатие кнопки "Пауза"."""
        if not stop_event.is_set() and not pause_event.is_set():
            if wafer_map_visual and wafer_map_visual.wafer_map:
                wafer_map_visual.wafer_map.protocol.stop_timer()

            set_button_active(pause_AOI_btn, False)
            set_button_active(continue_AOI_btn, True)
            set_button_active(update_protocol_btn, True)
            activate_scale_buttons()

            pause_event.set()  # Устанавливаем паузу
            tab_manager.show_all_tabs()  # Разблокирование табов
            wafer_map_visual.inspection_active = False  # Разблокирование нажатие на Canvas

            logger.info("Алгоритм приостановлен")

    def continue_AOI_handler(_e=None):
        """Событие на нажатие кнопки "Продолжить"."""
        if pause_event.is_set():
            if wafer_map_visual and wafer_map_visual.wafer_map:
                wafer_map_visual.wafer_map.protocol.start_timer()

            set_button_active(pause_AOI_btn, True)
            set_button_active(continue_AOI_btn, False)
            set_button_active(update_protocol_btn, False)
            deactivate_scale_buttons()

            pause_event.clear()  # Снимаем паузу
            tab_manager.block_tabs(["Инспекция кристаллов", "Руководство оператора"])  # Блокировка табов
            wafer_map_visual.inspection_active = True  # Блокировка нажатия на Canvas

            logger.info("Инспекция продолжена")

    def stop_AOI_handler(_e=None):
        """Событие на нажатие кнопки "Стоп"."""
        nonlocal algorithm_thread

        if stop_event.is_set():
            return

        def execute_stop():
            """Выполняет фактическую остановку алгоритма"""
            nonlocal algorithm_thread
            page = config.page

            stop_event.set()
            pause_event.clear()

            #  Чистим окна с изображениями
            left_image_container.content.src_base64 = ""
            left_image_container.update()
            right_image_container.content.src_base64 = ""
            right_image_container.update()

            wafer_map_visual.inspection_active = False  # Разблокирование нажатие на Canvas

            disconnect_all_cams(_e)  # Останавливаем трансляции с камер

            wafer_map = wafer_map_visual.wafer_map
            try:
                if wafer_map_visual and wafer_map_visual.wafer_map:
                    wafer_map_visual.wafer_map.protocol.stop_timer()

                wafer_map.protocol.update_protocol(wafer_map)

            except ProtocolException as ex:
                show_error("Ошибка обновления протоколов", str(ex), page, config)

            except KnownSystemException as ex:
                show_error("Системная ошибка при обработке карты годности", str(ex), page, config)

            except ValidationException as ex:
                show_error("Ошибка валидации бинарного файла карты годности", str(ex), page, config)

            except Exception as ex:
                logger.error(f"Ошибка при обработке карты годности: {ex}")
                show_error("Ошибка при обработке карты годности",
                           "Точная причина неизвестна", page, config)

            tab_manager.show_all_tabs()  # Разблокирование табов

            # Активируем все кнопки
            active_all_buttons(True)
            activate_scale_buttons()

            wafer_map.orientation.reset_first_reference_die(is_notify=False)
            wafer_map.orientation.reset_second_reference_die(is_notify=False)
            wafer_map.orientation.reset_rotation_angle(is_notify=True)

            # Дожидаемся завершения потока (не блокируя UI)
            def wait_for_thread():
                if algorithm_thread and algorithm_thread.is_alive() and algorithm_thread != threading.current_thread():
                    algorithm_thread.join(timeout=2.0)
                    if algorithm_thread.is_alive():
                        logger.warning("Поток алгоритма не завершился за 2 секунды")

            threading.Thread(target=wait_for_thread, daemon=True).start()

        # Если вызвано без события (из потока) - останавливаем сразу без диалога
        if _e is None:
            execute_stop()
            logger.info("Остановка потока алгоритма инспекции")
            return

        page = _e.page
        was_paused = pause_event.is_set()
        if not was_paused:
            pause_event.set()
            logger.debug("Алгоритм приостановлен для подтверждения остановки")

        def on_confirm(e):
            """ Оператор подтвердил остановку. """
            page.dialog.open = False
            page.update()

            execute_stop()
            logger.info("Инспекция остановлена оператором")

        def on_cancel(e):
            """ Оператор отменил остановку. """
            if not was_paused:
                pause_event.clear()
                logger.debug("Инспекция возобновлена после отмены остановки")

            page.dialog.open = False
            page.update()
            logger.info("Оператор отменил остановку инспекции")

        show_confirmation(
            title="Остановка алгоритма",
            message="После остановки инспекции её уже не возобновить с места остановки.\n"
                    "В случае повторного запуска инспекция запустится сначала.\n"
                    "Вы действительно хотите остановить алгоритм?\n",
            page=page,
            config=config,
            on_confirm=on_confirm,
            on_cancel=on_cancel,
            confirm_text="Подтвердить",
            cancel_text="Отмена"
        )

    def disconnect_all_cams(_e=None):
        page = config.page if _e is None else _e.page
        try:
            camera_manager.disconnect_all_cams()
        except CameraException as e:
            logger.error(f"Ошибка Камеры: {e}")
            show_error("Ошибка Камеры", e, page, config)
        except Exception as e:
            logger.error(f"Ошибка Камеры: {e}")
            show_error("Ошибка Камеры", "Неизвестная ошибка", page, config)

    def change_detectable_dice_handler(_e):
        """ Обработчик нажатия на кнопку "Определить типы детектируемых кристаллов"."""
        page = _e.page

        if wafer_map_visual is None or wafer_map_visual.wafer_map is None:
            return

        symbol_stats = wafer_map_visual.wafer_map.get_stats()
        current_selected_list = wafer_map_visual.wafer_map.symbols_need_check

        if symbol_stats is None or current_selected_list is None:
            logger.error("Ошибка определения типов кристаллов")
            show_error("Ошибка определения типов кристаллов",
                       "Невозможно выбрать типы детектируемых кристаллов",
                       _e.page, config)
            return

        # Проверяем, есть ли уже BAD или GOOD кристаллы
        has_inspected_dice = (
                wafer_map_visual.wafer_map.get_count_dice_of_status(DieStatus.BAD) > 0 or
                wafer_map_visual.wafer_map.get_count_dice_of_status(DieStatus.GOOD) > 0
        )

        # Сохраняем оригинальный список при первом открытии диалога после загрузки пластины
        if not hasattr(change_detectable_dice_handler, '_original_symbols_list_initialized'):
            if has_inspected_dice:
                # Если пластина уже была инспектирована, сохраняем текущий список как оригинальный
                change_detectable_dice_handler._original_symbols_list = current_selected_list.copy()
                logger.debug(f"Сохранен оригинальный список symbols_need_check: {current_selected_list}")
            else:
                # Если пластина не инспектирована, оригинального списка нет
                change_detectable_dice_handler._original_symbols_list = None
            change_detectable_dice_handler._original_symbols_list_initialized = True

        # Фильтруем символы: убираем 'D' и сортируем по убыванию количества
        available_symbols = [
            (symbol, count) for symbol, count in symbol_stats.items()
            if symbol != 'D'
        ]
        # Сортируем по количеству (по убыванию)
        available_symbols.sort(key=lambda x: x[1], reverse=True)

        # Создаем отсортированный список символов и соответствующий словарь статистики
        sorted_symbol_stats = {symbol: count for symbol, count in available_symbols}
        sorted_symbols_list = [symbol for symbol, _ in available_symbols]

        current_selected_set = set(current_selected_list) if current_selected_list else set()
        checkbox_states = {symbol: symbol in current_selected_set for symbol in sorted_symbols_list}
        checkboxes = []

        def create_checkbox(symbol: str):
            """Функция создания чекбокса с отображением количества"""
            count = sorted_symbol_stats.get(symbol, 0)
            label_text = f"{symbol} ({count})"

            return Checkbox(
                label=label_text,
                value=checkbox_states[symbol],
                on_change=lambda e, s=symbol: toggle_checkbox(s, e.control.value),
                label_style=TextStyle(size=22, color=application_colors["text"]),
                fill_color={ControlState.DEFAULT: application_colors["active"]},
                check_color=application_colors["background"],
            )

        # Функция переключения чекбокса
        def toggle_checkbox(symbol: str, value: bool):
            checkbox_states[symbol] = value

        # Создаем чекбоксы для всех символов (уже отсортированных)
        for symbol in sorted_symbols_list:
            checkbox = create_checkbox(symbol)
            checkboxes.append(checkbox)
            checkboxes.append(Container(height=5))

        # Колонка с чекбоксами
        checkboxes_column = Column(
            controls=checkboxes,
            spacing=0,
            horizontal_alignment=CrossAxisAlignment.START,
            scroll=ScrollMode.AUTO if len(sorted_symbols_list) > 8 else None,
            height=300 if len(sorted_symbols_list) > 8 else None,
        )

        # Кнопки сохранения, отмены и возврата к изначальному списку
        save_btn = create_button(
            active=True,
            text="Сохранить",
            width=140,
            height=48
        )
        cancel_btn = create_button(
            active=True,
            text="Отмена",
            width=140,
            height=48
        )

        save_btn.on_click = lambda e: save_selection()
        cancel_btn.on_click = lambda e: close_dialog()

        def save_selection():
            selected_list = [s for s, state in checkbox_states.items() if state]
            logger.info(f"Выбраны типы детектируемых кристаллов: {selected_list}")

            config.symbols_need_check = selected_list

            if wafer_map_visual is not None:
                wafer_map_visual.update_symbols_need_check(selected_list)
            close_dialog()

        def restore_original_list():
            """Восстанавливает оригинальный список symbols_need_check"""
            if hasattr(change_detectable_dice_handler, '_original_symbols_list') and \
                    change_detectable_dice_handler._original_symbols_list is not None:
                original_list = change_detectable_dice_handler._original_symbols_list
                logger.info(f"Восстановлен изначальный список symbols_need_check: {original_list}")

                config.symbols_need_check = original_list

                if wafer_map_visual is not None:
                    # Принудительно пересчитываем статусы всех кристаллов
                    wafer_map = wafer_map_visual.wafer_map
                    wafer_map.symbols_need_check = original_list

                    for row in range(wafer_map.total_rows):
                        for col in range(wafer_map.total_cols):
                            die = wafer_map.die_matrix[row][col]
                            if die and die.symbol:
                                # Определяем статус заново на основе символа
                                new_status = wafer_map.determine_die_status(die.symbol)
                                if die.status != new_status:
                                    die.status = new_status
                                    # Обновляем символ если нужно
                                    if new_status == DieStatus.BAD:
                                        die.symbol = "FV"
                                    elif new_status == DieStatus.GOOD:
                                        die.symbol = "PV"
                                    wafer_map_visual.update_visual_die(die, is_need_update_canvas=False)

                    # Обновляем canvas один раз
                    if wafer_map_visual._canvas_ref:
                        wafer_map_visual._canvas_ref.update()
                    wafer_map.update_stats()
            close_dialog()

        def close_dialog():
            if dialog_stack in page.overlay:
                page.overlay.remove(dialog_stack)
            page.update()

        # Создаем кнопку "Вернуться к изначальному списку" только если есть оригинальный список
        # И текущий выбор отличается от оригинального
        buttons_row_controls = [save_btn, cancel_btn]

        if hasattr(change_detectable_dice_handler, '_original_symbols_list') and \
                change_detectable_dice_handler._original_symbols_list is not None:

            current_selected = [s for s, state in checkbox_states.items() if state]
            original_list = change_detectable_dice_handler._original_symbols_list

            # Показываем кнопку только если списки различаются
            if set(current_selected) != set(original_list):
                restore_btn = create_button(
                    active=True,
                    text="Вернуться к изначальному списку",
                    width=420,
                    height=48,
                    text_style=TextStyle(size=22, weight=FontWeight.BOLD)
                )
                restore_btn.on_click = lambda e: restore_original_list()
                buttons_row_controls.append(restore_btn)

        # Основное содержимое диалога
        dialog_content = Column(
            controls=[
                # Заголовок
                Container(
                    content=Text(
                        "Выберите типы кристаллов, которые нужно инспектировать",
                        size=22,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"],
                        text_align=TextAlign.CENTER,
                    ),
                    alignment=alignment.center,
                    padding=padding.only(bottom=10),
                ),
                # Статистика
                Container(
                    content=Column(
                        controls=[
                            Text(
                                f"Всего типов на пластине: {len(sorted_symbol_stats)}",
                                size=20,
                                color=application_colors["text"],
                                italic=True,
                            ),
                            Text(
                                f"Всего не фиктивных кристаллов {sum(sorted_symbol_stats.values())}",
                                size=20,
                                color=application_colors["text"],
                                italic=True,
                            ),
                        ],
                        spacing=5,
                    ),
                    alignment=alignment.center,
                    padding=padding.only(bottom=5),
                ),
                # Чекбоксы
                Container(
                    content=checkboxes_column,
                    padding=padding.all(20),
                    alignment=alignment.center,
                ),
                # Кнопки
                Row(
                    controls=buttons_row_controls,
                    alignment=MainAxisAlignment.CENTER,
                    spacing=10,
                    wrap=True,
                ),
            ],
            spacing=0,
            horizontal_alignment=CrossAxisAlignment.CENTER,
        )

        # Размеры диалога (увеличиваем ширину для третьей кнопки)
        has_restore_btn = len(buttons_row_controls) > 2
        dialog_width = 500 if has_restore_btn else 420
        dialog_height = 320 + len(sorted_symbols_list) * 45 if has_restore_btn else 280 + len(sorted_symbols_list) * 45

        # Вычисляем позицию для центрирования относительно левой колонки
        left_column_width = width_image + 40
        dialog_left = (left_column_width - dialog_width) / 2

        # Создаем диалог
        dialog_stack = Stack(
            controls=[
                # Затемняющий фон
                Container(
                    width=page.width,
                    height=page.height,
                    bgcolor=Colors.with_opacity(0.3, Colors.BLACK),
                    on_click=lambda e: close_dialog(),
                ),
                # Диалоговое окно
                Container(
                    width=dialog_width,
                    height=dialog_height,
                    bgcolor=application_colors["background"],
                    border_radius=2,
                    border=border.all(2, application_colors["text"]),
                    padding=20,
                    left=dialog_left + 40,
                    top=page.height / 2 - dialog_height / 2,
                    content=dialog_content,
                )
            ]
        )

        page.overlay.append(dialog_stack)
        page.update()

    def active_all_buttons(active: bool):
        """
        Активирует или дизактивирует все кнопки с сохранением/восстановлением состояния

        :param active:
            False - сохранить текущее состояние и разактивировать все кнопки
            True - восстановить ранее сохраненное состояние кнопок
        """
        buttons = [
            download_wafer_map_btn,
            change_wafer_params_btn,
            update_wafer_params_btn,
            change_detectable_dice_btn,
            update_protocol_btn,
            start_AOI_btn,
            pause_AOI_btn,
            continue_AOI_btn,
            stop_AOI_btn
        ]

        if not active:
            # Сохраняем текущее состояние кнопок
            for btn in buttons:
                btn_key = btn.text if btn.text else str(id(btn))
                buttons_state_cache[btn_key] = not btn.disabled

            for btn in buttons:
                set_button_active(btn, False)

        else:
            # Восстанавливаем сохраненное состояние
            for btn in buttons:
                btn_key = btn.text if btn.text else str(id(btn))

                if btn_key in buttons_state_cache:
                    set_button_active(btn, buttons_state_cache[btn_key])
                else:
                    set_button_active(btn, False)

            buttons_state_cache.clear()

    def update_scale_button_highlight():
        """Обновляет подсветку кнопок масштаба в соответствии с текущим масштабом"""
        scale_mapping = {
            1.0: 0,
            1.5: 1,
            2.0: 2,
        }

        for btn in scale_buttons:
            btn.bgcolor = application_colors["inactive"]

        scale_buttons[scale_mapping[config.scale_buttons_panel]].bgcolor = application_colors["active"]

        for btn in scale_buttons:
            btn.update()

    def activate_scale_buttons():
        """Активирует кнопки масштаба"""
        for btn in scale_buttons:
            btn.disabled = False  # Включаем кнопки
            btn.bgcolor = application_colors["inactive"]
            btn.color = application_colors["text"]

        update_scale_button_highlight()

    def deactivate_scale_buttons():
        """Деактивирует кнопки масштаба"""
        for btn in scale_buttons:
            btn.disabled = True  # Отключаем кнопки
            btn.bgcolor = application_colors["top_bar"]
            btn.color = application_colors["unclickable"]

        for btn in scale_buttons:
            btn.update()

    def scale_changed(e, scale_value):
        """Обработчик нажатия на кнопку смены масштаба визуализации"""
        if scale_buttons[0].disabled:
            return

        nonlocal wafer_map_visual
        if config.scale_buttons_panel == scale_value or wafer_map_visual is None or wafer_map_visual.wafer_map is None:
            return

        page = e.page
        deactivate_scale_buttons()
        active_all_buttons(False)
        dynamic_grid_container.content = loading_container
        page.update()

        async def load_wafer_map_async():
            try:
                grid_view = wafer_map_visual.generate_visual(
                    scale_value=scale_value
                )

                if grid_view is not None:
                    button_grid.content = grid_view
                    dynamic_grid_container.content = button_grid
                    config.scale_buttons_panel = scale_value
                    update_scale_button_highlight()

                await page.update_async()

            except KnownSystemException as e:
                show_error(f"Ошибка при изменении масштаба", str(e), page, config)
                dynamic_grid_container.content = button_grid

            except Exception as e:
                logger.error(f"Ошибка при изменении масштаба: {e}")
                show_error(f"Ошибка при изменении масштаба",
                           "Точная причина неизвестна", page, config)
                dynamic_grid_container.content = button_grid

            finally:
                active_all_buttons(True)
                activate_scale_buttons()
                await page.update_async()

        time.sleep(0.1)
        page.run_task(load_wafer_map_async)

    # === ПРИВЯЗКА ОБРАБОТЧИКОВ ===

    download_wafer_map_btn.on_click = lambda e: download_wafer_map_handler(e)

    checkbox_container = strict_validation_checkbox.content.controls[0]
    checkbox_container.on_click = lambda e: toggle_strict_validation_handler(e)

    change_wafer_params_btn.on_click = lambda e: change_wafer_params_handler(e)
    update_wafer_params_btn.on_click = lambda e: update_wafer_params_handler(e)

    update_protocol_btn.on_click = lambda e: wafer_map_visual.wafer_map.protocol.update_protocol(
        wafer_map_visual.wafer_map)
    change_detectable_dice_btn.on_click = lambda e: change_detectable_dice_handler(e)

    start_AOI_btn.on_click = lambda e: start_AOI_handler(e)
    pause_AOI_btn.on_click = lambda e: pause_AOI_handler(e)
    continue_AOI_btn.on_click = lambda e: continue_AOI_handler(e)
    stop_AOI_btn.on_click = lambda e: stop_AOI_handler(e)

    scale_buttons[0].on_click = lambda e: scale_changed(e, 1.0)
    scale_buttons[1].on_click = lambda e: scale_changed(e, 1.5)
    scale_buttons[2].on_click = lambda e: scale_changed(e, 2.0)

    return workspace_tab
