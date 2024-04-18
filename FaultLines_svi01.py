# FaultLines SVI01 - QGIS Plug-in by FaultLines
# This library lets user fetch the nearest SVI point. 

from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY
from PyQt5.QtCore import QVariant
import requests

def get_session_token(api_key):
    url = "https://tile.googleapis.com/v1/createSession?key=" + api_key
    headers = {'Content-Type': 'application/json'}
    payload = {
        "mapType": "streetview",
        "language": "en-US",
        "region": "US"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("You got the session token!")
        return response.json().get('session')
    else:
        print("Error getting session token:", response.status_code, response.text)
        return None
def get_pano_location(session_token, api_key, pano_id):
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?pano={pano_id}&key={api_key}"
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.text}")

    if response.status_code == 200:
        data = response.json()
        lat = data.get('location', {}).get('lat')
        lng = data.get('location', {}).get('lng')
        return lat, lng
    else:
        print(f"Error retrieving pano location for panoID: {pano_id}")
        return None, None

def get_panorama_ids(session_token, api_key, lat, lng, new_layer, indexL, indexR):
    url = f"https://tile.googleapis.com/v1/streetview/panoIds?session={session_token}&key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {"locations": [{"lat": lat, "lng": lng}], "radius": 50}
    response = requests.post(url, json=payload, headers=headers)
    pano_ids = response.json().get('panoIds', [])
    result = []

    if response.status_code == 200:
        for pano_id in pano_ids:
            latSVI, lonSVI = get_pano_location(session_token, api_key, pano_id)
            feat = QgsFeature()
            feat.setAttributes([pano_id, lat, lng, latSVI, lonSVI, indexL, indexR])
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(lonSVI), float(latSVI))))
            new_layer.dataProvider().addFeature(feat)
        new_layer.updateExtents()
        QgsProject.instance().addMapLayer(new_layer)
        return result
    else:
        print("Error getting panorama IDs:", response.status_code, response.text)

def main(api_key, layer_name):
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    new_layer = QgsVectorLayer("Point?crs=EPSG:4326&field=panoId:string&field=latINTP:double(20,14)&field=lonINTP:double(20,14)&field=latSVI:double(20,14)&field=lonSVI:double(20,14)&field=indexL:string&field=indexR:string", f"{layer_name}_SVI", "memory")
    session_token = get_session_token(api_key)

    for feature in layer.getFeatures():
        indexL = feature['indexL']
        indexR = feature['indexR']
        latINTP = feature['latINTP']
        lonINTP = feature['lonINTP']
        get_panorama_ids(session_token, api_key, latINTP, lonINTP, new_layer, indexL, indexR)

    if new_layer.featureCount() > 0:
        QgsProject.instance().addMapLayer(new_layer)
    else:
        print("No features were added to the new layer.")

api_key = 'AIzaSyCHx5KhNPLmexJTaSP-oNyIQnF8qcGWpP4'
layer_name = '40187_Intersection'
main(api_key, layer_name)
