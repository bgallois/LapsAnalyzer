# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QGraphicsScene
from PySide6.QtCore import QFile, QStandardPaths, QCoreApplication, Qt
from PySide6.QtGui import QColor, QAction, QIcon, QPen, QPainter
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QAreaSeries

import rc_ressources

from gps import Gps


class QLaps(QMainWindow):
    def __init__(self):
        super(QLaps, self).__init__()
        self.load_ui()

        self.colorMap = [QColor(109, 144, 79, 255), QColor(252, 79, 48, 255), QColor(48,162,218, 255), QColor(229, 174, 56, 255), QColor(184, 184, 184, 255)]*10

        # ToolBar
        ele = QAction(QIcon(":/assets/images/elevation.png"), QCoreApplication.translate("main", "Elevation"), self)
        ele.setCheckable(True)
        ele.setChecked(True)
        ele.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "elevation"))
        self.ui.toolBar.addAction(ele)

        speed = QAction(QIcon(":/assets/images/speed.png"), QCoreApplication.translate("main", "Speed"), self)
        speed.setCheckable(True)
        speed.setChecked(True)
        speed.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "speed"))
        self.ui.toolBar.addAction(speed)

        hr = QAction(QIcon(":/assets/images/heartrate.png"), QCoreApplication.translate("main", "Heart Rate"), self)
        hr.setCheckable(True)
        hr.setChecked(True)
        hr.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "heartrate"))
        self.ui.toolBar.addAction(hr)

        cd = QAction(QIcon(":/assets/images/cadence.png"), QCoreApplication.translate("main", "Cadence"), self)
        cd.setCheckable(True)
        cd.setChecked(True)
        cd.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "cadence"))
        self.ui.toolBar.addAction(cd)

        pw = QAction(QIcon(":/assets/images/power.png"), QCoreApplication.translate("main", "Power"), self)
        pw.setCheckable(True)
        pw.setChecked(True)
        pw.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "power"))
        self.ui.toolBar.addAction(pw)

        lap = QAction(QIcon(":/assets/images/lap.png"), QCoreApplication.translate("main", "Laps"), self)
        lap.setCheckable(True)
        lap.setChecked(True)
        lap.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "laps"))
        self.ui.toolBar.addAction(lap)


        self.ui.actionOpen.triggered.connect(self.import_file)
        self.plotScene = QGraphicsScene()
        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.AllAnimations)
        self.chartView = QChartView(self.chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)
        self.ui.setCentralWidget(self.chartView)

    def load_ui(self):
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        print(path)
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def import_file(self):
        self.chart.removeAllSeries()
        fileName, __ = QFileDialog.getOpenFileName(self.ui, QCoreApplication.translate("main", "Open activity"), QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0], QCoreApplication.translate("main", "Activity Files (*.fit)"))
        if fileName:
            self.gpsData = Gps(fileName)
            self.get_plot_item()
            self.draw_plot()
            return True
        else:
            return False

    def get_plot_item(self):
        line = QPen()
        line.setWidth(3)
        elevationLine = QLineSeries()
        speed = QLineSeries()
        heartrate = QLineSeries()
        cadence = QLineSeries()
        power = QLineSeries()
        for i, j, k, l, m, n in zip(self.gpsData.get("distance"), self.gpsData.get("elevation"), self.gpsData.get("enhanced_speed"), self.gpsData.get("heartrate"), self.gpsData.get("cadence"), self.gpsData.get("power")):
            elevationLine.append(i/1000, j)
            speed.append(i/1000, k*3600*1e-3)
            heartrate.append(i/1000, l)
            cadence.append(i/1000, m)
            power.append(i/1000, n)

        elevation = QAreaSeries()
        elevation.setUpperSeries(elevationLine)
        elevation.setColor(QColor(184, 184, 184, 127));
        elevation.setBorderColor(QColor(184, 184, 184, 127))
        elevation.setName("elevation (m)")

        speed.setName("speed (km/h)")
        speed.setPen(line)
        speed.setColor(QColor(109, 144, 79, 255));

        heartrate.setPen(line)
        heartrate.setName("heart rate (bpm)")
        heartrate.setColor(QColor(252, 79, 48, 255));

        cadence.setName("cadence (rpm)")
        cadence.setPen(line)
        cadence.setColor(QColor(48,162,218, 255));

        power.setName("power (w)")
        power.setPen(line)
        power.setColor(QColor(229, 174, 56, 255));

        self.plotItem = {}
        colorMap = []
        for i in self.colorMap:
            i.setAlpha(80)
            colorMap.append(i)
        lap = self.gpsData.get_lap_len()
        offset = 0
        i = 0
        dist = 0
        while dist < self.gpsData.get("distance")[-1]:
            self.plotItem["lap_" + str(i)] = self.draw_rectangle(colorMap[i], dist, lap)
            i += 1
            dist += lap

        self.plotItem.update({"elevation": elevation, "heartrate": heartrate, "cadence": cadence, "speed": speed, "power": power})

    def draw_rectangle(self, color, x, width):
        rect = QAreaSeries()
        up = QLineSeries()
        rect.setBorderColor(color)
        for i in self.gpsData.get("distance"):
            if i >= x and i < x + width and x + width < self.gpsData.get("distance")[-1]:
                up.append(i/1000, 220)
        rect.setUpperSeries(up)
        rect.setColor(color);
        return rect

    def draw_plot(self, isChecked=True, key="all"):
        if key == "all":
            for i in self.plotItem.keys():
                self.chart.addSeries(self.plotItem[i])
                if i.startswith("lap_"): self.chart.legend().markers(self.plotItem[i])[0].setVisible(False)
            self.chart.createDefaultAxes()
        elif key == "laps":
            for i in self.plotItem.keys():
                if i.startswith("lap_"):
                    self.plotItem[i].setVisible(isChecked)
                    self.chart.legend().markers(self.plotItem[i])[0].setVisible(False)
            self.chart.createDefaultAxes()
        else:
            self.plotItem[key].setVisible(isChecked)
            self.chart.createDefaultAxes()


if __name__ == "__main__":
    app = QApplication([])
    widget = QLaps()
    widget.ui.show()
    sys.exit(app.exec())
