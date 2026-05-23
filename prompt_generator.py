import os, re, requests
from dotenv import load_dotenv

load_dotenv()

def ask_ai(prompt):
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [
            {"role": "system", "content": "Ты эксперт по вирусным промптам для нейросети Nano Banana. Промпты всегда на английском, детальные, фотореалистичные."},
            {"role": "user", "content": prompt}], "max_tokens": 1000})
    return r.json()["choices"][0]["message"]["content"].strip()

def wrap_prompts(text):
    """Оборачивает каждый пронумерованный промпт в <code> для копирования в Telegram."""
    parts = re.split(r'\n(?=\d+\.)', text.strip())
    result = []
    for part in parts:
        m = re.match(r'(\d+\.\s*)(.*)', part, re.DOTALL)
        if m:
            num, content = m.group(1), m.group(2).strip()
            result.append(f"{num}<code>{content}</code>")
        else:
            result.append(part)
    return '\n\n'.join(result)

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={"chat_id": os.getenv('TELEGRAM_CHAT_ID'), "text": text, "parse_mode": "HTML"})

def run_prompt_generator():
    send_tg("👩 <b>ДЕВУШКА</b>\n\n" + wrap_prompts(ask_ai("Создай 3 вирусных промпта для Nano Banana. Девушка: брюнетка, каре до плеч, зелёные глаза, спортивная. Разные локации. Нумерация 1. 2. 3.")))
    send_tg("👨 <b>МУЖЧИНА</b>\n\n" + wrap_prompts(ask_ai("Создай 3 вирусных промпта для Nano Banana. Мужчина: светлые волосы, очки тёмная оправа, стильный. Разные локации. Нумерация 1. 2. 3.")))
    send_tg("✨ <b>ГЕНЕРАЦИЯ ДНЯ</b>\n\n" + wrap_prompts(ask_ai("Создай 3 необычных креативных промпта для Nano Banana. Название на русском + промпт на английском. Нумерация 1. 2. 3.")))
    print("Готово!")
