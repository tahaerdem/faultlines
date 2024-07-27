from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY
from qgis.utils import iface
from PyQt5.QtCore import QVariant
import requests

class StreetViewPanoramaLocator(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('FaultLines - Panorama Locator')
        layout = QtWidgets.QVBoxLayout()

        # Layer selection
        self.layer_combo = QtWidgets.QComboBox()
        self.populateLayerCombo()
        layout.addWidget(QtWidgets.QLabel('Select Layer:'))
        layout.addWidget(self.layer_combo)

        # API Key input
        self.api_key_input = QtWidgets.QLineEdit()
        layout.addWidget(QtWidgets.QLabel('Enter Google API Key:'))
        layout.addWidget(self.api_key_input)

        # Process button
        self.process_button = QtWidgets.QPushButton('Locate Panoramas')
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
        api_key = self.api_key_input.text()

        if not layer:
            iface.messageBar().pushWarning("Error", "No layer selected")
            return
        if not api_key:
            iface.messageBar().pushWarning("Error", "API key is required")
            return

        self.main(api_key, layer)

    def get_session_token(self, api_key):
        url = "https://tile.googleapis.com/v1/createSession?key=" + api_key
        headers = {'Content-Type': 'application/json'}
        payload = {
            "mapType": "streetview",
            "language": "en-US",
            "region": "US"
        }
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            iface.messageBar().pushInfo("Success", "Session token obtained")
            return response.json().get('session')
        else:
            iface.messageBar().pushCritical("Error", f"Error getting session token: {response.status_code} {response.text}")
            return None

    def get_pano_location(self, api_key, pano_id):
        url = f"https://maps.googleapis.com/maps/api/streetview/metadata?pano={pano_id}&key={api_key}"
        headers = {'Content-Type': 'application/json'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            lat = data.get('location', {}).get('lat')
            lng = data.get('location', {}).get('lng')
            return lat, lng
        else:
            iface.messageBar().pushWarning("API Error", f"Error retrieving pano location for panoID: {pano_id}")
            return None, None

    def get_panorama_ids(self, session_token, api_key, lat, lng, new_layer, indexL, indexR):
        url = f"https://tile.googleapis.com/v1/streetview/panoIds?session={session_token}&key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {"locations": [{"lat": lat, "lng": lng}], "radius": 50}
        response = requests.post(url, json=payload, headers=headers)
        pano_ids = response.json().get('panoIds', [])
        if response.status_code == 200:
            for pano_id in pano_ids:
                latSVI, lonSVI = self.get_pano_location(api_key, pano_id)
                if latSVI is not None and lonSVI is not None:
                    feat = QgsFeature()
                    feat.setAttributes([pano_id, lat, lng, latSVI, lonSVI, indexL, indexR])
                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(lonSVI), float(latSVI))))
                    new_layer.dataProvider().addFeature(feat)
            new_layer.updateExtents()
        else:
            iface.messageBar().pushWarning("API Error", f"Error getting panorama IDs: {response.status_code} {response.text}")

    def main(self, api_key, layer):
        new_layer = QgsVectorLayer("Point?crs=EPSG:4326&field=panoId:string&field=latINTP:double(20,14)&field=lonINTP:double(20,14)&field=latSVI:double(20,14)&field=lonSVI:double(20,14)&field=indexL:string&field=indexR:string", f"{layer.name()}_SVI", "memory")
        session_token = self.get_session_token(api_key)
        if not session_token:
            iface.messageBar().pushCritical("Error", "Session token not available, aborting.")
            return

        total_features = layer.featureCount()
        for count, feature in enumerate(layer.getFeatures()):
            indexL = feature['indexL']
            indexR = feature['indexR']
            latINTP = feature['latINTP']
            lonINTP = feature['lonINTP']
            self.get_panorama_ids(session_token, api_key, latINTP, lonINTP, new_layer, indexL, indexR)
            
            # Update progress
            progress = int((count + 1) / total_features * 100)
            iface.messageBar().pushInfo("Progress", f"Processed {count + 1} of {total_features} points ({progress}%)")

        if new_layer.featureCount() > 0:
            QgsProject.instance().addMapLayer(new_layer)
            iface.messageBar().pushSuccess("Success", "New layer with panorama locations added to the map")
        else:
            iface.messageBar().pushWarning("Warning", "No features were added to the new layer.")

        self.close()

def run_streetview_panorama_locator():
    dialog = StreetViewPanoramaLocator()
    dialog.show()
    return dialog

# Run the tool
panorama_locator_dialog = run_streetview_panorama_locator()