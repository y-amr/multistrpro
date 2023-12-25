import subprocess
from flask import Flask, jsonify, request

app = Flask(__name__)

streams = {}  # Dictionnaire pour stocker les streams actifs (stream_id -> process)

@app.route('/startstream', methods=['POST'])
def start_stream():
    data = request.json
    stream_id = data.get('stream_id')

    if stream_id:
        # Vérifier si le stream est déjà en cours
        if stream_id in streams and not streams[stream_id].poll():
            return jsonify({'message': 'Stream already active', 'status': 'active'})

        # Démarrer le stream avec ffmpeg
        process = subprocess.Popen(f'ffmpeg -stream_loop -1 -re -i movie.mp4 -stream_loop -1 -i music.mp3 -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 160k -ac 2 -ar 44100 -f flv "rtmp://live.twitch.tv/app/{stream_id}"', shell=True)
        streams[stream_id] = process  # Stocker le processus associé au stream_id
        return jsonify({'message': 'Stream started', 'status': 'active'})
    else:
        return jsonify({'error': 'Stream ID or filename not provided'}), 400

@app.route('/stopstream', methods=['POST'])
def stop_stream():
    data = request.json
    stream_id = data.get('stream_id')

    if stream_id:
        # Vérifier si le stream est en cours
        if stream_id in streams and not streams[stream_id].poll():
            # Arrêter le processus ffmpeg associé au stream_id
            streams[stream_id].terminate()
            del streams[stream_id]  # Supprimer le stream de la liste des streams actifs
            return jsonify({'message': 'Stream stopped', 'status': 'inactive'})
        else:
            return jsonify({'message': 'Stream not active', 'status': 'inactive'})
    else:
        return jsonify({'error': 'Stream ID not provided'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
