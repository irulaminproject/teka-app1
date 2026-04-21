from services.supabase_db import supabase

def register_chat_handlers(bot):
    @bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'location', 'document', 'sticker'])
    def handle_chat_sync(message):
        u_id = message.from_user.id
        try:
            res = supabase.table("orders").select("*")\
                .or_(f"customer_tg_id.eq.{u_id},driver_tg_id.eq.{u_id}")\
                .eq("status", "taken")\
                .order("created_at", desc=True)\
                .limit(1).execute()

            if not res.data: return
            
            order = res.data[0]
            c_id, d_id = order.get('customer_tg_id'), order.get('driver_tg_id')

            if str(u_id) == str(c_id):
                target_id, label = d_id, "👤 *PESAN PEMBELI*"
            elif str(u_id) == str(d_id):
                target_id, label = c_id, "🛵 *PESAN KURIR*"
            else: return

            if message.content_type == 'text':
                bot.send_message(target_id, f"{label}:\n{message.text}", parse_mode="Markdown")
            elif message.content_type == 'photo':
                caption = f"{label}\n{message.caption}" if message.caption else label
                bot.send_photo(target_id, message.photo[-1].file_id, caption=caption, parse_mode="Markdown")
            elif message.content_type == 'location':
                bot.send_message(target_id, label, parse_mode="Markdown")
                bot.send_location(target_id, message.location.latitude, message.location.longitude)
            elif message.content_type == 'voice':
                bot.send_voice(target_id, message.voice.file_id, caption=label, parse_mode="Markdown")
            elif message.content_type == 'video':
                caption = f"{label}\n{message.caption}" if message.caption else label
                bot.send_video(target_id, message.video.file_id, caption=caption, parse_mode="Markdown")
            elif message.content_type == 'document':
                caption = f"{label}\n{message.caption}" if message.caption else label
                bot.send_document(target_id, message.document.file_id, caption=caption, parse_mode="Markdown")
            elif message.content_type == 'sticker':
                bot.send_message(target_id, label, parse_mode="Markdown")
                bot.send_sticker(target_id, message.sticker.file_id)

        except Exception as e:
            print(f"🚨 Error Chat: {e}")