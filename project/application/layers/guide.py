from flet import *
from functools import wraps
from project.application.addition.colors import color_mode
from project.application.addition.dialogs import show_warning

# Глобальное состояние авторизации
_is_admin_state = {"value": False}

# Константы для авторизации администратора
ADMIN_LOGIN = "adminMilandr"
ADMIN_PASSWORD = "passwordMilandr"


def admin_required(config=None):
    """
    Декоратор с параметром config.

    Использование:
        @admin_required(config)
        def опасная_функция(e):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _is_admin_state["value"]:
                page = None
                for arg in args:
                    if hasattr(arg, 'page'):
                        page = arg.page
                        break

                if page and config:
                    show_warning(
                        "Недостаточно прав",
                        "Для выполнения этого действия необходимы права администратора.\n"
                        "Войдите как администратор во вкладке 'Руководство пользователя'.",
                        page,
                        config
                    )
                return None
            return func(*args, **kwargs)

        return wrapper

    return decorator


def create_guide_layer(config):
    """
    Создает вкладку "Руководство пользователя" с подвкладками и панелью авторизации админа.

    :param config: Объект конфигурации приложения (ConfigManager)
    :return: Tab объект с руководством пользователя
    """
    application_colors = color_mode(config)

    # Используем глобальное состояние
    is_admin = _is_admin_state

    # === ПАНЕЛЬ АВТОРИЗАЦИИ АДМИНИСТРАТОРА ===

    # Словарь для хранения состояния авторизации админа
    # Используется словарь для передачи по ссылке и возможности изменения значения
    # в вложенных функциях. В будущем это значение можно использовать для
    # разграничения прав доступа к различным функциям приложения
    # Пример использования: if is_admin["value"]: # разрешить действие
    # is_admin = {"value": False}

    # Поле ввода логина администратора
    login_field = TextField(
        label="Логин",
        width=240,
        height=50,
        text_size=22,
        color=application_colors["text"],
        border_color=application_colors["text"],
    )

    # Поле ввода пароля администратора с возможностью скрытия/показа пароля
    password_field = TextField(
        label="Пароль",
        width=240,
        height=50,
        text_size=22,
        password=True,  # Скрывает вводимые символы
        can_reveal_password=True,  # Добавляет иконку для показа/скрытия пароля
        color=application_colors["text"],
        border_color=application_colors["text"],
    )

    # Текст сообщения об ошибке при неверном логине или пароле
    error_text = Text(
        "",
        size=22,
        color=Colors.RED,
        visible=False,  # Скрыт по умолчанию, показывается только при ошибке
    )

    # Текст сообщения об успешной авторизации
    success_text = Text(
        "Вы авторизованы как администратор",
        size=22,
        color=Colors.GREEN,
        visible=False,  # Скрыт по умолчанию, показывается после успешного входа
    )

    def on_login_click(e):
        """
        Обработчик нажатия кнопки "Войти".

        Проверяет введенные логин и пароль:
        - Если данные верны (adminMilandr/passwordMilandr):
          * Устанавливает флаг авторизации is_admin["value"] = True
          * Скрывает форму входа
          * Показывает кнопку "Отмена прав админа" и сообщение об успехе
          * Очищает поля ввода
        - Если данные неверны:
          * Показывает сообщение об ошибке

        :param e: Объект события Flet
        """
        if login_field.value == ADMIN_LOGIN and password_field.value == ADMIN_PASSWORD:
            is_admin["value"] = True
            login_form.visible = False
            logout_button.visible = True
            success_text.visible = True
            error_text.visible = False
            login_field.value = ""
            password_field.value = ""
        else:
            # Неверные учетные данные
            error_text.value = "Неверный логин или пароль"
            error_text.visible = True
            success_text.visible = False
        e.page.update()

    def on_logout_click(e):
        """
        Обработчик нажатия кнопки "Отмена прав админа".

        Сбрасывает авторизацию:
        - Устанавливает флаг is_admin["value"] = False
        - Показывает форму входа обратно
        - Скрывает кнопку выхода и сообщения

        :param e: Объект события Flet
        """
        is_admin["value"] = False
        login_form.visible = True
        logout_button.visible = False
        success_text.visible = False
        error_text.visible = False
        e.page.update()

    # Кнопка входа для администратора
    # Оформлена в едином стиле с другими кнопками приложения
    login_button = ElevatedButton(
        text="Войти",
        on_click=on_login_click,
        width=240,
        height=48,
        style=ButtonStyle(
            shape=RoundedRectangleBorder(radius=10),
            overlay_color=application_colors["hover"],  # Цвет при наведении
            bgcolor=application_colors["inactive"],  # Серый фон
            color=application_colors["text"],  # Белый текст
            text_style=TextStyle(
                size=22,
                weight=FontWeight.BOLD
            ),
            animation_duration=300,
        ),
    )

    # Кнопка выхода из режима администратора
    # Видна только после успешной авторизации
    logout_button = ElevatedButton(
        text="Отмена прав админа",
        on_click=on_logout_click,
        width=250,
        height=48,
        visible=False,  # Скрыта по умолчанию
        style=ButtonStyle(
            shape=RoundedRectangleBorder(radius=10),
            overlay_color=application_colors["hover"],
            bgcolor=application_colors["inactive"],
            color=application_colors["text"],
            text_style=TextStyle(
                size=22,
                weight=FontWeight.BOLD
            ),
            animation_duration=300,
        ),
    )

    # Колонка с формой входа
    # Содержит заголовок, поля ввода, кнопку входа и текст ошибки
    # Все элементы отцентрованы по горизонтали
    login_form = Column(
        spacing=10,
        horizontal_alignment=CrossAxisAlignment.CENTER,
        controls=[
            Text(
                "Вход для администратора",
                size=22,
                weight=FontWeight.BOLD,
                color=application_colors["text"],
                text_align=TextAlign.CENTER,
            ),
            login_field,
            password_field,
            login_button,
            error_text,
        ],
    )

    # Контейнер панели администратора
    # Содержит форму входа, кнопку выхода и сообщение об успешной авторизации
    # Размещается в левом нижнем углу вкладки "Основные операции" через Stack
    admin_panel = Container(
        content=Column(
            spacing=10,
            horizontal_alignment=CrossAxisAlignment.CENTER,
            controls=[
                login_form,
                logout_button,
                success_text,
            ],
        ),
        padding=10,
        border=border.all(1, application_colors["text"]),
        border_radius=8,
    )

    # === СОДЕРЖИМОЕ ПОДВКЛАДКИ "ЗАПУСК ИНСПЕКЦИИ" ===
    # Пошаговые инструкции по проверке годности изделия:
    # - Выбор формы паллеты
    # - Настройка параметров инспекции
    # - Запуск, пауза, продолжение и остановка инспекции
    basic_operations = Column(
        spacing=20,
        scroll=ScrollMode.AUTO,
        controls=[
            Container(height=10),
            Text(
                "Подготовка к работе:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "1. Установите паллету с кристаллами на рабочий стол микроскопа, зафиксировав её "
                        "в держателе. Убедитесь, что паллета расположена ровно и не имеет перекосов.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "2. Выберите форму паллеты в выпадающем меню над её визуализацией. "
                        "Форма должна соответствовать реальной геометрии установленной паллеты.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "3. При необходимости загрузите файл карты годности (BIN-файл) с результатами "
                        "предыдущих тестирований, нажав кнопку ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Загрузить карту\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ".",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Text(
                "Настройка параметров:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "4. Проверьте параметры инспекции в правой панели. Для изменения настроек нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Изменить\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ", войдите как администратор (см. панель входа в левом нижнем углу), "
                        "отредактируйте значения и нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Сохранить\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ".",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Text(
                "Запуск и управление:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "5. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Запуск\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для начала автоматической инспекции. Микроскоп начнёт последовательное "
                        "сканирование всех кристаллов на паллете. На карте годности ячейки будут окрашиваться "
                        "в соответствии с результатами проверки.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "6. Для временной приостановки процесса нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Пауза\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". Дождитесь полной остановки микроскопа перед выполнением других действий.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "7. Для продолжения инспекции после паузы нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Продолжить\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". Микроскоп продолжит работу с того места, где остановился.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "8. Для полной остановки и завершения инспекции нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Стоп\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". После остановки микроскопа инспекция будет прервана.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Text(
                "Сохранение результатов:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "9. После завершения инспекции сохраните результаты, нажав ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Сохранить карту\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". Карта годности будет сохранена в формате BIN для последующего анализа и архивирования.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
        ],
    )

    # === СОДЕРЖИМОЕ ПОДВКЛАДКИ "ИНТЕРПРЕТАЦИЯ РЕЗУЛЬТАТОВ" ===
    # Описание цветовых обозначений результатов инспекции и критериев оценки
    color_coding = Column(
        spacing=20,
        scroll=ScrollMode.AUTO,
        controls=[
            Container(height=10),
            Text(
                "Цветовая индикация на карте годности:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Container(
                        width=20,
                        height=20,
                        bgcolor=Colors.GREEN,
                        border_radius=4,
                    ),
                    Text(
                        "Зелёный — кристалл соответствует всем техническим требованиям.",
                        size=15,
                        color=application_colors["text"]
                    ),
                ],
                spacing=8,
                alignment=MainAxisAlignment.START,
            ),
            Text(
                "     Кристалл полностью годен и может быть использован в производстве без ограничений.",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Container(height=5),
            Row(
                controls=[
                    Container(
                        width=20,
                        height=20,
                        bgcolor=Colors.YELLOW_700,
                        border_radius=4,
                    ),
                    Text(
                        "Жёлтый — кристалл находится в пределах допустимых отклонений.",
                        size=15,
                        color=application_colors["text"]
                    ),
                ],
                spacing=8,
                alignment=MainAxisAlignment.START,
            ),
            Text(
                "     Кристалл пригоден для использования, но имеет небольшие отклонения от идеальных параметров.",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Container(height=5),
            Row(
                controls=[
                    Container(
                        width=20,
                        height=20,
                        bgcolor=Colors.RED,
                        border_radius=4,
                    ),
                    Text(
                        "Красный — кристалл не соответствует техническим требованиям.",
                        size=15,
                        color=application_colors["text"]
                    ),
                ],
                spacing=8,
                alignment=MainAxisAlignment.START,
            ),
            Text(
                "     Кристалл непригоден для использования из-за обнаруженных дефектов или несоответствий.",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Container(height=5),
            Row(
                controls=[
                    Container(
                        width=20,
                        height=20,
                        bgcolor=Colors.GREY_700,
                        border_radius=4,
                    ),
                    Text(
                        "Серый — кристалл не проверялся или пропущен при инспекции.",
                        size=15,
                        color=application_colors["text"]
                    ),
                ],
                spacing=8,
                alignment=MainAxisAlignment.START,
            ),
            Container(height=15),
            Text(
                "Типы обнаруживаемых дефектов:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Text(
                "• Ошибки резки — неровные края, сколы, трещины по периметру кристалла",
                size=15,
                color=application_colors["text"]
            ),
            Text(
                "• Чёрные точки — загрязнения, инородные частицы на поверхности",
                size=15,
                color=application_colors["text"]
            ),
            Text(
                "• Геометрические несоответствия — отклонения размеров от номинальных значений",
                size=15,
                color=application_colors["text"]
            ),
            Text(
                "• Дефекты центрирования — смещение активной области относительно центра кристалла",
                size=15,
                color=application_colors["text"]
            ),
            Container(height=10),
            Text(
                "Для просмотра детальной информации о конкретном кристалле кликните на его ячейку в карте годности.",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
        ],
    )

    # === СОДЕРЖИМОЕ ПОДВКЛАДКИ "НАСТРОЙКА ПЕРВОЙ ЯЧЕЙКИ" ===
    # Инструкции по калибровке координат первой ячейки паллеты
    calibration = Column(
        spacing=20,
        scroll=ScrollMode.AUTO,
        controls=[
            Container(height=10),
            Text(
                "Назначение:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Text(
                "Калибровка определяет стартовую точку сканирования паллеты. После установки координат "
                "первой ячейки система автоматически рассчитает положение всех остальных кристаллов на основе "
                "выбранной геометрии паллеты.",
                size=15,
                color=application_colors["text"]
            ),
            Container(height=10),
            Text(
                "Пошаговая инструкция:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "1. Перейдите на вкладку ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Калибровка\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " в главном меню приложения.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "2. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Подключить камеру\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для активации видеопотока с микроскопа. На экране появится изображение "
                        "с текущего положения камеры.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "3. Выберите режим работы переключателем:",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Text(
                "     • Перемещение на первую ячейку включено — после сохранения координат микроскоп "
                "автоматически переместится в заданную позицию",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • Перемещение на первую ячейку выключено — координаты будут сохранены без перемещения "
                "(рекомендуется для опытных пользователей)",
                size=14,
                color=application_colors["text"],
            ),
            Row(
                controls=[
                    Text(
                        "4. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Изменить координаты\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для активации режима ручного управления.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "5. В меню ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Шаг\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " выберите величину перемещения за один клик (от 0.1 мм до 10 мм). "
                        "Для грубого позиционирования используйте большие значения, для точной настройки — малые.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "6. Используйте кнопки управления для навигации:",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Text(
                "     • Крестовидные кнопки слева (↑↓←→) — перемещение по плоскости паллеты",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • Вертикальные кнопки справа (↑↓) — регулировка фокусного расстояния (высоты микроскопа)",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ Все — возврат во все нулевые координаты (центр + максимальная высота)",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ XY — возврат в центр паллеты с сохранением текущей высоты",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ Z — возврат на максимальную высоту с сохранением координат XY",
                size=14,
                color=application_colors["text"],
            ),
            Row(
                controls=[
                    Text(
                        "7. Наведите микроскоп на ",
                        size=15,
                        color=application_colors["text"],
                    ),
                    Text(
                        "центр первого кристалла",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " паллеты (обычно это кристалл в верхнем левом углу). "
                        "Убедитесь, что изображение находится в фокусе и кристалл чётко виден.",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Row(
                controls=[
                    Text(
                        "8. Координатные оси в правой части экрана показывают текущее положение микроскопа ",
                        size=15,
                        color=application_colors["text"],
                    ),
                    Text(
                        "(светлая точка)",
                        size=15,
                        color=application_colors["active"],
                        weight=FontWeight.BOLD,
                    ),
                    Text(
                        ". Используйте их для контроля перемещения.",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Row(
                controls=[
                    Text(
                        "9. После точного позиционирования нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Сохранить координаты\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". Система запомнит положение первой ячейки для всех последующих инспекций.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "10. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Отключить камеру\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для завершения калибровки и освобождения ресурсов камеры.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Container(
                content=Text(
                    "⚠ Важно: Калибровку необходимо проводить каждый раз при смене типа паллеты или "
                    "после перемещения установки. Точность калибровки напрямую влияет на качество инспекции.",
                    size=14,
                    color=Colors.ORANGE_400,
                    italic=True,
                ),
                padding=10,
                border=border.all(1, Colors.ORANGE_400),
                border_radius=8,
            ),
        ],
    )

    # === СОДЕРЖИМОЕ ПОДВКЛАДКИ "ИНСТРУМЕНТЫ ИЗМЕРЕНИЯ" ===
    # Инструкции по работе с инструментами для точных измерений на изображении
    measurement = Column(
        spacing=20,
        scroll=ScrollMode.AUTO,
        controls=[
            Container(height=10),
            Text(
                "Назначение:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Text(
                "Вкладка предназначена для проведения точных измерений геометрических параметров кристаллов "
                "и дефектов непосредственно на изображении с камеры микроскопа.",
                size=15,
                color=application_colors["text"]
            ),
            Container(height=10),
            Text(
                "Подготовка к измерениям:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "1. Перейдите на вкладку ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Измерения\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " в главном меню приложения.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "2. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Подключить камеру\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для активации видеопотока.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "3. Выберите единицы измерения в выпадающем меню:",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    )
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Text(
                "     • Миллиметры (мм) — для крупных элементов и общих размеров",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • Микрометры (мкм) — для точных измерений деталей кристалла (рекомендуется)",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • Пиксели (пкс) — для работы с необработанными данными изображения",
                size=14,
                color=application_colors["text"],
            ),
            Row(
                controls=[
                    Text(
                        "4. Выполните калибровку масштаба с помощью поверочного квадрата известного размера. "
                        "Перемещайте слайдер ",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                    Text(
                        "\"Коэффициент перевода пикселей\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ", пока размер на экране не совпадёт с реальным размером эталона.",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Text(
                "Доступные инструменты измерения:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "↔ Линия",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " — измерение линейных расстояний между двумя точками",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Text(
                "     Применение: толщина элементов, расстояние между объектами, длина дефектов",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Text(
                "     Использование: Выберите инструмент, зажмите кнопку мыши в начальной точке, "
                "протяните до конечной точки и отпустите. На экране отобразится длина отрезка.",
                size=14,
                color=application_colors["text"],
            ),
            Container(height=8),
            Row(
                controls=[
                    Text(
                        "○ Эллипс",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " — измерение диаметров круглых и овальных объектов",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Text(
                "     Применение: диаметры частиц загрязнений, контактных площадок, круглых дефектов",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Text(
                "     Использование: Зажмите кнопку мыши и растяните эллипс до нужного размера. "
                "Система покажет большой и малый диаметры эллипса.",
                size=14,
                color=application_colors["text"],
            ),
            Container(height=8),
            Row(
                controls=[
                    Text(
                        "▢ Прямоугольник",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " — измерение длины и ширины прямоугольных областей",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Text(
                "     Применение: габариты кристалла, размеры активных областей, контактных дорожек",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Text(
                "     Использование: Зажмите кнопку мыши в одном углу, растяните до противоположного угла. "
                "Будут показаны длина, ширина и площадь прямоугольника.",
                size=14,
                color=application_colors["text"],
            ),
            Container(height=8),
            Row(
                controls=[
                    Text(
                        "△ Треугольник",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " — измерение углов и сторон треугольных областей",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Text(
                "     Применение: угловые дефекты, фаски, наклонные элементы",
                size=14,
                color=application_colors["text"],
                italic=True,
            ),
            Text(
                "     Использование: Зажмите кнопку мыши и растяните треугольник до нужных размеров. "
                "Система покажет длины сторон и углы.",
                size=14,
                color=application_colors["text"],
            ),
            Container(height=15),
            Text(
                "Завершение работы:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "5. После завершения измерений нажмите ",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                    Text(
                        "\"Очистить окно от инструментов измерения\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для удаления всех нарисованных фигур с экрана.",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "6. Нажмите ",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                    Text(
                        "\"Отключить камеру\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для завершения работы с инструментами измерения.",
                        size=15,
                        color=application_colors["text"],
                        text_align=TextAlign.LEFT
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Container(
                content=Text(
                    "💡 Совет: Результаты измерений можно сохранить, сделав снимок экрана кнопкой "
                    "\"Сделать фото\" в правом верхнем углу видеопотока. Изображение будет сохранено с "
                    "наложенными измерениями.",
                    size=14,
                    color=Colors.BLUE_400,
                    italic=True,
                ),
                padding=10,
                border=border.all(1, Colors.BLUE_400),
                border_radius=8,
            ),
        ],
    )

    # === СОДЕРЖИМОЕ ПОДВКЛАДКИ "РУЧНОЕ УПРАВЛЕНИЕ" ===
    # Инструкции по ручному перемещению микроскопа для детального осмотра
    camera_mechanical = Column(
        spacing=20,
        scroll=ScrollMode.AUTO,
        controls=[
            Container(height=10),
            Text(
                "Назначение:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Text(
                "Режим ручного управления позволяет свободно перемещать микроскоп для детального осмотра "
                "отдельных кристаллов, проверки качества фокусировки или визуальной оценки дефектов без "
                "запуска автоматической инспекции.",
                size=15,
                color=application_colors["text"]
            ),
            Container(height=10),
            Text(
                "Активация режима:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "1. Перейдите на вкладку ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Ручное управление\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " в меню вкладки \"Калибровка\" или используйте соответствующий раздел в настройках.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "2. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Подключить камеру\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для активации видеопотока в режиме реального времени.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Text(
                "Настройка режима возврата:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "3. Выберите режим работы переключателем:",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Text(
                "     • Возвращение домой включено — после завершения работы микроскоп автоматически "
                "вернётся в исходное положение (центр паллеты, максимальная высота)",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • Возвращение домой выключено — микроскоп останется в текущем положении "
                "(используйте, если планируете продолжить работу с текущей позиции)",
                size=14,
                color=application_colors["text"],
            ),
            Container(height=10),
            Text(
                "Управление перемещением:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "4. Нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Изменить координаты\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " для активации элементов управления движением.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Row(
                controls=[
                    Text(
                        "5. В меню ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Шаг\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        " выберите величину перемещения за одно нажатие кнопки (от 0.1 мм до 10 мм). "
                        "Рекомендации:",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Text(
                "     • 5-10 мм — быстрое перемещение между удалёнными участками паллеты",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • 1-2 мм — навигация по соседним кристаллам",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • 0.1-0.5 мм — точное позиционирование для детального осмотра",
                size=14,
                color=application_colors["text"],
            ),
            Row(
                controls=[
                    Text(
                        "6. Используйте кнопки управления:",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Text(
                "     • Крестовидные стрелки (↑↓←→) — перемещение микроскопа в плоскости паллеты (X-Y)",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • Вертикальные стрелки (↑↓) — изменение высоты (Z) для фокусировки",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ Все — возврат в нулевые координаты по всем осям",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ XY — возврат в центр паллеты без изменения высоты",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ Z — возврат на максимальную высоту без изменения координат X-Y",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ X — возврат в центр по горизонтальной оси",
                size=14,
                color=application_colors["text"],
            ),
            Text(
                "     • ⌂ Y — возврат в центр по вертикальной оси",
                size=14,
                color=application_colors["text"],
            ),
            Row(
                controls=[
                    Text(
                        "7. Координатные оси в правой части экрана отображают текущее положение микроскопа ",
                        size=15,
                        color=application_colors["text"],
                    ),
                    Text(
                        "(светлая точка)",
                        size=15,
                        color=application_colors["active"],
                        weight=FontWeight.BOLD,
                    ),
                    Text(
                        " относительно рабочей области паллеты.",
                        size=15,
                        color=application_colors["text"],
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=4
            ),
            Container(height=10),
            Text(
                "Сохранение позиции:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "8. Если вы нашли интересующий объект и хотите сохранить его координаты, нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Сохранить координаты\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". Эти координаты можно использовать для возврата к точке позже.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Text(
                "Завершение работы:",
                size=18,
                weight=FontWeight.BOLD,
                text_align=TextAlign.LEFT,
                color=application_colors["text"]
            ),
            Row(
                controls=[
                    Text(
                        "9. После завершения осмотра нажмите ",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                    Text(
                        "\"Отключить камеру\"",
                        size=15,
                        weight=FontWeight.BOLD,
                        color=application_colors["text"]
                    ),
                    Text(
                        ". Если включён режим \"Возвращение домой\", микроскоп автоматически вернётся "
                        "в исходное положение.",
                        size=15,
                        text_align=TextAlign.LEFT,
                        color=application_colors["text"]
                    ),
                ],
                alignment=MainAxisAlignment.START,
                wrap=True,
                spacing=0
            ),
            Container(height=10),
            Container(
                content=Text(
                    "⚠ Внимание: Избегайте резких перемещений на большие расстояния при низкой высоте "
                    "микроскопа — это может привести к столкновению объектива с паллетой. Всегда поднимайте "
                    "микроскоп перед перемещением на новую область.",
                    size=14,
                    color=Colors.ORANGE_400,
                    italic=True,
                ),
                padding=10,
                border=border.all(1, Colors.ORANGE_400),
                border_radius=8,
            ),
        ],
    )

    # === КОНСТРУКТОР ПОДВКЛАДОК ===
    # Создание системы вкладок с переключением между различными разделами руководства
    # Панель администратора размещена только во вкладке "Запуск инспекции"
    # в правом нижнем углу
    tabs = Tabs(
        selected_index=0,  # По умолчанию открыта первая вкладка
        animation_duration=300,  # Плавная анимация переключения вкладок
        unselected_label_color=application_colors["text"],
        tabs=[
            Tab(
                text="Запуск инспекции",
                content=Container(
                    content=Stack(
                        controls=[
                            basic_operations,  # Основное содержимое вкладки
                            Container(
                                content=admin_panel,  # Панель администратора
                                bottom=10,  # Отступ снизу 10 пикселей
                                right=10,  # Отступ справа 10 пикселей
                            ),
                        ],
                    ),
                    padding=padding.all(10),
                ),
            ),
            Tab(
                text="Интерпретация результатов",
                content=Container(
                    content=color_coding,
                    padding=padding.all(10),
                ),
            ),
            Tab(
                text="Настройка первой ячейки",
                content=Container(
                    content=calibration,
                    padding=padding.all(10),
                ),
            ),
            Tab(
                text="Инструменты измерения",
                content=Container(
                    content=measurement,
                    padding=padding.all(10),
                ),
            ),
            Tab(
                text="Ручное управление",
                content=Container(
                    content=camera_mechanical,
                    padding=padding.all(10),
                ),
            ),
        ],
    )

    # === ОСНОВНОЙ TAB "РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ" ===
    # Главная вкладка, содержащая все подвкладки с инструкциями
# === ОСНОВНОЙ TAB "РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ" ===
    import threading
    import time
    
    # 1. Текст руководства
    guide_text = Text(
        value="Руководство пользователя",
        size=22,
        weight=FontWeight.BOLD,
        color=application_colors["text"],
        no_wrap=True,  # Запрещаем перенос на новую строку
    )

    # 2. Ряд со скрытой прокруткой (эффект "окна")
    marquee_row = Row(
        controls=[
            guide_text,
            Container(width=150) # Дополнительное пустое пространство в конце, чтобы тексту было куда уезжать
        ],
        width=250, # Видимая ширина вкладки
        scroll=ScrollMode.HIDDEN, # Скрываем ползунок скролла
    )

    # 3. Логика зацикленной анимации
    hover_state = {"hovered": False, "animating": False}

    def scroll_worker():
        if hover_state["animating"]:
            return
        hover_state["animating"] = True
        
        offset_target = 150
        while hover_state["hovered"]:
            # Прокручиваем в заданную сторону
            marquee_row.scroll_to(offset=offset_target, duration=2500)
            
            # Ждем 2.5 секунды (длительность анимации), 
            # разбивая ожидание на короткие шаги, чтобы мгновенно прерваться, если курсор убрали
            for _ in range(25):
                if not hover_state["hovered"]:
                    break
                time.sleep(0.1)
                
            # Меняем направление для следующего шага
            offset_target = 0 if offset_target == 150 else 150

        hover_state["animating"] = False

    def on_guide_hover(e):
        if e.data == "true":
            hover_state["hovered"] = True
            # Запускаем цикл прокрутки в отдельном потоке, чтобы не заморозить интерфейс
            threading.Thread(target=scroll_worker, daemon=True).start()
        else:
            hover_state["hovered"] = False
            # Быстро возвращаем в начало
            marquee_row.scroll_to(offset=0, duration=500)

    # 4. Собираем кастомную вкладку
    guide_tab = Tab(
        text="Руководство пользователя", # Для стабильной работы TabManager
        tab_content=Container(
            content=marquee_row,
            width=250,
            on_hover=on_guide_hover,
            alignment=alignment.center,
        ),
        content=Container(
            content=tabs,
            padding=10,
        ),
    )

    # Возвращаем готовую вкладку для добавления в главное окно приложения
    return guide_tab

    # Возвращаем готовую вкладку для добавления в главное окно приложения
    return guide_tab
