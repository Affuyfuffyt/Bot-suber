import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from datetime import datetime, timedelta

# تحميل المتغيرات
load_dotenv()
TOKEN = os.getenv("TOKEN")

# التحقق من التوكن
if not TOKEN:
    print("Error: TOKEN is missing.")
    exit(1)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

GET_TEXT, GET_INTERVAL, GET_DURATION, GET_LINK = range(4)

# دالة الإرسال المجدول
async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data['chat_id']
    text = job_data['text']
    end_time = job_data['end_time']
    
    if datetime.now() > end_time:
        context.job.schedule_removal()
        return

    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        print(f"Failed to send to {chat_id}: {e}")
        context.job.schedule_removal()

# بداية المحادثة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **أهلاً بك في بوت النشر التلقائي!**\n\n"
        "هذا البوت متاح للجميع. لاستخدامه:\n"
        "1. أضف البوت إلى مجموعتك (الكروب).\n"
        "2. ارسل الأمر /setup لبدء حملة نشر جديدة."
    )

async def setup_campaign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 أرسل النص الذي تريد نشره في المجموعات:")
    return GET_TEXT

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['text'] = update.message.text
    await update.message.reply_text("⏱️ كل كم **دقيقة** تريد تكرار الإرسال؟ (أرسل رقماً فقط):")
    return GET_INTERVAL

async def receive_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(update.message.text)
        if minutes < 1: minutes = 1
        context.user_data['interval'] = minutes
        await update.message.reply_text("⏳ كم **ساعة** تريد أن يستمر النشر؟ (مثلاً 24 ليوم كامل):")
        return GET_DURATION
    except ValueError:
        await update.message.reply_text("⚠️ الرجاء إرسال رقم صحيح.")
        return GET_INTERVAL

async def receive_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hours = int(update.message.text)
        context.user_data['duration'] = hours
        await update.message.reply_text(
            "🔗 الآن أرسل **رابط المجموعة** أو **المعرف** (@username).\n"
            "تأكد أن البوت مشرف أو عضو في المجموعة!"
        )
        return GET_LINK
    except ValueError:
        await update.message.reply_text("⚠️ الرجاء إرسال رقم صحيح.")
        return GET_DURATION

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    chat_id = link
    
    # معالجة الرابط لاستخراج اليوزر
    if "t.me/" in link:
        parts = link.split('/')
        username = parts[-1]
        if username.startswith('+') or "joinchat" in link:
            await update.message.reply_text("🚫 لا يمكن استخدام روابط الانضمام الخاصة. يرجى إرسال المعرف (ID) أو اليوزر العام.")
            return ConversationHandler.END
        chat_id = f"@{username}"
    elif not link.startswith("@") and not link.replace("-", "").isdigit():
         chat_id = f"@{link}"

    try:
        # اختبار الإرسال
        await context.bot.send_message(chat_id=chat_id, text=f"✅ **تم التفعيل!**\nسيتم نشر الرسالة كل {context.user_data['interval']} دقيقة.")
        
        # جدولة المهمة
        text = context.user_data['text']
        end_time = datetime.now() + timedelta(hours=context.user_data['duration'])
        
        context.job_queue.run_repeating(
            send_scheduled_message,
            interval=context.user_data['interval'] * 60,
            first=1,
            data={'chat_id': chat_id, 'text': text, 'end_time': end_time}
        )
        
        await update.message.reply_text("🚀 **تم بدء النشر بنجاح!**")
        
    except Exception as e:
        await update.message.reply_text(f"❌ **فشل الوصول للمجموعة:**\n{e}\nتأكد من إضافة البوت للمجموعة أولاً.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 تم الإلغاء.")
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setup', setup_campaign)],
        states={
            GET_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
            GET_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_interval)],
            GET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_duration)],
            GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)

    print("Bot Started...")
    application.run_polling()
