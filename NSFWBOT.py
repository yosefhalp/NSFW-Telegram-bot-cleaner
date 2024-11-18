import os
import sqlite3
from datetime import datetime
from nudenet import NudeDetector
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.helpers import escape_markdown

# הגדרות בסיסיות
DATABASE_PATH = "bot_settings.db"  # שם קובץ בסיס הנתונים
TEMP_FOLDER = "temp"  # תיקייה לשמירת קבצים זמניים
BOT_TOKEN = "YOUR TOKEN IS HERE"  # הטוקן של הבוט שלך
detector = NudeDetector()  # אתחול המודל לזיהוי תוכן לא ראוי

class ModBot:
    def __init__(self):
        # מזהה ה־super_admin (המזהה שלך בטלגרם)
        self.super_admin_id = "YOUR ID"
        self.init_database()  # אתחול בסיס הנתונים
        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)
    
    def init_database(self):
        """יצירת בסיס נתונים SQLite ואתחול נתונים ראשוניים"""
        try:
            print(f"מנסה ליצור/לפתוח בסיס נתונים ב: {os.path.abspath(DATABASE_PATH)}")
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            
            # יצירת טבלה אם לא קיימת
            c.execute("""
                CREATE TABLE IF NOT EXISTS chat_settings 
                (chat_id TEXT PRIMARY KEY, mode TEXT DEFAULT 'warn_and_delete')
            """)
            
            # הכנסת נתון ראשוני לבדיקה
            c.execute("""
                INSERT OR REPLACE INTO chat_settings (chat_id, mode) 
                VALUES (?, ?)
            """, ('test_chat', 'warn_and_delete'))
            
            conn.commit()
            
            # בדיקת תכולת הטבלה
            c.execute("SELECT * FROM chat_settings")
            rows = c.fetchall()
            print("\n📊 תוכן בסיס הנתונים אחרי אתחול:")
            for row in rows:
                print(f"צ'אט ID: {row[0]}, מצב: {row[1]}")
                
            conn.close()
            
            if os.path.exists(DATABASE_PATH):
                print(f"✅ בסיס הנתונים נוצר ועודכן בהצלחה ב: {os.path.abspath(DATABASE_PATH)}")
            else:
                print("❌ קובץ בסיס הנתונים לא נוצר!")
                
        except Exception as e:
            print(f"❌ שגיאה בעבודה עם בסיס הנתונים: {str(e)}")

    def print_db_content(self):
        """הדפסת תוכן בסיס הנתונים לדיבוג"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM chat_settings")
            rows = c.fetchall()
            conn.close()
            
            print("\n📊 תוכן בסיס הנתונים:")
            for row in rows:
                print(f"צ'אט ID: {row[0]}, מצב: {row[1]}")
            print()
        except Exception as e:
            print(f"❌ שגיאה בהדפסת תוכן בסיס הנתונים: {str(e)}")

    def get_chat_mode(self, chat_id: str) -> str:
        """קבלת המצב הנוכחי של צ'אט מסוים"""
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("SELECT mode FROM chat_settings WHERE chat_id = ?", (chat_id,))
        result = c.fetchone()
        conn.close()
        mode = result[0] if result else 'warn_and_delete'
        print(f"get_chat_mode: המצב בצ'אט {chat_id} הוא {mode}")
        return mode

    async def check_admin(self, update: Update, chat_id: int) -> bool:
        """בדיקה אם המשתמש הוא מנהל בצ'אט"""
        user_id = update.effective_user.id
        if str(user_id) == self.super_admin_id:
            return True
        try:
            member = await update.bot.get_chat_member(chat_id, user_id)
            return member.status in ['administrator', 'creator']
        except Exception:
            return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בפקודת /start"""
        print(f"התקבלה פקודת start מ: {update.effective_chat.id}")
        welcome_message = """
👋 <b>ברוכים הבאים!</b>

🛡️ <b>בוט המודרציה</b>

הבוט מזהה ומסיר אוטומטית תוכן לא ראוי בקבוצות ובערוצים

📱 <b>פקודות זמינות:</b>
• <b>/start</b> - התחלת השימוש
• <b>/help</b> - הצגת עזרה מפורטת
• <b>/get_mode</b> - הצגת המצב הנוכחי

שלח <b>/help</b> לקבלת מידע נוסף.

<b>קרדיט:</b> נוצר ורץ על ידי <a href="https://t.me/Yosefhalp">@Yosefhalp</a>
"""
        await update.message.reply_text(welcome_message, parse_mode='HTML')
        print("הודעת פתיחה נשלחה")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """הצגת עזרה והסברים על תפעול הבוט"""
        help_message = """
🛡️ <b>בוט המודרציה</b>

הבוט מזהה ומסיר תוכן לא ראוי (NSFW) אוטומטית

📱 <b>פקודות בסיסיות:</b>
• <b>/start</b> - הפעלת הבוט
• <b>/help</b> - הצגת העזרה
• <b>/get_mode</b> - הצגת המצב הנוכחי

👮‍♂️ <b>פקודות למנהלים:</b>
• <code>set_mode_for</code> + מזהה צ'אט + מצב - שינוי הגדרות
• <code>get_mode_for</code> + מזהה צ'אט - בדיקת מצב

⚙️ <b>מצבי פעולה אפשריים:</b>
• <code>warn_and_delete</code> - מחיקה ואזהרה
• <code>warn_only</code> - אזהרה בלבד
• <code>delete_only</code> - מחיקה בלבד

📝 <b>דוגמת שימוש:</b>
<code>set_mode_for -1001234567890 delete_only</code>

👑 <b>לבעל הבוט:</b>
• <b>/list_chats</b> - הצגת כל הצ'אטים

<b>❓ איך למצוא מזהה צ'אט?</b>
השתמשו בבוט <a href="https://t.me/GetChatID_IL_BOT">@GetChatID_IL_BOT</a>

"""
        await update.message.reply_text(help_message, parse_mode='HTML')
        print("הודעת עזרה נשלחה")

    async def set_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """שינוי מצב פעולת הבוט בצ'אט הנוכחי (למנהלים)"""
        try:
            chat_id = update.effective_chat.id
            if not await self.check_admin(update, chat_id):
                await update.message.reply_text("⚠️ פעולה זו מותרת למנהלים בלבד.")
                return

            new_mode = context.args[0] if context.args else None

            if new_mode not in ['warn_and_delete', 'warn_only', 'delete_only']:
                await update.message.reply_text("❌ מצב לא חוקי. אפשרויות: `warn_and_delete`, `warn_only`, `delete_only`", parse_mode='Markdown')
                return

            print(f"משנה את המצב של הצ'אט {chat_id} ל- {new_mode}")

            # שמירת המצב בבסיס הנתונים
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, mode) VALUES (?, ?)", (str(chat_id), new_mode))
            conn.commit()
            conn.close()

            # בדיקה שהערך נשמר
            mode_in_db = self.get_chat_mode(str(chat_id))
            print(f"המצב החדש בצ'אט {chat_id}: {mode_in_db}")

            await update.message.reply_text(f"✅ המצב שונה ל: `{new_mode}`", parse_mode='Markdown')

        except Exception as e:
            print(f"שגיאה בשינוי מצב: {str(e)}")

    async def get_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """קבלת המצב הנוכחי של הבוט בצ'אט"""
        mode = self.get_chat_mode(str(update.effective_chat.id))
        await update.message.reply_text(f"המצב הנוכחי הוא: `{mode}`", parse_mode='Markdown')

    async def set_mode_for(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """שינוי מצב של צ'אט לפי chat_id (לבעלים ולמנהלים בצ'אט)"""
        try:
            user_id = update.effective_user.id
            if len(context.args) < 2:
                await update.message.reply_text("שימוש: `set_mode_for <chat_id> <mode>`", parse_mode='MarkdownV2')
                return

            chat_id = context.args[0]
            new_mode = context.args[1]

            if new_mode not in ['warn_and_delete', 'warn_only', 'delete_only']:
                await update.message.reply_text("❌ מצב לא חוקי. אפשרויות: `warn_and_delete`, `warn_only`, `delete_only`", parse_mode='MarkdownV2')
                return

            # בדיקת תקינות chat_id
            try:
                chat_id_int = int(chat_id)
                chat = await context.bot.get_chat(chat_id_int)
                chat_title = chat.title or chat.first_name or "Unnamed"
                print(f"מנסה לעדכן מצב עבור צ'אט: {chat_id} ({chat_title})")
            except Exception:
                await update.message.reply_text(f"❌ chat_id לא תקין: {chat_id}")
                return

            # בדיקת הרשאות: אם המשתמש הוא הבעלים או מנהל בצ'אט
            if str(user_id) != self.super_admin_id:
                if not await self.check_admin(update, chat_id_int):
                    await update.message.reply_text("⚠️ אין לך הרשאות לשנות את המצב בצ'אט זה.")
                    return

            # שמירת המצב בבסיס הנתונים
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO chat_settings (chat_id, mode) VALUES (?, ?)", (chat_id, new_mode))
            conn.commit()
            conn.close()

            print(f"מצב הצ'אט {chat_id} עודכן ל- {new_mode}")
            await update.message.reply_text(f"✅ המצב של הצ'אט *{chat_title}* עודכן ל- `{new_mode}`", parse_mode='MarkdownV2')

        except Exception as e:
            print(f"שגיאה ב- set_mode_for: {str(e)}")

    async def get_mode_for(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """קבלת מצב של צ'אט לפי chat_id (לבעלים ולמנהלים בצ'אט)"""
        try:
            user_id = update.effective_user.id
            if len(context.args) < 1:
                await update.message.reply_text("שימוש: `get_mode_for <chat_id>`", parse_mode='MarkdownV2')
                return

            chat_id = context.args[0]

            # בדיקת תקינות chat_id
            try:
                chat_id_int = int(chat_id)
                chat = await context.bot.get_chat(chat_id_int)
                chat_title = chat.title or chat.first_name or "Unnamed"
            except Exception:
                await update.message.reply_text(f"❌ chat_id לא תקין: {chat_id}")
                return

            # בדיקת הרשאות: אם המשתמש הוא הבעלים או מנהל בצ'אט
            if str(user_id) != self.super_admin_id:
                if not await self.check_admin(update, chat_id_int):
                    await update.message.reply_text("⚠️ אין לך הרשאות לצפות במצב הצ'אט הזה.")
                    return

            mode = self.get_chat_mode(chat_id)
            await update.message.reply_text(f"המצב של הצ'אט *{chat_title}* הוא: `{mode}`", parse_mode='MarkdownV2')

        except Exception as e:
            print(f"שגיאה ב- get_mode_for: {str(e)}")

    async def list_chats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """הצגת רשימת הצ'אטים שבהם הבוט פעיל (זמין לבעלים בלבד)"""
        try:
            user_id = str(update.effective_user.id)
            if user_id != self.super_admin_id:
                await update.message.reply_text("⚠️ פקודה זו מותרת רק לבעלים של הבוט")
                return

            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute("SELECT chat_id, mode FROM chat_settings")
            chats = c.fetchall()
            conn.close()

            if not chats:
                await update.message.reply_text("📭 הבוט אינו פעיל באף צ'אט כרגע")
                return

            # הוספת מספר הצ'אטים הפעילים
            chats_count = len(chats)
            message_parts = [f"📋 <b>רשימת צ'אטים פעילים</b> ({chats_count}):\n"]
            
            for chat_id, mode in chats:
                try:
                    chat = await context.bot.get_chat(int(chat_id))
                    chat_title = chat.title or chat.first_name or "לא ידוע"
                    message_parts.append(f"• <b>{chat_title}</b>\n  💠 מזהה: <code>{chat_id}</code>\n  ⚙️ מצב: <code>{mode}</code>\n")
                except Exception:
                    message_parts.append(f"• צ'אט לא נגיש\n  💠 מזהה: <code>{chat_id}</code>\n  ⚙️ מצב: <code>{mode}</code>\n")

            message = "\n".join(message_parts)
            await update.message.reply_text(message, parse_mode='HTML')

        except Exception as e:
            print(f"שגיאה ב-list_chats: {str(e)}")
            await update.message.reply_text("❌ אירעה שגיאה בהצגת רשימת הצ'אטים")

    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בתמונות וסרטונים"""
        temp_path = None
        try:
            message = update.effective_message
            if not message:
                return

            chat_id = str(update.effective_chat.id)
            mode = self.get_chat_mode(chat_id)
            print(f"התקבלה הודעה בצ'אט {chat_id}")
            print(f"מצב נוכחי: {mode}")

            file_id = None
            if message.photo:
                file_id = message.photo[-1].file_id
                content_type = "תמונה"
            elif message.video:
                file_id = message.video.file_id
                content_type = "סרטון"
            elif message.document and message.document.mime_type:
                if message.document.mime_type.startswith(('image/', 'video/')):
                    file_id = message.document.file_id
                    content_type = "קובץ מדיה"

            if not file_id:
                return

            # הורדת הקובץ
            file = await context.bot.get_file(file_id)
            temp_path = os.path.join(TEMP_FOLDER, f"temp_{datetime.now().timestamp()}.jpg")
            await file.download_to_drive(temp_path)

            # קטגוריות לא ראויות
            nsfw_classes = {
                'BLOCKED': [
                    'FEMALE_BREAST_EXPOSED',
                    'MALE_GENITALIA_EXPOSED',
                    'FEMALE_GENITALIA_EXPOSED',
                    'BUTTOCKS_EXPOSED',
                    'FEMALE_BREAST_COVERED',
                    'FEMALE_GENITALIA_COVERED',
                ]
            }

            result = detector.detect(temp_path)
            print(f"תוצאת זיהוי: {result}")

            # זיהוי תוכן לא ראוי
            is_nsfw = any(
                pred['score'] > 0.6 and pred['class'] in nsfw_classes['BLOCKED']
                for pred in result
            )

            if is_nsfw:
                print(f"זוהה תוכן לא ראוי ב{content_type}")
                if mode in ['warn_and_delete', 'delete_only']:
                    await message.delete()
                    print(f"הודעה נמחקה במצב: {mode}")

                if mode in ['warn_and_delete', 'warn_only']:
                    warning_msg = f"⚠️ זוהה תוכן לא ראוי ב{content_type}"
                    if mode == 'warn_and_delete':
                        warning_msg += " והתוכן הוסר."
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=warning_msg
                    )

        except Exception as e:
            print(f"שגיאה בטיפול במדיה: {str(e)}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    async def handle_channel_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בהודעות שנשלחות בערוץ"""
        try:
            channel_post = update.channel_post
            if not channel_post:
                return

            chat_id = str(update.effective_chat.id)
            print(f"התקבלה הודעה בערוץ: {chat_id}")

            # ניתוב ההודעה לפונקציית handle_media אם יש מדיה
            if channel_post.photo or channel_post.video or (channel_post.document and (channel_post.document.mime_type.startswith('image/') or channel_post.document.mime_type.startswith('video/'))):
                # יצירת אובייקט Update חדש עם channel_post במקום message
                new_update = Update(
                    update.update_id,
                    message=channel_post,
                    channel_post=channel_post,
                    effective_chat=update.effective_chat,
                    effective_user=update.effective_user
                )
                await self.handle_media(new_update, context)

        except Exception as e:
            print(f"שגיאה ב- handle_channel_post: {str(e)}")

    # הוספת פונקציה לגיבוי בסיס הנתונים
    async def backup_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """גיבוי בסיס הנתונים"""
        if str(update.effective_user.id) != self.super_admin_id:
            return
            
        try:
            import shutil
            from datetime import datetime
            
            if not os.path.exists('backup'):
                os.makedirs('backup')
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DATABASE_PATH, backup_name)
            await update.message.reply_text(f"✅ בסיס הנתונים גובה בהצלחה: {backup_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ שגיאה בגיבוי: {str(e)}")

def main():
    """הפעלת הבוט"""
    application = Application.builder().token(BOT_TOKEN).build()
    mod_bot = ModBot()

    # פקודות למשתמשים
    application.add_handler(CommandHandler('start', mod_bot.start_command))
    application.add_handler(CommandHandler('help', mod_bot.help_command))
    application.add_handler(CommandHandler('get_mode', mod_bot.get_mode_command))

    # פקודות למנהלים
    application.add_handler(CommandHandler('set_mode_for', mod_bot.set_mode_for))
    application.add_handler(CommandHandler('get_mode_for', mod_bot.get_mode_for))

    # פקודה לבעל הבוט
    application.add_handler(CommandHandler('list_chats', mod_bot.list_chats))

    # פקודה לגיבוי בסיס הנתונים
    application.add_handler(CommandHandler('backup_db', mod_bot.backup_database))

    # טיפול במדיה
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.Document.IMAGE | filters.Document.VIDEO,
        mod_bot.handle_media
    ))

    # טיפול בהודעות בערוץ
    application.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST,
        mod_bot.handle_channel_post
    ))

    print("הבוט מופעל...")
    application.run_polling()

if __name__ == '__main__':
    main()
