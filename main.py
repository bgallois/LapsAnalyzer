# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
import numpy as np

from PySide2.QtWidgets import QApplication, QMainWindow, QAction, QFileDialog, QGraphicsScene, QToolTip, QTableWidget, QTableWidgetItem, QHeaderView, QGraphicsTextItem
from PySide2.QtCore import Signal, QFile, QStandardPaths, QCoreApplication, Qt, QPoint, QPointF, QTimer
from PySide2.QtGui import QColor, QIcon, QPen, QPainter, QPalette, QPixmap
import PySide2.QtXml

from PySide2.QtUiTools import QUiLoader

from PySide2.QtCharts import QtCharts
QChart = QtCharts.QChart
QChartView = QtCharts.QChartView
QLineSeries = QtCharts.QLineSeries
QAreaSeries = QtCharts.QAreaSeries
QValueAxis = QtCharts.QValueAxis

import rc_ressources

from gps import Gps


class QLaps(QMainWindow):

    resetted = Signal()

    def __init__(self):
        super(QLaps, self).__init__()
        self.load_ui()

        self.colorMap = [QColor(109, 144, 79, 255), QColor(252, 79, 48, 255), QColor(48,162,218, 255), QColor(229, 174, 56, 255), QColor(184, 184, 184, 255)]*10

        # ToolBar
        ele = QAction(QIcon(":/assets/images/elevation.png"), QCoreApplication.translate("main", "Elevation"), self)
        ele.setCheckable(True)
        ele.setChecked(True)
        ele.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "elevation"))
        self.resetted.connect(lambda: ele.setChecked(True))
        self.ui.toolBar.addAction(ele)

        speed = QAction(QIcon(":/assets/images/speed.png"), QCoreApplication.translate("main", "Speed"), self)
        speed.setCheckable(True)
        speed.setChecked(True)
        speed.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "speed"))
        self.resetted.connect(lambda: speed.setChecked(True))
        self.ui.toolBar.addAction(speed)

        hr = QAction(QIcon(":/assets/images/heartrate.png"), QCoreApplication.translate("main", "Heart Rate"), self)
        hr.setCheckable(True)
        hr.setChecked(True)
        hr.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "heartrate"))
        self.resetted.connect(lambda: hr.setChecked(True))
        self.ui.toolBar.addAction(hr)

        cd = QAction(QIcon(":/assets/images/cadence.png"), QCoreApplication.translate("main", "Cadence"), self)
        cd.setCheckable(True)
        cd.setChecked(True)
        cd.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "cadence"))
        self.resetted.connect(lambda: cd.setChecked(True))
        self.ui.toolBar.addAction(cd)

        pw = QAction(QIcon(":/assets/images/power.png"), QCoreApplication.translate("main", "Power"), self)
        pw.setCheckable(True)
        pw.setChecked(True)
        pw.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "power"))
        self.resetted.connect(lambda: pw.setChecked(True))
        self.ui.toolBar.addAction(pw)

        lap = QAction(QIcon(":/assets/images/lap.png"), QCoreApplication.translate("main", "Auto Laps"), self)
        lap.setCheckable(True)
        lap.setChecked(True)
        lap.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "laps"))
        lap.toggled.connect(lambda isChecked: manualLap.setChecked(not isChecked))
        lap.toggled.connect(self.load_statistic)
        lap.toggled.connect(self.set_mode)
        self.resetted.connect(lambda: lap.setChecked(True))
        self.ui.toolBar.addAction(lap)
        self.autoMode = True

        manualLap = QAction(QIcon(":/assets/images/lapManual.png"), QCoreApplication.translate("main", "Manual Laps"), self)
        manualLap.setCheckable(True)
        manualLap.setChecked(False)
        manualLap.toggled.connect(lambda isChecked: self.draw_plot(isChecked, "manual_laps"))
        manualLap.toggled.connect(lambda isChecked: lap.setChecked(not isChecked))
        manualLap.toggled.connect(self.load_statistic)
        self.ui.toolBar.addAction(manualLap)

        setting = QAction(QIcon(":/assets/images/settings.png"), QCoreApplication.translate("main", "Settings"), self)
        setting.setCheckable(True)
        setting.setChecked(False)
        self.ui.settingsDock.setVisible(False)
        setting.toggled.connect(self.ui.settingsDock.setVisible)
        self.ui.toolBar.addAction(setting)

        self.ui.actionOpen.triggered.connect(self.import_file)
        self.ui.actionExport.triggered.connect(self.export_as_png)
        self.plotScene = QGraphicsScene()
        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.AllAnimations)
        self.chartView = QChartView(self.chart)
        self.chartView.setRenderHint(QPainter.Antialiasing)
        self.ui.setCentralWidget(self.chartView)
        self.xAxis = QValueAxis()
        self.xAxis.setTickCount(5)
        self.xAxis.setTitleText("distance (km)")
        self.chart.addAxis(self.xAxis, Qt.AlignBottom)
        self.yAxis = QValueAxis()
        self.yAxis.setTickCount(12)
        self.yAxis.setTitleText("heartrate | cadence | speed")
        self.chart.addAxis(self.yAxis, Qt.AlignLeft)
        self.yAxisElev = QValueAxis()
        self.yAxisElev.setTitleText("elevation | power")
        self.chart.addAxis(self.yAxisElev, Qt.AlignRight)

        self.ui.diffTable.setHorizontalHeaderLabels(["Variable", "Min", "Mean", "Max"])
        self.ui.diffTable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.diffTable.verticalHeader().setVisible(False)

        self.ui.offset.valueChanged.connect(self.offset_changed)

    def load_ui(self):
        loader = QUiLoader()
        path = ":/form.ui"
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def set_mode(self, auto):
        self.autoMode = auto

    def offset_changed(self, value):
        if hasattr(self, 'gpsData'):
            self.chart.removeAllSeries()
            self.gpsData.set_offset(value*1000)
            self.get_plot_item()
            self.draw_plot()
            self.load_statistic()


    def import_file(self):
        self.resetted.emit()
        self.chart.removeAllSeries()
        fileName, __ = QFileDialog.getOpenFileName(self.ui, QCoreApplication.translate("main", "Open activity"), QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0], QCoreApplication.translate("main", "Activity Files (*.fit)"))
        if fileName:
            self.gpsData = Gps(fileName)
            self.ui.offset.setValue(0)
            tmpLen = self.gpsData.get_lap_len()
            self.ui.offset.setRange(0, (tmpLen[1] - tmpLen[0])/1000)
            self.gpsDataManual = Gps(fileName, False)
            self.get_plot_item()
            self.draw_plot()
            self.xAxis.setRange(0, self.gpsData.get("distance")[-1]*1e-3)
            self.yAxis.setRange(0, 220)
            self.load_statistic()
            return True
        else:
            return False

    def load_statistic(self):
        ## Model->View to implement
        if self.autoMode:
            data = self.gpsData
        else:
            data = self.gpsDataManual
        self.ui.statTab.clear()
        for l, i in enumerate(data.stat.keys()):
            table = QTableWidget(4,4)
            table.setHorizontalHeaderLabels(["Variable", "Min", "Mean", "Max"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.verticalHeader().setVisible(False)
            for k, j in enumerate(data.stat[i].keys()):
                table.setItem(k, 0, QTableWidgetItem(j))
                table.setItem(k, 1, QTableWidgetItem(str(np.around(data.stat[i][j]["min"], 1))))
                table.setItem(k, 2, QTableWidgetItem(str(np.around(data.stat[i][j]["mean"], 1))))
                table.setItem(k, 3, QTableWidgetItem(str(np.around(data.stat[i][j]["max"], 1))))
            table.setStyleSheet("QTableWidget{{ background-color: rgba({0}, {1}, {2}, {3}); }}".format(self.colorMap[l].red(), self.colorMap[l].green(), self.colorMap[l].blue(), 100))
            self.ui.statTab.addTab(table, i)

        self.ui.statTab1.clear()
        for l, i in enumerate(data.stat.keys()):
            table1 = QTableWidget(4,4)
            table1.setHorizontalHeaderLabels(["Variable", "Min", "Mean", "Max"])
            table1.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table1.verticalHeader().setVisible(False)
            for k, j in enumerate(data.stat[i].keys()):
                table1.setItem(k, 0, QTableWidgetItem(j))
                table1.setItem(k, 1, QTableWidgetItem(str(np.around(data.stat[i][j]["min"], 1))))
                table1.setItem(k, 2, QTableWidgetItem(str(np.around(data.stat[i][j]["mean"], 1))))
                table1.setItem(k, 3, QTableWidgetItem(str(np.around(data.stat[i][j]["max"], 1))))
            table1.setStyleSheet("QTableWidget{{ background-color: rgba({0}, {1}, {2}, {3}); }}".format(self.colorMap[l].red(), self.colorMap[l].green(), self.colorMap[l].blue(), 100))
            self.ui.statTab1.addTab(table1, i)

    def load_statistic_diff(self):
        if self.autoMode:
            data = self.gpsData
        else:
            data = self.gpsDataManual
        index = self.ui.statTab.currentIndex()
        index1 = self.ui.statTab1.currentIndex()
        if "lap_{0}".format(index) in data.stat and "lap_{0}".format(index1) in data.stat:
            for k, j in enumerate(data.stat["lap_{0}".format(index)].keys()):
                self.ui.diffTable.setItem(k, 0, QTableWidgetItem(j))
                self.ui.diffTable.setItem(k, 1, QTableWidgetItem(str(np.around(data.stat["lap_{0}".format(index)][j]["min"] - data.stat["lap_{0}".format(index1)][j]["min"], 1))))
                self.ui.diffTable.setItem(k, 2, QTableWidgetItem(str(np.around(data.stat["lap_{0}".format(index)][j]["mean"] - data.stat["lap_{0}".format(index1)][j]["mean"], 1))))
                self.ui.diffTable.setItem(k, 3, QTableWidgetItem(str(np.around(data.stat["lap_{0}".format(index)][j]["max"] - data.stat["lap_{0}".format(index1)][j]["max"], 1))))
        for i in range(self.ui.diffTable.rowCount()):
            for j in range(self.ui.diffTable.columnCount() - 1):
                if float(self.ui.diffTable.item(i, j + 1).text()) > 0:
                    self.ui.diffTable.item(i, j + 1).setBackground(self.colorMap[0])
                elif float(self.ui.diffTable.item(i, j + 1).text()) < 0:
                    self.ui.diffTable.item(i, j + 1).setBackground(self.colorMap[1])
                else:
                    self.ui.diffTable.item(i, j + 1).setBackground(self.colorMap[2])


    def get_plot_item(self):
        line = QPen()
        line.setWidth(3)
        elevationLine = QLineSeries()
        speed = QLineSeries()
        heartrate = QLineSeries()
        cadence = QLineSeries()
        power = QLineSeries()
        for i, j, k, l, m, n in zip(self.gpsData.get("distance"), self.gpsData.get("elevation"), self.gpsData.get("speed"), self.gpsData.get("heartrate"), self.gpsData.get("cadence"), self.gpsData.get("power")):
            elevationLine.append(i/1000, j)
            speed.append(i/1000, k)
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

        # Automatic laps
        self.plotItem = {}
        colorMap = []
        for i in self.colorMap:
            i.setAlpha(80)
            colorMap.append(i)
        for i, j in enumerate(self.gpsData.laps[0:-1]):
            self.plotItem["lap_" + str(i)] = self.draw_rectangle(colorMap[i], j, self.gpsData.laps[i+1]-j, i, True)

        # Manual laps
        for i, j in enumerate(self.gpsDataManual.laps[0:-1]):
            self.plotItem["manual_lap_" + str(i)] = self.draw_rectangle(colorMap[i], j, self.gpsDataManual.laps[i+1]-j, i, False)

        self.plotItem.update({"elevation": elevation, "heartrate": heartrate, "cadence": cadence, "speed": speed, "power": power})

    def draw_rectangle(self, color, x, width, count, auto=True):
        rect = QAreaSeries()
        up = QLineSeries()
        rect.setBorderColor(color)
        for i in self.gpsData.get("distance"):
            if i >= x and i < x + width and x + width <= self.gpsData.get("distance")[-1]:
                up.append(i/1000, 220)
        rect.setUpperSeries(up)
        rect.setColor(color);
        summary = QToolTip()
        palette = QToolTip.palette();
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255, 255));
        summary.setPalette(palette)
        if auto:
            rect.hovered.connect(lambda x, y: summary.showText(self.chartView.mapToGlobal(self.chartView.rect().topLeft()), self.gpsData.get_short_summary(count)))
        else:
            rect.hovered.connect(lambda x, y: summary.showText(self.chartView.mapToGlobal(self.chartView.rect().topLeft()), self.gpsDataManual.get_short_summary(count)))
        rect.clicked.connect(lambda x: self.ui.statTab.setCurrentIndex(count))
        rect.clicked.connect(self.load_statistic_diff)
        rect.hovered.connect(lambda x: self.ui.statTab1.setCurrentIndex(count))
        rect.hovered.connect(self.load_statistic_diff)
        return rect

    def export_as_png(self):
        self.ui.showFullScreen()
        QTimer.singleShot(1000, self.save_png) # Wait that the screen is repaint then save the chart

    def save_png(self):
        if self.autoMode:
            data = self.gpsData
        else:
            data = self.gpsDataManual

        overlay = []
        for i, j in enumerate(data.laps[0:-1]):
            text = QGraphicsTextItem(data.get_short_summary(i))
            text.setPos(self.chart.mapToScene(self.chart.mapToPosition(QPointF(j/1000, 220), self.plotItem["speed"])))
            self.chartView.scene().addItem(text)
            overlay.append(text)

        text = QGraphicsTextItem("https://github.com/bgallois/LapsAnalyzer/")
        text.setPos(self.chart.mapToScene(self.chart.mapToPosition(QPointF(0, -10), self.plotItem["speed"])))
        self.chartView.scene().addItem(text)
        overlay.append(text)

        p = QPixmap(self.chartView.size())
        self.chartView.render(p)
        p.save(QStandardPaths.standardLocations(QStandardPaths.PicturesLocation)[0] + "/" + str(np.random.randint(100, 999)) + ".png", "PNG", 100)
        for i in overlay:
            self.chartView.scene().removeItem(i)
        self.ui.showNormal()

    def draw_plot(self, isChecked=True, key="all"):
        if key == "all":
            for i in self.plotItem.keys():
                self.chart.addSeries(self.plotItem[i])
                if i in ["elevation", "power"]:
                    self.plotItem[i].attachAxis(self.xAxis);
                    self.plotItem[i].attachAxis(self.yAxisElev);
                else:
                    self.plotItem[i].attachAxis(self.xAxis);
                    self.plotItem[i].attachAxis(self.yAxis);
                if i.startswith("lap_"): self.chart.legend().markers(self.plotItem[i])[0].setVisible(False)
                if i.startswith("manual_lap_"):
                    self.chart.legend().markers(self.plotItem[i])[0].setVisible(False)
                    self.plotItem[i].setVisible(False)
        elif key == "laps":
            for i in self.plotItem.keys():
                if i.startswith("lap_"):
                    self.plotItem[i].setVisible(isChecked)
                    self.chart.legend().markers(self.plotItem[i])[0].setVisible(False)
        elif key == "manual_laps":
            for i in self.plotItem.keys():
                if i.startswith("manual_lap_"):
                    self.plotItem[i].setVisible(isChecked)
                    self.chart.legend().markers(self.plotItem[i])[0].setVisible(False)
        else:
            self.plotItem[key].setVisible(isChecked)



if __name__ == "__main__":
    app = QApplication([])
    widget = QLaps()
    widget.ui.show()
    sys.exit(app.exec_())
