import subprocess
import time
import threading
import json
import os
import signal
import psutil
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request

app = Flask(__name__)

path1 = '/root/flask_app/'
path= ''
def find_ffmpeg_pid(stream_key):
    try:
        # Utiliser la commande ps pour obtenir la liste des processus
        output = subprocess.check_output(['ps', 'aux'])

        # Convertir la sortie en chaîne et la diviser en lignes
        output_lines = output.decode().split('\n')

        # Parcourir les lignes pour trouver le PID de ffmpeg correspondant au stream_key
        for line in output_lines:
            if 'ffmpeg' in line and stream_key in line:
                # Extraire le PID du processus ffmpeg
                pid = int(line.split()[1])
                return pid
    except Exception as e:
        print(f"Erreur lors de la recherche du PID de ffmpeg : {e}")
        return None

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

def stop_stream(stream_id, duration):
    time.sleep(duration)  # Attendre la durée spécifiée
    if stream_id in streams:
        stream_process = streams[stream_id]['process']
        if stream_process.poll() is None:  # Si le processus est encore actif
            stream_process.terminate()  # Arrêter le processus
        del streams[stream_id]  # Supprimer le stream de la liste
        print(f"Stream {stream_id} stopped after {duration} seconds.")


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
        print(f"Date et heure actuelles : {current_time}")
        for stream_id, info in list(streams.items()):
            end_time = datetime.strptime(info['end_time'], '%Y-%m-%d %H:%M:%S')
            time_left = end_time - current_time
            print(f"Vérification du flux {stream_id}")
            print(f"Date et heure de fin du flux : {end_time}")
            print(f"Temps restant pour le flux : {time_left}")
            if current_time >= end_time:
                try:
                    os.kill(info["process_id"], signal.SIGKILL)
                    print(f"Le flux {stream_id} a été arrêté car il a dépassé l'heure de fin")
                except Exception as e:
                    print(f"Erreur lors de l'arrêt du flux {stream_id}: {e}")
                del streams[stream_id]
        
        file.seek(0)
        file.truncate()
        json.dump(streams, file)
        print('Checked streams')
        # Réinitialiser le timer pour exécuter à nouveau cette fonction après 30 secondes
        threading.Timer(30, check_streams).start()

streams = {}

@app.route('/startstream', methods=['POST'])
def start_stream():

    # Chemin du dossier contenant les vidéos
    video_folder = path + 'movie'

    # Lister tous les fichiers dans le dossier
    video_files = os.listdir(video_folder)

    # Filtrer la liste pour ne garder que les fichiers vidéo 
    video_files = [file for file in video_files if file.endswith('.mp4')]

    # Sélectionner aléatoirement un fichier vidéo
    selected_video = random.choice(video_files)

    # Chemin complet de la vidéo sélectionnée
    video_path = os.path.join(video_folder, selected_video)

    data = request.json
    stream_id = data.get('stream_id')
    stream_duration = data.get('stream_duration')
    
    if stream_id and stream_duration:
        # Vérifier si le stream est déjà en cours
        for process in psutil.process_iter():
            try:
                # Récupérer les arguments de la commande du processus
                process_cmd = process.cmdline()
                if 'ffmpeg' in process_cmd and f'rtmp://live.twitch.tv/app/{stream_id}' in process_cmd:
                    return jsonify({'message': 'Stream already active', 'status': 'active'})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Modifier la commande ffmpeg pour utiliser la vidéo sélectionnée
        subprocess.Popen(f'ffmpeg -t {stream_duration} -stream_loop -1 -re -i {video_path} -c:v libx264 -preset veryfast -b:v 3000k -maxrate 3000k -bufsize 6000k -pix_fmt yuv420p -g 50 -c:a aac -b:a 160k -ac 2 -ar 44100 -f flv "rtmp://live.twitch.tv/app/{stream_id}"', shell=True)

        
        return jsonify({'message': 'Stream started', 'status': 'active'}), 200
    else:
        return jsonify({'error': 'Stream ID or duration not provided'}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
