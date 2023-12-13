#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os
from difflib import get_close_matches

import sentry_sdk
from constants import CATEGORIES, STATES, SUBCATEGORIES
from constants import PLACES as ALL_PLACES
from dotenv import load_dotenv
from query import Ejare, Metrazh, Price, Query, Vadie
from state import Place
from telegram import ReplyKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    PicklePersistence,
    Updater,
)
from watchdog import Watchdog

load_dotenv()

sentry_sdk.init(
    os.getenv('SENTRY_DNS')
)

TOKEN = os.getenv('TOKEN')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

(
    STATE,
    DISPATCHER,
    DELETE,
    METRAZH_FROM,
    METRAZH_TO,
    VADIE_FROM,
    VADIE_TO,
    EJARE_FROM,
    EJARE_TO,
    PLACES,
    ATRAF,
    WATCHDOG,
    CATEGORY,
    SUBCATEGORY,
    PRICE_FROM,
    PRICE_TO,
    SEARCH,
) = range(17)

SKIP = 'بعدی'
YES = 'بله'
NO = 'نه'
INT_FAIL = 'مشکلی پیش اومده! لطفا یک عدد وارد کنید\n'
NEW_DOG_CMD = 'ساخت نگهبان جدید'
DELETE_CMD = 'حذف'
CANCEL = 'لغو'
DONE = 'پایان'
ALL = 'همه'


DEFAULT_OPTIONS = [CANCEL, DONE, SKIP]


def divide_chunks(l, n):
    res = []
    l = list(l)
    for i in range(0, len(l), n):
        res.append(l[i:i + n])

    return res


def find_state_by_name(name):
    for state in STATES:
        if state.name == name:
            return state

    return None


def check_jobs(job_queue, wds):
    for wd in wds:
        job = job_queue.get_jobs_by_name(wd.job_name)
        if len(job) == 0:
            wd.start_job(job_queue)


def start(update, context):
    context.user_data['query'] = None
    if 'watchdogs' not in context.user_data:
        context.user_data['watchdogs'] = []

    reply_keyboard = [[
        NEW_DOG_CMD,
        DELETE_CMD
    ]]

    update.message.reply_text(
        'شما میتونید نگهبان جدیدی بسازید یا نگهبان‌'
        'های قبلیتونو مدیریت کنید\n',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return DISPATCHER


def dispatcher(update, context):
    text = update.message.text
    if text == NEW_DOG_CMD:
        return new_dog(update, context)
    elif text == DELETE_CMD:
        if not context.user_data['watchdogs'] \
                or len(context.user_data['watchdogs']) == 0:
            return start(update, context)
        return delete_msg(update, context)


def delete_msg(update, context):
    reply_keyboard = [
        [CANCEL],
        *divide_chunks([str(wd) for wd in context.user_data['watchdogs']], 2),
    ]
    update.message.reply_text(
        'یکی از نگهبان‌های زیر را انتخاب کنید',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return DELETE


def delete(update, context):
    wds = context.user_data['watchdogs']
    text = update.message.text

    if text == CANCEL:
        return start(update, context)

    for i, wd_ in enumerate(wds):
        if str(wd_) == text:
            job = context.job_queue.get_jobs_by_name(wd_.job_name)[0]
            job.schedule_removal()
            del wds[i]
            break

    return start(update, context)


def new_dog(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)

    reply_keyboard = [[CANCEL] + [state.name for state in STATES]]

    update.message.reply_text(
        'کجا؟',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return STATE


def state(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)

    state = find_state_by_name(text)
    context.user_data['query'] = Query(state=state)

    update.message.reply_text(
        'جستجوی عبارت', reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )
    return SEARCH


def search(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)

    context.user_data['query'].search = text
    divided_categories = [chunk for chunk in divide_chunks(CATEGORIES.keys(), 2)]
    reply_keyboard = [*divided_categories, [CANCEL, DONE, ALL]]
    update.message.reply_text(
        'دسته‌بندی', reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CATEGORY


def category(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)
    elif text == ALL:
        update.message.reply_text(
            'محله‌هایی که باید نگهبانی بدم رو پشت‌سرهم'
            'و با یک فاصله وارد کنید',
            reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
        )
        return PLACES

    category = CATEGORIES.get(text, None)
    if not category:
        update.message.reply_text(
            f'دسته‌بندی {text} وجود ندارد!'
        )
        return CATEGORY

    context.user_data['query'].category = category
    sub_categories = SUBCATEGORIES.get(category, None)
    if not sub_categories:
        update.message.reply_text(
            'محله‌هایی که باید نگهبانی بدم رو پشت‌سرهم'
            'و با یک فاصله وارد کنید',
            reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
        )
        return PLACES

    divided_sub_categories = [
        chunk for chunk in divide_chunks(sub_categories.keys(), 2)
    ]
    reply_keyboard = [*divided_sub_categories, [CANCEL, DONE, ALL]]
    update.message.reply_text(
        'دسته‌بندی دقیق‌تر؟',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return SUBCATEGORY


def sub_category(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)
    elif text == ALL:
        update.message.reply_text(
            'محله‌هایی که باید نگهبانی بدم رو پشت‌سرهم'
            'و با یک فاصله وارد کنید',
            reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
        )
        return PLACES

    category = context.user_data['query'].category
    sub_category = SUBCATEGORIES[category][text]
    context.user_data['query'].sub_category = sub_category
    query = context.user_data['query']
    print(query.url)

    update.message.reply_text(
        'محله‌هایی که باید نگهبانی بدم رو پشت‌سرهم'
        'و با یک فاصله وارد کنید',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )
    return PLACES


def places(update, context):
    query = context.user_data['query']
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        input_places = text.split()
        places = []
        for input_place in input_places:
            place_names = get_close_matches(input_place, ALL_PLACES.keys())
            if len(place_names) == 0:
                continue
            place_name = place_names[0]
            places.append(Place(name=place_name, code=ALL_PLACES[place_name]))

        query.places = places

        print(query.url)
        update.message.reply_text(
            'محله‌های اطراف رو هم نگهبانی بدم؟',
            reply_markup=ReplyKeyboardMarkup([[YES, NO], [CANCEL]])
        )
        return ATRAF

    return atraf(update, context)



def atraf(update, context):
    query = context.user_data['query']
    text = update.message.text
    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)
    elif text != SKIP:
        if text == YES:
            query.near = True
        else:
            query.near = False

    print(query.url)

    if query.category == 'املاک-مسکن/':
        update.message.reply_text(
            'متراژ از؟',
            reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
        )
        return METRAZH_FROM

    update.message.reply_text(
        'قیمت از؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )
    return PRICE_FROM


def price_from(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            from_ = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return PRICE_FROM

        price = Price(from_=from_)
        context.user_data['query'].fields.append(price)

    query = context.user_data['query']
    print(query.url)
    update.message.reply_text(
        'قیمت تا؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )

    return PRICE_TO


def price_to(update, context):
    query = context.user_data['query']
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            to = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return PRICE_TO

        if query.price:
            query.price.to = to
        else:
            price = Price(to=to)
            query.fields.append(price)

    print(query.url)

    return end(update, context)


def metrazh_from(update, context):
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            from_ = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return METRAZH_FROM

        metrazh = Metrazh(from_=from_)
        context.user_data['query'].fields.append(metrazh)

    query = context.user_data['query']
    print(query.url)
    update.message.reply_text(
        'متراژ تا؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )

    return METRAZH_TO


def metrazh_to(update, context):
    query = context.user_data['query']
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            to = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return METRAZH_TO

        if query.metrazh:
            query.metrazh.to = to
        else:
            metrazh = Metrazh(to=to)
            query.fields.append(metrazh)

    print(query.url)
    if query.sub_category == 'اجاره و رهن':
        update.message.reply_text(
            'ودیعه از؟',
            reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
        )
        return VADIE_FROM

    update.message.reply_text(
        'قیمت از؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )
    return PRICE_FROM


def vadie_from(update, context):
    query = context.user_data['query']
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            from_ = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return VADIE_FROM

        vadie = Vadie(from_=from_)
        query.fields.append(vadie)

    print(query.url)
    update.message.reply_text(
        'ودیعه تا؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )

    return VADIE_TO


def vadie_to(update, context):
    query = context.user_data['query']
    text = update.message.text
    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            to = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return VADIE_TO

        if query.vadie:
            query.vadie.to = to
        else:
            vadie = Vadie(to=to)
            query.fields.append(vadie)

    print(query.url)
    update.message.reply_text(
        'اجاره از؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )

    return EJARE_FROM


def ejare_from(update, context):
    query = context.user_data['query']
    text = update.message.text

    if text == CANCEL:
        return start(update, context)
    elif text == DONE:
        return end(update, context)

    elif text != SKIP:
        try:
            from_ = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return EJARE_FROM

        ejare = Ejare(from_=from_)
        query.fields.append(ejare)

    print(query.url)
    update.message.reply_text(
        'اجاره تا؟',
        reply_markup=ReplyKeyboardMarkup([[CANCEL, DONE, SKIP]])
    )

    return EJARE_TO


def ejare_to(update, context):
    query = context.user_data['query']
    text = update.message.text

    if text == CANCEL:
        return START
    elif text == DONE:
        return end(update, context)
    elif text != SKIP:
        try:
            to = int(text)
        except ValueError:
            update.message.reply_text(INT_FAIL)
            return EJARE_TO

        if query.ejare:
            query.ejare.to = to
        else:
            ejare = Ejare(to=to)
            query.fields.append(ejare)

    print(query.url)

    return end(update, context)


def start_watchdog(update, context):
    job_queue = context.job_queue
    query = context.user_data['query']
    chat = update.effective_chat

    w = Watchdog(query, chat)
    w.start_job(job_queue)
    context.user_data['watchdogs'].append(w)
    return


def end(update, context):
    start_watchdog(update, context)
    update.message.reply_text(
        'نگهبان جدید شروع به کار کرد!\n'
        'این نگهبان در کمتر از یک دقیقه آگهی‌های جدید رو براتون میفرسته.',
    )
    return start(update, context)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    pp = PicklePersistence(filename='bidar.data')
    updater = Updater(TOKEN, persistence=pp, use_context=True)
    dp = updater.dispatcher
    states = [state.name for state in STATES]

    conv_handler = ConversationHandler(
        name='conv_handler',
        persistent=True,

        entry_points=[CommandHandler('start', start)],

        states={
            DISPATCHER: [MessageHandler(Filters.text, dispatcher)],
            DELETE: [MessageHandler(Filters.text, delete)],

            CATEGORY: [MessageHandler(Filters.text, category)],
            SUBCATEGORY: [MessageHandler(Filters.text, sub_category)],
            SEARCH: [MessageHandler(Filters.text, search)],
            STATE: [MessageHandler(Filters.text, state)],

            PRICE_FROM: [MessageHandler(Filters.text, price_from),],
            PRICE_TO: [MessageHandler(Filters.text, price_to),],

            METRAZH_FROM: [MessageHandler(Filters.text, metrazh_from),],
            METRAZH_TO: [MessageHandler(Filters.text, metrazh_to),],

            VADIE_FROM: [MessageHandler(Filters.text, vadie_from),],
            VADIE_TO: [MessageHandler(Filters.text, vadie_to),],

            EJARE_FROM: [MessageHandler(Filters.text, ejare_from),],
            EJARE_TO: [MessageHandler(Filters.text, ejare_to),],

            PLACES: [MessageHandler(Filters.text, places),],
            ATRAF: [MessageHandler(Filters.text, atraf),],
        },

        fallbacks=[CommandHandler('cancel', start)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    for user, data in pp.get_user_data().items():
        for wd in data['watchdogs']:
            wd.start_job(updater.job_queue)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

