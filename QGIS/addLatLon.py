from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProject, QgsField, QgsPointXY, QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.utils import iface
from PyQt5.QtCore import QVariant

class LatLonAdder(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('FaultLines - LatLon')
        layout = QtWidgets.QVBoxLayout()

        # Layer selection
        self.layer_combo = QtWidgets.QComboBox()
        self.populateLayerCombo()
        layout.addWidget(QtWidgets.QLabel('Select Point Layer:'))
        layout.addWidget(self.layer_combo)

        # Process button
        self.process_button = QtWidgets.QPushButton('Add Lat/Lon')
        self.process_button.clicked.connect(self.process)
        layout.addWidget(self.process_button)

        self.setLayout(layout)

    def populateLayerCombo(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == 0 and layer.geometryType() == 0:  # Vector layer and point geometry
                self.layer_combo.addItem(layer.name(), layer)

    def process(self):
        selected_layer = self.layer_combo.currentData()
        if not selected_layer:
            iface.messageBar().pushWarning("Error", "No point layer selected")
            return

        # Check if fields already exist
        fields = selected_layer.fields()
        if 'latINTP' not in fields.names():
            selected_layer.dataProvider().addAttributes([QgsField('latINTP', QVariant.Double, len=10, prec=8)])
        if 'lonINTP' not in fields.names():
            selected_layer.dataProvider().addAttributes([QgsField('lonINTP', QVariant.Double, len=11, prec=8)])
        selected_layer.updateFields()

        # Get field indices
        lat_field_index = selected_layer.fields().indexOf('latINTP')
        lon_field_index = selected_layer.fields().indexOf('lonINTP')

        # Set up coordinate transform if needed
        source_crs = selected_layer.crs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())

        # Start editing
        selected_layer.startEditing()

        # Update features
        for feature in selected_layer.getFeatures():
            point = feature.geometry().asPoint()
            # Transform point if CRS is not already EPSG:4326
            if source_crs != dest_crs:
                point = transform.transform(point)
            
            attrs = {
                lat_field_index: point.y(),
                lon_field_index: point.x()
            }
            selected_layer.changeAttributeValues(feature.id(), attrs)

        # Commit changes
        if selected_layer.commitChanges():
            iface.messageBar().pushSuccess("Success", "Latitude and Longitude added successfully")
        else:
            iface.messageBar().pushCritical("Error", "Failed to add Latitude and Longitude")

        self.close()

def run_lat_lon_adder():
    dialog = LatLonAdder()
    dialog.show()
    return dialog

# Run the tool
lat_lon_dialog = run_lat_lon_adder()