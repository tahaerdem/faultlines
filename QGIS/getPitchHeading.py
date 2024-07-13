from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField
from PyQt5.QtCore import QVariant
from math import atan2, degrees


def calculate_pitch_heading(layer_name):
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]

    # Add new fields for pitch and heading
    layer.dataProvider().addAttributes([QgsField("pitch", QVariant.Double), QgsField("heading", QVariant.Double)])
    layer.updateFields()

    # Create a dictionary to store the pitch and heading values for each feature
    pitch_heading_dict = {}

    for feature in layer.getFeatures():
        latINTP = feature['latINTP']
        lonINTP = feature['lonINTP']
        latSVI = feature['latSVI']
        lonSVI = feature['lonSVI']
        panoId = feature['panoId']

        # Calculate the pitch and heading values
        dx = lonINTP - lonSVI
        dy = latINTP - latSVI
        heading = degrees(atan2(dx, dy))
        pitch = 0  # Assuming a flat surface, set pitch to 0

        # Store the pitch and heading values in the dictionary with panoId as the key
        pitch_heading_dict[panoId] = (pitch, heading)

    # Update the features with the calculated pitch and heading values
    layer.startEditing()
    for feature in layer.getFeatures():
        panoId = feature['panoId']
        if panoId in pitch_heading_dict:
            pitch, heading = pitch_heading_dict[panoId]
            feature.setAttribute(feature.fieldNameIndex('pitch'), pitch)
            feature.setAttribute(feature.fieldNameIndex('heading'), heading)
            layer.updateFeature(feature)
    layer.commitChanges()


def draw_lines(layer_name):
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]

    # Create a new memory layer for the lines
    line_layer = QgsVectorLayer("LineString?crs=EPSG:4326", f"{layer_name}_Arrows", "memory")

    # Add a new field for the panoId
    line_layer.dataProvider().addAttributes([QgsField("panoId", QVariant.String)])
    line_layer.updateFields()

    for feature in layer.getFeatures():
        latINTP = feature['latINTP']
        lonINTP = feature['lonINTP']
        latSVI = feature['latSVI']
        lonSVI = feature['lonSVI']
        panoId = feature['panoId']

        # Create a new feature for the line
        line_feature = QgsFeature()
        line_feature.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(lonSVI, latSVI), QgsPointXY(lonINTP, latINTP)]))
        line_feature.setAttributes([panoId])
        line_layer.dataProvider().addFeature(line_feature)

    # Create a line symbol with an arrow symbol layer
    line_symbol = QgsLineSymbol()
    arrow_symbol_layer = QgsArrowSymbolLayer()
    arrow_symbol_layer.setArrowWidth(0.5)
    arrow_symbol_layer.setArrowStartWidth(0.5)
    arrow_symbol_layer.setHeadLength(1.5)
    arrow_symbol_layer.setHeadThickness(1.5)
    line_symbol.appendSymbolLayer(arrow_symbol_layer)

    # Apply the line symbol to the line layer
    line_layer.renderer().setSymbol(line_symbol)

    QgsProject.instance().addMapLayer(line_layer)


layer_name = '40187_Intersection_SVI_2'
calculate_pitch_heading(layer_name)
draw_lines(layer_name)