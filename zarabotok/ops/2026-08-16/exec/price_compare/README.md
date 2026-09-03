# Walmart↔Amazon Price Comparator (прототип под заказ FL 5518190)

Модульная программа сравнения цен по UPC/EAN/GTIN.

## Архитектура (под расширение новыми сайтами)

```
main.py                CLI: input.csv -> report.csv
sources/base.py        SourceAdapter (интерфейс: поиск товара по штрихкоду)
sources/walmart.py     адаптер Walmart (graphql repSearchItems)
keepa_client.py        клиент Keepa API (search type=upc -> ASIN; product -> buyBox)
compare.py             подсчёт diff / ROI
report.py              экспорт в CSV (utf-8-sig, открывается в Excel)
```

- Новый сайт (Target/Costco/HomeDepot/eBay) = новый файл в `sources/` + одна строка в `main.py`.
- Сопоставление: UPC/EAN/GTIN через Keepa search `type=upc` (встроенное сопоставление Keepa, исключает ложные матчи), кросс-проверка по названию при необходимости.
- Keepa запрошена на количество API-запросов: 1 search + 1 product на товар.

## Запуск

```
pip install -r requirements.txt
export KEEPA_API_KEY=xxx            # ключ заказчика (у него есть подписка)
export KEEPA_DOMAIN=1               # 1 = Amazon US
python main.py orders.csv report.csv --delay 2
```

`orders.csv` — колонка с заголовком `upc`/`ean`/`gtin` (+ опционально `title`).

Выход: `report.csv` с колонками UPC, Title, WalmartPriceUSD, WalmartURL, AmazonPriceUSD, DiffUSD, ROI%, Note.

## Проверено

- `python -m py_compile` — ок (все модули).
- Без ключа Keepa прогон по 2 строкам падает с понятной ошибкой (это ожидаемо: ключ у заказчика).
- Walmart-адаптер обращается к публичной поисковой ручке; при блокировке/антиботе возвращает строку с ошибкой в Note, не роняя прогон. Для продакшена: ротация заголовков/прокси через `HTTP_PROXY`.

## Срок/стоимость (для отклика)

- Консольная версия + Expand (eBay) + отчёт: 3–5 дней, от 35 000 ₽.
- С веб-интерфейсом и расписанием: 7–10 дней, от 55 000 ₽.