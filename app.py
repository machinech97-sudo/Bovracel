import telebot
from telebot import types
import time
import threading
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response
import json

# --- Configuration ---

# ⚙️ बॉट टोकन (आपके द्वारा प्रदान किया गया)
# Vercel पर इसे Environment Variable के रूप में सेट करें
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7798626397:AAEJwRv5ImcwHl2et7YP7JTT0pX1CS9DThM")

# ⚠️ महत्वपूर्ण: इस ID को अपने चैनल या ग्रुप ID से बदलें।
CHANNEL_ID = -1003219682551
GROUP_ID = -5035899924 # ग्रुप ID (पिछली बार काम नहीं कर रही थी, कृपया एडमिन अनुमतियाँ जांचें)

# सभी डेस्टिनेशन ID की लिस्ट
DESTINATION_IDS = [CHANNEL_ID, GROUP_ID]

# इमेज का URL (स्थानीय फ़ाइल के बजाय) - यह केवल कोड शेड्यूलिंग के लिए डिफ़ॉल्ट इमेज के रूप में उपयोग होगा
DEFAULT_IMAGE_URL = "https://ibb.co/SXp00xPn"

# --- Bot Initialization and Data Storage ---

# बॉट को इनिशियलाइज़ करें
bot = telebot.TeleBot(BOT_TOKEN, threaded=False) # Webhook के लिए threaded=False

# डेटा स्टोरेज: यूज़र ID -> {'type': 'code'/'image', 'content': '...', 'caption': '...', 'time_to_post': 300}
# Webhook mode में, यह डेटा इन-मेमोरी रहेगा, जो Vercel पर restart होने पर खो जाएगा।
# Production के लिए, आपको Redis या Database का उपयोग करना होगा।
# अभी के लिए, हम इसे simple रखेंगे।
user_data = {}

# --- Inline Keyboard Functions (Same as before) ---

def get_main_menu():
    """मुख्य मेनू के लिए Inline Keyboard बनाता है"""
    markup = types.InlineKeyboardMarkup()
    schedule_btn = types.InlineKeyboardButton("🚀 नया कंटेंट शेड्यूल करें", callback_data='schedule')
    help_btn = types.InlineKeyboardButton("📚 सहायता", callback_data='help')
    markup.add(schedule_btn)
    markup.add(help_btn)
    return markup

def get_content_type_menu():
    """कंटेंट टाइप चयन के लिए Inline Keyboard बनाता है"""
    markup = types.InlineKeyboardMarkup()
    code_btn = types.InlineKeyboardButton("📝 कोड/टेक्स्ट", callback_data='type_code')
    image_btn = types.InlineKeyboardButton("🖼️ इमेज", callback_data='type_image')
    markup.add(code_btn, image_btn)
    return markup

# --- Countdown Logic (Same as before, but runs in a separate thread) ---

def countdown_and_post(messages_to_edit, content_type, content, caption, delay_seconds):
    """लाइव काउंटडाउन चलाता है और फिर कंटेंट पोस्ट करता है"""
    start_time = time.time()
    end_time = start_time + delay_seconds
    
    while time.time() < end_time:
        remaining_seconds = int(end_time - time.time())
        
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        
        countdown_text = f"⏳ **अगला कंटेंट आ रहा है...**\n\n"
        countdown_text += f"⏰ **बाकी समय:** `{minutes:02d}:{seconds:02d}`\n\n"
        countdown_text += "🚨 **तैयार हो जाओ!** कोड क्लेम करके स्क्रीनशॉट DM में @Marco62A को भेजो! 🚀"
        
        for chat_id, message_id in messages_to_edit:
            try:
                bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=countdown_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error editing message in {chat_id}: {e}")
                
        time.sleep(5)

    # काउंटडाउन खत्म होने के बाद, फाइनल कंटेंट पोस्ट करें
    final_text = ""
    if content_type == 'code':
        final_text = f"✅ **नया कोड आ गया है!**\n\n"
        final_text += "```\n"
        final_text += content
        final_text += "```"
    elif content_type == 'image':
        if caption:
            final_text = caption
        else:
            final_text = f"✅ **नई इमेज आ गई है!**"
    
    for chat_id, message_id in messages_to_edit:
        try:
            bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=final_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error posting final content in {chat_id}: {e}")
            if content_type == 'code':
                bot.send_photo(chat_id, DEFAULT_IMAGE_URL, caption=final_text, parse_mode='Markdown')
            elif content_type == 'image':
                bot.send_photo(chat_id, content, caption=final_text, parse_mode='Markdown')


# --- Message Handlers (Modified to be functions that take a message object) ---

def send_welcome(message):
    """/start कमांड को हैंडल करता है"""
    text = "👋 **BotifyHost.com में आपका स्वागत है!**\n\n"
    text += "मैं आपका **शेड्यूलर बॉट** हूँ। मैं आपके कोड स्निपेट या इमेज को एक लाइव काउंटडाउन के बाद आपके चैनल/ग्रुप में पोस्ट कर सकता हूँ।\n\n"
    text += "नीचे दिए गए बटन का उपयोग करके शुरू करें।"
    
    bot.send_message(
        message.chat.id, 
        text, 
        reply_markup=get_main_menu(), 
        parse_mode='Markdown'
    )

def send_help(message):
    """/help कमांड को हैंडल करता है"""
    text = "📚 **बॉट सहायता**\n\n"
    text += "उपलब्ध कमांड्स:\n"
    text += "• /start - मुख्य मेनू दिखाता है\n"
    text += "• /help - यह सहायता संदेश दिखाता है\n\n"
    text += "आप **🚀 नया कंटेंट शेड्यूल करें** बटन का उपयोग करके एक नया पोस्ट करने की प्रक्रिया शुरू कर सकते हैं।"
    
    bot.send_message(
        message.chat.id, 
        text, 
        parse_mode='Markdown'
    )

# --- Callback Query Handler (Modified to be a function that takes a call object) ---

def handle_callback_query(call):
    user_id = call.from_user.id
    
    if call.data == 'schedule':
        process_content_type_step(call.message)
        bot.answer_callback_query(call.id, "शेड्यूलिंग शुरू हो गई है।")
        
    elif call.data == 'type_code':
        msg = bot.send_message(
            call.message.chat.id, 
            "📝 **कृपया वह कोड स्निपेट या टेक्स्ट भेजें जिसे आप शेड्यूल करना चाहते हैं।**\n\n"
            "आप कोड को ```` के अंदर भेज सकते हैं ताकि फॉर्मेटिंग सही रहे।"
        )
        user_data[user_id] = {'type': 'code'}
        bot.register_next_step_handler(msg, process_code_input_step)
        bot.answer_callback_query(call.id, "कोड/टेक्स्ट शेड्यूलिंग शुरू।")

    elif call.data == 'type_image':
        msg = bot.send_message(
            call.message.chat.id, 
            "🖼️ **कृपया वह इमेज (फोटो) भेजें जिसे आप शेड्यूल करना चाहते हैं।**\n\n"
            "आप इमेज के साथ कैप्शन भी भेज सकते हैं।"
        )
        user_data[user_id] = {'type': 'image'}
        bot.register_next_step_handler(msg, process_image_input_step)
        bot.answer_callback_query(call.id, "इमेज शेड्यूलिंग शुरू।")
        
    elif call.data == 'help':
        send_help(call.message)
        bot.answer_callback_query(call.id, "सहायता संदेश दिखाया गया।")
        
    else:
        bot.answer_callback_query(call.id, "अज्ञात कमांड।")

# --- Next Step Handlers (Same as before) ---

def process_content_type_step(message):
    """यूज़र से कंटेंट टाइप (कोड/इमेज) चुनने के लिए पूछता है"""
    text = "❓ **आप क्या शेड्यूल करना चाहते हैं?**"
    bot.send_message(
        message.chat.id, 
        text, 
        reply_markup=get_content_type_menu(), 
        parse_mode='Markdown'
    )

def process_code_input_step(message):
    """यूज़र से कोड स्निपेट प्राप्त करता है और समय चयन मेनू दिखाता है"""
    user_id = message.from_user.id
    
    if user_id not in user_data or user_data[user_id].get('type') != 'code':
        bot.send_message(user_id, "❌ **त्रुटि:** कृपया /start से पुनः प्रयास करें।")
        return

    user_data[user_id]['content'] = message.text
    user_data[user_id]['caption'] = None
    
    ask_for_time(message)

def process_image_input_step(message):
    """यूज़र से इमेज प्राप्त करता है और समय चयन मेनू दिखाता है"""
    user_id = message.from_user.id
    
    if user_id not in user_data or user_data[user_id].get('type') != 'image':
        bot.send_message(user_id, "❌ **त्रुटि:** कृपया /start से पुनः प्रयास करें।")
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = message.caption if message.caption else None
        
        user_data[user_id]['content'] = file_id
        user_data[user_id]['caption'] = caption
        
        ask_for_time(message)
    else:
        msg = bot.send_message(
            user_id,
            "❌ **अवैध इनपुट!** कृपया **एक फोटो** भेजें जिसे आप शेड्यूल करना चाहते हैं।"
        )
        bot.register_next_step_handler(msg, process_image_input_step)

def ask_for_time(message):
    """समय इनपुट के लिए पूछता है और अगले स्टेप को रजिस्टर करता है"""
    text = "⏱️ **शानदार! अब कृपया मिनटों में समय दर्ज करें:**\n\n"
    text += "यह वह समय है जिसके बाद आपका कंटेंट चैनल/ग्रुप में पोस्ट हो जाएगा।\n"
    text += "*(न्यूनतम 1 मिनट, अधिकतम 60 मिनट)*"
    
    msg = bot.send_message(
        message.chat.id, 
        text, 
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_time_step)


def process_time_step(message):
    """यूज़र से कस्टम समय प्राप्त करता है, उसे वैलिडेट करता है, और शेड्यूलिंग शुरू करता है।"""
    user_id = message.from_user.id
    
    try:
        delay_minutes = int(message.text.strip())
        
        if not (1 <= delay_minutes <= 60):
            raise ValueError("Time out of range")
            
    except ValueError:
        msg = bot.send_message(
            user_id,
            "❌ **अवैध समय!** कृपया 1 से 60 के बीच एक संख्या दर्ज करें।"
        )
        bot.register_next_step_handler(msg, process_time_step)
        return

    delay_seconds = delay_minutes * 60
    
    if user_id not in user_data or 'content' not in user_data[user_id]:
        bot.send_message(user_id, "❌ **त्रुटि:** आपका कंटेंट डेटा खो गया है। कृपया /start से पुनः प्रयास करें।")
        return

    content_type = user_data[user_id]['type']
    content = user_data[user_id]['content']
    caption = user_data[user_id].get('caption')
    
    countdown_text = f"⏳ **अगला कंटेंट आ रहा है...**\n\n"
    countdown_text += f"⏰ **बाकी समय:** `{delay_minutes:02d}:00`\n\n"
    countdown_text += "🚨 **तैयार हो जाओ!** कोड क्लेम करके स्क्रीनशॉट DM में @Marco62A को भेजो! 🚀"       
    try:
        messages_to_edit = []
        
        start_markup = types.InlineKeyboardMarkup()
        start_button = types.InlineKeyboardButton("▶️ Start Bot", url=f"https://t.me/Freecodedellybot?start=schedule")
        start_markup.add(start_button)
        
        for chat_id in DESTINATION_IDS:
            try:
                if content_type == 'code':
                    sent_message = bot.send_photo(
                            chat_id, 
                            DEFAULT_IMAGE_URL, 
                            caption=countdown_text, 
                            parse_mode='Markdown',
                            reply_markup=start_markup
                        )
                elif content_type == 'image':
                    sent_message = bot.send_photo(
                            chat_id, 
                            content,
                            caption=countdown_text, 
                            parse_mode='Markdown',
                            reply_markup=start_markup
                        )
                
                messages_to_edit.append((sent_message.chat.id, sent_message.message_id))
            except Exception as e:
                error_message = f"❌ **पोस्टिंग में त्रुटि:** ID `{chat_id}` में मैसेज नहीं भेजा जा सका।\n"
                error_message += "कृपया सुनिश्चित करें कि बॉट इस चैनल/ग्रुप का **एडमिन** है और उसके पास अनुमति है।"
                bot.send_message(user_id, error_message, parse_mode='Markdown')
                print(f"Posting error in {chat_id}: {e}")

        if not messages_to_edit:
            bot.send_message(user_id, "कोई भी मैसेज सफलतापूर्वक पोस्ट नहीं हुआ।")
            return

        bot.send_message(
            user_id, 
            f"✅ **शेड्यूल सफल!**\n\n"
            f"आपका कंटेंट **{delay_minutes} मिनट** में आपके सभी डेस्टिनेशन में पोस्ट हो जाएगा।\n"
            f"लाइव काउंटडाउन शुरू हो गया है।"
        )
        
        countdown_thread = threading.Thread(
            target=countdown_and_post, 
            args=(messages_to_edit, content_type, content, caption, delay_seconds)
        )
        countdown_thread.start()
        
        del user_data[user_id]
        
    except Exception as e:
        error_message = f"❌ **अज्ञात पोस्टिंग त्रुटि:**\n\n"
        error_message += "कृपया सुनिश्चित करें कि बॉट के पास सभी आवश्यक अनुमतियाँ हैं।"
        bot.send_message(user_id, error_message, parse_mode='Markdown')
        print(f"General Posting error: {e}")


# --- Webhook Implementation with FastAPI ---

app = FastAPI()

@app.post(f"/{BOT_TOKEN}")
async def process_webhook(request: Request):
    """Telegram Webhook endpoint"""
    if request.headers.get('content-type') == 'application/json':
        json_string = await request.json()
        update = telebot.types.Update.de_json(json_string)
        
        # Process the update
        if update.message:
            message = update.message
            if message.text == '/start':
                send_welcome(message)
            elif message.text == '/help':
                send_help(message)
            else:
                # Check if there is a next step handler registered
                # Note: In a serverless environment, next_step_handlers are not reliable
                # as the process dies after the request. We will rely on the
                # telebot's internal mechanism which might work for short periods.
                # For a robust solution, state should be saved to a database.
                bot.process_new_messages([message])
        
        elif update.callback_query:
            handle_callback_query(update.callback_query)
            
        return Response(status_code=200)
    else:
        return Response(status_code=403)

@app.get("/")
def read_root():
    return {"status": "OK", "message": "Telegram Bot Webhook is running."}

# The main function is removed as FastAPI/Uvicorn will handle the serving.
# The bot.infinity_polling() is also removed.
