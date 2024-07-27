from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsSpatialIndex, QgsFeature, QgsGeometry, QgsUnitTypes, QgsProject, QgsDistanceArea
from qgis.utils import iface

class Worker(QtCore.QObject):
    progressChanged = QtCore.pyqtSignal(int)
    selectionCompleted = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal()

    def __init__(self, tolerance):
        super().__init__()
        self.tolerance = tolerance
        self.abort_flag = False

    def process(self):
        try:
            layer = iface.activeLayer()
            if layer is None:
                self.finished.emit()
                return
            
            index = QgsSpatialIndex()
            features = list(layer.getFeatures())
            total_features = len(features)

            for i, feature in enumerate(features):
                if self.abort_flag:
                    self.finished.emit()
                    return
                index.insertFeature(feature)
                if i % 100 == 0:
                    self.progressChanged.emit(int((i / total_features) * 50))

            adjacent_building_ids = set()

            for i, feature in enumerate(features):
                if self.abort_flag:
                    self.finished.emit()
                    return
                geom = feature.geometry()
                buffer_geom = geom.buffer(self.tolerance, 5)
                bbox = buffer_geom.boundingBox()
                intersecting_ids = index.intersects(bbox)
                
                for intersecting_id in intersecting_ids:
                    if intersecting_id == feature.id():
                        continue
                    
                    intersecting_feature = layer.getFeature(intersecting_id)
                    intersecting_geom = intersecting_feature.geometry()
                    
                    if buffer_geom.intersects(intersecting_geom):
                        adjacent_building_ids.add(feature.id())
                        adjacent_building_ids.add(intersecting_id)
                
                if i % 100 == 0:
                    self.progressChanged.emit(50 + int(((i + 1) / total_features) * 50))

            if not self.abort_flag:
                layer.selectByIds(list(adjacent_building_ids))
                self.progressChanged.emit(100)
                self.selectionCompleted.emit(len(adjacent_building_ids))
        finally:
            self.finished.emit()

    def abort(self):
        self.abort_flag = True

class ToleranceSelector(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.distance_area = QgsDistanceArea()
        self.distance_area.setEllipsoid(QgsProject.instance().ellipsoid())
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('FaultLines - Adjacency')
        
        layout = QtWidgets.QVBoxLayout()

        self.layer_label = QtWidgets.QLabel('Selected layer:')
        layout.addWidget(self.layer_label)
        
        layer = iface.activeLayer()
        self.layer_name_label = QtWidgets.QLabel(layer.name() if layer else 'No layer selected')
        layout.addWidget(self.layer_name_label)
        
        self.line_divider = QtWidgets.QFrame()
        self.line_divider.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(self.line_divider)
        
        self.buffer_label = QtWidgets.QLabel('Buffer distance')
        layout.addWidget(self.buffer_label)

        self.crs_label = QtWidgets.QLabel('In project\'s own CRS units')
        font = self.crs_label.font()
        font.setPointSize(8)
        self.crs_label.setFont(font)
        self.crs_label.setStyleSheet('color: gray')
        layout.addWidget(self.crs_label)
        
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)  # Increased maximum for higher precision
        self.slider.setValue(1)
        self.slider.setTickInterval(10)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider.valueChanged.connect(self.updateTextBox)
        
        self.textbox = QtWidgets.QLineEdit()
        self.textbox.setText(str(self.slider.value() / 1))  # Adjusted division
        self.textbox.textChanged.connect(self.updateSlider)
        
        self.converted_label = QtWidgets.QLabel()
        self.updateConvertedValue()
        
        self.button = QtWidgets.QPushButton('Run')
        self.button.clicked.connect(self.runSelection)
        
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        
        layout.addWidget(self.slider)
        layout.addWidget(self.textbox)
        layout.addWidget(self.converted_label)
        layout.addWidget(self.button)
        layout.addWidget(self.progressBar)
        
        self.setLayout(layout)
        
    def updateTextBox(self):
        value = self.slider.value() / 100  # Adjusted division
        self.textbox.setText(f"{value:.9f}")  # Format to 6 decimal places
        self.updateConvertedValue()
        
    def updateSlider(self):
        try:
            value = float(self.textbox.text())
            self.slider.setValue(int(value * 100))  # Adjusted multiplication
        except ValueError:
            pass  # Ignore invalid input
        self.updateConvertedValue()
        
    def updateConvertedValue(self):
        try:
            value = float(self.textbox.text())
            layer = iface.activeLayer()
            if layer:
                self.distance_area.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
                meters = self.distance_area.convertLengthMeasurement(value, QgsUnitTypes.DistanceMeters)
                layer_units = self.distance_area.convertLengthMeasurement(value, layer.crs().mapUnits())
                if meters >= 1:
                    converted = f"{meters:.2f}m"
                elif meters >= 0.01:
                    converted = f"{meters*100:.2f}cm"
                elif meters >= 0.001:
                    converted = f"{meters*1000:.2f}mm"
                else:
                    converted = f"{meters*1000000:.2f}µm"
                self.converted_label.setText(f"≈ {converted} (Layer units: {layer_units:.8f})")
            else:
                self.converted_label.setText("No layer selected")
        except ValueError:
            self.converted_label.setText("Invalid input")
        
    def runSelection(self):
        try:
            tolerance = float(self.textbox.text())
            layer = iface.activeLayer()
            if layer:
                # Convert tolerance to layer units
                tolerance_layer_units = self.distance_area.convertLengthMeasurement(tolerance, layer.crs().mapUnits())
                self.progressBar.setValue(0)

                self.stopWorker()
                
                self.thread = QtCore.QThread(self)
                self.worker = Worker(tolerance_layer_units)
                self.worker.moveToThread(self.thread)
                self.thread.started.connect(self.worker.process)
                self.worker.progressChanged.connect(self.progressBar.setValue)
                self.worker.selectionCompleted.connect(self.onSelectionCompleted)
                self.worker.finished.connect(self.thread.quit)
                self.worker.finished.connect(self.worker.deleteLater)
                self.thread.finished.connect(self.onThreadFinished)
                self.thread.start()
                
                self.button.setText("Cancel")
                self.button.clicked.disconnect()
                self.button.clicked.connect(self.cancelSelection)
            else:
                QtWidgets.QMessageBox.warning(self, "No Layer Selected", "Please select a layer before running the selection.")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for the tolerance.")

    def stopWorker(self):
        if self.thread and self.thread.isRunning():
            self.thread.requestInterruption()
            self.thread.quit()
            self.thread.wait()
        if self.worker:
            self.worker.abort()
        self.thread = None
        self.worker = None

    def cancelSelection(self):
        self.stopWorker()
        self.resetUI()

    def onSelectionCompleted(self, count):
        QtWidgets.QMessageBox.information(self, "Selection Completed", f"Selected {count} adjacent buildings")
        self.resetUI()

    def onThreadFinished(self):
        self.thread.deleteLater()
        self.thread = None
        self.worker = None
        self.resetUI()

    def resetUI(self):
        self.progressBar.setValue(0)
        self.button.setText("Run")
        self.button.clicked.disconnect()
        self.button.clicked.connect(self.runSelection)
        self.button.setEnabled(True)

    def closeEvent(self, event):
        self.stopWorker()
        event.accept()

# Create and display the UI
tolerance_selector = ToleranceSelector()
tolerance_selector.show()