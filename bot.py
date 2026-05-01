import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import cloudscraper
import re
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from aiogram.types import FSInputFile

TOKEN = "8716094991:AAEHEjbLhnl4z9rD0MTETd2yGjYPr8R7AqQ"

bot = Bot(token=TOKEN)
dp = Dispatcher()

RSS_URL = "https://asterios.tm/index.php?cmd=rss&serv=6&filter=keyboss"

# Боси які цікавлять
BOSSES = [
    "Kernon",
    "Death Lord Hallate",
    "Shilen's Messenger Cabrio",
    "Longhorn Golkonda"
    
]

#"Queen Ant",
#    "Baium",
 #  "Antharas",
  #  "Valakas",
   # "Orfen"
# Зберігаємо останні кілли
last_kills = {}



def parse_rss():
    print("--- Пошук у HTML-таблиці (Asterios Mode) ---")
    scraper = cloudscraper.create_scraper()
    
    try:
        response = scraper.get(RSS_URL, timeout=20)
        if response.status_code != 200:
            return {}

        content = response.text
        bosses = {}

        # 1. Шукаємо всі посилання, які містять дату та ім'я боса
        # Приклад з вашого тексту: 2026-04-16 12:11:36: Убит босс Kernon
        pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}): Убит босс ([\w\s']+)"
        
        matches = re.findall(pattern, content)
        print(f"Знайдено всього босів у списку: {len(matches)}")

        for date_str, boss_name in matches:
            boss_name = boss_name.strip()
            
            # Перевіряємо, чи є цей бос у нашому списку BOSSES
            for target_boss in BOSSES:
                if target_boss.lower() in boss_name.lower():
                    try:
                        # Формат: 2026-04-16 12:11:36
                        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        
                        # Зберігаємо тільки найсвіжішу дату для кожного боса
                        if target_boss not in bosses or bosses[target_boss] < dt:
                            bosses[target_boss] = dt
                            print(f"✅ Знайдено: {target_boss} | Час: {dt}")
                    except Exception as e:
                        print(f"Помилка дати для {boss_name}: {e}")

        print(f"Успішно оброблено: {len(bosses)} з {len(BOSSES)}")
        return bosses

    except Exception as e:
        print(f"Помилка парсингу: {e}")
        return {}
        
        
# Переконайтеся, що в функції build_message викликається саме parse_rss()


async def auto_notify():
    while True:
        try:
            print("Оновлення даних...")
            parse_rss()
        except Exception as e:
            print(f"Помилка в автооновленні: {e}")
        await asyncio.sleep(120)

def calc_respawn(death):
    # Наприклад: мінімальний через 12 годин, максимальний через 24
    min_resp = death + timedelta(hours=18)
    max_resp = death + timedelta(hours=30)
    return min_resp, max_resp

def format_time(td):
    total = int(td.total_seconds())
    if total < 0:
        return "0:00:00"
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h}:{m:02}:{s:02}"

def draw_text_shadow(draw, pos, text, font, fill, shadow=(0,0,0)):
    x, y = pos
    draw.text((x+1, y+1), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def prepare_data():
    raw = parse_rss()
    now = datetime.now()

    result = {}

    for boss in BOSSES:
        if boss not in raw:
            continue

        death = raw[boss]
        min_resp, max_resp = calc_respawn(death)

        # 👉 ВСЕ МАЄ БУТИ ВСЕРЕДИНІ ЦИКЛУ
        if now < min_resp:
            status = " FOR MIN RESP "
            left = format_time(min_resp - now)

        elif min_resp <= now <= max_resp:
            status = "RESP PROSES"
            left = format_time(max_resp - now)

        else:
            status = "LIVE"
            left = "-"

        result[boss] = {
            "death_dt": death,
            "min_dt": min_resp,
            "max_dt": max_resp,
            "death": death.strftime('%d-%m %H:%M'),
            "min": min_resp.strftime('%H:%M'),
            "max": max_resp.strftime('%H:%M'),
            "status": status,
            "left": left
        }

    return result

def draw_bar(draw, x, y, width, height, progress):
    # фон
    draw.rectangle((x, y, x+width, y+height), fill=(40,40,40))
    
    # заповнення
    fill_w = int(width * progress)
    color = (255,180,0) if progress < 1 else (255,80,80)
    draw.rectangle((x, y, x+fill_w, y+height), fill=color)

def draw_bar(draw, x, y, width, height, progress):
    draw.rectangle((x, y, x+width, y+height), fill=(40,40,40))
    fill_w = int(width * progress)
    color = (255,180,0) if progress < 1 else (255,80,80)
    draw.rectangle((x, y, x+fill_w, y+height), fill=color)


def generate_image(data):
    width = 700
    row_h = 110
    margin = 20
    header_h = 50
    height = row_h * len(data) + header_h

    img = Image.new("RGB", (width, height), (20, 22, 24))
    draw = ImageDraw.Draw(img)

    try:
        f_name = ImageFont.truetype("arialbd.ttf", 24)
        f_time = ImageFont.truetype("arial.ttf", 16)
        f_status = ImageFont.truetype("arialbd.ttf", 18)
        f_small = ImageFont.truetype("arial.ttf", 14)
    except:
        f_name = f_time = f_status = f_small = ImageFont.load_default()

    # Шапка
    draw.rectangle((0, 0, width, header_h), fill=(30, 33, 36))
    draw.text((margin, 12), "BOSS MONITORING • MEDEA x3", fill=(140, 150, 160), font=f_status)

    y = header_h
    now = datetime.now()

    for boss, info in data.items():
        # Визначаємо статус для кольору
        if now < info["min_dt"]:
            status_color = (150, 150, 150) # Очікування (сірий)
            status_text = "WAITING"
        elif info["min_dt"] <= now <= info["max_dt"]:
            status_color = (255, 165, 0)   # У вікні (помаранчевий)
            status_text = "RESP PROSES"
        else:
            status_color = (76, 175, 80)   # Живий (зелений)
            status_text = "ALIVE / LATE"

        # Плашка боса
        draw.rectangle((10, y + 5, width - 10, y + row_h - 5), fill=(28, 31, 35), outline=(50, 54, 58))
        
        # Назва
        draw.text((margin, y + 15), boss.upper(), fill=(255, 255, 255), font=f_name)

        # Таймінги (З ДОДАВАННЯМ ДАТИ, якщо це не сьогодні)
        def format_with_day(dt):
            if dt.date() > now.date():
                return dt.strftime('%H:%M (%d.%m)') # Додаємо дату, якщо завтра+
            return dt.strftime('%H:%M')

        kill_s = info["death_dt"].strftime('%H:%M (%d.%m)')
        min_s = format_with_day(info["min_dt"])
        max_s = format_with_day(info["max_dt"])
        
        draw.text((margin, y + 50), f"Death: {kill_s}  |  Min: {min_s}  |  Max: {max_s}", fill=(170, 170, 170), font=f_time)

        # Статус праворуч
        draw.text((width - 170, y + 15), status_text, fill=status_color, font=f_status)
        
        # Час до респу
        if now < info["min_dt"]:
            time_str = f"To Min: {info['left']}"
        else:
            time_str = f"To Max: {info['left']}"
        draw.text((width - 170, y + 40), time_str, fill=(200, 200, 200), font=f_time)

        # Прогрес-бар (візуалізація вікна)
        bar_x, bar_y, bar_w, bar_h_val = margin, y + 80, width - 220, 10
        draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h_val), fill=(45, 48, 52))
        
        total_window = (info["max_dt"] - info["min_dt"]).total_seconds()
        passed = (now - info["min_dt"]).total_seconds()
        
        if total_window > 0:
            progress = max(0, min(1, passed / total_window))
            if progress > 0:
                draw.rectangle((bar_x, bar_y, bar_x + int(bar_w * progress), bar_y + bar_h_val), fill=status_color)

        y += row_h

    img.save("boss.png")


    
def build_message():
    data = parse_rss()
    now = datetime.now()

    if not data:
        return "⚠️ Не вдалося отримати дані з сервера."

    text = "<b>📊 Респ РБ (Medea x3)</b>\n\n"

    for boss in BOSSES:
        if boss not in data:
            text += f"❓ <b>{boss}</b>: немає даних\n\n"
            continue

        death = data[boss]
        min_resp, max_resp = calc_respawn(death)

        if now < min_resp:
            status = "❌ Не почався"
            time_left = format_time(min_resp - now)
        elif min_resp <= now <= max_resp:
            status = "🔥 Респ йде"
            time_left = format_time(max_resp - now)
        else:
            status = "⌛ Очікуємо кілл"
            time_left = "—"

        # центрування (приблизне)
        boss_name = boss.center(26)

        text += (
            f"<pre>"
            f"{'':<8}{boss_name}\n"
            f"{'-'*30}\n"
            f"☠  {death.strftime('%d-%m %H:%M')}\n"
            f"🟢  {min_resp.strftime('%H:%M')}\n"
            f"🔴  {max_resp.strftime('%H:%M')}\n"
            f"{status}\n"
            f"⏳  {time_left}\n"
            f"</pre>\n"
        )

    return text

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Бот респу РБ запущений!\n\nКоманда: /boss")


@dp.message(Command("boss"))
async def boss(message: Message):
    data = prepare_data()

    if not data:
        await message.answer("⚠️ Немає даних")
        return

    generate_image(data)

    photo = FSInputFile("boss.png")
    await message.answer_photo(photo)


# автооновлення (опціонально)
async def auto_notify():
    while True:
        print("Оновлення...")
        parse_rss()
        await asyncio.sleep(120)


async def main():
    asyncio.create_task(auto_notify())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())