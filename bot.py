from telegram.ext import Application, CommandHandler, ContextTypes
import os

# API টোকেন (Render-এ Environment Variable থেকে নেওয়া হবে)
TOKEN = os.environ.get('TOKEN')

# /start কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "হ্যালো! আমি আপনার aibot! আমি এখানে আপনাকে সাহায্য করতে এসেছি। /help টাইপ করলে আরো তথ্য পাবেন!"
    )

# বট চালানোর ফাংশন
def main() -> None:
    # Application তৈরি
    application = Application.builder().token(TOKEN).build()

    # /start কমান্ড যোগ
    application.add_handler(CommandHandler("start", start))

    # বট চালু করা
    print("বট চলছে...")
    application.run_polling()

if __name__ == '__main__':
    main()
