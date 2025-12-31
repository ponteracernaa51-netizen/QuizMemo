from datetime import datetime, timedelta

def calculate_sm2(rating, interval, ease_factor, repetitions):
    now = datetime.now()

    # --- ЭТАП 1: Кнопка "СНОВА" (Rating 0) ---
    # Всегда сбрасывает на 1 минуту, независимо от этапа
    if rating == 0:
        return 0, ease_factor, 0, now + timedelta(minutes=1)

    # --- ЭТАП 2: НОВАЯ КАРТОЧКА (repetitions == 0) ---
    if repetitions == 0:
        if rating == 1: # Трудно
            return 0, ease_factor, 1, now + timedelta(minutes=5)
        elif rating == 2: # Хорошо
            return 0, ease_factor, 2, now + timedelta(minutes=10)
        else: # Легко (Rating 3) - Сразу переводим в статус "Изучено" на 4 дня
            return 4, ease_factor, 1, now + timedelta(days=4)

    # --- ЭТАП 3: КАРТОЧКА В ПРОЦЕССЕ ОБУЧЕНИЯ (interval == 0) ---
    # (Она уже виделась сегодня, но еще не перешла в разряд "на завтра")
    if interval == 0:
        if rating == 1: # Трудно
            return 0, ease_factor, repetitions + 1, now + timedelta(minutes=10)
        elif rating == 2: # Хорошо - Переводим на 1 день
            return 1, ease_factor, 1, now + timedelta(days=1)
        else: # Легко - Переводим на 4 дня
            return 4, ease_factor, 1, now + timedelta(days=4)

    # --- ЭТАП 4: ЗАКРЕПЛЕННАЯ КАРТОЧКА (interval >= 1) ---
    # Работает стандартный интервальный повтор
    new_ease_factor = ease_factor + (0.1 if rating == 3 else -0.15 if rating == 1 else 0)
    if new_ease_factor < 1.3: new_ease_factor = 1.3

    if rating == 1: # Трудно
        new_interval = max(1, round(interval * 1.2))
    elif rating == 2: # Хорошо
        new_interval = round(interval * new_ease_factor)
    else: # Легко
        new_interval = round(interval * new_ease_factor * 1.3)

    return new_interval, new_ease_factor, repetitions + 1, now + timedelta(days=new_interval)