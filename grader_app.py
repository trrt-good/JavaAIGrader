import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel, QProgressBar, QMessageBox, 
                             QComboBox, QLineEdit, QGroupBox, QFormLayout, QTableView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QAbstractTableModel
import pandas as pd
from grader import grade_submissions

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]
        return None

class GradingThread(QThread):
    finished = pyqtSignal(pd.DataFrame)
    error = pyqtSignal(str)

    def __init__(self, student_code_dir, assignment_pdf, scoring_sheet_file, grading_breakdown_dir, config):
        super().__init__()
        self.student_code_dir = student_code_dir
        self.assignment_pdf = assignment_pdf
        self.scoring_sheet_file = scoring_sheet_file
        self.grading_breakdown_dir = grading_breakdown_dir
        self.config = config

    def run(self):
        try:
            result = grade_submissions(
                self.student_code_dir,
                self.assignment_pdf,
                self.scoring_sheet_file,
                self.grading_breakdown_dir,
                self.config
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Grading Application")
        self.setGeometry(100, 100, 1000, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()

        self.student_code_dir_edit = QLineEdit()
        self.student_code_dir_btn = QPushButton("Browse")
        self.student_code_dir_btn.clicked.connect(lambda: self.select_directory("student_code_dir"))
        file_layout.addRow("Student Code Directory:", self.create_browse_layout(self.student_code_dir_edit, self.student_code_dir_btn))

        self.assignment_pdf_edit = QLineEdit()
        self.assignment_pdf_btn = QPushButton("Browse")
        self.assignment_pdf_btn.clicked.connect(lambda: self.select_file("assignment_pdf", "PDF Files (*.pdf)"))
        file_layout.addRow("Assignment PDF:", self.create_browse_layout(self.assignment_pdf_edit, self.assignment_pdf_btn))

        self.scoring_sheet_edit = QLineEdit()
        self.scoring_sheet_btn = QPushButton("Browse")
        self.scoring_sheet_btn.clicked.connect(lambda: self.select_file("scoring_sheet", "Text Files (*.txt *.md)"))
        file_layout.addRow("Scoring Sheet:", self.create_browse_layout(self.scoring_sheet_edit, self.scoring_sheet_btn))

        self.output_dir_edit = QLineEdit()
        self.output_dir_btn = QPushButton("Browse")
        self.output_dir_btn.clicked.connect(lambda: self.select_directory("output_dir"))
        file_layout.addRow("Output Directory:", self.create_browse_layout(self.output_dir_edit, self.output_dir_btn))

        file_group.setLayout(file_layout)
        self.layout.addWidget(file_group)

        # Model selection
        model_group = QGroupBox("Model Selection")
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        model_layout.addWidget(QLabel("Select Model:"))
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)
        self.layout.addWidget(model_group)

        # Grading button
        self.grade_btn = QPushButton("Start Grading")
        self.grade_btn.setEnabled(False)
        self.grade_btn.clicked.connect(self.start_grading)
        self.layout.addWidget(self.grade_btn)

        # Results display
        self.results_table = QTableView()
        self.layout.addWidget(self.results_table, 1)

        # Export options
        export_group = QGroupBox("Export Results")
        export_layout = QHBoxLayout()
        self.export_combo = QComboBox()
        self.export_combo.addItems(["CSV", "Excel", "TSV"])
        self.export_btn = QPushButton("Export")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_results)
        export_layout.addWidget(QLabel("Export Format:"))
        export_layout.addWidget(self.export_combo)
        export_layout.addWidget(self.export_btn)
        export_group.setLayout(export_layout)
        self.layout.addWidget(export_group)

    def create_browse_layout(self, line_edit, button):
        layout = QHBoxLayout()
        layout.addWidget(line_edit)
        layout.addWidget(button)
        return layout

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                self.config = json.load(f)
            self.model_combo.addItems(self.config["model_map"].keys())
            self.model_combo.setCurrentText(self.config["default_model"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config: {str(e)}")

    def select_directory(self, attr_name):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            getattr(self, f"{attr_name}_edit").setText(directory)
            self.check_grading_ready()

    def select_file(self, attr_name, file_filter):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            getattr(self, f"{attr_name}_edit").setText(file_path)
            self.check_grading_ready()

    def check_grading_ready(self):
        self.grade_btn.setEnabled(
            all(getattr(self, f"{attr}_edit").text() for attr in 
                ["student_code_dir", "assignment_pdf", "scoring_sheet", "output_dir"])
        )

    def start_grading(self):
        self.grade_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        selected_model = self.model_combo.currentText()
        self.config["default_model"] = selected_model

        self.grading_thread = GradingThread(
            self.student_code_dir_edit.text(),
            self.assignment_pdf_edit.text(),
            self.scoring_sheet_edit.text(),
            self.output_dir_edit.text(),
            self.config
        )
        self.grading_thread.finished.connect(self.display_results)
        self.grading_thread.error.connect(self.show_error)
        self.grading_thread.start()

    def display_results(self, results_df):
        self.results_df = results_df
        model = PandasModel(results_df)
        self.results_table.setModel(model)
        self.results_table.resizeColumnsToContents()
        self.grade_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        QMessageBox.information(self, "Grading Complete", "The grading process has finished successfully.")

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", f"An error occurred during grading: {error_message}")
        self.grade_btn.setEnabled(True)

    def export_results(self):
        if not hasattr(self, 'results_df'):
            QMessageBox.warning(self, "No Results", "There are no results to export.")
            return

        export_format = self.export_combo.currentText()
        file_filters = {
            "CSV": "CSV Files (*.csv)",
            "Excel": "Excel Files (*.xlsx)",
            "TSV": "TSV Files (*.tsv)"
        }
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "", file_filters[export_format])
        
        if file_path:
            try:
                if export_format == "CSV":
                    self.results_df.to_csv(file_path, index=False)
                elif export_format == "Excel":
                    self.results_df.to_excel(file_path, index=False)
                elif export_format == "TSV":
                    self.results_df.to_csv(file_path, sep='\t', index=False)
                QMessageBox.information(self, "Export Successful", f"Results exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export results: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
