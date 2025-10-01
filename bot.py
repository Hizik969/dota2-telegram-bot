import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import matplotlib.pyplot as plt
import io
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "....")
PLAYER_ID = os.getenv("DOTA2_PLAYER_ID", "....")


# Загрузка героев и предметов
def load_heroes():
    url = "https://api.opendota.com/api/heroes"
    r = requests.get(url)
    heroes = {}
    if r.status_code == 200:
        for hero in r.json():
            heroes[hero["id"]] = hero["localized_name"]
    return heroes


def load_items():
    url = "https://api.opendota.com/api/constants/items"
    r = requests.get(url)
    items = {}
    if r.status_code == 200:
        item_data = r.json()
        for item_id, item_info in item_data.items():
            if isinstance(item_info, dict) and 'id' in item_info:
                items[item_info['id']] = item_info.get('dname', item_id)
    return items


HEROES = load_heroes()
ITEMS = load_items()


def get_profile():
    url = f"https://api.opendota.com/api/players/{PLAYER_ID}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        profile = data.get("profile", {})
        mmr = data.get("mmr_estimate", {}).get("estimate", "Неизвестно")
        return f"👤 Ник: {profile.get('personaname', 'Неизвестно')}\n🏆 MMR: {mmr}\n🔗 Профиль: {profile.get('profileurl', f'https://www.opendota.com/players/{PLAYER_ID}')}"
    else:
        return "Ошибка при получении данных."


def get_recent_matches(limit=5):
    url = f"https://api.opendota.com/api/players/{PLAYER_ID}/recentMatches"
    r = requests.get(url)
    if r.status_code == 200:
        matches = r.json()[:limit]
        result = "📊 Последние матчи:\n\n"
        buttons = []
        for match in matches:
            hero_name = HEROES.get(match.get("hero_id"), f"ID {match.get('hero_id')}")
            kills = match.get("kills", 0)
            deaths = match.get("deaths", 0)
            assists = match.get("assists", 0)
            player_slot = match.get("player_slot", 0)
            win = match.get("radiant_win")
            duration = round(match.get("duration", 0) / 60, 1)
            match_id = match.get("match_id")

            outcome = "✅ Победа" if (win and player_slot < 128) or (not win and player_slot >= 128) else "❌ Поражение"

            result += (
                f"🎮 Матч {match_id}\n"
                f"Герой: {hero_name}\n"
                f"K/D/A: {kills}/{deaths}/{assists}\n"
                f"⌛ {duration} мин\n"
                f"{outcome}\n\n"
            )
            buttons.append([InlineKeyboardButton(f"📖 Детали матча {match_id}", callback_data=f"match_{match_id}")])
        return result, InlineKeyboardMarkup(buttons)
    else:
        return "Ошибка при получении матчей.", None


def get_match_details(match_id: int):
    url = f"https://api.opendota.com/api/matches/{match_id}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        duration_seconds = data.get("duration", 0)
        duration_minutes = round(duration_seconds / 60, 1)
        radiant_win = data.get("radiant_win")

        players = data.get("players", [])

        # Находим нашего игрока
        player_data = next((p for p in players if str(p.get("account_id")) == PLAYER_ID), None)

        if not player_data:
            return "Данные игрока не найдены в этом матче"

        # Основная статистика игрока
        hero_name = HEROES.get(player_data.get("hero_id"), f"ID {player_data.get('hero_id')}")
        kills = player_data.get("kills", 0)
        deaths = player_data.get("deaths", 0)
        assists = player_data.get("assists", 0)
        gold = player_data.get("gold", 0)
        networth = player_data.get("net_worth", 0)
        level = player_data.get("level", 0)
        xp = player_data.get("total_xp", player_data.get("xp", 0))  # Исправлено: используем total_xp
        last_hits = player_data.get("last_hits", 0)
        denies = player_data.get("denies", 0)
        hero_damage = player_data.get("hero_damage", 0)
        tower_damage = player_data.get("tower_damage", 0)
        hero_healing = player_data.get("hero_healing", 0)
        gpm = player_data.get("gold_per_min", 0)
        xpm = player_data.get("xp_per_min", 0)

        # Определяем сторону и результат
        player_slot = player_data.get("player_slot", 0)
        side = "Radiant" if player_slot < 128 else "Dire"
        player_outcome = "✅ Победа" if (radiant_win and side == "Radiant") or (
                    not radiant_win and side == "Dire") else "❌ Поражение"

        # Предметы с названиями
        item_names = []
        for i in range(6):
            item_id = player_data.get(f"item_{i}")
            if item_id and item_id > 0:
                item_name = ITEMS.get(item_id, f"Предмет {item_id}")
                item_names.append(item_name)

        # Форматируем большие числа
        def format_number(num):
            if num >= 1000:
                return f"{num / 1000:.1f}k"
            return str(num)

        return (
            f"🎮 Матч {match_id}\n"
            f"🧙 Герой: {hero_name} ({side})\n"
            f"🏆 Результат: {player_outcome}\n\n"
            f"⚔️ K/D/A: {kills}/{deaths}/{assists}\n"
            f"💰 Текущее золото: {format_number(gold)}\n"
            f"💎 Networth: {format_number(networth)}\n"
            f"📊 Уровень: {level}\n"
            f"🌟 Опыт: {format_number(xp)}\n"
            f"🎯 Ластхиты/Денаи: {last_hits}/{denies}\n"
            f"📈 GPM/XPM: {gpm}/{xpm}\n\n"
            f"🔥 Урон по героям: {format_number(hero_damage)}\n"
            f"🏰 Урон по towers: {format_number(tower_damage)}\n"
            f"❤️ Лечение: {format_number(hero_healing)}\n"
            f"⌛ Длительность: {duration_minutes} мин\n"
            f"🎒 Предметы: {', '.join(item_names) if item_names else 'Нет предметов'}"
        )
    else:
        return "Ошибка при получении данных о матче."


def get_gold_xp_graph(match_id: int):
    """Создает график золота и опыта по минутам"""
    url = f"https://api.opendota.com/api/matches/{match_id}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()
    players = data.get("players", [])

    # Находим нашего игрока
    player_data = next((p for p in players if str(p.get("account_id")) == PLAYER_ID), None)

    if not player_data or "gold_t" not in player_data or "xp_t" not in player_data:
        return None

    gold_data = player_data["gold_t"]
    xp_data = player_data["xp_t"]

    # Создаем график
    plt.figure(figsize=(10, 6))
    minutes = list(range(len(gold_data)))

    plt.plot(minutes, gold_data, label='Gold', color='gold', linewidth=2)
    plt.plot(minutes, [x / 100 for x in xp_data], label='XP (divided by 100)', color='blue', linewidth=2)

    plt.xlabel('Минуты')
    plt.ylabel('Значения')
    plt.title(f'Gold и XP по минутам - Матч {match_id}')
    plt.legend()
    plt.grid(True)

    # Сохраняем в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def get_win_lose_stats():
    url = f"https://api.opendota.com/api/players/{PLAYER_ID}/wl"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        win = data.get("win", 0)
        lose = data.get("lose", 0)
        total = win + lose
        winrate = (win / total * 100) if total > 0 else 0
        return f"📈 Общая статистика:\n✅ Побед: {win}\n❌ Поражений: {lose}\n🏆 Винрейт: {winrate:.1f}%"
    return "Ошибка получения статистики"


def get_top_heroes(limit=5):
    url = f"https://api.opendota.com/api/players/{PLAYER_ID}/heroes"
    r = requests.get(url)
    if r.status_code == 200:
        heroes = r.json()[:limit]
        result = "🏅 Топ герои:\n\n"
        for h in heroes:
            hero_name = HEROES.get(h["hero_id"], f"ID {h['hero_id']}")
            games = h["games"]
            wins = h["win"]
            winrate = round(wins / games * 100, 1) if games > 0 else 0
            result += f"{hero_name}: {wins}/{games} побед ({winrate}%)\n"
        return result
    else:
        return "Ошибка при получении топ героев."


def get_peers(limit=5):
    url = f"https://api.opendota.com/api/players/{PLAYER_ID}/peers"
    r = requests.get(url)
    if r.status_code == 200:
        peers = r.json()[:limit]
        result = "👥 Частые соратники:\n\n"
        for i, peer in enumerate(peers, 1):
            games = peer.get("with_games", 0)
            wins = peer.get("with_win", 0)
            winrate = (wins / games * 100) if games > 0 else 0
            result += f"{i}. {peer.get('personaname', 'Unknown')}\n   Игр вместе: {games} | Побед: {wins} ({winrate:.1f}%)\n"
        return result
    return "Ошибка получения данных"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📊 Профиль"), KeyboardButton("🎮 Последние матчи")],
        [KeyboardButton("🏅 Топ герои"), KeyboardButton("📈 Статистика Win/Lose")],
        [KeyboardButton("👥 Частые соратники"), KeyboardButton("📈 График Gold/XP")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Выбирай действие:", reply_markup=markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📊 Профиль":
        await update.message.reply_text(get_profile(), disable_web_page_preview=True)
    elif text == "🎮 Последние матчи":
        matches_text, buttons = get_recent_matches()
        await update.message.reply_text(matches_text, reply_markup=buttons)
    elif text == "🏅 Топ герои":
        await update.message.reply_text(get_top_heroes())
    elif text == "📈 Статистика Win/Lose":
        await update.message.reply_text(get_win_lose_stats())
    elif text == "👥 Частые соратники":
        await update.message.reply_text(get_peers())
    elif text == "📈 График Gold/XP":
        # Получаем последний матч для графика
        url = f"https://api.opendota.com/api/players/{PLAYER_ID}/recentMatches"
        r = requests.get(url)
        if r.status_code == 200 and r.json():
            match_id = r.json()[0]["match_id"]
            graph_buf = get_gold_xp_graph(match_id)
            if graph_buf:
                await update.message.reply_photo(photo=graph_buf, caption=f"📊 График Gold/XP для матча {match_id}")
            else:
                await update.message.reply_text("Не удалось создать график для последнего матча")
        else:
            await update.message.reply_text("Не найдено последних матчей")
    else:
        await update.message.reply_text("Не понял 🤔 Используй кнопки ниже.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("match_"):
        match_id = int(query.data.split("_")[1])
        details = get_match_details(match_id)

        # Отправляем детали матча
        await query.message.reply_text(details)

        # Пытаемся отправить график
        graph_buf = get_gold_xp_graph(match_id)
        if graph_buf:
            await query.message.reply_photo(photo=graph_buf, caption=f"📊 График Gold/XP для матча {match_id}")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
