import requests
import json
import os

def download_and_extract_districts():
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    print(f"Downloading from {url}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print("Download complete. Analyzing data...")
        
        if 'features' not in data:
            print("Error: No 'features' key in GeoJSON")
            return

        if len(data['features']) > 0:
            print("First feature properties:", data['features'][0]['properties'])
        
        maharashtra_features = []

        for feature in data['features']:
            props = feature['properties']
            
            is_maharashtra = False
            for key, value in props.items():
                if isinstance(value, str) and 'Maharashtra' in value:
                    is_maharashtra = True
                    break
            
            if is_maharashtra:
                maharashtra_features.append(feature)
        
        print(f"Found {len(maharashtra_features)} district features for Maharashtra.")
        
        if len(maharashtra_features) == 0:
            print("Error: No Maharashtra features found.")
            return

        output_geojson = {
            "type": "FeatureCollection",
            "features": maharashtra_features
        }
        
        output_path = "static/geojson/maharashtra_districts.geojson"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_geojson, f)
            
        print(f"Saved extracted Maharashtra districts to {output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    download_and_extract_districts()
