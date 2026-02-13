from html import escape as html_escape


def html_safe(text: str) -> str:
    return html_escape(text or "")


ASK_NICK = "Привет! Отправь, пожалуйста, свой ник в Pokerbros."

ALREADY_REGISTERED = "Снова привет! Твой ник в Pokerbros уже сохранён."

QUESTION_FORMAT = "Во что ты хочешь собрать игру?"

QUESTION_LIMIT = "На каком лимите ты хочешь играть?"

CONFIRM_TEMPLATE = (
    "Проверь, всё ли верно:\n\n"
    "Формат: <b>{format}</b>\n"
    "Лимит: <b>{limit}</b>"
)

CONFIRM_YES = "ДА верно"
CONFIRM_NO = "нет, ошибка"

BANNED_TEXT = "Вы заблокированы."

NO_FORMATS_TEXT = (
    "Форматы ещё не настроены. Напишите администратору: @Bravo_Poker"
)

NO_LIMITS_TEXT = (
    "Для выбранного формата пока не настроены лимиты. Напишите администратору: @Bravo_Poker"
)

HELP_TEXT = "Напишите администратору: @Bravo_Poker"

REQUEST_TO_ADMIN_TEMPLATE = (
    "Игрок <b>{nick}</b> хочет собрать игру\n"
    "Формат: <b>{format}</b>\n"
    "Лимит: <b>{limit}</b>\n"
    "Ссылка на игрока: {link}"
)

BROADCAST_TEMPLATE = (
    "Игрок '{nick}' ждет тебя на Pokerbros\n\n"
    "'{nick}' ждет тебя за столом '{format}' + '{limit}'\n\n"
    "Если хочешь присоединиться открывай приложение Pokerbros и заходи в Bravo Poker\n\n"
    "Если нужно сделать депозит пиши СЮДА ({deposit_link})"
)

REJECT_PLAYER_TEXT = (
    "К сожалению, ваше предложение не отправлено, для уточнения причины напишите "
    "менеджеру @Bravo_Poker"
)

ADMIN_ONLY_TEXT = "Эта команда доступна только администраторам."

USER_NOT_FOUND_TEXT = "Игрок не найден."

FORMAT_ADDED_TEXT = "Формат добавлен, id = {id}."

LIMIT_ADDED_TEXT = "Лимит добавлен, id = {id}."

LINK_ADDED_TEXT = "Связь формат/лимит сохранена."

SEGMENT_CREATED_TEXT = "Сегмент id = {id} для формат_id={format_id}, лимит_id={limit_id}."

ASSIGNED_TEXT = "Игрок назначен на сегмент {segment_id}."

UNASSIGNED_TEXT = "Игрок удалён из сегмента {segment_id}."

USER_INFO_TEMPLATE = (
    "Игрок:\n"
    "internal_id: {internal_id}\n"
    "tg_id: {tg_id}\n"
    "username: {username}\n"
    "nick: {nick}\n"
    "is_banned: {is_banned}\n"
    "segments: {segments}"
)

SEGMENTS_LIST_HEADER = "Сегменты:"

SEGMENT_ITEM_TEMPLATE = (
    "#{segment_id}: формат '{format_name}' (id={format_id}), лимит '{limit_name}' (id={limit_id})"
)

BAN_OK = "Игрок заблокирован."
UNBAN_OK = "Игрок разблокирован."
SETNICK_OK = "Ник игрока обновлён."

PARSING_ERROR = "Некорректный формат команды."

