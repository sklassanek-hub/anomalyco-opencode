Вот готовое решение задачи по разработке лендинга студии йоги "Прана". Проект выполнен на чистом стеке (HTML5, CSS3, ES6+), полностью адаптивен и соответствует тематическому дизайну.

### Структура проекта

1.  **index.html** — Семантическая разметка страницы.
2.  **style.css** — Стили с использованием переменных и Flexbox/Grid.
3.  **script.js** — Логика мобильного меню и валидации формы.

---

### 1. Файл `index.html`

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Студия йоги Прана | Йога для тела и души</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&family=Lora:ital,wght@1,500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
</head>
<body>

    <!-- Шапка сайта -->
    <header class="site-header">
        <div class="container header-inner">
            <a href="#" class="logo">Прана<span class="dot">.</span></a>
            
            <nav class="main-nav" id="navbar">
                <ul>
                    <li><a href="#hero">Главная</a></li>
                    <li><a href="#schedule">Расписание</a></li>
                    <li><a href="#pricing">Тарифы</a></li>
                    <li><a href="#reviews">Отзывы</a></li>
                </ul>
            </nav>

            <button class="mobile-toggle" id="menu-btn" aria-label="Меню">
                <span></span>
                <span></span>
                <span></span>
            </button>
        </div>
    </header>

    <!-- Hero-блок -->
    <section id="hero" class="hero-section">
        <div class="container hero-content">
            <h1 class="fade-in-up">Найди свой баланс</h1>
            <p class="subtitle fade-in-up">Современная студия йоги в центре города. Занимайтесь с профессионалами, дышите полной грудью.</p>
            <div class="hero-buttons fade-in-up">
                <a href="#contact" class="btn btn-primary">Записаться на пробное</a>
            </div>
        </div>
    </section>

    <!-- Расписание -->
    <section id="schedule" class="section-padding">
        <div class="container">
            <h2 class="section-title">Расписание занятий</h2>
            <div class="schedule-grid">
                <!-- Карточка 1 -->
                <article class="card schedule-card">
                    <div class="card-time">08:00 - 09:00</div>
                    <div class="card-info">
                        <h3>Vinyasa Flow</h3>
                        <span class="instructor">Инструктор: Анна С.</span>
                    </div>
                </article>
                <!-- Карточка 2 -->
                <article class="card schedule-card">
                    <div class="card-time">10:00 - 11:00</div>
                    <div class="card-info">
                        <h3>Hatha Yoga</h3>
                        <span class="instructor">Инструктор: Мария К.</span>
                    </div>
                </article>
                <!-- Карточка 3 -->
                <article class="card schedule-card">
                    <div class="card-time">18:00 - 19:00</div>
                    <div class="card-info">
                        <h3>Meditation & Breath</h3>
                        <span class="instructor">Инструктор: Олег В.</span>
                    </div>
                </article>
            </div>
        </div>
    </section>

    <!-- Тарифы -->
    <section id="pricing" class="section-padding bg-dark">
        <div class="container">
            <h2 class="section-title">Тарифные планы</h2>
            <div class="pricing-grid">
                <div class="price-card">
                    <h3>Разовое занятие</h3>
                    <p class="price">800 ₽</p>
                    <ul class="features">
                        <li>Доступ к залу</li>
                        <li>Бесплатная вода</li>
                    </ul>
                    <a href="#contact" class="btn btn-outline">Выбрать</a>
                </div>
                <div class="price-card featured">
                    <div class="badge">Популярный</div>
                    <h3>Абонемент "Месяц"</h3>
                    <p class="price">8 000 ₽</p>
                    <ul class="features">
                        <li>12 занятий в месяц</li>
                        <li>Доступ к групповым классам</li