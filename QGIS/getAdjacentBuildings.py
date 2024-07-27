from qgis.core import QgsSpatialIndex, QgsProject, QgsGeometry
from qgis.utils import iface

# Get the currently selected layer
layer = iface.activeLayer()

# Check if a layer is selected
if layer is None:
    print("No layer selected.")
else:
    # Define the tolerance (buffer distance)
    tolerance = 1.0  # Adjust this value as needed (units are in layer's CRS units)

    # Create a spatial index
    index = QgsSpatialIndex()
    for feature in layer.getFeatures():
        index.insertFeature(feature)

    # List to hold IDs of adjacent buildings
    adjacent_building_ids = set()

    # Iterate over each feature in the layer
    for feature in layer.getFeatures():
        geom = feature.geometry()
        buffer_geom = geom.buffer(tolerance, 5)  # Create a buffer around the geometry
        bbox = buffer_geom.boundingBox()
        
        # Find features within the bounding box of the buffer
        intersecting_ids = index.intersects(bbox)
        
        for intersecting_id in intersecting_ids:
            if intersecting_id == feature.id():
                continue
            
            intersecting_feature = layer.getFeature(intersecting_id)
            intersecting_geom = intersecting_feature.geometry()
            
            if buffer_geom.intersects(intersecting_geom):
                adjacent_building_ids.add(feature.id())
                adjacent_building_ids.add(intersecting_id)

    # Select the adjacent buildings
    layer.selectByIds(list(adjacent_building_ids))

    print(f"Selected {len(adjacent_building_ids)} adjacent buildings")