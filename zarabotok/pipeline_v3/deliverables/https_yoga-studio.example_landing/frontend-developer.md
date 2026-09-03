Вот готовое решение задачи по разработке одностраничного лендинга для студии йоги "Прана". Проект выполнен на чистых технологиях (HTML5, CSS3, ES6 JavaScript) с использованием семантической верстки и современного дизайна.

### План реализации:
1.  **HTML:** Семантическая структура документа с использованием тегов `<header>`, `<main>`, `<section>`, `<footer>`.
2.  **CSS:** Использование CSS-переменных для управления палитрой (темно-зеленая тема), Flexbox/Grid для адаптивной сетки и медиа-запросов для мобильных устройств.
3.  **JS:** Реализация мобильного меню, плавного скролла и базовой валидации формы.

---

### Файл: `index.html`

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Студия йоги Прана | Йога для тела и души</title>
    <!-- Подключение шрифтов Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&family=Playfair+Display:ital,wght@0,600;1,600&display=swap" rel="stylesheet">
    
    <!-- Стили -->
    <link rel="stylesheet" href="style.css">

    <style>
        /* Встраиваем CSS для удобства копирования в один файл, 
           но логически разделяем его на секции */
        
        :root {
            --primary-color: #1a3c34; /* Глубокий зеленый */
            --secondary-color: #2c5e56; /* Светлее для ховеров */
            --accent-color: #d4af37; /* Золотой акцент */
            --text-light: #f4f4f4;
            --text-dark: #333333;
            --bg-dark: #122623;
            --transition-speed: 0.3s;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Montserrat', sans-serif;
            color: var(--text-dark);
            line-height: 1.6;
            background-color: #f9fdfa;
        }

        /* --- Header & Nav --- */
        .header {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            padding: 20px 5%;
            background-color: rgba(26, 60, 52, 0.95);
            backdrop-filter: blur(5px);
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-family: 'Playfair Display', serif;
            color: var(--accent-color);
            font-size: 24px;
            text-decoration: none;
            letter-spacing: 1px;
        }

        .nav-menu {
            display: flex;
            list-style: none;
            gap: 30px;
        }

        .nav-link {
            color: var(--text-light);
            text-decoration: none;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: color var(--transition-speed);
        }

        .nav-link:hover {
            color: var(--accent-color);
        }

        /* Мобильное меню (бургер) */
        .burger {
            display: none;
            cursor: pointer;
        }
        
        .burger div {
            width: 25px;
            height: 3px;
            background-color: var(--text-light);
            margin: 5px;
            transition: all 0.3s ease-in-out;
        }

        /* --- Hero Section --- */
        .hero {
            height: 100vh;
            background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.6)), 
                        url('https://images.unsplash.com/photo-1599903487624-b8e6d4b8c93f?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80') no-repeat center/cover;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: var(--text-light);
            padding: 0 20px;
        }

        .hero-content h1 {
            font-family: 'Playfair Display', serif;
            font-size: 3.5rem;
            margin-bottom: 20px;
            line-height: 1.2;
        }

        .hero-content p {
            font-size: 1.2rem;
            max-width: 600px;
            margin: