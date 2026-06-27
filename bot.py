import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "paakyl": {
            "projects": {},
            "subjects": [],
            "filming_dates": [],
            "tasks": {
                "تدوین": [],
                "تصویربرداری": [],
                "رنگبندی": [],
                "صدا": [],
                "انتشار": [],
                "چک‌لیست": []
            }
        },
        "ra": {
            "projects": {},
            "tasks": {
                "تدوین": [],
                "تصویربرداری": [],
                "ادیت": [],
                "تحویل": [],
                "چک‌لیست": []
            }
        }
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

(SELECTING_SECTION, SELECTING_PAAKYL_MENU, SELECTING_RA_MENU,
 SELECTING_TASK_CATEGORY, ADDING_TASK, ADDING_PROJECT,
 ADDING_SUBJECT, ADDING_DATE, SELECTING_PROJECT,
 UPDATING_PROGRESS, ADDING_CUSTOM_CATEGORY) = range(11)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 PAAKYL", callback_data="section_paakyl")],
        [InlineKeyboardButton("📢 Ra (را)", callback_data="section_ra")],
    ]
    await update.message.reply_text(
        "سلام! به بات تیم خوش اومدی 👋\nکدوم بخش؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_SECTION

async def section_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = query.data.split("_")[1]
    context.user_data["section"] = section
    if section == "paakyl":
        return await paakyl_menu(update, context)
    else:
        return await ra_menu(update, context)

async def paakyl_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📋 وظایف", callback_data="menu_tasks")],
        [InlineKeyboardButton("📁 پروژه‌ها و پیشرفت", callback_data="menu_projects")],
        [InlineKeyboardButton("🎯 لیست سوژه‌ها", callback_data="menu_subjects")],
        [InlineKeyboardButton("📅 تقویم فیلمبرداری", callback_data="menu_dates")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_start")],
    ]
    await query.edit_message_text(
        "🎬 *PAAKYL*\nچی می‌خوای؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECTING_PAAKYL_MENU

async def ra_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("📋 وظایف", callback_data="menu_tasks")],
        [InlineKeyboardButton("📁 پروژه‌ها و پیشرفت", callback_data="menu_projects")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_start")],
    ]
    await query.edit_message_text(
        "📢 *Ra (را)*\nچی می‌خوای؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECTING_RA_MENU

async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🎬 PAAKYL", callback_data="section_paakyl")],
        [InlineKeyboardButton("📢 Ra (را)", callback_data="section_ra")],
    ]
    await query.edit_message_text("کدوم بخش؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_SECTION

async def back_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section", "paakyl")
    if section == "paakyl":
        return await paakyl_menu(update, context)
    else:
        return await ra_menu(update, context)

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section")
    data = load_data()
    categories = list(data[section]["tasks"].keys())
    keyboard = []
    for cat in categories:
        count = len(data[section]["tasks"][cat])
        keyboard.append([InlineKeyboardButton(f"{cat} ({count})", callback_data=f"cat_{cat}")])
    keyboard.append([InlineKeyboardButton("➕ دسته‌بندی جدید", callback_data="add_category")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="back_section")])
    await query.edit_message_text(
        "📋 *وظایف*\nیه دسته‌بندی انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return SELECTING_TASK_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.replace("cat_", "")
    context.user_data["category"] = cat
    section = context.user_data.get("section")
    data = load_data()
    tasks = data[section]["tasks"].get(cat, [])
    text = f"📋 *{cat}*\n\n"
    if tasks:
        for i, task in enumerate(tasks, 1):
            status = "✅" if task.get("done") else "⬜"
            text += f"{status} {i}. {task['text']}\n"
            if task.get("deadline"):
                text += f"   ⏰ {task['deadline']}\n"
    else:
        text += "هنوز وظیفه‌ای نیست."
    keyboard = [
        [InlineKeyboardButton("➕ اضافه کردن وظیفه", callback_data="add_task")],
        [InlineKeyboardButton("✅ علامت زدن انجام شده", callback_data="toggle_task")],
        [InlineKeyboardButton("🗑 حذف وظیفه", callback_data="delete_task")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="menu_tasks")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SELECTING_TASK_CATEGORY

async def add_task_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("وظیفه رو بنویس:\n(می‌تونی ددلاین هم اضافه کنی، مثلاً: تدوین اپیزود ۳ | ۱۵ تیر)")
    return ADDING_TASK

async def receive_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    section = context.user_data.get("section")
    cat = context.user_data.get("category")
    data = load_data()
    parts = text.split("|")
    task = {"text": parts[0].strip(), "done": False}
    if len(parts) > 1:
        task["deadline"] = parts[1].strip()
    data[section]["tasks"][cat].append(task)
    save_data(data)
    await update.message.reply_text(f"✅ وظیفه اضافه شد به *{cat}*", parse_mode="Markdown")
    return await show_main_menu(update, context)

async def toggle_task_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section")
    cat = context.user_data.get("category")
    data = load_data()
    tasks = data[section]["tasks"].get(cat, [])
    if not tasks:
        await query.edit_message_text("وظیفه‌ای نیست.")
        return SELECTING_TASK_CATEGORY
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if task.get("done") else "⬜"
        keyboard.append([InlineKeyboardButton(f"{status} {task['text']}", callback_data=f"toggle_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"cat_{cat}")])
    await query.edit_message_text("کدوم رو علامت بزنم؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_TASK_CATEGORY

async def toggle_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("toggle_", ""))
    section = context.user_data.get("section")
    cat = context.user_data.get("category")
    data = load_data()
    data[section]["tasks"][cat][idx]["done"] = not data[section]["tasks"][cat][idx]["done"]
    save_data(data)
    return await category_selected(update, context)

async def delete_task_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section")
    cat = context.user_data.get("category")
    data = load_data()
    tasks = data[section]["tasks"].get(cat, [])
    if not tasks:
        await query.edit_message_text("وظیفه‌ای نیست.")
        return SELECTING_TASK_CATEGORY
    keyboard = []
    for i, task in enumerate(tasks):
        keyboard.append([InlineKeyboardButton(f"🗑 {task['text']}", callback_data=f"deltask_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"cat_{cat}")])
    await query.edit_message_text("کدوم رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_TASK_CATEGORY

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("deltask_", ""))
    section = context.user_data.get("section")
    cat = context.user_data.get("category")
    data = load_data()
    removed = data[section]["tasks"][cat].pop(idx)
    save_data(data)
    return await category_selected(update, context)

async def add_category_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("اسم دسته‌بندی جدید رو بنویس:")
    return ADDING_CUSTOM_CATEGORY

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_name = update.message.text.strip()
    section = context.user_data.get("section")
    data = load_data()
    if cat_name not in data[section]["tasks"]:
        data[section]["tasks"][cat_name] = []
        save_data(data)
        await update.message.reply_text(f"✅ دسته‌بندی *{cat_name}* اضافه شد", parse_mode="Markdown")
    else:
        await update.message.reply_text("این دسته‌بندی قبلاً هست.")
    return await show_main_menu(update, context)

async def projects_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section")
    data = load_data()
    projects = data[section]["projects"]
    text = "📁 *پروژه‌های در حال انجام*\n\n"
    if projects:
        for name, info in projects.items():
            progress = info.get("progress", 0)
            bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
            text += f"*{name}*\n[{bar}] {progress}%\n\n"
    else:
        text += "هنوز پروژه‌ای نیست."
    keyboard = [
        [InlineKeyboardButton("➕ پروژه جدید", callback_data="add_project")],
        [InlineKeyboardButton("📊 آپدیت پیشرفت", callback_data="update_progress")],
        [InlineKeyboardButton("🗑 حذف پروژه", callback_data="delete_project")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_section")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SELECTING_PROJECT

async def add_project_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("اسم پروژه رو بنویس:\n(مثلاً: اپیزود ۴ - صبورا)")
    return ADDING_PROJECT

async def receive_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    section = context.user_data.get("section")
    data = load_data()
    data[section]["projects"][name] = {"progress": 0, "created": str(datetime.now().date())}
    save_data(data)
    await update.message.reply_text(f"✅ پروژه *{name}* اضافه شد", parse_mode="Markdown")
    return await show_main_menu(update, context)

async def update_progress_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section")
    data = load_data()
    projects = data[section]["projects"]
    if not projects:
        await query.edit_message_text("پروژه‌ای نیست.")
        return SELECTING_PROJECT
    keyboard = []
    for name in projects:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"proj_{name}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="menu_projects")])
    await query.edit_message_text("کدوم پروژه؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return UPDATING_PROGRESS

async def project_selected_for_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    proj_name = query.data.replace("proj_", "")
    context.user_data["project"] = proj_name
    keyboard = []
    row = []
    for p in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        row.append(InlineKeyboardButton(f"{p}%", callback_data=f"progress_{p}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="update_progress")])
    await query.edit_message_text(f"پیشرفت *{proj_name}* چقدره؟", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return UPDATING_PROGRESS

async def set_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    progress = int(query.data.replace("progress_", ""))
    section = context.user_data.get("section")
    proj_name = context.user_data.get("project")
    data = load_data()
    data[section]["projects"][proj_name]["progress"] = progress
    save_data(data)
    return await projects_menu(update, context)

async def delete_project_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    section = context.user_data.get("section")
    data = load_data()
    projects = data[section]["projects"]
    if not projects:
        await query.edit_message_text("پروژه‌ای نیست.")
        return SELECTING_PROJECT
    keyboard = []
    for name in projects:
        keyboard.append([InlineKeyboardButton(f"🗑 {name}", callback_data=f"delproj_{name}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="menu_projects")])
    await query.edit_message_text("کدوم رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_PROJECT

async def delete_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    proj_name = query.data.replace("delproj_", "")
    section = context.user_data.get("section")
    data = load_data()
    del data[section]["projects"][proj_name]
    save_data(data)
    return await projects_menu(update, context)

async def subjects_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    subjects = data["paakyl"]["subjects"]
    text = "🎯 *لیست سوژه‌ها*\n\n"
    if subjects:
        for i, s in enumerate(subjects, 1):
            text += f"{i}. {s['title']}"
            if s.get("location"):
                text += f" — {s['location']}"
            text += "\n"
    else:
        text += "هنوز سوژه‌ای نیست."
    keyboard = [
        [InlineKeyboardButton("➕ سوژه جدید", callback_data="add_subject")],
        [InlineKeyboardButton("🗑 حذف سوژه", callback_data="delete_subject")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_section")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADDING_SUBJECT

async def add_subject_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("سوژه رو بنویس:\n(مثلاً: کفاش قدیمی بازار | شهسوار)")
    return ADDING_SUBJECT

async def receive_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split("|")
    subject = {"title": parts[0].strip()}
    if len(parts) > 1:
        subject["location"] = parts[1].strip()
    data = load_data()
    data["paakyl"]["subjects"].append(subject)
    save_data(data)
    await update.message.reply_text("✅ سوژه اضافه شد")
    return await show_main_menu(update, context)

async def delete_subject_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    subjects = data["paakyl"]["subjects"]
    if not subjects:
        await query.edit_message_text("سوژه‌ای نیست.")
        return ADDING_SUBJECT
    keyboard = []
    for i, s in enumerate(subjects):
        keyboard.append([InlineKeyboardButton(f"🗑 {s['title']}", callback_data=f"delsub_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="menu_subjects")])
    await query.edit_message_text("کدوم رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADDING_SUBJECT

async def delete_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("delsub_", ""))
    data = load_data()
    data["paakyl"]["subjects"].pop(idx)
    save_data(data)
    return await subjects_menu(update, context)

async def dates_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    dates = data["paakyl"]["filming_dates"]
    text = "📅 *تقویم فیلمبرداری*\n\n"
    if dates:
        for d in sorted(dates, key=lambda x: x["date"]):
            text += f"📍 {d['date']} — {d['description']}\n"
    else:
        text += "هنوز تاریخی ثبت نشده."
    keyboard = [
        [InlineKeyboardButton("➕ تاریخ جدید", callback_data="add_date")],
        [InlineKeyboardButton("🗑 حذف تاریخ", callback_data="delete_date")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_section")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ADDING_DATE

async def add_date_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("تاریخ و توضیح رو بنویس:\n(مثلاً: ۱۵ تیر | روستای صبورا)")
    return ADDING_DATE

async def receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split("|")
    entry = {"date": parts[0].strip(), "description": parts[1].strip() if len(parts) > 1 else ""}
    data = load_data()
    data["paakyl"]["filming_dates"].append(entry)
    save_data(data)
    await update.message.reply_text("✅ تاریخ فیلمبرداری ثبت شد")
    return await show_main_menu(update, context)

async def delete_date_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    dates = data["paakyl"]["filming_dates"]
    if not dates:
        await query.edit_message_text("تاریخی نیست.")
        return ADDING_DATE
    keyboard = []
    for i, d in enumerate(dates):
        keyboard.append([InlineKeyboardButton(f"🗑 {d['date']} — {d['description']}", callback_data=f"deldate_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="menu_dates")])
    await query.edit_message_text("کدوم رو حذف کنم؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADDING_DATE

async def delete_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    idx = int(query.data.replace("deldate_", ""))
    data = load_data()
    data["paakyl"]["filming_dates"].pop(idx)
    save_data(data)
    return await dates_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎬 PAAKYL", callback_data="section_paakyl")],
        [InlineKeyboardButton("📢 Ra (را)", callback_data="section_ra")],
    ]
    await update.message.reply_text("منوی اصلی:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_SECTION

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("از /start شروع کن.")

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_SECTION: [CallbackQueryHandler(section_selected, pattern="^section_")],
            SELECTING_PAAKYL_MENU: [
                CallbackQueryHandler(tasks_menu, pattern="^menu_tasks$"),
                CallbackQueryHandler(projects_menu, pattern="^menu_projects$"),
                CallbackQueryHandler(subjects_menu, pattern="^menu_subjects$"),
                CallbackQueryHandler(dates_menu, pattern="^menu_dates$"),
                CallbackQueryHandler(back_start, pattern="^back_start$"),
            ],
            SELECTING_RA_MENU: [
                CallbackQueryHandler(tasks_menu, pattern="^menu_tasks$"),
                CallbackQueryHandler(projects_menu, pattern="^menu_projects$"),
                CallbackQueryHandler(back_start, pattern="^back_start$"),
            ],
            SELECTING_TASK_CATEGORY: [
                CallbackQueryHandler(category_selected, pattern="^cat_"),
                CallbackQueryHandler(add_task_prompt, pattern="^add_task$"),
                CallbackQueryHandler(toggle_task_prompt, pattern="^toggle_task$"),
                CallbackQueryHandler(toggle_task, pattern="^toggle_\\d+$"),
                CallbackQueryHandler(delete_task_prompt, pattern="^delete_task$"),
                CallbackQueryHandler(delete_task, pattern="^deltask_"),
                CallbackQueryHandler(add_category_prompt, pattern="^add_category$"),
                CallbackQueryHandler(tasks_menu, pattern="^menu_tasks$"),
                CallbackQueryHandler(back_section, pattern="^back_section$"),
            ],
            ADDING_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task)],
            ADDING_CUSTOM_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_category)],
            SELECTING_PROJECT: [
                CallbackQueryHandler(add_project_prompt, pattern="^add_project$"),
                CallbackQueryHandler(update_progress_prompt, pattern="^update_progress$"),
                CallbackQueryHandler(delete_project_prompt, pattern="^delete_project$"),
                CallbackQueryHandler(delete_project, pattern="^delproj_"),
                CallbackQueryHandler(projects_menu, pattern="^menu_projects$"),
                CallbackQueryHandler(back_section, pattern="^back_section$"),
            ],
            ADDING_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_project)],
            UPDATING_PROGRESS: [
                CallbackQueryHandler(project_selected_for_update, pattern="^proj_"),
                CallbackQueryHandler(set_progress, pattern="^progress_"),
                CallbackQueryHandler(update_progress_prompt, pattern="^update_progress$"),
                CallbackQueryHandler(projects_menu, pattern="^menu_projects$"),
            ],
            ADDING_SUBJECT: [
                CallbackQueryHandler(add_subject_prompt, pattern="^add_subject$"),
                CallbackQueryHandler(delete_subject_prompt, pattern="^delete_subject$"),
                CallbackQueryHandler(delete_subject, pattern="^delsub_"),
                CallbackQueryHandler(subjects_menu, pattern="^menu_subjects$"),
                CallbackQueryHandler(back_section, pattern="^back_section$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_subject),
            ],
            ADDING_DATE: [
                CallbackQueryHandler(add_date_prompt, pattern="^add_date$"),
                CallbackQueryHandler(delete_date_prompt, pattern="^delete_date$"),
                CallbackQueryHandler(delete_date, pattern="^deldate_"),
                CallbackQueryHandler(dates_menu, pattern="^menu_dates$"),
                CallbackQueryHandler(back_section, pattern="^back_section$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
