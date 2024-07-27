from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsSpatialIndex, QgsFeature, QgsGeometry, QgsProject, QgsField, QgsPointXY
from qgis.utils import iface
from PyQt5.QtCore import QVariant

class Worker(QtCore.QObject):
    progressChanged = QtCore.pyqtSignal(int)
    indexingCompleted = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    def __init__(self, tolerance=10):
        super().__init__()
        self.abort_flag = False
        self.tolerance = tolerance

    def process(self):
        try:
            points_layer_name = '10_40192_Vertices_Intersections'
            buildings_layer_name = '00_40192'
            
            points_layers = QgsProject.instance().mapLayersByName(points_layer_name)
            buildings_layers = QgsProject.instance().mapLayersByName(buildings_layer_name)

            if not points_layers or not buildings_layers:
                raise ValueError(f"Layers not found: {points_layer_name}, {buildings_layer_name}")

            points_layer = points_layers[0]
            buildings_layer = buildings_layers[0]

            print(f"Points Layer: {points_layer_name}, Found: {points_layer is not None}")
            print(f"Buildings Layer: {buildings_layer_name}, Found: {buildings_layer is not None}")

            index = QgsSpatialIndex(buildings_layer.getFeatures())

            if points_layer.fields().indexFromName('indexR') == -1:
                points_layer.dataProvider().addAttributes([QgsField('indexR', QVariant.String)])
            if points_layer.fields().indexFromName('indexL') == -1:
                points_layer.dataProvider().addAttributes([QgsField('indexL', QVariant.String)])
            points_layer.updateFields()

            print("Attributes 'indexR' and 'indexL' added to points layer.")

            points_layer.startEditing()

            def get_relative_position(point, building_feature):
                centroid = building_feature.geometry().centroid().asPoint()
                angle = QgsPointXY(point).azimuth(QgsPointXY(centroid))
                return 'left' if 90 < angle < 270 else 'right'

            total_features = points_layer.featureCount()
            for i, point_feature in enumerate(points_layer.getFeatures()):
                if self.abort_flag:
                    break
                
                if point_feature.geometry() is None or point_feature.geometry().isEmpty():
                    continue

                point = point_feature.geometry().asPoint()
                bbox = QgsGeometry.fromPointXY(QgsPointXY(point)).buffer(self.tolerance, 5).boundingBox()
                intersecting_ids = index.intersects(bbox)

                nearest_right = (None, float('inf'))
                nearest_left = (None, float('inf'))

                for intersecting_id in intersecting_ids:
                    building_feature = buildings_layer.getFeature(intersecting_id)
                    distance = point_feature.geometry().distance(building_feature.geometry())
                    position = get_relative_position(point, building_feature)
                    
                    if position == 'right' and distance < nearest_right[1]:
                        nearest_right = (building_feature['index'], distance)
                    elif position == 'left' and distance < nearest_left[1]:
                        nearest_left = (building_feature['index'], distance)

                if nearest_right[0] is not None:
                    points_layer.changeAttributeValue(point_feature.id(), points_layer.fields().indexFromName('indexR'), str(nearest_right[0]))
                if nearest_left[0] is not None:
                    points_layer.changeAttributeValue(point_feature.id(), points_layer.fields().indexFromName('indexL'), str(nearest_left[0]))

                if i % 10 == 0:
                    self.progressChanged.emit(int((i / total_features) * 100))

            points_layer.commitChanges()
            if not self.abort_flag:
                self.indexingCompleted.emit()
                print("Indexing completed successfully.")
            
        except Exception as e:
            print(f"Error during processing: {e}")
        finally:
            self.finished.emit()

    def abort(self):
        self.abort_flag = True

class IndexingUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.thread = None
        self.worker = None

    def initUI(self):
        self.setWindowTitle('FaultLines - Adjacency Indexer')

        layout = QtWidgets.QVBoxLayout()

        self.layer_label = QtWidgets.QLabel('Selected Layers:')
        layout.addWidget(self.layer_label)

        self.points_layer_label = QtWidgets.QLabel('Points Layer: ' + self.get_layer_name('10_40192_Vertices_Intersections'))
        layout.addWidget(self.points_layer_label)

        self.buildings_layer_label = QtWidgets.QLabel('Buildings Layer: ' + self.get_layer_name('00_40192'))
        layout.addWidget(self.buildings_layer_label)

        self.tolerance_label = QtWidgets.QLabel('Tolerance (meters):')
        layout.addWidget(self.tolerance_label)
        self.tolerance_input = QtWidgets.QSpinBox()
        self.tolerance_input.setRange(1, 100)
        self.tolerance_input.setValue(10)
        layout.addWidget(self.tolerance_input)

        self.start_button = QtWidgets.QPushButton('Start Indexing')
        self.start_button.clicked.connect(self.start_indexing)
        layout.addWidget(self.start_button)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        layout.addWidget(self.progressBar)

        self.setLayout(layout)

    def get_layer_name(self, layer_name):
        layers = QgsProject.instance().mapLayersByName(layer_name)
        print(f"Searching for layer: {layer_name}, found: {len(layers)}")
        return layers[0].name() if layers else 'Layer not found'

    def start_indexing(self):
        self.progressBar.setValue(0)
        self.stop_worker()
        
        tolerance = self.tolerance_input.value()
        self.thread = QtCore.QThread(self)
        self.worker = Worker(tolerance=tolerance)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.process)
        self.worker.progressChanged.connect(self.progressBar.setValue)
        self.worker.indexingCompleted.connect(self.on_indexing_completed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()
        
        self.start_button.setText('Cancel')
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.cancel_indexing)

    def stop_worker(self):
        if self.thread and self.thread.isRunning():
            self.thread.requestInterruption()
            self.thread.quit()
            self.thread.wait()
        if self.worker:
            self.worker.abort()

    def cancel_indexing(self):
        self.stop_worker()
        self.reset_ui()

    def on_indexing_completed(self):
        QtWidgets.QMessageBox.information(self, 'Indexing Completed', 'Indexing of adjacency completed successfully.')
        self.reset_ui()

    def on_thread_finished(self):
        self.thread.deleteLater()
        self.thread = None
        self.worker = None
        self.reset_ui()

    def reset_ui(self):
        self.progressBar.setValue(0)
        self.start_button.setText('Start Indexing')
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.start_indexing)

    def closeEvent(self, event):
        self.stop_worker()
        event.accept()

# Create and display the UI
indexing_ui = IndexingUI()
indexing_ui.show()