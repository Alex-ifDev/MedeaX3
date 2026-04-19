# Використовуємо легку версію Python
FROM python:3.10-slim

# Встановлюємо системні залежності для Pillow та шрифти
RUN apt-get update && apt-get install -y \
    fonts-liberation \
    fontconfig \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Створюємо робочу директорію
WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо бібліотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код бота та шрифти в контейнер
COPY . .

# Hugging Face Spaces очікує, що додаток слухатиме порт 7860.
# Навіть якщо бот не використовує веб-інтерфейс, це допомагає уникнути помилок.
EXPOSE 7860

# Запуск бота
CMD ["python", "bot.py"]