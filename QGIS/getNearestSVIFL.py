from qgis.PyQt import QtWidgets, QtCore
from qgis.core import (QgsProject, QgsVectorLayer, QgsField, QgsFeature, 
                       QgsGeometry, QgsPointXY, QgsCategorizedSymbolRenderer,
                       QgsRendererCategory, QgsMarkerSymbol, QgsWkbTypes)
from qgis.utils import iface
from PyQt5.QtCore import QVariant
import requests

class NearestStreetViewLocator(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Nearest Street View Locator')
        layout = QtWidgets.QVBoxLayout()

        # Layer selection
        self.layer_combo = QtWidgets.QComboBox()
        self.populateLayerCombo()
        layout.addWidget(QtWidgets.QLabel('Select Adjacency Points Layer:'))
        layout.addWidget(self.layer_combo)

        # API Key input
        self.api_key_input = QtWidgets.QLineEdit()
        layout.addWidget(QtWidgets.QLabel('Enter Google API Key:'))
        layout.addWidget(self.api_key_input)

        # Process button
        self.process_button = QtWidgets.QPushButton('Find Nearest Street View Locations')
        self.process_button.clicked.connect(self.process)
        layout.addWidget(self.process_button)

        self.setLayout(layout)

    def populateLayerCombo(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsVectorLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PointGeometry:
                self.layer_combo.addItem(layer.name(), layer)

    def process(self):
        selected_layer = self.layer_combo.currentData()
        api_key = self.api_key_input.text()

        if not selected_layer:
            iface.messageBar().pushWarning("Error", "No layer selected")
            return
        if not api_key:
            iface.messageBar().pushWarning("Error", "API key is required")
            return

        self.find_nearest_street_view_locations(selected_layer, api_key)

    def find_nearest_street_view_locations(self, layer, api_key):
        # Create a new layer for Street View locations
        sv_layer = QgsVectorLayer("Point?crs=EPSG:4326", "Nearest_StreetView_Locations", "memory")
        sv_provider = sv_layer.dataProvider()

        # Add attributes
        sv_provider.addAttributes([
            QgsField("original_id", QVariant.Int),
            QgsField("pano_id", QVariant.String),
            QgsField("latitude", QVariant.Double),
            QgsField("longitude", QVariant.Double),
            QgsField("status", QVariant.String)
        ])
        sv_layer.updateFields()

        # Process each feature in the input layer
        total_features = layer.featureCount()
        for count, feature in enumerate(layer.getFeatures()):
            if feature.geometry() is None or feature.geometry().isNull():
                iface.messageBar().pushWarning("Null Geometry", f"Feature ID {feature.id()} has a null geometry. Skipping.")
                continue

            try:
                # Get the point coordinates
                point = feature.geometry().asPoint()
                
                # Query the Street View API
                url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={point.y()},{point.x()}&key={api_key}"
                response = requests.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')

                    if status == 'OK':
                        # Create a new feature for the Street View location
                        sv_feat = QgsFeature()
                        sv_feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(data['location']['lng']), float(data['location']['lat']))))
                        sv_feat.setAttributes([
                            feature.id(),
                            data['pano_id'],
                            float(data['location']['lat']),
                            float(data['location']['lng']),
                            status
                        ])
                        sv_provider.addFeature(sv_feat)
                    else:
                        # Add a feature at the original location with status
                        sv_feat = QgsFeature()
                        sv_feat.setGeometry(QgsGeometry.fromPointXY(point))
                        sv_feat.setAttributes([feature.id(), '', point.y(), point.x(), status])
                        sv_provider.addFeature(sv_feat)
                else:
                    iface.messageBar().pushWarning("API Error", f"Failed to query API for feature {feature.id()}")
            except Exception as e:
                iface.messageBar().pushWarning("Processing Error", f"Error processing feature {feature.id()}: {str(e)}")

            # Update progress
            progress = int((count + 1) / total_features * 100)
            iface.messageBar().pushInfo("Progress", f"Processed {count + 1} of {total_features} points ({progress}%)")

        # Add the layer to the map
        QgsProject.instance().addMapLayer(sv_layer)

        # Style the layer
        self.style_layer(sv_layer)

        iface.messageBar().pushSuccess("Success", "Nearest Street View locations added to the map")
        self.close()

    def style_layer(self, layer):
        # Create a categorized renderer
        renderer = QgsCategorizedSymbolRenderer('status')

        # Define categories and their styles
        categories = [
            ('OK', 'green', 'Street View Available'),
            ('ZERO_RESULTS', 'red', 'No Street View'),
            ('', 'gray', 'Unknown')
        ]

        for value, color, label in categories:
            symbol = QgsMarkerSymbol.createSimple({'name': 'circle', 'color': color, 'size': '3'})
            category = QgsRendererCategory(value, symbol, label)
            renderer.addCategory(category)

        # Apply the renderer to the layer
        layer.setRenderer(renderer)
        layer.triggerRepaint()

def run_nearest_street_view_locator():
    dialog = NearestStreetViewLocator()
    dialog.show()
    return dialog

# Run the tool
nearest_sv_dialog = run_nearest_street_view_locator()