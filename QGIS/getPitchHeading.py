from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField, QgsLineSymbol, QgsArrowSymbolLayer
from qgis.utils import iface
from PyQt5.QtCore import QVariant
from math import atan2, degrees

class PitchHeadingCalculator(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('FaultLines - Get PH')
        layout = QtWidgets.QVBoxLayout()

        # Layer selection
        self.layer_combo = QtWidgets.QComboBox()
        self.populateLayerCombo()
        layout.addWidget(QtWidgets.QLabel('Select Layer:'))
        layout.addWidget(self.layer_combo)

        # Draw lines checkbox
        self.draw_lines_checkbox = QtWidgets.QCheckBox('Draw Lines')
        self.draw_lines_checkbox.setChecked(True)
        layout.addWidget(self.draw_lines_checkbox)

        # Process button
        self.process_button = QtWidgets.QPushButton('Calculate Pitch and Heading')
        self.process_button.clicked.connect(self.process)
        layout.addWidget(self.process_button)

        self.setLayout(layout)

    def populateLayerCombo(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsVectorLayer.VectorLayer:
                self.layer_combo.addItem(layer.name(), layer)

    def process(self):
        layer = self.layer_combo.currentData()
        if not layer:
            iface.messageBar().pushWarning("Error", "No layer selected")
            return

        self.calculate_pitch_heading(layer)
        if self.draw_lines_checkbox.isChecked():
            self.draw_lines(layer)

    def calculate_pitch_heading(self, layer):
        if 'pitch' not in layer.fields().names():
            layer.dataProvider().addAttributes([QgsField("pitch", QVariant.Double)])
        if 'heading' not in layer.fields().names():
            layer.dataProvider().addAttributes([QgsField("heading", QVariant.Double)])
        layer.updateFields()

        pitch_heading_dict = {}
        total_features = layer.featureCount()
        for count, feature in enumerate(layer.getFeatures()):
            latINTP = feature['latINTP']
            lonINTP = feature['lonINTP']
            latSVI = feature['latSVI']
            lonSVI = feature['lonSVI']
            panoId = feature['panoId']
            dx = lonINTP - lonSVI
            dy = latINTP - latSVI
            heading = degrees(atan2(dx, dy))
            pitch = 0  # Assuming a flat surface, set pitch to 0
            pitch_heading_dict[panoId] = (pitch, heading)
            
            progress = int((count + 1) / total_features * 100)
            iface.messageBar().pushInfo("Progress", f"Calculated {count + 1} of {total_features} features ({progress}%)")

        layer.startEditing()
        for feature in layer.getFeatures():
            panoId = feature['panoId']
            if panoId in pitch_heading_dict:
                pitch, heading = pitch_heading_dict[panoId]
                feature.setAttribute(feature.fieldNameIndex('pitch'), pitch)
                feature.setAttribute(feature.fieldNameIndex('heading'), heading)
                layer.updateFeature(feature)
        layer.commitChanges()
        
        iface.messageBar().pushSuccess("Success", "Pitch and heading calculated successfully")

    def draw_lines(self, layer):
        line_layer = QgsVectorLayer("LineString?crs=EPSG:4326", f"{layer.name()}_Arrows", "memory")
        line_layer.dataProvider().addAttributes([QgsField("panoId", QVariant.String)])
        line_layer.updateFields()

        total_features = layer.featureCount()
        for count, feature in enumerate(layer.getFeatures()):
            latINTP = feature['latINTP']
            lonINTP = feature['lonINTP']
            latSVI = feature['latSVI']
            lonSVI = feature['lonSVI']
            panoId = feature['panoId']
            line_feature = QgsFeature()
            line_feature.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(lonSVI, latSVI), QgsPointXY(lonINTP, latINTP)]))
            line_feature.setAttributes([panoId])
            line_layer.dataProvider().addFeature(line_feature)
            
            progress = int((count + 1) / total_features * 100)
            iface.messageBar().pushInfo("Progress", f"Drew {count + 1} of {total_features} lines ({progress}%)")

        line_symbol = QgsLineSymbol()
        arrow_symbol_layer = QgsArrowSymbolLayer()
        arrow_symbol_layer.setArrowWidth(0.5)
        arrow_symbol_layer.setArrowStartWidth(0.5)
        arrow_symbol_layer.setHeadLength(1.5)
        arrow_symbol_layer.setHeadThickness(1.5)
        line_symbol.appendSymbolLayer(arrow_symbol_layer)
        line_layer.renderer().setSymbol(line_symbol)
        QgsProject.instance().addMapLayer(line_layer)
        
        iface.messageBar().pushSuccess("Success", "Arrow lines drawn successfully")

def run_pitch_heading_calculator():
    dialog = PitchHeadingCalculator()
    dialog.show()
    return dialog

# Run the tool
pitch_heading_dialog = run_pitch_heading_calculator()