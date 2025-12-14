import sys
import subprocess
import os
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QMenuBar,
    QSplitter,
    QMenu,
)
from PyQt6.QtGui import QAction  # Исправленный импорт
from PyQt6.QtCore import QProcess


class PythonIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Мой PyQt6 Python IDE")
        self.setGeometry(100, 100, 900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        splitter = QSplitter()
        layout.addWidget(splitter)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Введите Python код здесь...")
        splitter.addWidget(self.editor)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Вывод программы...")
        splitter.addWidget(self.console)

        splitter.setSizes([600, 200])
        self.create_menu()
        self.process = QProcess(self)

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")

        new_act = QAction("Новый", self)
        new_act.triggered.connect(self.new_file)
        file_menu.addAction(new_act)

        open_act = QAction("Открыть", self)
        open_act.triggered.connect(self.open_file)
        file_menu.addAction(open_act)

        save_act = QAction("Сохранить", self)
        save_act.triggered.connect(self.save_file)
        file_menu.addAction(save_act)

        run_act = QAction("Запустить", self)
        run_act.triggered.connect(self.run_code)
        file_menu.addAction(run_act)

    def new_file(self):
        self.editor.clear()
        self.console.clear()

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть файл", "", "Python Files (*.py)"
        )
        if file_name:
            with open(file_name, "r") as f:
                self.editor.setText(f.read())

    def save_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл", "", "Python Files (*.py)"
        )
        if file_name:
            with open(file_name, "w") as f:
                f.write(self.editor.toPlainText())

    def run_code(self):
        code = self.editor.toPlainText()
        temp_file = "temp.py"
        with open(temp_file, "w") as f:
            f.write(code)

        self.console.clear()
        self.process.start("python", [temp_file])
        if not self.process.waitForStarted():
            QMessageBox.critical(self, "Ошибка", "Не удалось запустить код")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return

        self.process.waitForFinished()
        output = self.process.readAllStandardOutput().data().decode()
        error = self.process.readAllStandardError().data().decode()

        self.console.setText(output + error)
        if os.path.exists(temp_file):
            os.remove(temp_file)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ide = PythonIDE()
    ide.show()
    sys.exit(app.exec())
