import sys
import os
import json
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QSplitter,
    QHeaderView, QComboBox, QLineEdit, QLabel, QMessageBox, QFrame, 
    QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class RuleEditorWidget(QWidget):
    def __init__(self, rules_data):
        super().__init__()
        self.rules_data = rules_data
        self.sort_column = 0
        self.sort_order = Qt.SortOrder.AscendingOrder
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Код правила", "Цель", "Серьезность", "Действия"])  # ✅ Русские заголовки
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_table)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.load_selected_rule)
        splitter.addWidget(self.table)
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        form_frame = QFrame()
        form_layout = QGridLayout(form_frame)
        row = 0
        form_layout.addWidget(QLabel("Код правила:"), row, 0)
        self.code_edit = QLineEdit()
        form_layout.addWidget(self.code_edit, row, 1)
        row += 1
        form_layout.addWidget(QLabel("Цель (target):"), row, 0)
        self.target_edit = QLineEdit()
        form_layout.addWidget(self.target_edit, row, 1)
        row += 1
        form_layout.addWidget(QLabel("Check:"), row, 0)
        self.check_edit = QLineEdit()
        form_layout.addWidget(self.check_edit, row, 1)
        row += 1
        form_layout.addWidget(QLabel("Условие:"), row, 0)
        self.condition_edit = QTextEdit()
        self.condition_edit.setMaximumHeight(60)
        form_layout.addWidget(self.condition_edit, row, 1)
        row += 1
        form_layout.addWidget(QLabel("Сообщение:"), row, 0)
        self.message_edit = QTextEdit()
        self.message_edit.setMaximumHeight(80)
        form_layout.addWidget(self.message_edit, row, 1)
        row += 1
        form_layout.addWidget(QLabel("Серьезность:"), row, 0)
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["info", "low", "medium", "warning", "high", "error", "critical"])
        form_layout.addWidget(self.severity_combo, row, 1)
        editor_layout.addWidget(form_frame)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Сохранить правило")
        self.save_btn.clicked.connect(self.save_rule)
        self.add_btn = QPushButton("➕ Добавить правило")
        self.add_btn.clicked.connect(self.add_new_rule)
        self.delete_btn = QPushButton("🗑️ Удалить правило")
        self.delete_btn.clicked.connect(self.delete_rule)
        self.load_json_btn = QPushButton("📂 Загрузить JSON")
        self.load_json_btn.clicked.connect(self.load_json_file)
        self.save_json_btn = QPushButton("💾 Сохранить JSON")
        self.save_json_btn.clicked.connect(self.save_json_file)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.load_json_btn)
        btn_layout.addWidget(self.save_json_btn)
        editor_layout.addLayout(btn_layout)
        editor_layout.addStretch()
        splitter.addWidget(editor_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        self.refresh_table()

    def create_backup(self, file_path):
        """
        Создает .bak файл
        """
        if os.path.exists(file_path):
            backup_path = file_path + ".bak"
            shutil.copy2(file_path, backup_path)
            print(f"Создан backup: {backup_path}")

    def sort_table(self, column):
        """
        Сортировка таблицы по столбцу
        """
        if column == 3:
            return
            
        self.sort_column = column
        self.sort_order = (
            Qt.SortOrder.AscendingOrder 
            if self.sort_order == Qt.SortOrder.DescendingOrder 
            else Qt.SortOrder.DescendingOrder
        )
        
        reverse = self.sort_order == Qt.SortOrder.DescendingOrder
        
        def get_sort_key(rule, col):
            if col == 0: 
                return rule.get("code", "").lower()
            elif col == 1:
                return rule.get("target", "").lower()
            elif col == 2:
                order = {"info": 0, "low": 1, "medium": 2, "warning": 3, "high": 4, "error": 5, "critical": 6}
                return order.get(rule.get("severity", "info"), 0)
            return ""
        
        self.rules_data.sort(key=lambda r: get_sort_key(r, column), reverse=reverse)
        self.refresh_table()

    def refresh_table(self):
        """
        Обновляет таблицу правил
        """
        self.table.setRowCount(len(self.rules_data))
        for row, rule in enumerate(self.rules_data):
            self.table.setItem(row, 0, QTableWidgetItem(rule.get("code", "")))
            self.table.setItem(row, 1, QTableWidgetItem(rule.get("target", "")))
            self.table.setItem(row, 2, QTableWidgetItem(rule.get("severity", "")))
            self.table.setItem(row, 3, QTableWidgetItem("Редактировать"))

    def load_selected_rule(self):
        """
        Загружает выбранное правило в форму редактирования
        """
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule = self.rules_data[row]
        self.code_edit.setText(rule.get("code", ""))
        self.target_edit.setText(rule.get("target", ""))
        self.check_edit.setText(rule.get("check", ""))
        self.condition_edit.setPlainText(rule.get("condition", ""))
        self.message_edit.setPlainText(rule.get("message", ""))
        self.severity_combo.setCurrentText(rule.get("severity", "info"))

    def save_rule(self):
        """
        Сохраняет правило из формы в данные
        """
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Предупреждение", "Выберите правило для редактирования!")
            return
        row = selected[0].row()
        self.rules_data[row] = {
            "code": self.code_edit.text(),
            "target": self.target_edit.text(),
            "check": self.check_edit.text(),
            "condition": self.condition_edit.toPlainText(),
            "message": self.message_edit.toPlainText(),
            "severity": self.severity_combo.currentText()
        }
        self.refresh_table()
        QMessageBox.information(self, "Успех", "Правило сохранено!")

    def add_new_rule(self):
        """
        Добавляет новое правило
        """
        new_rule = {
            "code": f"NEW-{len(self.rules_data) + 1}",
            "target": "store_vars",
            "check": "name",
            "condition": "",
            "message": "",
            "severity": "medium"
        }
        self.rules_data.append(new_rule)
        self.refresh_table()
        self.table.selectRow(len(self.rules_data) - 1)
        self.load_selected_rule()

    def delete_rule(self):
        """
        Удаляет выбранное правило
        """
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        reply = QMessageBox.question(self, "Подтверждение", 
                                   f"Удалить правило '{self.rules_data[row].get('code', 'NEW')} '?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.rules_data[row]
            self.refresh_table()

    def load_json_file(self):
        """
        Загружает правила из JSON файла с созданием .bak
        """
        file_path, _ = QFileDialog.getOpenFileName(self, "Загрузить правила", "", "JSON (*.json)")
        if file_path:
            try:
                self.create_backup(file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.rules_data = json.load(f)
                self.refresh_table()
                QMessageBox.information(self, "Успех", f"Загружено {len(self.rules_data)} правил\nBackup: {file_path}.bak")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{str(e)}")

    def save_json_file(self):
        """
        Сохраняет правила в JSON файл
        """
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить правила", "rules.json", "JSON (*.json)")
        if file_path:
            try:
                self.create_backup(file_path)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.rules_data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Успех", f"Сохранено {len(self.rules_data)} правил\nBackup: {file_path}.bak")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{str(e)}")


class RuleEditorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор правил AST анализатора")
        self.resize(1200, 800)
        rules_data = []
        if os.path.exists("rules.json"):
            try:
                self.widget = RuleEditorWidget(rules_data)
            except:
                rules_data = []
        else:
            rules_data = []
        central_widget = RuleEditorWidget(rules_data)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = RuleEditorApp()
    window.show()
    sys.exit(app.exec())
