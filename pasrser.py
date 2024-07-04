from flask import Flask, request
import requests
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build

app = Flask(__name__)

YOUTUBE_API_KEY = 'AIzaSyDjIUxA08jGo8VOOQ-ivBuQwoRRzoWHuZw'

def get_tiktok_stats(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None, None, None

    views_match = re.search(r'"playCount":(\d+)', response.text)
    likes_match = re.search(r'"diggCount":(\d+)', response.text)
    shares_match = re.search(r'"shareCount":(\d+)', response.text)
    
    if views_match and likes_match and shares_match:
        views = int(views_match.group(1))
        likes = int(likes_match.group(1))
        shares = int(shares_match.group(1))
        return views, likes, shares
    else:
        return None, None, None

def get_youtube_shorts_stats(url):
    video_id = None

    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        video_id = parsed_url.path[1:]
    elif parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        if parsed_url.path == '/watch':
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path[:7] == '/shorts':
            video_id = parsed_url.path.split('/')[2]

    if not video_id:
        return None, None, None

    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    response = youtube.videos().list(part='statistics', id=video_id).execute()

    if not response['items']:
        return None, None, None

    stats = response['items'][0]['statistics']
    views = int(stats['viewCount'])
    likes = int(stats['likeCount'])
    shares = None

    return views, likes, shares

def save_to_google_sheets(url, views, likes, shares):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1rfNZda21tgNIrwTrD7S2g4MZxABV8nX9xRkHTMOfcpc/edit?usp=sharing").sheet1

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_row([url, views, likes, shares, current_time])

@app.route('/')
def home():
    return '''
        <form action="/stats" method="post">
            Ссылка на видос(TikTok or YouTube Shorts): <input type="text" name="url">
            <input type="submit" value="Get Stats">
        </form>
    '''

@app.route('/stats', methods=['POST'])
def stats():
    url = request.form['url']
    parsed_url = urlparse(url)
    if 'tiktok.com' in parsed_url.netloc:
        views, likes, shares = get_tiktok_stats(url)
    elif 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
        views, likes, shares = get_youtube_shorts_stats(url)
    else:
        return "Не поддерживаемая ссылка. Втавьляй только ссылки от тиктока и ютб шортс."

    if views is not None and likes is not None:
        save_to_google_sheets(url, views, likes, shares)
        return f'''
            Количество просмотров: {views}<br>
            Количество лайков: {likes}<br>
            Количество репостов: {shares if shares is not None else 'N/A'}<br>
            Данные сохранены в Google Таблицу.
        '''
    else:
        return "Не удалось получить данные о просмотрах, лайках и/или репостах."

if __name__ == '__main__':
    app.run(debug=True)
