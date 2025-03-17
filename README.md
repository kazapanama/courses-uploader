# courses-uploader

## Опис
courses-uploader дозволяє автоматично завантажувати відеофайли з локальної папки на Telegram канал. Програма проходить через вказану директорію, знаходить усі відеофайли та завантажує їх у вказаний Telegram канал, зберігаючи структуру папок.

## Встановлення
1. Клонуйте репозиторій:
```
git clone https://github.com/kazapanama/courses-uploader
cd courses-uploader
```

2. Створіть віртуальне середовище та активуйте його:
```
python -m venv myenv
myenv\Scripts\activate  # для Windows
source myenv/bin/activate  # для Linux/Mac
```

3. Встановіть залежності з файлу requirements.txt:
```
pip install -r requirements.txt
```

Створіть файл .env на основі наданого шаблону .env.example:
```
cp .env.example .env
```

Відредагуйте файл .env, щоб додати свої параметри:

CopyTELEGRAM_BOT_TOKEN=ваш_токен_бота
TELEGRAM_CHANNEL_USERNAME=назва_каналу_або_id
VIDEO_ROOT_FOLDER=шлях_до_папки_з_відео

## Використання
Запустіть скрипт командою:
```
python main.py
```

## Особливості
- Автоматичне завантаження відео з підтримкою потокового перегляду
- Перевірка на дублікати перед завантаженням
- Організація відео за структурою папок
- Повторні спроби для невдалих завантажень
- Обробка помилок