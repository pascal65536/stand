import sys
from pathlib import Path
import json

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QTreeView,
    QFileSystemModel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
)
from PySide6.QtCore import Qt, QDir


TEXT_EXTENSIONS = {".txt", ".py", ".md", ".log", ".cfg", ".ini", ".json", ".csv"}


class MainWindow(QMainWindow):
    """
    Главное окно приложения для синтаксического анализа кода.
    
    Приложение предоставляет графический интерфейс для просмотра файлов,
    их анализа с помощью различных инструментов (pylint, flake8, mypy, bandit, vulture)
    и отображения результатов анализа в табличном виде и в формате JSON.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учебный синтаксический анализатор кода")

        self.current_file: Path | None = None

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        # --- Панель кнопок: открыть каталог + сканировать файл ---
        buttons_layout = QHBoxLayout()
        self.open_dir_btn = QPushButton("Открыть каталог")
        self.scan_file_btn = QPushButton("Сканировать выбранный файл")

        self.open_dir_btn.clicked.connect(self.choose_directory)
        self.scan_file_btn.clicked.connect(self.scan_current_file)

        buttons_layout.addWidget(self.open_dir_btn)
        buttons_layout.addWidget(self.scan_file_btn)
        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        # --- Главный вертикальный сплиттер: (дерево+таблица) / JSON ---
        self.main_splitter = QSplitter(Qt.Vertical)

        # --- Верхний горизонтальный сплиттер: дерево | таблица ---
        self.top_splitter = QSplitter(Qt.Horizontal)

        # ====== ДЕРЕВО ФАЙЛОВ ======
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.currentPath())

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.currentPath()))
        self.tree.setColumnWidth(0, 250)
        self.tree.setHeaderHidden(False)

        self.tree.clicked.connect(self.on_item_activated)
        self.tree.doubleClicked.connect(self.on_item_activated)

        # ====== ТАБЛИЦА ======
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#",
            "pylint",
            "flake8",
            "mypy",
            "bandit",
            "vulture",
            "custom",
            "text",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.table.currentCellChanged.connect(self.on_table_row_changed)

        self.top_splitter.addWidget(self.tree)
        self.top_splitter.addWidget(self.table)
        self.top_splitter.setSizes([300, 900])

        # ====== НИЖНЯЯ JSON‑ОБЛАСТЬ ======
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(False)
        self.json_view.setPlaceholderText(
            "Здесь будет JSON‑информация о выбранной строке и результатах анализаторов..."
        )

        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.json_view)
        self.main_splitter.setSizes([500, 200])

        main_layout.addWidget(self.main_splitter)

        self.resize(1300, 750)

    # --- Выбор каталога ---
    def choose_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог с исходниками",
            QDir.currentPath(),
        )
        if directory:
            self.model.setRootPath(directory)
            self.tree.setRootIndex(self.model.index(directory))

    # --- Выбор файла в дереве ---
    def on_item_activated(self, index):
        if not index.isValid():
            return

        file_path = self.model.filePath(index)
        p = Path(file_path)

        if not p.is_file():
            return

        if p.suffix.lower() not in TEXT_EXTENSIONS:
            return

        self.current_file = p

        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = p.read_text(errors="replace")

        lines = text.splitlines()
        self.fill_table_with_lines(lines)

        self.json_view.setPlainText(
            json.dumps(
                {
                    "file": str(p),
                    "line": None,
                    "analyzers": {},
                    "message": "Выберите строку в таблице или нажмите 'Сканировать выбранный файл'",
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    # --- Заполнение таблицы ---
    def fill_table_with_lines(self, lines: list[str]):
        self.table.clearContents()
        self.table.setRowCount(len(lines))

        for row, line in enumerate(lines):
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            item_pylint = QTableWidgetItem("")
            item_flake8 = QTableWidgetItem("")
            item_mypy = QTableWidgetItem("")
            item_bandit = QTableWidgetItem("")
            item_vulture = QTableWidgetItem("")
            item_custom = QTableWidgetItem("")

            for item in (
                item_pylint,
                item_flake8,
                item_mypy,
                item_bandit,
                item_vulture,
                item_custom,
            ):
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            text_item = QTableWidgetItem(line)
            text_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

            self.table.setItem(row, 0, num_item)
            self.table.setItem(row, 1, item_pylint)
            self.table.setItem(row, 2, item_flake8)
            self.table.setItem(row, 3, item_mypy)
            self.table.setItem(row, 4, item_bandit)
            self.table.setItem(row, 5, item_vulture)
            self.table.setItem(row, 6, item_custom)
            self.table.setItem(row, 7, text_item)

        self.table.resizeColumnToContents(0)
        for col in range(1, 7):
            self.table.setColumnWidth(col, 70)
        self.table.horizontalHeader().setStretchLastSection(True)

    # --- Выбор строки таблицы ---
    def on_table_row_changed(self, current_row, current_col, prev_row, prev_col):
        if current_row < 0:
            return

        num_item = self.table.item(current_row, 0)
        text_item = self.table.item(current_row, 7)

        line_number = int(num_item.text()) if num_item else current_row + 1
        line_text = text_item.text() if text_item else ""

        data = {
            "file": str(self.current_file) if self.current_file else None,
            "line": line_number,
            "text": line_text,
            "analyzers": {
                "pylint": None,
                "flake8": None,
                "mypy": None,
                "bandit": None,
                "vulture": None,
                "custom": None,
            },
            "message": "Здесь будет подробная информация об этой строке после анализа.",
        }
        self.json_view.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    # --- Кнопка "Сканировать выбранный файл" ---
    def scan_current_file(self):
        if not self.current_file:
            self.json_view.setPlainText(
                json.dumps(
                    {
                        "error": "Файл не выбран",
                        "message": "Сначала выберите файл в дереве слева.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        p = self.current_file
        file_str = str(p)

        # Пути к json‑отчётам
        pylint_json = p.with_suffix(".pylint.json")
        flake8_json = p.with_suffix(".flake8.json")
        bandit_json = p.with_suffix(".bandit.json")
        mypy_json = p.with_suffix(".mypy.json")
        vulture_json = p.with_suffix(".vulture.json")

        # Команды, которые нужно выполнить вручную/через subprocess
        commands = {
            "pylint": {
                "text": f"pylint {file_str}",
                "json": f"pylint --output-format=json {file_str} > {pylint_json.name}",
            },
            "flake8": {
                "text": f"flake8 {file_str}",
                "json": f"flake8 --format=json {file_str} > {flake8_json.name}",
            },
            "bandit": {
                "text": f"bandit {file_str}",
                "json": f"bandit -f json {file_str} > {bandit_json.name}",
            },
            "mypy": {
                "text": f"mypy {file_str}",
                "json": f"mypy --output=json {file_str} > {mypy_json.name}",
            },
            "vulture": {
                "text": f"vulture {file_str}",
                "json": (
                    f"python vulture_to_json.py {file_str} {vulture_json.name}"
                ),
            },
        }

        info = {
            "file": file_str,
            "commands": commands,
            "json_reports": {
                "pylint": str(pylint_json),
                "flake8": str(flake8_json),
                "bandit": str(bandit_json),
                "mypy": str(mypy_json),
                "vulture": str(vulture_json),
            },
            "hint": (
                "В интерфейсе можно запускать эти команды через subprocess и затем "
                "парсить соответствующие JSON‑файлы для заполнения таблицы и нижней области."
            ),
        }

        self.json_view.setPlainText(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
