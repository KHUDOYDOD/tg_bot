# Forex Analysis Telegram Bot

A multi-language Telegram bot for financial market analysis that provides advanced technical indicators and user-friendly trading tools.

## Быстрый старт

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## Развертывание на Render

1. Нажмите кнопку "Deploy to Render" выше
2. Войдите в свой аккаунт Render или создайте новый
3. Добавьте необходимые переменные окружения:
   - `BOT_TOKEN`: Токен вашего Telegram бота от @BotFather
   - `DATABASE_URL`: URL вашей PostgreSQL базы данных
4. Нажмите "Apply" для запуска развертывания

## Features

- Multi-language support (Tajik, Russian, Uzbek, Kazakh, English)
- Real-time market analysis with technical indicators:
  - RSI
  - MACD
  - EMA
  - Bollinger Bands
- 30+ currency pairs support
- User authentication system
- Admin panel
- Monitoring system with web interface
- Automatic error recovery
- Detailed market analysis charts

## Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/forex-analysis-bot.git
cd forex-analysis-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
# Edit with your values
```

Required environment variables:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `DATABASE_URL`: PostgreSQL database URL


## Support

For support and questions:
- Telegram: @tradeporu
- Website: [TRADEPO.RU](https://tradepo.ru)

## License

This project is licensed under the MIT License - see the LICENSE file for details.