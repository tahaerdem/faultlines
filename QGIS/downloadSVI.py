import os
import requests
from qgis.core import QgsProject, QgsVectorLayer, QgsField
from PyQt5.QtCore import QVariant

def download_street_view_images(layer_name, base_folder_path, api_key, start_index=0):
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    
    size = "300x800"
    fov = "120"
    
    folder_name_split = layer_name.split('_')[0]
    folder_name = f"{folder_name_split}_size{size}_fov{fov}"
    folder_path = os.path.join(base_folder_path, folder_name)
    
    layer.dataProvider().addAttributes([QgsField("filepath", QVariant.String)])
    layer.updateFields()
    
    os.makedirs(folder_path, exist_ok=True)
    
    layer.startEditing()
    
    count = 0
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
            print("Couldn't get the SVI")
        
        count += 1
    
    layer.commitChanges()

api_key = 'AIzaSyCHx5KhNPLmexJTaSP-oNyIQnF8qcGWpP4'
layer_name = '40187_Intersection_SVI_2'
base_folder_path = '/Users/taha/Library/CloudStorage/GoogleDrive-teo2109@columbia.edu/.shortcut-targets-by-id/1t6cmqB2ioLvG70pqgEvlSBeBfE-WVYI_/2303_istanbul_earthquake/02_Datasets/01_GIS/04_PYTHON SCRIPTS/02_SVI Images/'
start_index = 200

download_street_view_images(layer_name, base_folder_path, api_key, start_index)