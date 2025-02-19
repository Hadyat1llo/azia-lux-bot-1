import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Bot tokeni
TOKEN = "7950155092:AAETDdxNCb4t0C_f5Eo0S-kKK_SivCFiC6k"
#akjdss

# Bot va Dispatcher obyektlari
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Excel fayldan mahsulotlarni yuklash funksiyasi
def load_products():
    try:
        df = pd.read_excel("C:\\Users\\user\\Downloads\\Telegram Desktop\\products.xlsx")  # Excel faylini yuklash
        products = df.to_dict(orient="records")  # Mahsulotlarni lug'atlar ro'yxatiga aylantirish
        return products
    except Exception as e:
        print(f"Excel faylni yuklashda xatolik: {e}")
        return []

# Mahsulotlarni yuklash
products = load_products()

# Foydalanuvchilarning hozirgi mahsulot indekslarini saqlash
user_product_index = {}

# Savatni saqlash uchun lug'at
user_carts = {}

# Foydalanuvchi ma'lumotlarini saqlash uchun lug'at
user_data = {}

# Miqdor kiritish uchun holatlar
class QuantityState(StatesGroup):
    waiting_for_quantity = State()
    editing_quantity = State()

# Buyurtma ma'lumotlarini so'rash uchun holatlar
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_location = State()

# Excel faylga foydalanuvchi ma'lumotlarini yozish funksiyasi
def save_user_data_to_excel(user_data):
    try:
        # Excel fayl manzili
        excel_path = "C:\\Users\\user\\Desktop\\Azia Lux Mijozlari Ma'lumotlari.xlsx"
        
        # Fayl mavjud bo'lsa, uni yuklash, aks holda yangi DataFrame yaratish
        try:
            df = pd.read_excel(excel_path)
        except FileNotFoundError:
            df = pd.DataFrame(columns=["Ism", "Telefon", "Joylashuv"])
            
        # Yangi ma'lumotlarni qo'shish
        new_data = pd.DataFrame([user_data])
        df = pd.concat([df, new_data], ignore_index=True)
        
        # Excel faylga saqlash
        df.to_excel(excel_path, index=False)
        print("Foydalanuvchi ma'lumotlari Excel fayliga saqlandi.")
    except Exception as e:
        print(f"Excel faylga yozishda xatolik: {e}")

# Mahsulotni ko'rsatish funksiyasi
async def show_product(chat_id, index, message_id=None):
    user_product_index[chat_id] = index
    product = products[index]

    caption = f"🛍 *{product['name']}*\n💰 *Narxi:* {product['price']}\n📄 *Tavsif:* {product['desc']}"

    # Inline tugmalar
    buttons = [
        [InlineKeyboardButton(text="🛒 Savatga qo‘shish", callback_data=f"add_{index}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_list")],
        [InlineKeyboardButton(text="🛒 Savatcha", callback_data="view_cart")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if message_id:
        # Agar eski xabar mavjud bo'lsa, uni o'chirib yangisini yuboramiz
        await bot.delete_message(chat_id, message_id)
    await bot.send_photo(chat_id, photo=product["image"], caption=caption, reply_markup=keyboard, parse_mode="Markdown")

# Azia Lux Maxsulotlari tugmachasi bosilganda mahsulotlar ro'yxatini ko'rsatish
async def azia_lux_products(message: types.Message):
    if not products:
        await message.answer("⚠️ Mahsulotlar topilmadi. Iltimos, keyinroq urinib ko'ring.")
        return

    # Mahsulotlar ro'yxati uchun inline tugmalar
    buttons = [
        [InlineKeyboardButton(text=product["name"], callback_data=f"product_{i}")]
        for i, product in enumerate(products)
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Rasmni yuborish
    photo_url = "https://imgur.com/a/nfFfWlR"  # Rasm URL manzili
    caption = "🫧 Azia Lux Maxsulotlari - tanlang:"
    await message.answer_photo(photo=photo_url, caption=caption, reply_markup=keyboard)

# Callback tugmalar uchun ishlov berish
async def button_handler(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    message_id = callback.message.message_id

    if callback.data.startswith("product_"):
        # Foydalanuvchi mahsulotni tanladi
        index = int(callback.data.split("_")[1])
        await show_product(chat_id, index, message_id)
    elif callback.data == "back_to_list":
        # Orqaga qaytish
        await azia_lux_products(callback.message)
    elif callback.data == "view_cart":
        # Savatchani ko'rsatish
        await show_cart(callback.message)
    elif callback.data.startswith("add_"):
        # Savatga qo'shish
        product_index = int(callback.data.split("_")[1])
        await state.update_data(product_index=product_index)
        await callback.message.answer("Miqdorni kiriting (masalan: 2):")
        await state.set_state(QuantityState.waiting_for_quantity)

    await callback.answer()

# Miqdor kiritilganda ishlov berish
async def process_quantity(message: types.Message, state: FSMContext):
    chat_id = message.chat.id  # chat_id ni aniqlash
    data = await state.get_data()
    product_index = data.get("product_index")
    quantity = message.text

    if not quantity.isdigit():
        await message.answer("⚠️ Iltimos, raqam kiriting!")
        return

    product = products[product_index]
    if chat_id not in user_carts:
        user_carts[chat_id] = []
    user_carts[chat_id].append({"product": product, "quantity": int(quantity)})

    await message.answer(f"✅ {product['name']} dan {quantity} ta savatga qo‘shildi!")

    # Yana nimadir xohlaysizmi?
    buttons = [
        [InlineKeyboardButton(text="Ha", callback_data="more_products")],
        [InlineKeyboardButton(text="Yo'q", callback_data="no_more_products")],
        [InlineKeyboardButton(text="Asosiy menyu", callback_data="main_menu")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Yana nimadir xohlaysizmi?", reply_markup=keyboard)

    await state.clear()

# Yana mahsulot xohlash tugmasi bosilganda
@dp.callback_query(F.data == "more_products")
async def more_products_handler(callback: types.CallbackQuery):
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)  # Eski xabarni o'chirish
    await azia_lux_products(callback.message)
    await callback.answer()

# Yo'q tugmasi bosilganda (buyurtma berish bo'limiga o'tkazish)
@dp.callback_query(F.data == "no_more_products")
async def no_more_products_handler(callback: types.CallbackQuery):
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)  # Eski xabarni o'chirish
    await show_cart(callback.message)
    await callback.answer()

# Asosiy menyu tugmasi bosilganda
@dp.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: types.CallbackQuery):
    await bot.delete_message(callback.message.chat.id, callback.message.message_id)  # Eski xabarni o'chirish
    await order_command(callback.message)
    await callback.answer()

# Savatni ko'rsatish
async def show_cart(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in user_carts or not user_carts[chat_id]:
        await message.answer("🛒 Savatingiz bo'sh.")
        return

    cart_text = "🛒 Savatingiz:\n"
    total = 0
    for item in user_carts[chat_id]:
        product = item["product"]
        quantity = item["quantity"]
        cart_text += f"🛍 {product['name']} - {quantity} ta\n"
        total += int(product['price'].replace(",", "").replace(" so‘m", "")) * quantity

    cart_text += f"\n💰 Jami: {total} so‘m"

    # Inline tugmalar
    buttons = [
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_list")],
        [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="place_order")],
        [InlineKeyboardButton(text="✏️ Savatni tahrirlash", callback_data="edit_cart")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(cart_text, reply_markup=keyboard)

# Savatni tahrirlash
@dp.callback_query(F.data == "edit_cart")
async def edit_cart(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in user_carts or not user_carts[chat_id]:
        await callback.message.answer("🛒 Savatingiz bo'sh.")
        return

    # Savatdagi mahsulotlarni ko'rsatish
    buttons = [
        [InlineKeyboardButton(text=f"{item['product']['name']} - {item['quantity']} ta", callback_data=f"edit_{i}")]
        for i, item in enumerate(user_carts[chat_id])
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer("Qaysi mahsulotni tahrirlamoqchisiz?", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_"))
async def edit_product(callback: types.CallbackQuery, state: FSMContext):
    try:
        chat_id = callback.message.chat.id
        # callback.data ni tekshirish va noto'g'ri formatda kelgan taqdirda xatolikni oldini olish
        if "_" not in callback.data or len(callback.data.split("_")) != 2:
            await callback.message.answer("⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            return

        product_index = int(callback.data.split("_")[1])  # Tahrirlash uchun mahsulot indeksi

        # Tahrirlash uchun tugmalar
        buttons = [ 
            [InlineKeyboardButton(text="✏️ Miqdorni o'zgartirish", callback_data=f"change_quantity_{product_index}")],
            [InlineKeyboardButton(text="🗑 Mahsulotni o'chirish", callback_data=f"remove_product_{product_index}")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_cart")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer("Tanlangan mahsulotni tahrirlash:", reply_markup=keyboard)
    except (IndexError, ValueError) as e:
        await callback.message.answer("⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
    await callback.answer()

# Miqdorni o'zgartirish
@dp.callback_query(F.data.startswith("change_quantity_"))
async def change_quantity(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    product_index = int(callback.data.split("_")[2])

    await state.update_data(product_index=product_index)
    await callback.message.answer("Yangi miqdorni kiriting:")
    await state.set_state(QuantityState.editing_quantity)
    await callback.answer()

# Miqdorni yangilash
@dp.message(QuantityState.editing_quantity)
async def update_quantity(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    data = await state.get_data()
    product_index = data.get("product_index")
    quantity = message.text

    if not quantity.isdigit():
        await message.answer("⚠️ Iltimos, raqam kiriting!")
        return

    user_carts[chat_id][product_index]["quantity"] = int(quantity)
    await message.answer(f"✅ Miqdor muvaffaqiyatli yangilandi!")
    await state.clear()
    await show_cart(message)

# Mahsulotni o'chirish
@dp.callback_query(F.data.startswith("remove_product_"))
async def remove_product(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    product_index = int(callback.data.split("_")[2])

    removed_product = user_carts[chat_id].pop(product_index)
    await callback.message.answer(f"✅ {removed_product['product']['name']} savatdan o'chirildi!")
    await show_cart(callback.message)
    await callback.answer()

# Orqaga qaytish (savatga)
@dp.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: types.CallbackQuery):
    await show_cart(callback.message)
    await callback.answer()

# Buyurtma berish tugmasi bosilganda
@dp.callback_query(F.data == "place_order")
async def place_order(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    if chat_id in user_data:
        # Foydalanuvchi ma'lumotlari mavjud
        data = user_data[chat_id]
        name = data.get("name")
        phone = data.get("phone")
        location = data.get("location")

        # Ma'lumotlarni ko'rsatish va tasdiqlash/tahrirlash tugmalari
        buttons = [
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order")],
            [InlineKeyboardButton(text="✏️ Ma'lumotlarni tahrirlash", callback_data="edit_user_data")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer(
            f"Foydalanuvchi ma'lumotlari:\n👤 Ism: {name}\n📞 Telefon: {phone}\n📍 Joylashuv: {location}\n\nBuyurtmani tasdiqlaysizmi yoki ma'lumotlarni tahrirlamoqchimisiz?",
            reply_markup=keyboard
        )
    else:
        # Foydalanuvchi ma'lumotlari mavjud emas
        await callback.message.answer("Ismingizni kiriting:")
        await state.set_state(OrderState.waiting_for_name)
    await callback.answer()

async def send_order_to_channel(chat_id):
    if chat_id not in user_carts or not user_carts[chat_id]:
        return

    cart_text = "🛒 Yangi buyurtma:\n"
    total = 0
    for item in user_carts[chat_id]:
        product = item["product"]
        quantity = item["quantity"]
        cart_text += f"🛍 {product['name']} - {quantity} ta\n"
        total += int(product['price'].replace(",", "").replace(" so‘m", "")) * quantity

    cart_text += f"\n💰 Jami: {total} so‘m"

    # Foydalanuvchi ma'lumotlari
    user_info = user_data.get(chat_id, {})
    name = user_info.get("name", "Noma'lum")
    phone = user_info.get("phone", "Noma'lum")
    location = user_info.get("location", "Noma'lum")

    cart_text += f"\n\n👤 Foydalanuvchi ma'lumotlari:\nIsm: {name}\nTelefon: {phone}\nJoylashuv: {location}"

    # Kanalga yuborish
    channel_id = "@azia_lux_orders"  # Kanal username
    await bot.send_message(channel_id, cart_text)

def clear_cart(chat_id):
    if chat_id in user_carts:
        user_carts[chat_id] = []

@dp.callback_query(F.data == "confirm_order")
async def confirm_order(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id in user_data:
        data = user_data[chat_id]
        name = data.get("name")
        phone = data.get("phone")
        location = data.get("location")

        # Buyurtma ma'lumotlarini Excel faylga saqlash
        save_user_data_to_excel({"Ism": name, "Telefon": phone, "Joylashuv": location})

        # Buyurtma ma'lumotlarini kanalga yuborish
        await send_order_to_channel(chat_id)

        # Savatni tozalash
        clear_cart(chat_id)

        await callback.message.answer(
            "✅ Buyurtmangiz qabul qilindi! Xaridingizdan mamnunmiz. Siz bilan menedjerlarimiz bog'lanishadi."
        )
    else:
        await callback.message.answer("⚠️ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
    await callback.answer()

# Tasdiqlash tugmasi bosilganda 

# Ma'lumotlarni tahrirlash tugmasi bosilganda
@dp.callback_query(F.data == "edit_user_data")
async def edit_user_data(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Ismingizni kiriting:")
    await state.set_state(OrderState.waiting_for_name)
    await callback.answer()

# Ismni qabul qilish
@dp.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Telefon raqamingizni kiriting (masalan: +998901234567 yoki 901234567):")
    await state.set_state(OrderState.waiting_for_phone)

# Telefon raqamini qabul qilish va tekshirish
@dp.message(OrderState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    if (phone.startswith("+998") and len(phone) == 13) or (phone.isdigit() and len(phone) == 9):
        await state.update_data(phone=phone)
        await message.answer("Joylashuvingizni kiriting (masalan: Toshkent shahar, Yunusobod tumani):")
        await state.set_state(OrderState.waiting_for_location)
    else:
        await message.answer("⚠️ Iltimos, telefon raqamingizni to'g'ri kiriting (masalan: +998901234567 yoki 901234567):")

# Joylashuvni qabul qilish va ma'lumotlarni saqlash
@dp.message(OrderState.waiting_for_location)
async def process_location(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    await state.update_data(location=message.text)
    data = await state.get_data()
    user_data[chat_id] = data  # Foydalanuvchi ma'lumotlarini saqlash

    # Ma'lumotlarni ko'rsatish va tasdiqlash/tahrirlash tugmalari
    buttons = [
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order")],
        [InlineKeyboardButton(text="✏️ Ma'lumotlarni tahrirlash", callback_data="edit_user_data")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"Foydalanuvchi ma'lumotlari:\n👤 Ism: {data['name']}\n📞 Telefon: {data['phone']}\n📍 Joylashuv: {data['location']}\n\nBuyurtmani tasdiqlaysizmi yoki ma'lumotlarni tahrirlamoqchimisiz?",
        reply_markup=keyboard
    )
    await state.clear()

# Asosiy menyu
menu_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Buyurtma berish")],
        [KeyboardButton(text="🛒 Savatcha")],
        [KeyboardButton(text="ℹ️ Biz haqimizda")],
        [KeyboardButton(text="📑 Buyurtmalarim")],
        [KeyboardButton(text="🏢 Filiallar")],
        [KeyboardButton(text="✍️ Fikr bildirish")],
        [KeyboardButton(text="⚙️ Sozlamalar")]
    ],
    resize_keyboard=True
)

# Buyurtma bo'limi uchun klaviatura
order_buttons = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🫧 Azia Lux Maxsulotlari")],
        [KeyboardButton(text="🥞 Oziq-ovqat")],
        [KeyboardButton(text="🧼 Parfumeriya")],
        [KeyboardButton(text="🍻 Ichimliklar")],
        [KeyboardButton(text="🔙 Ortga")]
    ],
    resize_keyboard=True
)

# /start komandasi
async def start_command(message: types.Message):
    await message.answer("Xush kelibsiz!", reply_markup=menu_buttons)

# Buyurtma bo'limi
async def order_command(message: types.Message):
    await message.answer("Buyurtma turini tanlang:", reply_markup=order_buttons)

# Savatchani ko'rsatish
async def cart_command(message: types.Message):
    await show_cart(message)

# Ortga qaytish
async def back_to_menu(message: types.Message):
    await message.answer("Asosiy menyuga qaytdingiz.", reply_markup=menu_buttons)

# Handlerni ro'yxatdan o'tkazish
dp.message.register(start_command, Command("start"))
dp.message.register(order_command, F.text == "📦 Buyurtma berish")
dp.message.register(cart_command, F.text == "🛒 Savatcha")
dp.message.register(azia_lux_products, F.text == "🫧 Azia Lux Maxsulotlari")
dp.message.register(back_to_menu, F.text == "🔙 Ortga")
dp.callback_query.register(button_handler)  # Callback tugmalar uchun
dp.callback_query.register(more_products_handler, F.data == "more_products")  # Ha tugmasi uchun
dp.callback_query.register(no_more_products_handler, F.data == "no_more_products")  # Yo'q tugmasi uchun
dp.callback_query.register(main_menu_handler, F.data == "main_menu")  # Asosiy menyu tugmasi uchun
dp.callback_query.register(edit_cart, F.data == "edit_cart")  # Savatni tahrirlash uchun
dp.callback_query.register(edit_product, F.data.startswith("edit_"))  # Mahsulotni tahrirlash uchun
dp.callback_query.register(change_quantity, F.data.startswith("change_quantity_"))  # Miqdorni o'zgartirish uchun
dp.callback_query.register(remove_product, F.data.startswith("remove_product_"))  # Mahsulotni o'chirish uchun
dp.callback_query.register(back_to_cart, F.data == "back_to_cart")  # Savatga qaytish uchun
dp.callback_query.register(place_order, F.data == "place_order")  # Buyurtma berish uchun
dp.callback_query.register(confirm_order, F.data == "confirm_order")  # Tasdiqlash tugmasi uchun
dp.callback_query.register(edit_user_data, F.data == "edit_user_data")  # Ma'lumotlarni tahrirlash tugmasi uchun
dp.message.register(process_quantity, QuantityState.waiting_for_quantity)  # Miqdor kiritish uchun
dp.message.register(update_quantity, QuantityState.editing_quantity)  # Miqdorni yangilash uchun
dp.message.register(process_name, OrderState.waiting_for_name)  # Ismni qabul qilish uchun
dp.message.register(process_phone, OrderState.waiting_for_phone)  # Telefon raqamini qabul qilish uchun
dp.message.register(process_location, OrderState.waiting_for_location)  # Joylashuvni qabul qilish uchun

# Asosiy funksiya
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Botni ishga tushirish
if __name__ == "__main__":
    asyncio.run(main()) 