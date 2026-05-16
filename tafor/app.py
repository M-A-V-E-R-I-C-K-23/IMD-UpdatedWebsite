from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from scraper import IMDScraper, OgimetScraper
from taf_generator import TafGenerator
from metar_parser import decode_metar
from cleanup import run_automated_cleanup
import threading

app = Flask(__name__)
app.secret_key = 'super_secret_taf_key'  

@app.route('/api/taf/<station>', methods=['GET'])
def get_taf(station):
    station = station.upper()
    imd_scraper = IMDScraper()
    ogimet_scraper = OgimetScraper()
    generator = TafGenerator()

    imd_data = imd_scraper.fetch_data(station)
    ogimet_data = ogimet_scraper.fetch_data(station)

    if "error" in imd_data:
        return jsonify({"error": f"IMD Error: {imd_data['error']}"}), 500
    if "error" in ogimet_data:
        return jsonify({"error": f"Ogimet Error: {ogimet_data['error']}"}), 500

    try:
        short_taf = generator.generate_short_taf(imd_data, ogimet_data)
        
        parsed_metar = None
        if "raw_metar" in ogimet_data and "dt" in ogimet_data:
            parsed_metar = decode_metar(ogimet_data["raw_metar"], station, ogimet_data["dt"])
            if parsed_metar and "timestamp_utc" in parsed_metar:
                parsed_metar["timestamp_utc"] = parsed_metar["timestamp_utc"].isoformat() + "Z"

        return jsonify({
            "short_taf": short_taf, 
            "station": station,
            "ogimet_metar": parsed_metar
        })
    except Exception as e:
        return jsonify({"error": f"Generation Error: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
                                                            
    threading.Thread(target=run_automated_cleanup, daemon=True).start()

    station = request.form.get('station', 'VABB').upper()
    
    imd_scraper = IMDScraper()
    ogimet_scraper = OgimetScraper()
    generator = TafGenerator()

    imd_data = imd_scraper.fetch_data(station)
    
    ogimet_data = ogimet_scraper.fetch_data(station)

    error_msg = None
    debug_forms = None
    
    if "error" in imd_data:
        error_msg = f"IMD Error: {imd_data['error']}"
        debug_forms = imd_data.get('debug_forms', None)                                  
        if debug_forms:
            print("\n[DEBUG info for Developer]")
            print(str(debug_forms))
            print("[End Debug info]\n")
    elif "error" in ogimet_data:
        error_msg = f"Ogimet Error: {ogimet_data['error']}"
    
    long_taf = ""
    short_taf = ""
    
    if not error_msg:
        try:
            long_taf = generator.generate_long_taf(imd_data, ogimet_data) 
            short_taf = generator.generate_short_taf(imd_data, ogimet_data)
        except Exception as e:
            error_msg = f"Generation Error: {str(e)}"

    return render_template('index.html', 
                         long_taf=long_taf, 
                         short_taf=short_taf, 
                         error=error_msg, 
                         debug_forms=debug_forms,
                         last_station=station)

if __name__ == '__main__':
                                                                 
    app.run(debug=True, port=5000)
