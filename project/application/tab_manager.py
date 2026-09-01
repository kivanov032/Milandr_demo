from typing import Optional, List
from flet import Tabs, Tab


class TabManager:
    """
    Менеджер для управления вкладками приложения.
    Позволяет блокировать/разблокировать, скрывать/показывать отдельные вкладки.
    """
    _instance: Optional['TabManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._tabs_control: Optional[Tabs] = None
            self._all_tabs: List[Tab] = []
            self._tabs_visibility_cache: dict = {}
            self._initialized = True

    def initialize(self, tabs_control: Tabs) -> None:
        """
        Инициализирует менеджер с контролом вкладок.

        Args:
            tabs_control: Объект Tabs из flet
        """
        self._tabs_control = tabs_control
        self._all_tabs = tabs_control.tabs.copy()

    def get_tab_by_text(self, tab_text: str) -> Optional[Tab]:
        """Возвращает вкладку по её тексту."""
        for tab in self._all_tabs:
            if tab.text == tab_text:
                return tab
        return None

    def show_tab(self, tab_text: str) -> bool:
        """
        Показывает конкретную вкладку.

        Args:
            tab_text: Текст вкладки для отображения

        Returns:
            bool: True если вкладка найдена и показана, иначе False
        """
        tab = self.get_tab_by_text(tab_text)
        if tab:
            tab.visible = True
            if self._tabs_control:
                self._tabs_control.update()
            return True
        return False

    def hide_tab(self, tab_text: str) -> bool:
        """
        Скрывает конкретную вкладку.

        Args:
            tab_text: Текст вкладки для скрытия

        Returns:
            bool: True если вкладка найдена и скрыта, иначе False
        """
        tab = self.get_tab_by_text(tab_text)
        if tab:
            tab.visible = False
            if self._tabs_control:
                self._tabs_control.update()
            return True
        return False

    def show_tabs(self, tab_texts: List[str]) -> None:
        """Показывает несколько вкладок по списку текстов."""
        for tab_text in tab_texts:
            self.show_tab(tab_text)

    def hide_tabs(self, tab_texts: List[str]) -> None:
        """Скрывает несколько вкладок по списку текстов."""
        for tab_text in tab_texts:
            self.hide_tab(tab_text)

    def show_all_tabs(self) -> None:
        """Показывает все вкладки."""
        for tab in self._all_tabs:
            tab.visible = True
        if self._tabs_control:
            self._tabs_control.update()

    def hide_all_tabs(self) -> None:
        """Скрывает все вкладки."""
        for tab in self._all_tabs:
            tab.visible = False
        if self._tabs_control:
            self._tabs_control.update()

    def block_tabs(self, allowed_tabs: List[str]) -> None:
        """
        Блокирует все вкладки, оставляя видимыми только указанные.

        Args:
            allowed_tabs: Список текстов вкладок, которые должны остаться видимыми
        """
        # Сохраняем текущее состояние для возможного восстановления
        self._tabs_visibility_cache.clear()

        for tab in self._all_tabs:
            self._tabs_visibility_cache[tab.text] = tab.visible
            tab.visible = tab.text in allowed_tabs

        if self._tabs_control:
            self._tabs_control.update()

    def unblock_tabs(self) -> None:
        """Восстанавливает видимость всех вкладок до последней блокировки."""
        if self._tabs_visibility_cache:
            for tab in self._all_tabs:
                if tab.text in self._tabs_visibility_cache:
                    tab.visible = self._tabs_visibility_cache[tab.text]
            self._tabs_visibility_cache.clear()
        else:
            self.show_all_tabs()

    def set_active_tab(self, tab_text: str) -> bool:
        """
        Устанавливает активную вкладку.

        Args:
            tab_text: Текст вкладки для активации

        Returns:
            bool: True если вкладка найдена и активирована, иначе False
        """
        tab = self.get_tab_by_text(tab_text)
        if tab and self._tabs_control:
            # Находим индекс вкладки
            for i, t in enumerate(self._all_tabs):
                if t.text == tab_text:
                    self._tabs_control.selected_index = i
                    self._tabs_control.update()
                    return True
        return False

    def get_current_tab(self) -> Optional[str]:
        """Возвращает текст текущей активной вкладки."""
        if self._tabs_control and 0 <= self._tabs_control.selected_index < len(self._all_tabs):
            return self._all_tabs[self._tabs_control.selected_index].text
        return None

    def is_tab_visible(self, tab_text: str) -> bool:
        """Проверяет, видима ли вкладка."""
        tab = self.get_tab_by_text(tab_text)
        return tab.visible if tab else False

    def switch_to_tab(self, tab_text: str) -> bool:
        """
        Переключает на указанную вкладку.

        Args:
            tab_text: Текст вкладки, на которую нужно переключиться

        Returns:
            bool: True если вкладка найдена и переключение выполнено, иначе False
        """
        if not self._tabs_control:
            return False

        for i, tab in enumerate(self._all_tabs):
            if tab.text == tab_text:
                self._tabs_control.selected_index = i
                self._tabs_control.update()
                return True
        return False


# Глобальный экземпляр менеджера
tab_manager = TabManager()
