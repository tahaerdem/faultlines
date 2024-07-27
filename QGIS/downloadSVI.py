import os
import requests
from qgis.PyQt import QtWidgets, QtCore
from qgis.core import QgsProject, QgsVectorLayer, QgsField
from qgis.utils import iface
from PyQt5.QtCore import QVariant

class StreetViewDownloader(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('FaultLines - SVI Downloader')
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

        # Base folder path input
        self.base_folder_input = QtWidgets.QLineEdit()
        self.folder_button = QtWidgets.QPushButton('Browse')
        self.folder_button.clicked.connect(self.selectFolder)
        folder_layout = QtWidgets.QHBoxLayout()
        folder_layout.addWidget(self.base_folder_input)
        folder_layout.addWidget(self.folder_button)
        layout.addWidget(QtWidgets.QLabel('Base Folder Path:'))
        layout.addLayout(folder_layout)

        # Image size inputs
        size_layout = QtWidgets.QHBoxLayout()
        self.width_input = QtWidgets.QSpinBox()
        self.width_input.setRange(1, 1000)
        self.width_input.setValue(300)
        self.height_input = QtWidgets.QSpinBox()
        self.height_input.setRange(1, 1000)
        self.height_input.setValue(800)
        size_layout.addWidget(QtWidgets.QLabel('Image Size:'))
        size_layout.addWidget(self.width_input)
        size_layout.addWidget(QtWidgets.QLabel('x'))
        size_layout.addWidget(self.height_input)
        layout.addLayout(size_layout)

        # FOV input
        self.fov_input = QtWidgets.QSpinBox()
        self.fov_input.setRange(1, 360)
        self.fov_input.setValue(120)
        layout.addWidget(QtWidgets.QLabel('Field of View (FOV):'))
        layout.addWidget(self.fov_input)

        # Start index input
        self.start_index_input = QtWidgets.QSpinBox()
        self.start_index_input.setRange(0, 1000000)
        self.start_index_input.setValue(200)
        layout.addWidget(QtWidgets.QLabel('Start Index:'))
        layout.addWidget(self.start_index_input)

        # Process button
        self.process_button = QtWidgets.QPushButton('Download Images')
        self.process_button.clicked.connect(self.process)
        layout.addWidget(self.process_button)

        self.setLayout(layout)

    def populateLayerCombo(self):
        self.layer_combo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsVectorLayer.VectorLayer:
                self.layer_combo.addItem(layer.name(), layer)

    def selectFolder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Base Folder")
        if folder:
            self.base_folder_input.setText(folder)

    def process(self):
        layer = self.layer_combo.currentData()
        api_key = self.api_key_input.text()
        base_folder_path = self.base_folder_input.text()
        size = f"{self.width_input.value()}x{self.height_input.value()}"
        fov = str(self.fov_input.value())
        start_index = self.start_index_input.value()

        if not layer:
            iface.messageBar().pushWarning("Error", "No layer selected")
            return
        if not api_key:
            iface.messageBar().pushWarning("Error", "API key is required")
            return
        if not base_folder_path:
            iface.messageBar().pushWarning("Error", "Base folder path is required")
            return

        self.download_street_view_images(layer, base_folder_path, api_key, size, fov, start_index)

    def download_street_view_images(self, layer, base_folder_path, api_key, size, fov, start_index=0):
        folder_name_split = layer.name().split('_')[0]
        folder_name = f"{folder_name_split}_size{size}_fov{fov}"
        folder_path = os.path.join(base_folder_path, folder_name)
        
        if 'filepath' not in layer.fields().names():
            layer.dataProvider().addAttributes([QgsField("filepath", QVariant.String)])
            layer.updateFields()
        
        os.makedirs(folder_path, exist_ok=True)
        
        layer.startEditing()
        
        count = 0
        total_features = layer.featureCount()
        for feature in layer.getFeatures():
            if count < start_index:
                count += 1
                continue
            
            rowId = feature['rowId']
            panoId = feature['panoId']
            latINTP = feature['latINTP']
            lonINTP = feature['lonINTP']
            indexL = feature['indexL']
            indexR = feature['indexR']
            heading = feature['heading']
            pitch = feature['pitch']
            
            file_name = f"SVI-{rowId}-{panoId}-{latINTP}-{lonINTP}-{indexL}-{indexR}.jpg"
            file_path = os.path.join(folder_path, file_name)
            
            url = f"https://maps.googleapis.com/maps/api/streetview?&pano={panoId}&size={size}&fov={fov}&heading={heading}&pitch={pitch}&key={api_key}"
            response = requests.get(url)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                
                feature.setAttribute(feature.fieldNameIndex('filepath'), file_path)
                layer.updateFeature(feature)
            else:
                iface.messageBar().pushWarning("API Error", f"Couldn't get the SVI for feature {rowId}")
            
            count += 1
            # Update progress
            progress = int((count / total_features) * 100)
            iface.messageBar().pushInfo("Progress", f"Downloaded {count} of {total_features} images ({progress}%)")
        
        layer.commitChanges()
        iface.messageBar().pushSuccess("Success", "Street View images downloaded successfully")
        self.close()

def run_street_view_downloader():
    dialog = StreetViewDownloader()
    dialog.show()
    return dialog

# Run the tool
street_view_dialog = run_street_view_downloader()