"""Статистика инспекций.

Исправления:
- блок "Проверено" на втором месте между "Всего" и "Годных";
- график столбчатый (BarChart), ось X - инспекции, ось Y - дефекты/годные;
- увеличен размер графика в высоту и добавлен запас по оси Y, чтобы всплывающие подсказки не срезались;
- поиск по диапазону (например, 1-100);
- таблица кристаллов изначально пустая для предотвращения зависаний.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from flet import *

from project.application.addition.colors import color_mode
from project.application.addition.logger import logger
from project.configuration.config_manager import ConfigManager


def key_name(value: Any) -> str:
    return "".join(c for c in str(value).strip().lower() if c.isalnum())


def to_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def show_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def as_dict(value: Any) -> dict[str, Any]:
    return {key_name(k): v for k, v in value.items()} if isinstance(value, dict) else {}


def find_value(root: Any, *names: str, default: Any = None) -> Any:
    wanted = {key_name(n) for n in names}
    for item in walk(root):
        if isinstance(item, dict):
            data = as_dict(item)
            for name in wanted:
                if name in data:
                    return data[name]
    return default


def find_dict(root: Any, *names: str) -> dict[str, Any]:
    return as_dict(find_value(root, *names, default={}))


def find_dies(root: Any) -> list[dict[str, Any]]:
    value = find_value(root, "dicesinfo", "diesinfo", "dice_info", "dies", default=[])
    return [as_dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def file_date(path: Path, modified: float) -> str:
    name = path.stem
    for fmt, length in (("%Y%m%d_%H%M%S", 15), ("%Y%m%d%H%M%S", 14)):
        for i in range(len(name)):
            try:
                return datetime.strptime(name[i:i + length], fmt).strftime("%d.%m.%Y %H:%M:%S")
            except ValueError:
                pass
    return datetime.fromtimestamp(modified).strftime("%d.%m.%Y %H:%M")


@dataclass
class Inspection:
    path: Path
    raw: Any
    modified: float
    recognized: bool

    @property
    def dies(self):
        return find_dies(self.raw)

    @property
    def start_stats(self) -> dict[str, Any]:
        return find_dict(self.raw, "startstats", "start_stats")

    @property
    def final_stats(self) -> dict[str, Any]:
        return find_dict(self.raw, "finalstats", "final_stats")

    def value(self, *names, default=None):
        return find_value(self.raw, *names, default=default)

    @property
    def wafer(self):
        return show_value(self.value("waferid", "wafer_id", default=self.path.stem))

    @property
    def total(self):
        value = self.value("totaldice", "total_dice", default=None)
        return to_int(value) if value is not None else len(self.dies)

    @property
    def passed(self):
        val = self.final_stats.get("good")
        if val is not None:
            return to_int(val)
        return 0

    @property
    def failed(self):
        val = self.final_stats.get("bad")
        if val is not None:
            return to_int(val)
        return 0

    @property
    def defects(self):
        value = self.value("totaldefects", "total_defects", default=None)
        if value is not None:
            return to_int(value)
        return sum(to_int(d.get("totaldefectsondie", 0)) for d in self.dies)

    @property
    def checked(self):
        start_need = to_int(self.start_stats.get("needcheck", 0))
        final_need = to_int(self.final_stats.get("needcheck", 0))
        diff = start_need - final_need
        return max(0, diff)

    @property
    def avg_time(self):
        val = self.value("averagetimeperdie", "average_time_per_die", default=None)
        if val is None or val == "":
            return "—"
        try:
            f_val = float(val)
            return f"{f_val:.3f} сек"
        except (ValueError, TypeError):
            return str(val)

    @property
    def defects_statistics(self) -> dict[str, Any]:
        val = self.value("defectsstatistics", "defects_statistics", default={})
        return val if isinstance(val, dict) else {}

    @property
    def date(self):
        return file_date(self.path, self.modified)


def create_statistics_layer(config: ConfigManager) -> Tab:
    colors = color_mode(config)
    directory = Path(getattr(config, "statistics_reports_path", "") or ".")
    reports: list[Inspection] = []
    selected: set[Path] = set()
    hidden_reports: set[Path] = set()
    current: Inspection | None = None

    def safe_update(control: Control) -> None:
        if control.page is None:
            return
        try:
            control.update()
        except Exception:
            try:
                control.page.update()
            except Exception:
                pass

    def message(page: Page, title: str, body: str, color=Colors.ORANGE_400):
        def close(event):
            if page.dialog is not None:
                page.dialog.open = False
                page.update()
        page.dialog = AlertDialog(
            modal=True,
            title=Text(title),
            content=Text(body, selectable=True),
            actions=[TextButton("Закрыть", on_click=close, style=ButtonStyle(color=color))],
        )
        page.dialog.open = True
        page.update()

    def card(content, expand=False):
        return Container(content=content, padding=14, expand=expand,
                         bgcolor=colors["top_bar"], border_radius=12,
                         border=border.all(1, colors["inactive"]))

    def make_button(label, icon, width, callback, danger=False):
        return ElevatedButton(
            text=label, icon=icon, width=width, height=48, on_click=callback,
            style=ButtonStyle(
                shape=RoundedRectangleBorder(radius=12),
                bgcolor=colors["red"] if danger else colors["inactive"],
                color=colors["text"], overlay_color=colors["hover"],
                text_style=TextStyle(size=18, weight=FontWeight.BOLD),
            ),
        )

    folder = Text(str(directory) if directory.is_dir() else "Каталог отчётов не выбран",
                  color=colors["unclickable"], expand=True)
    report_list = Column(scroll=ScrollMode.AUTO, spacing=7, expand=True)
    details = Column(scroll=ScrollMode.AUTO, spacing=10, expand=True)
    charts = Column(scroll=ScrollMode.AUTO, expand=True)
    
    search = TextField(
        label="ID кристалла (или диапазон 1-100) и Enter",
        width=420,
        color=colors["text"], bgcolor=colors["top_bar"],
        border_color=colors["text"], focused_border_color=colors["active"],
        label_style=TextStyle(color=colors["text"]),
    )
    search_status = Text("", size=13, color=colors["unclickable"])
    filtered_dies: list[dict[str, Any]] = []

    dies_table = DataTable(
        columns=[DataColumn(Text(x, color=colors["text"], weight=FontWeight.BOLD))
                 for x in ("ID", "Map X", "Map Y", "Символ", "Статус", "Дефекты")],
        rows=[],
        heading_row_color=colors["inactive"],
        border=border.all(1, colors["inactive"]),
        column_spacing=20,
        horizontal_margin=12,
    )
    dies_view = Column([dies_table], scroll=ScrollMode.AUTO, expand=True)

    file_picker = FilePicker()

    def on_dialog_result(e: FilePickerResultEvent):
        if not e.path:
            return
        nonlocal directory, current
        directory = Path(e.path)
        folder.value = str(directory)
        current = None
        reports.clear()
        selected.clear()
        hidden_reports.clear()
        details.controls = [Text("Выберите инспекцию в списке.", color=colors["unclickable"], size=18)]
        safe_update(details)
        load_reports()
        update_list()
        try:
            config.statistics_reports_path = str(directory)
        except Exception:
            pass

    file_picker.on_result = on_dialog_result

    def choose_directory(event):
        if file_picker not in event.page.overlay:
            event.page.overlay.append(file_picker)
            event.page.update()
        file_picker.get_directory_path(dialog_title="Выберите каталог с JSON-отчётами")

    def read_report(path: Path):
        try:
            with path.open("r", encoding="utf-8-sig") as stream:
                raw = json.load(stream)
            if not isinstance(raw, (dict, list)):
                return None
            recognized_names = {"waferid", "dicesinfo", "diesinfo", "finalstats", "totaldice", "totalfaildice", "totalpassdice"}
            recognized = any(key_name(k) in recognized_names for item in walk(raw) if isinstance(item, dict) for k in item)
            return Inspection(path, raw, path.stat().st_mtime, recognized)
        except Exception as error:
            logger.warning(f"Не удалось прочитать JSON {path}: {error}")
            return None

    def load_reports():
        reports.clear()
        if not directory.is_dir():
            return
        checked = 0
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() != ".json":
                continue
            if path in hidden_reports:
                continue
            checked += 1
            report = read_report(path)
            if report is not None:
                reports.append(report)
        reports.sort(key=lambda item: item.modified)

    def apply_filter(force_message=False):
        nonlocal filtered_dies
        filtered_dies = []
        
        if current is None:
            search_status.value = "Выберите инспекцию на первой подвкладке."
            safe_update(search_status)
            build_dies_table()
            return

        q = (search.value or "").strip()
        
        # Если пусто - не загружаем кристаллы (чтобы не висло)
        if not q:
            search_status.value = "Ожидание ввода. Введите ID или диапазон (например, 1-100) и нажмите Enter."
        else:
            # Обработка диапазона (например: 1-100)
            if "-" in q and q.count("-") == 1:
                try:
                    start_str, end_str = q.split("-")
                    start_id = int(start_str.strip())
                    end_id = int(end_str.strip())
                    
                    for die in current.dies:
                        die_id_raw = die.get("id")
                        try:
                            die_id_int = int(die_id_raw)
                            if start_id <= die_id_int <= end_id:
                                filtered_dies.append(die)
                        except (ValueError, TypeError):
                            pass
                except ValueError:
                    # Если распарсить как диапазон не вышло, ищем как обычный текст
                    for die in current.dies:
                        did = show_value(die.get("id"))
                        if q == did or q.casefold() in did.casefold():
                            filtered_dies.append(die)
            else:
                # Обычный поиск по ID
                for die in current.dies:
                    did = show_value(die.get("id"))
                    if q == did or q.casefold() in did.casefold():
                        filtered_dies.append(die)
                        
            search_status.value = f"Найдено: {len(filtered_dies)}"
            if force_message:
                search_status.value += f" (по запросу '{q}')"
                
        build_dies_table()
        safe_update(search_status)

    def build_dies_table():
        if current is None or not filtered_dies:
            dies_table.rows = []
            safe_update(dies_table)
            return
        rows = []
        for die in filtered_dies:
            count = to_int(die.get("totaldefectsondie", 0))
            rows.append(DataRow(cells=[
                DataCell(Text(show_value(die.get("id")), color=colors["text"])),
                DataCell(Text(show_value(die.get("mapx")), color=colors["text"])),
                DataCell(Text(show_value(die.get("mapy")), color=colors["text"])),
                DataCell(Text(show_value(die.get("symbol")), color=colors["text"])),
                DataCell(Text(show_value(die.get("status")), color=colors["text"])),
                DataCell(Text(str(count), color=colors["red"] if count else colors["text"])),
            ]))
        dies_table.rows = rows
        safe_update(dies_table)

    def show_report(report: Inspection):
        nonlocal current, filtered_dies
        current = report
        
        percent = round(report.failed * 100 / report.total, 2) if report.total else 0
        fields = [("Пластина", "waferid"), ("Имя JSON", "jsonprotocolfilename"),
                  ("Размер X, мм", "cellsizexmm"), ("Размер Y, мм", "cellsizeymm"),
                  ("Строк", "totalrows"), ("Столбцов", "totalcols"),
                  ("Время инспекции", "inspectiontimeformatted"),
                  ("Ср. время на кристалл", "averagetimeperdie"),
                  ("Каталог", "mainfolderpath")]
        
        # Перенесен блок "Проверено" на 2 позицию
        metrics = Row([
            card(Column([Text("Всего", color=colors["unclickable"]), Text(str(report.total), size=22, color=colors["text"], weight=FontWeight.BOLD)]), True),
            card(Column([Text("Проверено", color=colors["unclickable"]), Text(str(report.checked), size=22, color=colors["text"], weight=FontWeight.BOLD)]), True),
            card(Column([Text("Годных", color=colors["unclickable"]), Text(str(report.passed), size=22, color=colors["active"], weight=FontWeight.BOLD)]), True),
            card(Column([Text("Негодных", color=colors["unclickable"]), Text(f"{report.failed} ({percent}%)", size=22, color=colors["red"], weight=FontWeight.BOLD)]), True),
            card(Column([Text("Дефектов", color=colors["unclickable"]), Text(str(report.defects), size=22, color=colors["red"], weight=FontWeight.BOLD)]), True),
        ], spacing=10)

        details.controls = [
            Text(f"Инспекция: {report.wafer}", size=24, weight=FontWeight.BOLD, color=colors["text"]),
            Text(f"{report.date} • {report.path.name}", color=colors["unclickable"]),
            metrics,
            card(Column([
                Text("Метаданные", size=20, weight=FontWeight.BOLD, color=colors["text"]),
                *[Row([Text(label, width=220, color=colors["unclickable"]), Text(show_value(report.value(key)), color=colors["text"], selectable=True)]) for label, key in fields],
            ])),
        ]
        if not report.recognized:
            details.controls.insert(2, Text("Raw report: структура распознана частично.", color=colors["active"]))
        safe_update(details)
        
        search.value = ""
        safe_update(search)
        apply_filter()
        update_charts()

    def update_charts():
        chosen = [item for item in reports if item.path in selected] or reports
        charts.controls.clear()
        if not chosen:
            charts.controls.append(Text("JSON-отчёты не найдены.", color=colors["unclickable"], size=18))
            safe_update(charts)
            return

        all_defect_types = set()
        for report in chosen:
            stats = report.defects_statistics
            if isinstance(stats, dict):
                for orig_key in stats.keys():
                    all_defect_types.add(orig_key)
        
        all_defect_types = sorted(list(all_defect_types))

        palette = [
            Colors.GREEN_500, Colors.RED_500, Colors.BLUE_500, Colors.ORANGE_500, 
            Colors.PURPLE_500, Colors.CYAN_500, Colors.PINK_500, Colors.TEAL_500,
            Colors.LIME_500, Colors.INDIGO_500, Colors.BROWN_500, Colors.AMBER_500
        ]

        bar_groups = []
        x_labels = []
        max_y = 0

        for i, report in enumerate(chosen):
            x_val = i + 1
            waf_label = f"{x_val}. {report.wafer}"
            short_waf = waf_label if len(waf_label) <= 12 else waf_label[:10] + ".."
            x_labels.append(ChartAxisLabel(value=x_val, label=Text(short_waf, size=11, color=colors["text"])))

            rods = []
            
            passed = report.passed
            rods.append(BarChartRod(to_y=passed, color=palette[0], tooltip=f"[{report.wafer}]\nГодные кристаллы: {passed}"))
            max_y = max(max_y, passed)

            total_defs = report.defects
            rods.append(BarChartRod(to_y=total_defs, color=palette[1], tooltip=f"[{report.wafer}]\nВсего дефектов: {total_defs}"))
            max_y = max(max_y, total_defs)

            raw_stats = report.defects_statistics
            for j, def_type in enumerate(all_defect_types):
                count = to_int(raw_stats.get(def_type, 0))
                color_idx = (j + 2) % len(palette)
                rods.append(BarChartRod(to_y=count, color=palette[color_idx], tooltip=f"[{report.wafer}]\n{def_type}: {count}"))
                max_y = max(max_y, count)
            
            bar_groups.append(BarChartGroup(x=x_val, bar_rods=rods))

        # Добавляем "воздуха" сверху для тултипов (примерно 2 дополнительных шага сетки)
        step = max(1, (max_y + 5) // 6)
        y_max = max(step * 6, max_y, 1)
        chart_max_y = y_max + step * 2  

        legend_items = [
            Row([Container(width=12, height=12, bgcolor=palette[0], border_radius=2), Text("Годные кристаллы", color=colors["text"], size=12)]),
            Row([Container(width=12, height=12, bgcolor=palette[1], border_radius=2), Text("Всего дефектов", color=colors["text"], size=12)])
        ]
        for j, def_type in enumerate(all_defect_types):
            c_idx = (j + 2) % len(palette)
            legend_items.append(
                Row([Container(width=12, height=12, bgcolor=palette[c_idx], border_radius=2), Text(def_type, color=colors["text"], size=12)])
            )

        charts.controls = [
            Text("Количество дефектов и годных кристаллов", size=22, weight=FontWeight.BOLD, color=colors["text"]),
            # Увеличенная высота графика (height=550) + запас по оси Y (chart_max_y)
            card(BarChart(
                bar_groups=bar_groups,
                left_axis=ChartAxis(
                    labels=[ChartAxisLabel(value=i, label=Text(str(i), size=12, color=colors["text"])) for i in range(0, int(chart_max_y) + 1, step)],
                    labels_size=45,
                    title=Text("Количество", color=colors["text"], weight=FontWeight.BOLD),
                ),
                bottom_axis=ChartAxis(
                    labels=x_labels,
                    labels_size=35,
                ),
                horizontal_grid_lines=ChartGridLines(color=colors.get("inactive", Colors.GREY_800), width=1, dash_pattern=[4, 4]),
                tooltip_bgcolor=colors.get("top_bar", Colors.GREY_900),
                max_y=chart_max_y,
                height=550,
                expand=True,
                interactive=True,
            )),
            Row(legend_items, wrap=True, spacing=15, run_spacing=10),
        ]
        safe_update(charts)

    def update_list():
        report_list.controls.clear()
        for report in reports:
            checkbox = Checkbox(value=report.path in selected, active_color=colors["active"])
            def toggle(event, item=report):
                if event.control.value:
                    selected.add(item.path)
                else:
                    selected.discard(item.path)
                update_charts()
            checkbox.on_change = toggle
            report_list.controls.append(card(Row([
                checkbox,
                Column([
                    Text(report.wafer, size=19, weight=FontWeight.BOLD, color=colors["text"]),
                    Text(f"{report.date} • годные: {report.defects} • негодные: {report.failed}", size=14, color=colors["unclickable"]),
                ], expand=True),
                IconButton(icon=Icons.VISIBILITY_OUTLINED, icon_color=colors["active"], tooltip="Открыть", on_click=lambda e, item=report: show_report(item)),
            ], vertical_alignment=CrossAxisAlignment.CENTER)))
        if not reports:
            report_list.controls.append(Text("JSON-отчёты не найдены.", color=colors["unclickable"], size=18))
        safe_update(report_list)
        update_charts()

    def refresh(event=None):
        nonlocal current
        current_dir = directory
        reports.clear()
        selected.clear()
        current = None
        details.controls = [Text("Выберите инспекцию в списке.", color=colors["unclickable"], size=18)]
        safe_update(details)
        if current_dir.is_dir():
            load_reports()
        update_list()

    def remove_selected(event):
        nonlocal current
        if not selected:
            message(event.page, "Статистика", "Отметьте инспекции галочками, которые нужно убрать из списка.")
            return
        
        for p in selected:
            hidden_reports.add(p)
            
        removed = selected.copy()
        reports[:] = [item for item in reports if item.path not in removed]
        selected.clear()
        
        if current and current.path in removed:
            current = None
            details.controls = [Text("Выберите инспекцию в списке.", color=colors["unclickable"], size=18)]
            safe_update(details)
            dies_table.rows = []
            safe_update(dies_table)
            search_status.value = ""
            safe_update(search_status)
            
        update_list()

    def on_enter_search(event):
        apply_filter(force_message=True)

    search.on_submit = on_enter_search
    search.on_blur = lambda e: None
    
    load_reports()
    apply_filter()

    inspections_page = Container(content=Column([
        Row([
            Text("Статистика инспекций", size=26, weight=FontWeight.BOLD, color=colors["text"], expand=True),
            make_button("Выбрать каталог", Icons.FOLDER_OPEN, 210, choose_directory),
            make_button("Обновить", Icons.REFRESH, 150, refresh),
            make_button("Убрать из списка", Icons.DELETE_OUTLINE, 220, remove_selected, True),
        ]),
        Row([Icon(Icons.FOLDER_OUTLINED, color=colors["active"]), folder]),
        Divider(color=colors["inactive"]),
        Row([
            Container(content=Column([Text("Инспекции", size=21, weight=FontWeight.BOLD, color=colors["text"]), report_list], expand=True), width=580),
            VerticalDivider(color=colors["inactive"]),
            Container(content=details, expand=True),
        ], expand=True),
    ], expand=True), padding=10, bgcolor=colors["background"], expand=True)

    dies_page = Container(content=Column([
        Row([Text("Кристаллы выбранной инспекции", size=24, weight=FontWeight.BOLD, color=colors["text"], expand=True), search]),
        search_status,
        Text("Поиск: введите ID или диапазон (например 1-100) и нажмите Enter.", color=colors["unclickable"]),
        dies_view,
    ], expand=True), padding=10, bgcolor=colors["background"], expand=True)

    charts_page = Container(content=charts, padding=10, bgcolor=colors["background"], expand=True)

    return Tab(text="Статистика", content=Tabs(
        tabs=[
            Tab(text="Инспекции", content=inspections_page),
            Tab(text="Кристаллы и метаданные", content=dies_page),
            Tab(text="Графики", content=charts_page),
        ],
        selected_index=0,
        animation_duration=300,
        expand=True,
        label_color=colors["active"],
        unselected_label_color=colors["text"],
        indicator_color=colors["active"],
        divider_color=colors["top_bar"],
    ))