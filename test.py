import subprocess
import time
import threading
import json
import os
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

streams = {}  # Dictionnaire pour stocker les streams actifs (stream_id -> process)
@app.route('/startstream', methods=['POST'])
def start_stream():

    # Chemin du dossier contenant les vidéos
    video_folder = '/root/flask_app/movie'

    # Lister tous les fichiers dans le dossier
    video_files = os.listdir(video_folder)

    # Filtrer la liste pour ne garder que les fichiers vidéo (optionnel, selon vos besoins)
    # Par exemple, pour ne garder que les fichiers .mp4 :
    video_files = [file for file in video_files if file.endswith('.mp4')]

    # Sélectionner aléatoirement un fichier vidéo
    selected_video = random.choice(video_files)

    # Chemin complet de la vidéo sélectionnée
    video_path = os.path.join(video_folder, selected_video)

    data = request.json
    stream_id = data.get('stream_id')
    stream_duration = data.get('stream_duration')  # Nouveau paramètre

    if stream_id and stream_duration:
        # Vérifier si le stream est déjà en cours
        if stream_id in streams and not streams[stream_id].poll():
            return jsonify({'message': 'Stream already active', 'status': 'active'})
        print(video_path)
        # Modifier la commande ffmpeg pour utiliser la vidéo sélectionnée
        process = subprocess.Popen(f'ffmpeg -stream_loop -1 -re -i {video_path} -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 160k -ac 2 -ar 44100 -f flv "rtmp://live.twitch.tv/app/{stream_id}"', shell=True)
        streams[stream_id] = process  # Stocker le processus associé au stream_id

        # Lancer un thread pour arrêter le stream après la durée spécifiée
        threading.Thread(target=stop_after_duration, args=(stream_id, stream_duration)).start()

        save_stream_info(stream_id, process.pid, stream_duration)

        return jsonify({'message': 'Stream started', 'process_id' : process.pid ,'status': 'active'})
    else:
        return jsonify({'error': 'Stream ID or duration not provided'}), 400

def save_stream_info(stream_id, process_id, duration):
    end_time = datetime.now() + timedelta(minutes=duration)
    stream_info = {
        'process_id': process_id,
        'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S')
    }
    with open('/root/flask_app/streams.json', 'r+') as file:
        streams = json.load(file)
        streams[stream_id] = stream_info
        file.seek(0)
        json.dump(streams, file)

def stop_after_duration(stream_id, duration):
    time.sleep(duration * 60)
    with open('/root/flask_app/streams.json', 'r+') as file:
        streams = json.load(file)
        if stream_id in streams:
            process_id = streams[stream_id]['process_id']
            subprocess.Popen(f'kill {process_id}', shell=True)
            del streams[stream_id]
            file.seek(0)
            file.truncate()
            json.dump(streams, file)

@app.route('/stopallstream', methods=['POST'])
def stop_all_streams():
    try:
        # Trouver et tuer tous les processus ffmpeg
        subprocess.run(['pkill', '-f', 'ffmpeg'], check=True)

        # Vider le fichier streams.json
        with open('/root/flask_app/streams.json', 'w') as file:
            json.dump({}, file)

        return jsonify({'message': 'All ffmpeg streams stopped'}), 200

    except subprocess.CalledProcessError as e:
        # Logger l'erreur ou retourner un message d'erreur si pkill échoue
        app.logger.error(f'Error stopping ffmpeg streams: {e}')
        return jsonify({'error': 'Failed to stop ffmpeg streams'}), 500

def check_streams():
    with open('/root/flask_app/streams.json', 'r+') as file:
        streams = json.load(file)
        current_time = datetime.now()
        for stream_id, info in list(streams.items()):
            end_time = datetime.strptime(info['end_time'], '%Y-%m-%d %H:%M:%S')
            if current_time >= end_time:
                subprocess.Popen(f'kill {info["process_id"]}', shell=True)
                del streams[stream_id]

        file.seek(0)
        file.truncate()
        json.dump(streams, file)
        print('Checked streams')
        # Réinitialiser le timer pour exécuter à nouveau cette fonction après 30 secondes
        threading.Timer(30, check_streams).start()


if __name__ == '__main__':
    # Démarrer la vérification périodique des streams
    check_streams()

    app.run(host='0.0.0.0', port=6000)
