from flask import Flask, request, render_template, redirect, url_for
import os
import json
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt

# Use the Agg backend for Matplotlib
plt.switch_backend('Agg')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    files = request.files.getlist('files')
    all_data = []
    
    for file in files:
        if file.filename.endswith('.json'):
            try:
                data = json.load(file)
                all_data.extend(data)
            except json.JSONDecodeError:
                return render_template('index.html', error="Invalid JSON file.")
    
    if not all_data:
        return render_template('index.html', error="No valid JSON data found in uploaded files.")
    
    insights = analyze_data(all_data)
    return render_template('insights.html', insights=insights)

@app.route('/customize', methods=['POST'])
def customize():
    insights = request.form['insights']
    return render_template('customize.html', insights=insights)

@app.route('/generate_post', methods=['POST'])
def generate_post():
    selected_data = request.form.getlist('data')
    include_pie_chart = 'include_pie_chart' in request.form
    text_color = request.form['text_color']
    background_file = request.files.get('background_file')

    if background_file and background_file.filename != '':
        background_path = os.path.join(app.config['UPLOAD_FOLDER'], background_file.filename)
        background_file.save(background_path)
        background = '/' + background_path
    else:
        background = '/static/default_background.jpg'  # Default background if none provided

    insights = json.loads(request.form['insights'])
    last_streamed_date = insights['last_streamed_date']
    
    # Generate pie chart for top artists
    pie_chart_url = ''
    if include_pie_chart and 'top_artists' in selected_data:
        artist_names = [artist['name'] for artist in insights['top_artists']]
        artist_counts = [artist['count'] for artist in insights['top_artists']]
        plt.figure(figsize=(6, 6))
        plt.pie(artist_counts, labels=artist_names, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.gca().set_facecolor('none')
        pie_chart_path = os.path.join(app.config['UPLOAD_FOLDER'], 'pie_chart.png')
        plt.savefig(pie_chart_path, transparent=True)
        pie_chart_url = '/' + pie_chart_path

    return render_template('post.html', selected_data=selected_data, background=background, text_color=text_color, insights=insights, last_streamed_date=last_streamed_date, pie_chart_url=pie_chart_url)

def analyze_data(data):
    if not data:
        return {
            "top_artists": [],
            "top_songs": [],
            "total_listening_time": 0,
            "average_listening_time_per_day": 0,
            "most_listened_day": {"date": "N/A", "ms_played": 0},
            "last_streamed_date": "N/A"
        }

    artist_counts = {}
    song_counts = {}
    daily_listening = defaultdict(int)
    total_listening_time = 0
    last_streamed_date = None

    for item in data:
        artist = item['artistName']
        song = item['trackName']
        ms_played = item['msPlayed']
        end_time = datetime.strptime(item['endTime'], '%Y-%m-%d %H:%M')
        
        if last_streamed_date is None or end_time > last_streamed_date:
            last_streamed_date = end_time

        if artist in artist_counts:
            artist_counts[artist] += 1
        else:
            artist_counts[artist] = 1
        
        if song in song_counts:
            song_counts[song] += 1
        else:
            song_counts[song] = 1
        
        date_str = end_time.strftime('%Y-%m-%d')
        daily_listening[date_str] += ms_played
        total_listening_time += ms_played

    top_artists = sorted(artist_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_songs = sorted(song_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    most_listened_day = max(daily_listening.items(), key=lambda x: x[1]) if daily_listening else ("N/A", 0)
    
    insights = {
        "top_artists": [{"name": artist, "count": count} for artist, count in top_artists],
        "top_songs": [{"name": song, "count": count} for song, count in top_songs],
        "total_listening_time": total_listening_time,
        "average_listening_time_per_day": total_listening_time / len(daily_listening) if daily_listening else 0,
        "most_listened_day": {"date": most_listened_day[0], "ms_played": most_listened_day[1]},
        "last_streamed_date": last_streamed_date.strftime('%B %d, %Y') if last_streamed_date else "N/A"
    }
    return insights

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
