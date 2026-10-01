import nest_asyncio
import asyncio
import sqlite3
import json

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

nest_asyncio.apply()


# =========================================================
# SETTINGS
# =========================================================

import os
TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 1612260431

DB_NAME = "epsf_bot.db"


# =========================================================
# EVENTS
# =========================================================

EVENTS = {
    "recruitment": "🎯 Recruitment",
    "blood": "🩸 Blood Donation",
    "sep": "🌱 SEP",
    "pink": "🎀 Pink October",
    "symposium": "🎤 Symposium",
    "step": "🚶 Step on the Way",
    "phocus": "🔬 PHocus",
    "sessions": "📚 Sessions",
    "workshop": "🛠️ Workshop"
}


# =========================================================
# DATABASE
# =========================================================

def get_db():
    return sqlite3.connect(DB_NAME)


def setup_database():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            pdf_file_id TEXT,
            created_by INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS idea_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            file_id TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tutorials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL
        )
    """)

    db.commit()
    db.close()


# =========================================================
# HELPERS
# =========================================================

def is_admin(user_id):
    return user_id == ADMIN_ID


def main_menu_keyboard():

    buttons = []

    for key, name in EVENTS.items():

        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data=f"event_{key}"
            )
        ])

    return InlineKeyboardMarkup(buttons)


def event_keyboard(event):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💡 Ideas",
                callback_data=f"ideas_{event}"
            )
        ],
        [
            InlineKeyboardButton(
                "🎥 Tutorials / Videos",
                callback_data=f"tutorials_{event}"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back_main"
            )
        ]
    ])


def admin_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Idea",
                callback_data="admin_add_idea"
            )
        ],
        [
            InlineKeyboardButton(
                "🎥 Add Tutorial",
                callback_data="admin_add_tutorial"
            )
        ],
        [
            InlineKeyboardButton(
                "👁️ View Content",
                callback_data="admin_view"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Delete Content",
                callback_data="admin_delete"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Main Menu",
                callback_data="back_main"
            )
        ]
    ])


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "🌟 *Welcome to EPSF-Alex Bot!*\n\n"
        "Choose an event:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


# =========================================================
# ADMIN COMMAND
# =========================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):

        await update.message.reply_text(
            "❌ You don't have permission to access the Admin Panel."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ *Admin Panel*\n\nChoose an action:",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown"
    )


# =========================================================
# EVENT
# =========================================================

async def event_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    event = query.data.replace("event_", "")

    await query.edit_message_text(
        f"{EVENTS[event]}\n\nChoose what you want to see:",
        reply_markup=event_keyboard(event)
    )


# =========================================================
# SHOW IDEAS
# =========================================================

async def show_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    event = query.data.replace("ideas_", "")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, title, description, pdf_file_id
        FROM ideas
        WHERE event=?
        ORDER BY id DESC
    """, (event,))

    ideas = cursor.fetchall()

    for idea_id, title, description, pdf_file_id in ideas:

        cursor.execute("""
            SELECT file_id
            FROM idea_images
            WHERE idea_id=?
            ORDER BY id
        """, (idea_id,))

        images = [row[0] for row in cursor.fetchall()]

        # -------------------------
        # SEND IMAGES
        # -------------------------

        if images:

            media = [
                InputMediaPhoto(media=file_id)
                for file_id in images[:10]
            ]

            try:
                await query.message.reply_media_group(
                    media=media
                )
            except Exception as e:
                print("Image error:", e)

        # -------------------------
        # SEND PDF
        # -------------------------

        if pdf_file_id:

            try:
                await query.message.reply_document(
                    document=pdf_file_id
                )
            except Exception as e:
                print("PDF error:", e)

        # -------------------------
        # SEND IDEA INFO
        # -------------------------

        text = f"💡 *{title}*"

        if description:
            text += f"\n\n📝 {description}"

        await query.message.reply_text(
            text,
            parse_mode="Markdown"
        )

    db.close()

    if not ideas:

        await query.message.reply_text(
            "💡 No ideas have been added yet."
        )

    await query.message.reply_text(
        "Choose another option:",
        reply_markup=event_keyboard(event)
    )


# =========================================================
# SHOW TUTORIALS
# =========================================================

async def show_tutorials(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    event = query.data.replace("tutorials_", "")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT title, link
        FROM tutorials
        WHERE event=?
        ORDER BY id DESC
    """, (event,))

    tutorials = cursor.fetchall()

    db.close()

    if not tutorials:

        await query.message.reply_text(
            "🎥 No tutorials have been added yet."
        )

    else:

        for title, link in tutorials:

            await query.message.reply_text(
                f"🎥 *{title}*\n\n{link}",
                parse_mode="Markdown"
            )

    await query.message.reply_text(
        "Choose another option:",
        reply_markup=event_keyboard(event)
    )


# =========================================================
# ADMIN ADD IDEA
# =========================================================

async def admin_add_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    context.user_data.clear()

    buttons = []

    for key, name in EVENTS.items():

        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data=f"addidea_event_{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data="admin_cancel"
        )
    ])

    await query.edit_message_text(
        "➕ *Add New Idea*\n\n"
        "Choose the event:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


# =========================================================
# CHOOSE IDEA EVENT
# =========================================================

async def choose_idea_event(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    event = query.data.replace("addidea_event_", "")

    context.user_data["event"] = event
    context.user_data["step"] = "idea_title"
    context.user_data["photos"] = []
    context.user_data["pdf"] = None

    await query.edit_message_text(
        f"➕ Adding an idea to:\n\n"
        f"{EVENTS[event]}\n\n"
        "✏️ Send the *title* of the idea.",
        parse_mode="Markdown"
    )


# =========================================================
# ADMIN ADD TUTORIAL
# =========================================================

async def admin_add_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    context.user_data.clear()

    buttons = []

    for key, name in EVENTS.items():

        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data=f"addtutorial_event_{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "❌ Cancel",
            callback_data="admin_cancel"
        )
    ])

    await query.edit_message_text(
        "🎥 *Add Tutorial / Video*\n\n"
        "Choose the event:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


# =========================================================
# CHOOSE TUTORIAL EVENT
# =========================================================

async def choose_tutorial_event(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    event = query.data.replace("addtutorial_event_", "")

    context.user_data["event"] = event
    context.user_data["step"] = "tutorial_title"

    await query.edit_message_text(
        f"🎥 Adding tutorial to:\n\n"
        f"{EVENTS[event]}\n\n"
        "✏️ Send the *title* of the tutorial.",
        parse_mode="Markdown"
    )


# =========================================================
# ADMIN TEXT HANDLER
# =========================================================

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    step = context.user_data.get("step")

    text = update.message.text.strip()

    # =====================================================
    # IDEA TITLE
    # =====================================================

    if step == "idea_title":

        context.user_data["idea_title"] = text
        context.user_data["step"] = "idea_photos"

        await update.message.reply_text(
            "📸 *Images*\n\n"
            "Send one or more images.\n\n"
            "When you're finished, press *✅ Done Images*.\n\n"
            "Then we'll move to the PDF.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Done Images",
                        callback_data="idea_images_done"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data="admin_cancel"
                    )
                ]
            ]),
            parse_mode="Markdown"
        )

        return

    # =====================================================
    # IDEA DESCRIPTION
    # =====================================================

    if step == "idea_description":

        event = context.user_data["event"]
        title = context.user_data["idea_title"]
        description = text
        photos = context.user_data.get("photos", [])
        pdf_file_id = context.user_data.get("pdf")

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO ideas
            (event, title, description, pdf_file_id, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event,
            title,
            description,
            pdf_file_id,
            update.effective_user.id
        ))

        idea_id = cursor.lastrowid

        for file_id in photos:

            cursor.execute("""
                INSERT INTO idea_images
                (idea_id, file_id)
                VALUES (?, ?)
            """, (idea_id, file_id))

        db.commit()
        db.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ *Idea added successfully!*\n\n"
            f"💡 {title}\n"
            f"🖼️ Images: {len(photos)}\n"
            f"📄 PDF: {'Yes' if pdf_file_id else 'No'}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⚙️ Admin Panel",
                        callback_data="admin_panel"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="back_main"
                    )
                ]
            ]),
            parse_mode="Markdown"
        )

        return

    # =====================================================
    # TUTORIAL TITLE
    # =====================================================

    if step == "tutorial_title":

        context.user_data["tutorial_title"] = text
        context.user_data["step"] = "tutorial_link"

        await update.message.reply_text(
            "🔗 Now send the tutorial/video link."
        )

        return

    # =====================================================
    # TUTORIAL LINK
    # =====================================================

    if step == "tutorial_link":

        event = context.user_data["event"]
        title = context.user_data["tutorial_title"]
        link = text

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO tutorials
            (event, title, link)
            VALUES (?, ?, ?)
        """, (event, title, link))

        db.commit()
        db.close()

        context.user_data.clear()

        await update.message.reply_text(
            "✅ *Tutorial added successfully!*",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⚙️ Admin Panel",
                        callback_data="admin_panel"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="back_main"
                    )
                ]
            ]),
            parse_mode="Markdown"
        )

        return


# =========================================================
# ADMIN PHOTO HANDLER
# =========================================================

async def admin_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if context.user_data.get("step") != "idea_photos":
        return

    photo = update.message.photo[-1]

    context.user_data.setdefault(
        "photos",
        []
    ).append(photo.file_id)

    count = len(context.user_data["photos"])

    await update.message.reply_text(
        f"📸 Image {count} added!\n\n"
        "Send another image or press *✅ Done Images*.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Done Images",
                    callback_data="idea_images_done"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="admin_cancel"
                )
            ]
        ]),
        parse_mode="Markdown"
    )


# =========================================================
# DONE IMAGES
# =========================================================

async def idea_images_done(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    photos = context.user_data.get("photos", [])

    if not photos:

        await query.answer(
            "Send at least one image first 📸",
            show_alert=True
        )

        return

    context.user_data["step"] = "idea_pdf"

    await query.edit_message_text(
        "📄 *PDF*\n\n"
        "If this idea has a PDF, send it now.\n\n"
        "If you don't want to add a PDF, press:\n"
        "➡️ *Skip PDF*",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "➡️ Skip PDF",
                    callback_data="skip_pdf"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="admin_cancel"
                )
            ]
        ]),
        parse_mode="Markdown"
    )


# =========================================================
# PDF HANDLER
# =========================================================

async def admin_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if context.user_data.get("step") != "idea_pdf":
        return

    document = update.message.document

    if document.mime_type != "application/pdf":

        await update.message.reply_text(
            "❌ Please send a PDF file."
        )

        return

    context.user_data["pdf"] = document.file_id
    context.user_data["step"] = "idea_description"

    await update.message.reply_text(
        "📄 PDF added successfully! ✅\n\n"
        "📝 Now send the *description* of the idea.",
        parse_mode="Markdown"
    )


# =========================================================
# SKIP PDF
# =========================================================

async def skip_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    context.user_data["pdf"] = None
    context.user_data["step"] = "idea_description"

    await query.edit_message_text(
        "👍 No PDF added.\n\n"
        "📝 Now send the *description* of the idea.",
        parse_mode="Markdown"
    )


# =========================================================
# VIEW CONTENT
# =========================================================

async def admin_view(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    buttons = []

    for key, name in EVENTS.items():

        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data=f"view_event_{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Admin Panel",
            callback_data="admin_panel"
        )
    ])

    await query.edit_message_text(
        "👁️ *View Content*\n\nChoose an event:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def view_event(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    event = query.data.replace("view_event_", "")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, title, pdf_file_id
        FROM ideas
        WHERE event=?
    """, (event,))

    ideas = cursor.fetchall()

    cursor.execute("""
        SELECT id, title, link
        FROM tutorials
        WHERE event=?
    """, (event,))

    tutorials = cursor.fetchall()

    db.close()

    text = f"📂 *{EVENTS[event]}*\n\n"

    text += "💡 *Ideas:*\n"

    if ideas:

        for idea_id, title, pdf_file_id in ideas:

            pdf = "📄 PDF" if pdf_file_id else "No PDF"

            text += f"• #{idea_id} — {title} ({pdf})\n"

    else:

        text += "No ideas.\n"

    text += "\n🎥 *Tutorials:*\n"

    if tutorials:

        for tutorial_id, title, link in tutorials:

            text += f"• #{tutorial_id} — {title}\n"

    else:

        text += "No tutorials.\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Admin Panel",
                    callback_data="admin_panel"
                )
            ]
        ]),
        parse_mode="Markdown"
    )


# =========================================================
# DELETE
# =========================================================

async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    buttons = []

    for key, name in EVENTS.items():

        buttons.append([
            InlineKeyboardButton(
                name,
                callback_data=f"delete_event_{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Admin Panel",
            callback_data="admin_panel"
        )
    ])

    await query.edit_message_text(
        "🗑️ *Delete Content*\n\nChoose an event:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    event = query.data.replace("delete_event_", "")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT id, title
        FROM ideas
        WHERE event=?
    """, (event,))

    ideas = cursor.fetchall()

    cursor.execute("""
        SELECT id, title
        FROM tutorials
        WHERE event=?
    """, (event,))

    tutorials = cursor.fetchall()

    db.close()

    buttons = []

    for idea_id, title in ideas:

        buttons.append([
            InlineKeyboardButton(
                f"💡 {title}",
                callback_data=f"delete_idea_{idea_id}"
            )
        ])

    for tutorial_id, title in tutorials:

        buttons.append([
            InlineKeyboardButton(
                f"🎥 {title}",
                callback_data=f"delete_tutorial_{tutorial_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Admin Panel",
            callback_data="admin_panel"
        )
    ])

    if not ideas and not tutorials:

        await query.edit_message_text(
            "Nothing to delete in this event.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        return

    await query.edit_message_text(
        f"🗑️ *{EVENTS[event]}*\n\n"
        "Choose the content to delete:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def delete_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    idea_id = int(
        query.data.replace("delete_idea_", "")
    )

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM idea_images WHERE idea_id=?",
        (idea_id,)
    )

    cursor.execute(
        "DELETE FROM ideas WHERE id=?",
        (idea_id,)
    )

    db.commit()
    db.close()

    await query.edit_message_text(
        "✅ Idea deleted successfully.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⚙️ Admin Panel",
                    callback_data="admin_panel"
                )
            ]
        ])
    )


async def delete_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    tutorial_id = int(
        query.data.replace("delete_tutorial_", "")
    )

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM tutorials WHERE id=?",
        (tutorial_id,)
    )

    db.commit()
    db.close()

    await query.edit_message_text(
        "✅ Tutorial deleted successfully.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⚙️ Admin Panel",
                    callback_data="admin_panel"
                )
            ]
        ])
    )


# =========================================================
# ADMIN PANEL
# =========================================================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    context.user_data.clear()

    await query.edit_message_text(
        "⚙️ *Admin Panel*\n\nChoose an action:",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown"
    )


# =========================================================
# CANCEL
# =========================================================

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        return

    context.user_data.clear()

    await query.edit_message_text(
        "❌ Cancelled.",
        reply_markup=admin_keyboard()
    )


# =========================================================
# BACK MAIN
# =========================================================

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "🌟 *EPSF-Alex Bot*\n\nChoose an event:",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


# =========================================================
# ERROR
# =========================================================

async def error_handler(update, context):

    print("ERROR:", context.error)


# =========================================================
# RUN BOT
# =========================================================

async def run_bot():

    setup_database()

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("admin", admin_command)
    )

    # Main menu
    app.add_handler(
        CallbackQueryHandler(
            event_selected,
            pattern=r"^event_"
        )
    )

    # Public content
    app.add_handler(
        CallbackQueryHandler(
            show_ideas,
            pattern=r"^ideas_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            show_tutorials,
            pattern=r"^tutorials_"
        )
    )

    # Admin - Add
    app.add_handler(
        CallbackQueryHandler(
            admin_add_idea,
            pattern=r"^admin_add_idea$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            choose_idea_event,
            pattern=r"^addidea_event_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_add_tutorial,
            pattern=r"^admin_add_tutorial$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            choose_tutorial_event,
            pattern=r"^addtutorial_event_"
        )
    )

    # Idea images
    app.add_handler(
        CallbackQueryHandler(
            idea_images_done,
            pattern=r"^idea_images_done$"
        )
    )

    # PDF
    app.add_handler(
        CallbackQueryHandler(
            skip_pdf,
            pattern=r"^skip_pdf$"
        )
    )

    # View
    app.add_handler(
        CallbackQueryHandler(
            admin_view,
            pattern=r"^admin_view$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            view_event,
            pattern=r"^view_event_"
        )
    )

    # Delete
    app.add_handler(
        CallbackQueryHandler(
            admin_delete,
            pattern=r"^admin_delete$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_event,
            pattern=r"^delete_event_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_idea,
            pattern=r"^delete_idea_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            delete_tutorial,
            pattern=r"^delete_tutorial_"
        )
    )

    # Admin panel
    app.add_handler(
        CallbackQueryHandler(
            admin_panel,
            pattern=r"^admin_panel$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            admin_cancel,
            pattern=r"^admin_cancel$"
        )
    )

    # Back
    app.add_handler(
        CallbackQueryHandler(
            back_main,
            pattern=r"^back_main$"
        )
    )

    # Photos
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            admin_photo_handler
        )
    )

    # PDF documents
    app.add_handler(
        MessageHandler(
            filters.Document.PDF,
            admin_document_handler
        )
    )

    # Text
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            admin_text_handler
        )
    )

    app.add_error_handler(error_handler)

    # Start
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    print("✅ EPSF-Alex Bot is running!")

    while True:
        await asyncio.sleep(3600)


asyncio.run(run_bot())
