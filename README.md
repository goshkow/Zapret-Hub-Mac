<div align="center">

# 🚀 [Zapret Hub](https://github.com/goshkow/Zapret-Hub-Mac)

**Zapret Hub** - macOS-приложение для **удобного управления** `ByeDPI` / `SpoofDPI` и `TG WS Proxy` из **одного интерфейса**.

**Для обычных пользователей** - без ручного запуска бинарников, поиска системных папок и настройки конфигов в терминале.

<img width="879" height="539" alt="image" src="https://github.com/user-attachments/assets/cd3523fe-e181-4d6d-9afb-2f20caa5df1c" />

**Автор**: goshkow • [GitHub](https://github.com/goshkow/Zapret-Hub-Mac)

Что-то не работает? • [Исправить](#не-работает) • [Создать issue](https://github.com/goshkow/Zapret-Hub-Mac/issues)

</div>

## 💡 Что это такое

Проект объединяет в **одном окне**:

✅ запуск/остановку `ByeDPI`/`SpoofDPI` и `TG WS Proxy`  
✅ единую кнопку ON/OFF со статусами  
✅ остается в menu bar при активных обходах  
✅ автозапуск и запуск в скрытом режиме  
✅ диагностику и просмотр логов  

> Приложение не требует внешних bat/ps1-скриптов и использует встроенные компоненты macOS-версии.

## ✨ Возможности

| Фича | Описание |
|------|----------|
| 🎮 **Единая кнопка** | Включение/отключение стека одним кликом |
| ⚙️ **Выбор движка** | `ByeDPI` или `SpoofDPI` в компонентах |
| 🌐 **Системный прокси** | Автоматически применяется с выбранным движком |
| ✈️ **TG WS Proxy** | Встроенный Telegram bridge с быстрым подключением |
| 🍎 **Menu bar режим** | При закрытии с активным стеком окно скрывается, работа продолжается в menu bar |
| 📜 **Логи** | Живые логи приложения, backend, TG WS Proxy, движков |
| 🧠 **Настройки** | Тема (System/Light/Dark), язык (RU/EN), автозапуск, автостарт компонентов |
| 🔄 **Проверка обновлений** | Проверка при запуске и каждые 5 часов, переход к релизу по кнопке |
| 💾 **Сохранение данных** | Настройки и состояние сохраняются вне `.app` в `~/Library/Application Support` |

## 💻 Требования

- 🍎 macOS 15.0+
- Apple Silicon / Intel Mac

> Для разработки:
>
> 🐍 Python 3.11+
>
> 🛠 Xcode Command Line Tools

## 📦 Сборка

### Локальная dev-сборка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m zapret_hub_mac.main
```

### Production `.app`

```bash
./scripts/build_xcode_app.sh
```

Результат: `dist/Zapret Hub.app`

## 🔗 Используемые проекты

| Инструмент | Автор |
|------------|--------|
| [tg-ws-proxy](https://github.com/Flowseal/tg-ws-proxy) | **Flowseal** |
| [SpoofDPI](https://github.com/xvzc/SpoofDPI) | **xvzc** |
| [byedpiDPI-MacOSApp](https://github.com/ollesss/byedpiDPI-MacOSApp) (ciadpi) | **ollesss** |

> [!CAUTION]
>
> ### Авторство
> **Zapret Hub** = интерфейс + менеджер поверх перечисленных инструментов.
>
> Авторство инструментов указано в приложении и документации.

# ↪️ Для разработчиков

## 📁 Структура проекта

- `src/zapret_hub_mac` — прикладная логика, UI и сервисы
- `resources` — профили, иконки, UI-ассеты
- `packaging` — конфигурация PyInstaller
- `scripts` — сборка, иконки, вспомогательные скрипты
- `xcode` и `ZapretHubMac.xcodeproj` — обертка и native icon pipeline

Рабочие каталоги пользователя:

- `~/Library/Application Support/Zapret Hub Mac/data`
- `~/Library/Application Support/Zapret Hub Mac/logs`
- `~/Library/Application Support/Zapret Hub Mac/state`
- `~/Library/Application Support/Zapret Hub Mac/profiles`

> Благодаря этому переустановка/обновление приложения не удаляет пользовательские настройки и данные.

# Не работает

> [!WARNING]
>
> ### Приложение не открывается
> Если macOS выдаёт предупреждение, что приложение повреждено или не может быть открыто, откройте Терминал и выполните команду для снятия ограничений безопасности:  
> `sudo xattr -r -d com.apple.quarantine /Applications/Zapret Hub.app`

> [!IMPORTANT]
>
> ### Не работают обходы
> При ошибках и нестабильной работе:
>
> 1. Переключите движок `ByeDPI` ↔ `SpoofDPI`
> 2. Нажмите единую кнопку OFF/ON для полного перезапуска стека
> 3. Проверьте логи во вкладке `Логи`
> 4. Убедитесь, что системный прокси не занят сторонними приложениями
> 5. Проверьте доступность целевых доменов и DNS в сети

