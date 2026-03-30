import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


class DataFrameViewer(QMainWindow):
    def __init__(self, df: pd.DataFrame):
        super().__init__()

        self.setWindowTitle("Reporte de Resultados")
        self.resize(800, 500)

        self.table = QTableWidget()
        self.setCentralWidget(self.table)

        self.load_dataframe(df)

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        self.table.resizeColumnsToContents()
        self.table.setAlternatingRowColors(True)

    def load_dataframe(self, df: pd.DataFrame):
        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])
        self.table.setHorizontalHeaderLabels(df.columns)

        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iat[i, j]))
                self.table.setItem(i, j, item)

    def keyPressEvent(self, event):
        if (
            event.key() == Qt.Key.Key_C
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.copy_selection()
        else:
            super().keyPressEvent(event)

    def copy_selection(self):
        selected = self.table.selectedRanges()
        if not selected:
            return

        s = ""
        for r in selected:
            for i in range(r.topRow(), r.bottomRow() + 1):
                row_data = []
                for j in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self.table.item(i, j)
                    row_data.append(item.text() if item else "")
                s += "\t".join(row_data) + "\n"

        QApplication.clipboard().setText(s)

    # 🔥 AQUÍ está lo que quieres
    @staticmethod
    def show_dataframe(df: pd.DataFrame):
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)

        viewer = DataFrameViewer(df)
        viewer.show()
        app.exec()


if __name__ == "__main__":
    data = {
        "Nombre": ["Alice", "Bob", "Charlie"],
        "Edad": [25, 30, 35],
        "Ciudad": ["New York", "Los Angeles", "Chicago"],
    }
    df = pd.DataFrame(data)

    DataFrameViewer.show_dataframe(df)
