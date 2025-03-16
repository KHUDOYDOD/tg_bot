import logging
import hashlib
import time
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import *
from market_analyzer import MarketAnalyzer
from utils import get_currency_keyboard, get_language_keyboard, format_signal_message
try:
    from generate_sample import create_analysis_image
except ImportError:
    logging.error("Could not import generate_sample module. Chart generation will be disabled.")
    def create_analysis_image(*args, **kwargs):
        logging.warning("Chart generation is disabled due to missing module")
        return False
from datetime import datetime
from models import add_user, get_user, approve_user, verify_user_password, update_user_language
from keep_alive import keep_alive

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)
logger = logging.getLogger(__name__)

ADMIN_USERNAME = "tradeporu"
PENDING_USERS = {}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username

        # Add user to database
        add_user(user_id, username)
        user_data = get_user(user_id)

        # Set default language
        lang_code = user_data['language_code'] if user_data else 'tg'

        # Send welcome message with keyboard
        keyboard = get_currency_keyboard(current_lang=lang_code)
        await update.message.reply_text(
            MESSAGES[lang_code]['WELCOME'],
            reply_markup=keyboard,
            parse_mode='MarkdownV2'
        )

    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        await update.message.reply_text(MESSAGES['tg']['ERRORS']['GENERAL_ERROR'])

async def get_admin_chat_id(bot):
    """Get admin's chat ID by username"""
    try:
        admin_chat = await bot.get_chat(f"@{ADMIN_USERNAME}")
        return admin_chat.id
    except Exception as e:
        logger.error(f"Error getting admin chat ID: {str(e)}")
        return None

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Ignore header buttons
    if query.data.startswith('header_'):
        await query.answer()
        return

    admin_username = update.effective_user.username

    if not admin_username or admin_username.lower() != ADMIN_USERNAME.lower():
        await query.answer("❌ У вас нет прав администратора")
        return

    action, user_id = query.data.split('_')
    user_id = int(user_id)

    if user_id not in PENDING_USERS:
        await query.answer("❌ Заявка не найдена или уже обработана")
        return

    user_info = PENDING_USERS[user_id]

    if action == "approve":
        password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
        password_hash = hash_password(password)

        if approve_user(user_id, password_hash):
            del PENDING_USERS[user_id]
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ Ваша заявка одобрена!\n\nВаш пароль для входа: `{password}`\n\nПожалуйста, сохраните его.",
                parse_mode='MarkdownV2'
            )
            await query.edit_message_text(f"✅ Пользователь @{user_info['username']} одобрен")
        else:
            await query.edit_message_text("❌ Ошибка при одобрении пользователя")
    else:
        del PENDING_USERS[user_id]
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Ваша заявка отклонена администратором."
        )
        await query.edit_message_text(f"❌ Пользователь @{user_info['username']} отклонен")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_data = get_user(user.id)

    if not user_data:
        add_user(user.id, user.username)
        user_data = get_user(user.id)

    lang_code = user_data['language_code'] if user_data else 'tg'
    keyboard = get_currency_keyboard(current_lang=lang_code)
    await update.message.reply_text(
        MESSAGES[lang_code]['WELCOME'],
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        lang_code = query.data.split('_')[1]
        user_id = update.effective_user.id
        logger.info(f"Language change request from user {user_id} to {lang_code}")

        # Update user's language in database
        if update_user_language(user_id, lang_code):
            # Get fresh keyboard with new language
            keyboard = get_currency_keyboard(current_lang=lang_code)
            welcome_message = MESSAGES[lang_code]['WELCOME']

            try:
                # Delete previous message if exists
                try:
                    await query.message.delete()
                except Exception:
                    pass  # Ignore if message can't be deleted

                # Send new welcome message
                await update.effective_chat.send_message(
                    text=welcome_message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )

                # Send confirmation in the selected language
                lang_confirmations = {
                    'tg': '✅ Забон иваз карда шуд',
                    'ru': '✅ Язык изменен',
                    'uz': '✅ Til oʻzgartirildi',
                    'kk': '✅ Тіл өзгертілді',
                    'en': '✅ Language changed'
                }
                await query.answer(lang_confirmations.get(lang_code, '✅ OK'))
                logger.info(f"Language successfully changed to {lang_code} for user {user_id}")

            except Exception as e:
                logger.error(f"Error sending message after language change: {e}")
                await query.answer("❌ Error sending message")
        else:
            logger.error(f"Failed to update language to {lang_code} for user {user_id}")
            await query.answer("❌ Error updating language")

    except Exception as e:
        logger.error(f"Language selection error: {str(e)}")
        await query.answer("❌ Error processing language change")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        # Handle "Return to Main" button
        if query.data == "return_to_main":
            user_id = update.effective_user.id
            user_data = get_user(user_id)
            lang_code = user_data['language_code'] if user_data else 'tg'

            keyboard = get_currency_keyboard(current_lang=lang_code)
            try:
                await query.message.delete()
            except Exception:
                pass  # Ignore if message can't be deleted

            await update.effective_chat.send_message(
                text=MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            return

        # Ignore clicks on header buttons
        if query.data.startswith('header_'):
            await query.answer()
            return

        # Get user data
        user_id = update.effective_user.id
        user_data = get_user(user_id)

        if not user_data:
            add_user(user_id, update.effective_user.username)
            user_data = get_user(user_id)

        lang_code = user_data['language_code'] if user_data else 'tg'
        logger.info(f"Current language for user {user_id}: {lang_code}")

        if query.data.startswith('lang_'):
            await handle_language_selection(update, context)
            return

        if query.data == "change_language":
            keyboard = get_language_keyboard()
            msg = "Выберите язык / Забонро интихоб кунед / Tilni tanlang / Тілді таңдаңыз / Choose language:"
            try:
                if query.message.photo:
                    await query.message.reply_text(msg, reply_markup=keyboard)
                else:
                    await query.message.edit_text(msg, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error showing language selection: {e}")
            return

        pair = query.data
        symbol = CURRENCY_PAIRS.get(pair)
        if not symbol:
            await query.message.reply_text(MESSAGES[lang_code]['ERRORS']['GENERAL_ERROR'])
            return

        analyzing_message = await query.message.reply_text(
            MESSAGES[lang_code]['ANALYZING'],
            parse_mode='MarkdownV2'
        )

        try:
            analyzer = MarketAnalyzer(symbol)
            analyzer.set_language(lang_code)
            analysis_result = analyzer.analyze_market()

            if not analysis_result or 'error' in analysis_result:
                error_msg = analysis_result.get('error', MESSAGES[lang_code]['ERRORS']['ANALYSIS_ERROR'])
                await analyzing_message.edit_text(error_msg, parse_mode='MarkdownV2')
                return

            market_data, error_message = analyzer.get_market_data(minutes=30)
            if error_message or market_data is None or market_data.empty:
                await analyzing_message.edit_text(MESSAGES[lang_code]['ERRORS']['NO_DATA'])
                return

            result_message = format_signal_message(pair, analysis_result, lang_code)

            try:
                create_analysis_image(analysis_result, market_data, lang_code)
                with open('analysis_sample.png', 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=result_message,
                        parse_mode='MarkdownV2',
                        reply_markup=get_currency_keyboard(current_lang=lang_code)
                    )
                await analyzing_message.delete()
            except Exception as img_error:
                logger.error(f"Chart error: {str(img_error)}")
                await analyzing_message.edit_text(
                    text=result_message,
                    parse_mode='MarkdownV2',
                    reply_markup=get_currency_keyboard(current_lang=lang_code)
                )

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            await analyzing_message.edit_text(MESSAGES[lang_code]['ERRORS']['ANALYSIS_ERROR'])

    except Exception as e:
        logger.error(f"Button click error: {str(e)}")
        await query.message.reply_text(MESSAGES[lang_code]['ERRORS']['GENERAL_ERROR'])

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the website.zip file to the user"""
    try:
        with open('website.zip', 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename='website.zip',
                caption='🌐 Архиви веб-сайт | Архив веб-сайта | Website archive'
            )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await update.message.reply_text("❌ Хатогӣ ҳангоми боргирӣ рух дод. Лутфан, дубора кӯшиш кунед.")

def main():
    reconnect_delay = 5  # Start with 5 seconds delay
    max_reconnect_delay = 30  # Maximum delay between reconnection attempts
    max_consecutive_errors = 10
    error_count = 0
    last_error_time = None

    while True:  # Infinite loop for continuous operation
        try:
            # Start the keep-alive server
            keep_alive()
            logger.info("Starting bot...")

            application = Application.builder().token(BOT_TOKEN).build()

            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("download", download))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            application.add_handler(CallbackQueryHandler(button_click))

            # Set up error handlers
            application.add_error_handler(error_handler)

            # Reset error count on successful startup
            error_count = 0
            last_error_time = None

            # Run the bot with enhanced polling settings
            logger.info("Bot is running...")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            current_time = datetime.now()

            # Reset error count if last error was more than 1 hour ago
            if last_error_time and (current_time - last_error_time).seconds > 3600:
                error_count = 0

            error_count += 1
            last_error_time = current_time

            logger.error(f"Bot crashed with error: {str(e)}")
            logger.info(f"Attempting to restart in {reconnect_delay} seconds...")

            if error_count >= max_consecutive_errors:
                logger.critical("Too many consecutive errors. Forcing system restart...")
                try:
                    # Additional cleanup before restart
                    if 'application' in locals():
                        try:
                            application.stop()
                        except:
                            pass
                    os.execv(sys.executable, ['python'] + sys.argv)
                except Exception as restart_error:
                    logger.error(f"Failed to restart: {restart_error}")
                continue

            # Implement exponential backoff for reconnection attempts
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

            # Log detailed error information
            logger.error("Detailed error information:", exc_info=True)
            continue
        finally:
            # Reset reconnect delay on successful connection
            reconnect_delay = 5

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Хатогӣ рух дод. Лутфан, дубора кӯшиш кунед."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

if __name__ == '__main__':
    main()