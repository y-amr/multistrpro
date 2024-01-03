import subprocess
import time
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

streams = {}  # Dictionnaire pour stocker les streams actifs (stream_id -> process)
@app.route('/startstream', methods=['POST'])
def start_stream():
    data = request.json
    stream_id = data.get('stream_id')
    stream_duration = data.get('stream_duration')  # Nouveau paramètre

    if stream_id and stream_duration:
        # Vérifier si le stream est déjà en cours
        if stream_id in streams and not streams[stream_id].poll():
            return jsonify({'message': 'Stream already active', 'status': 'active'})

        # Démarrer le stream avec ffmpeg
        process = subprocess.Popen(f'ffmpeg -stream_loop -1 -re -i /root/flask_app/movie.mp4 -stream_loop -1 -i music.mp3 -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 160k -ac 2 -ar 44100 -f flv "rtmp://live.twitch.tv/app/{stream_id}"', shell=True)
        streams[stream_id] = process  # Stocker le processus associé au stream_id

        # Lancer un thread pour arrêter le stream après la durée spécifiée
        threading.Thread(target=stop_after_duration, args=(stream_id, stream_duration)).start()

        return jsonify({'message': 'Stream started', 'status': 'active'})
    else:
        return jsonify({'error': 'Stream ID or duration not provided'}), 400

# Fonction pour arrêter le stream après une durée spécifiée
def stop_after_duration(stream_id, duration):
    time.sleep(duration * 60)  # Convertir la durée en minutes en secondes
    if stream_id in streams and not streams[stream_id].poll():
        streams[stream_id].terminate()
        del streams[stream_id]

@app.route('/stopallstream', methods=['GET'])
def stop_all_streams():
    for stream_id in streams:
        if not streams[stream_id].poll():
            streams[stream_id].terminate()
    streams.clear()  # Effacer tous les streams de la liste
    return jsonify({'message': 'All streams stopped'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
