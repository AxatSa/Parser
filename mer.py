from flask import Flask, request
import requests
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

def get_tiktok_stats(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
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

def save_to_google_sheets(url, views, likes, shares):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1rfNZda21tgNIrwTrD7S2g4MZxABV8nX9xRkHTMOfcpc/edit?usp=sharing").sheet1
    sheet.append_row([url, views, likes, shares])

@app.route('/')
def home():
    return '''
        <form action="/stats" method="post">
            TikTok Video URL: <input type="text" name="url">
            <input type="submit" value="Get Stats">
        </form>
    '''

@app.route('/stats', methods=['POST'])
def stats():
    url = request.form['url']
    views, likes, shares = get_tiktok_stats(url)
    if views is not None and likes is not None and shares is not None:
        save_to_google_sheets(url, views, likes, shares)
        return f'''
            Количество просмотров: {views}<br>
            Количество лайков: {likes}<br>
            Количество репостов: {shares}<br>
            Данные сохранены в Google Таблицу.
        '''
    else:
        return "Не удалось получить данные о просмотрах, лайках и/или репостах."

if __name__ == '__main__':
    app.run(debug=True)
