import platform

from bot.helper.ext_utils.shorteners import short_url
 #from bot.helper.ext_utils.db import bot_name
from bot import botStartTime
from base64 import b64encode
from datetime import datetime
from os import path as ospath
from pkg_resources import get_distribution, DistributionNotFound
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from re import match as re_match
from time import time
from html import escape
from uuid import uuid4
from subprocess import run as srun
from psutil import disk_usage, disk_io_counters, Process, cpu_percent, swap_memory, cpu_count, cpu_freq, getloadavg, virtual_memory, net_io_counters, boot_time
from asyncio import create_subprocess_exec, create_subprocess_shell, run_coroutine_threadsafe, sleep
from asyncio.subprocess import PIPE
from functools import partial, wraps
from concurrent.futures import ThreadPoolExecutor
from aiohttp import ClientSession as aioClientSession
from psutil import virtual_memory, cpu_percent, disk_usage
from requests import get as rget
from bot import user_data
#from pyrogram.enums import ChatType
from pyrogram.types import BotCommand
from pyrogram.errors import PeerIdInvalid
from bot.helper.themes import BotTheme
from bot.version import get_version

from bot.helper.button_build import ButtonMaker
THREADPOOL   = ThreadPoolExecutor(max_workers=1000)
MAGNET_REGEX = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*'
URL_REGEX    = r'^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$'
SIZE_UNITS   = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']
STATUS_START = 0
PAGES        = 1
PAGE_NO      = 1

def update_user_ldata(id_, key=None, value=None):
    exception_keys = ['is_sudo', 'is_auth', 'dly_tasks', 'is_blacklist', 'token', 'time']
    if key is None and value is None:
        if id_ in user_data:
            updated_data = {}
            for k, v in user_data[id_].items():
                if k in exception_keys:
                    updated_data[k] = v
            user_data[id_] = updated_data
        return
    user_data.setdefault(id_, {})
    user_data[id_][key] = value
    
def checking_access(user_id, button=None):
    if not TG_CONFIG.token_timeout: #or bool(user_id == OWNER_ID or user_id in user_data and user_data[user_id].get('is_sudo')):
        return None, button
    if user_id in TG_CONFIG.sudo_users and TG_CONFIG.TESTOVER:
        return None, button
    user_data.setdefault(user_id, {})
    data = user_data[user_id]
    expire = data.get('time')
 #   if config_dict['LOGIN_PASS'] is not None and data.get('token', '') == config_dict['LOGIN_PASS']:
       # return None, button
    isExpired = (expire is None or expire is not None and (time() - expire) > TG_CONFIG.token_timeout)
                 
    if isExpired:
        token = data['token'] if expire is None and 'token' in data else str(uuid4())
        if expire is not None:
            del data['time']
        data['token'] = token
        user_data[user_id].update(data)
        if button is None:
            button = ButtonMaker()
        encrypt_url = b64encode(f"{token}&&{user_id}".encode()).decode()
        button.ubutton('Generate New Token', short_url(f'https://t.me/leechbot460_bot?start={encrypt_url}'))
        return f'<i>Temporary Token has been expired,</i> Kindly generate a New Temp Token to start using bot Again.\n<b>Validity :</b> <code>{get_readable_time(TG_CONFIG.token_timeout)}</code>', button
    return None, button

def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result
def get_readable_file_size(size_in_bytes):
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes}B'


def get_progress_bar_string(pct):
    pct = float(str(pct).strip('%'))
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    cPart = int(p % 8 - 1)
    p_str = '■' * cFull
    if cPart >= 0:
        p_str += ['▤', '▥', '▦', '▧', '▨', '▩', '■'][cPart]
    p_str += '□' * (12 - cFull)
    return f"[{p_str}]"



async def get_stats(event, key="home"):
    user_id = event.from_user.id
    btns = ButtonMaker()
    btns.ibutton('Back', f'wzmlx {user_id} stats home')
    if key == "home":
        btns = ButtonMaker()
        btns.ibutton('Bot Stats', f'wzmlx {user_id} stats stbot')
        btns.ibutton('OS Stats', f'wzmlx {user_id} stats stsys')
        btns.ibutton('Repo Stats', f'wzmlx {user_id} stats strepo')
        btns.ibutton('Bot Limits', f'wzmlx {user_id} stats botlimits')
        msg = "⌬ <b><i>Bot & OS Statistics!</i></b>"
    elif key == "stbot":
        total, used, free, disk = disk_usage('/')
        swap = swap_memory()
        memory = virtual_memory()
        disk_io = disk_io_counters()
        msg = BotTheme(
            'BOT_STATS',
            bot_uptime=get_readable_time(time() - botStartTime),
            ram_bar=get_progress_bar_string(memory.percent),
            ram=memory.percent,
            ram_u=get_readable_file_size(memory.used),
            ram_f=get_readable_file_size(memory.available),
            ram_t=get_readable_file_size(memory.total),
            swap_bar=get_progress_bar_string(swap.percent),
            swap=swap.percent,
            swap_u=get_readable_file_size(swap.used),
            swap_f=get_readable_file_size(swap.free),
            swap_t=get_readable_file_size(swap.total),
            disk=disk,
            disk_bar=get_progress_bar_string(disk),
            disk_read=f"{get_readable_file_size(disk_io.read_bytes)} ({get_readable_time(disk_io.read_time / 1000)})"
            if disk_io
            else "Access Denied",
            disk_write=f"{get_readable_file_size(disk_io.write_bytes)} ({get_readable_time(disk_io.write_time / 1000)})"
            if disk_io
            else "Access Denied",
            disk_t=get_readable_file_size(total),
            disk_u=get_readable_file_size(used),
            disk_f=get_readable_file_size(free),
        )
    elif key == "stsys":
        cpuUsage = cpu_percent(interval=0.5)
        msg = BotTheme('SYS_STATS',
            os_uptime=get_readable_time(time() - boot_time()),
            os_version=platform.version(),
            os_arch=platform.platform(),
            up_data=get_readable_file_size(net_io_counters().bytes_sent),
            dl_data=get_readable_file_size(net_io_counters().bytes_recv),
            pkt_sent=str(net_io_counters().packets_sent)[:-3],
            pkt_recv=str(net_io_counters().packets_recv)[:-3],
            tl_data=get_readable_file_size(net_io_counters().bytes_recv + net_io_counters().bytes_sent),
            cpu=cpuUsage,
            cpu_bar=get_progress_bar_string(cpuUsage),
            cpu_freq=f"{cpu_freq(percpu=False).current / 1000:.2f} GHz" if cpu_freq() else "Access Denied",
            sys_load="%, ".join(str(round((x / cpu_count() * 100), 2)) for x in getloadavg()) + "%, (1m, 5m, 15m)",
            p_core=cpu_count(logical=False),
            v_core=cpu_count(logical=True) - cpu_count(logical=False),
            total_core=cpu_count(logical=True),
            cpu_use=len(Process().cpu_affinity()),
        )
    elif key == "strepo":
        last_commit, changelog = 'No Data', 'N/A'
        if await aiopath.exists('.git'):
            last_commit = "COMMIT BATANE KA TIME NHI HAI 😁"
            changelog = "changelog Banane ka Time Nhi hai😁"
        official_v = '1.2.3.x0'#(await cmd_exec(f"curl -o latestversion.py https://raw.githubusercontent.com/weebzone/WZML-X/alpha/bot/version.py -s && python3 latestversion.py && rm latestversion.py", True))[0]
        msg = BotTheme('REPO_STATS',
            last_commit=last_commit,
            bot_version=get_version(),
            lat_version=official_v,
            commit_details=changelog,
            remarks="KOI JARURAT NHI HAI ABHI ISKA! COMMING SOON✨",
        )
    elif key == "botlimits":
        msg = "LIMITS LAGAKE ABHI KYA KAREGA CHORO LIMITS KO USE UNLIMITED ✨"
    btns.ibutton('Close', f'wzmlx {user_id} close')
    return msg, btns.build_menu(2)
    
