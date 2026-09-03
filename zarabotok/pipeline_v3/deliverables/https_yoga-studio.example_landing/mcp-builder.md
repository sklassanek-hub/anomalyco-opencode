Вот готовое решение задачи по разработке лендинга для студии йоги «Прана».

### План разработки:
1.  **HTML**: Семантическая верстка с использованием тегов `<header>`, `<main>`, `<section>`, `<footer>` и `nav`.
2.  **CSS**: Использование CSS-переменных для управления темной зеленой палитрой, Flexbox/Grid для сетки и медиа-запросов для адаптивности под мобильные устройства.
3.  **JS**: Реализация мобильного меню (бургер), плавного скролла к секциям и базовой валидации формы записи.

---

### Файл `index.html`

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Студия йоги Прана | Йога и медитация</title>
    <link rel="stylesheet" href="style.css">
    <!-- Подключение шрифтов (опционально) -->
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet">
</head>
<body>

    <!-- Шапка сайта -->
    <header class="site-header">
        <div class="container header-inner">
            <a href="#" class="logo">Прана<span class="dot">.</span></a>
            
            <nav class="main-nav" id="desktop-menu">
                <ul>
                    <li><a href="#about">О нас</a></li>
                    <li><a href="#schedule">Расписание</a></li>
                    <li><a href="#pricing">Тарифы</a></li>
                    <li><a href="#reviews">Отзывы</a></li>
                    <li><a href="#contact" class="btn-primary">Записаться</a></li>
                </ul>
            </nav>

            <!-- Мобильное меню (бургер) -->
            <div class="mobile-toggle" id="burger-btn">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    </header>

    <main>
        <!-- Hero-блок -->
        <section id="hero" class="hero-section">
            <div class="container hero-content">
                <h1 class="hero-title">Найди гармонию внутри себя</h1>
                <p class="hero-subtitle">Профессиональные инструкторы, уютная атмосфера и программы для любого уровня подготовки.</p>
                <a href="#contact" class="btn-large">Попробовать бесплатно</a>
            </div>
        </section>

        <!-- Преимущества (кратко) -->
        <section id="about" class="features-section">
            <div class="container">
                <h2 class="section-title">Почему выбирают нас</h2>
                <div class="features-grid">
                    <div class="feature-item">
                        <h3>Опытные инструкторы</h3>
                        <p>Сертифицированные тренеры с опытом более 5 лет.</p>
                    </div>
                    <div class="feature-item">
                        <h3>Чистота и уют</h3>
                        <p>Ежедневная уборка, натуральные ароматы и мягкие коврики.</p>
                    </div>
                    <div class="feature-item">
                        <h3>Индивидуальный подход</h3>
                        <p>Учитываем ваши пожелания и уровень подготовки.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Расписание -->
        <section id="schedule" class="schedule-section">
            <div class="container">
                <h2 class="section-title">Расписание занятий</h2>
                <p class="section-desc">Занятия проходят ежедневно с 08:00 до 21:00</p>
                
                <div class="schedule-grid">
                    <!-- Карточка 1 -->
                    <article class="card schedule-card">
                        <h3>Хатха Йога</h3>
                        <span class="time">18:00 - 19:30</span>
                        <p>Классическая практика для начинающих.</p>
                    </article>
                    
                    <!-- Карточка 2 -->
                    <article class="card schedule-card">
                        <h3>Vinyasa Flow</h3>
                        <span class="time">19:45 - 21:00</span>
                        <p>Динамичная практика с дыханием.</p>
                    </article>

                     <!-- Карточка 3 -->
                     <article class="card schedule-card">
                        <h3>Meditation & Pranayama</h3>
                        <span class="time">10:00 - 11:00</span>
                        <p>Утренний поток для энергии.</p>
                    </article>
                </div>
            </div>
        </section>

        <!-- Цены -->
        <section id="pricing" class="pricing-section">
            <div class="container">
                <h2 class="section-title">Тарифы</h2>
                <div class="pricing-grid">
                    <div class="price-card">
                        <h3>Разовое занятие</h3>
                        <p class="price">800 ₽</p>
                        <ul>
                            <li>Доступ к залу</li>
                            <li>Включено в стоимость</li>
                        </ul>
                    </div>
                    <div class="price-card active">
                        <h3>Абонемент "Месяц"</h3>
                        <p class="price">12 000 ₽</p>
                        <ul>
                            <li>10 занятий в месяц</li>
                            <li>Скидка на групповые классы</li>