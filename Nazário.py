import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import asyncio, functools, gc, json, logging, os, platform as _plt, random, requests, time
from typing import Dict, List, Optional, Set, Tuple
if _plt.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
else:
    try:
        import uvloop as _uvloop; _uvloop.install()
        print("  uvloop active")
    except ImportError:
        pass
from telegram import Bot, ChatMemberAdministrator, ReactionTypeEmoji, Update
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError
from telegram.ext import (
    Application, ChatMemberHandler,
    CommandHandler, ContextTypes, MessageHandler, PrefixHandler, filters,
)
TOKENS: List[str] = [

]
OWNER_ID = "8580917913"  # Primary Owner ID (display format)
OWNER_INFO = {
    "id": OWNER_ID,
    "name": None,  # Will be fetched on startup
    "username": None,  # Will be fetched on startup
}
OWNERS = frozenset({int(OWNER_ID)})  # Used for access control (int for comparison)
SUDO_PATH:  str       = "v13_sudo.json"
NEXUS_PATH: str       = "v13_nc_bots.json"
def safe_task(coro):
    """Schedule a background coroutine without leaking unhandled task exceptions."""
    async def _wrapped():
        try:
            return await coro
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"Background task failure: {type(e).__name__}: {e}")
            raise
    return asyncio.create_task(_wrapped())
async def _retry_async(coro_func, *args, max_retries=3, base_delay=0.5, **kwargs):
    """Retry async function with exponential backoff"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await coro_func(*args, **kwargs)
        except asyncio.TimeoutError as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(min(delay, 60))  # Cap delay at 60s
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(min(delay, 60))
            else:
                break
    if last_error:
        logging.error(f"Operation failed after {max_retries} attempts: {last_error}")
    return None
_Λ_PULSE: float = 0.00001  # Ultra-fast pulse for maximum NC speed
_Θ_HOUND: float = 3600.0
_NC_GLOBAL_LIMIT = max(8, min(32, int(os.getenv("UD_NC_GLOBAL_CONCURRENCY", "32"))))
_NC_PER_GROUP_LIMIT = max(1, min(2, int(os.getenv("UD_NC_GROUP_CONCURRENCY", "2"))))
_NC_QUEUE_DEPTH_PER_BOT = max(10, int(os.getenv("UD_NC_QUEUE_DEPTH_PER_BOT", "20")))
_NC_SEM_LOOP = None
_NC_GLOBAL_SEM = None
_NC_GROUP_SEMS: Dict[int, asyncio.Semaphore] = {}
_NC_GROUP_SEM_LOOP = None
_nc_next_allowed: Dict[Tuple[int, int], float] = {}
_nc_cache_reset_interval = 3600  # FIX: Reset cache entries every 1 hour to prevent 7-day speed degradation
_nc_success: int = 0
_nc_fail: int = 0
_nc_last_latency_ms: float = 0.0
_nc_active_requests: int = 0
_nc_peak_active: int = 0
_nc_rate_limit_hits: int = 0
_nc_started_at: float = time.monotonic()
_ι_relay_mode: Dict[int, bool] = {}
_ι_worker_registry: Dict[Tuple[int, int], asyncio.Task] = {}
_ι_overseer_active: bool = False
_active_tasks: set = set()  # Track all async tasks for cleanup
_connection_pool_timeout = 30.0  # Connection timeout in seconds
_max_retry_attempts = 5  # Max retries for failed operations
_retry_base_delay = 1.0  # Base delay for exponential backoff
def _register_task(task: asyncio.Task):
    """Register a task for lifecycle management"""
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)
def _cancel_all_tasks():
    """Cancel all pending tasks for clean shutdown"""
    for task in list(_active_tasks):
        if not task.done():
            task.cancel()
_ι_overseer_stats: Dict[str, int] = {
    "total_operations": 0,
    "successful_ops": 0,
    "failed_ops": 0,
}
def _nc_global_sem() -> asyncio.Semaphore:
    """Get or create global semaphore for concurrency control"""
    global _NC_GLOBAL_SEM, _NC_SEM_LOOP
    loop = asyncio.get_running_loop()
    if _NC_GLOBAL_SEM is None or _NC_SEM_LOOP is not loop:
        _NC_GLOBAL_SEM = asyncio.Semaphore(_NC_GLOBAL_LIMIT)
        _NC_SEM_LOOP = loop
    return _NC_GLOBAL_SEM
def _nc_group_sem(cid: int) -> asyncio.Semaphore:
    """Get or create per-group semaphore"""
    global _NC_GROUP_SEM_LOOP
    loop = asyncio.get_running_loop()
    if _NC_GROUP_SEM_LOOP is not loop:
        _NC_GROUP_SEMS.clear()
        _NC_GROUP_SEM_LOOP = loop
    sem = _NC_GROUP_SEMS.get(cid)
    if sem is None:
        sem = asyncio.Semaphore(_NC_PER_GROUP_LIMIT)
        _NC_GROUP_SEMS[cid] = sem
    return sem
_ξ_GLYPH = "nc"
_ν_GLYPH = "spam"
_μ_GLYPH = "swipe"
_Δ_delay: List[float] = [0.0]
_Ψ_task_count: List[int] = [1]
_Φ_mpfp: List[Optional[str]] = [None]
_P_NC: List[str] = [
"«|-😜-|»", "«|-😉-|»", "«|-😎-|»", "«|-🤩-|»", "«|-🥳-|»",
"«|-😏-|»", "«|-😁-|»", "«|-😆-|»", "«|-🤣-|»", "«|-😂-|»",
"«|-😊-|»", "«|-😍-|»", "«|-😘-|»", "«|-😗-|»", "«|-😙-|»",
"«|-😚-|»", "«|-🤗-|»", "«|-🙂-|»", "«|-🙃-|»", "«|-😋-|»",
"«|-🤪-|»", "«|-😝-|»", "«|-😛-|»", "«|-🤭-|»", "«|-🫢-|»",
"«|-🫣-|»", "«|-🤫-|»", "«|-🤔-|»", "«|-🫡-|»", "«|-😇-|»",
"«|-🥰-|»", "«|-😌-|»", "«|-🤠-|»", "«|-🥸-|»", "«|-😺-|»",
"«|-😸-|»", "«|-😹-|»", "«|-😻-|»", "«|-😼-|»", "«|-🙈-|»",
"«|-🙉-|»", "«|-🙊-|»", "«|-🐱-|»", "«|-🐶-|»", "«|-🦊-|»",
"«|-🐼-|»", "«|-🐨-|»", "«|-🐯-|»", "«|-🦁-|»", "«|-🐸-|»",
"«|-🐵-|»", "«|-🦄-|»", "«|-🐲-|»", "«|-🐉-|»", "«|-🦋-|»",
"«|-🐝-|»", "«|-🐞-|»", "«|-🕷️-|»", "«|-🦂-|»", "«|-🐢-|»",
"«|-🐬-|»", "«|-🦈-|»", "«|-🐙-|»", "«|-🦀-|»", "«|-🐠-|»",
"«|-🔥-|»", "«|-⚡-|»", "«|-💥-|»", "«|-✨-|»", "«|-🌟-|»",
"«|-⭐-|»", "«|-🌙-|»", "«|-☀️-|»", "«|-🌈-|»", "«|-❄️-|»",
"«|-☁️-|»", "«|-🌊-|»", "«|-🌪️-|»", "«|-🌋-|»", "«|-🪐-|»",
"«|-🌍-|»", "«|-🌎-|»", "«|-🌏-|»", "«|-☄️-|»", "«|-💫-|»",
"«|-🍀-|»", "«|-🌹-|»", "«|-🌺-|»", "«|-🌸-|»", "«|-🌻-|»",
"«|-🌼-|»", "«|-🍁-|»", "«|-🍂-|»", "«|-🌴-|»", "«|-🌵-|»",
"«|-🎉-|»", "«|-🎊-|»", "«|-🎈-|»", "«|-🎁-|»", "«|-🎀-|»",
"«|-🏆-|»", "«|-🥇-|»", "«|-🥈-|»", "«|-🥉-|»", "«|-👑-|»",
"«|-💎-|»", "«|-🛡️-|»", "«|-⚔️-|»", "«|-🏹-|»", "«|-🔱-|»",
"«|-❤️-|»", "«|-🧡-|»", "«|-💛-|»", "«|-💚-|»", "«|-💙-|»",
"«|-💜-|»", "«|-🖤-|»", "«|-🤍-|»", "«|-🤎-|»", "«|-💕-|»",
"«|-💞-|»", "«|-💓-|»", "«|-💗-|»", "«|-💖-|»", "«|-💘-|»",
"«|-🚀-|»", "«|-🛸-|»", "«|-✈️-|»", "«|-🚁-|»", "«|-⛵-|»",
"«|-🚗-|»", "«|-🏍️-|»", "«|-🚓-|»", "«|-🚒-|»", "«|-🚑-|»",
"«|-⌚-|»", "«|-📱-|»", "«|-💻-|»", "«|-🖥️-|»", "«|-⌨️-|»",
"«|-🖱️-|»", "«|-🎮-|»", "«|-🕹️-|»", "«|-📷-|»", "«|-🎥-|»",
"«|-🎵-|»", "«|-🎶-|»", "«|-🎸-|»", "«|-🎹-|»", "«|-🥁-|»",
"«|-🎺-|»", "«|-🎻-|»", "«|-🎷-|»", "«|-🎤-|»", "«|-🎧-|»",
"«|-🍕-|»", "«|-🍔-|»", "«|-🍟-|»", "«|-🌭-|»", "«|-🌮-|»",
"«|-🌯-|»", "«|-🍗-|»", "«|-🍖-|»", "«|-🍜-|»", "«|-🍣-|»",
"«|-🍩-|»", "«|-🍪-|»", "«|-🎂-|»", "«|-🍰-|»", "«|-🧁-|»",
"«|-☕-|»", "«|-🍵-|»", "«|-🥤-|»", "«|-🧃-|»", "«|-🍫-|»",
"«|-💰-|»", "«|-💵-|»", "«|-💸-|»", "«|-🏦-|»", "«|-📈-|»",
"«|-📉-|»", "«|-📝-|»", "«|-📚-|»", "«|-📖-|»", "«|-🔮-|»",
"«|-🎯-|»", "«|-🎲-|»", "«|-♠️-|»", "«|-♥️-|»", "«|-♦️-|»",
"«|-♣️-|»", "«|-🃏-|»", "«|-🎰-|»", "«|-🎳-|»", "«|-🏀-|»"
]
_P_NCCHUD: List[str] = [
"⋆｡🎀｡⋆", "⋆｡💍｡⋆", "⋆｡🍫｡⋆", "⋆｡❄️｡⋆", "⋆｡🍃｡⋆", "⋆｡💥｡⋆", "⋆｡🐊｡⋆", "⋆｡🌟｡⋆", "⋆｡🪵｡⋆", "⋆｡👾｡⋆", "⋆｡🎈｡⋆", "⋆｡🍓｡⋆", "⋆｡🪐｡⋆"
]
_P_NCZARIO: List[str] = [
"𝗟ꪊꪀ𝗗 𝗖ʜꪊs 𝗦ꪶꪖꪜꫀ",
"तेरी 𝘔𝘰𝘮 𝘞𝘰𝘳𝘭𝘥 𝘊𝘭𝘢𝘴𝘴 रण्डी😂🔥",
"सही 𝘊𝘩𝘶𝘥𝘪 तेरी Mom😠😝😠",
"𝘛𝘦𝘳𝘪 मां को अल्लाह 𝘊𝘩𝘰𝘥𝘦🖕🎀🐊",
"𝘒𝘺𝘢 रे 𝘚𝘮𝘪𝘭𝘦𝘺 जैसा रन्डी बनेगा🤴👑",
"तेरी 𝘔𝘢 𝘊𝘩𝘰𝘥𝘶 क्या RandSon🥰🔥🥀",
"तेरी माँ की छूट में गुलाब जामुन 🚀💢🍕",
"अपनी मां 𝘬𝘪 𝘊𝘩𝘶𝘥𝘢𝘪 का आनंद ले !!"
]
_P_SEXUAL: List[str] = [
"Rᴀɴᴅ ₊˚₊˚.⋆⋆",
"Cᴜᴅ ᴋᴇsᴇ Gᴀʏᴀ ₊˚₊˚.⋆⋆",
"Bʜᴀɢ Mᴀᴛ ₊˚₊˚.⋆⋆",
"Gᴜʟᴀᴍ Bᴀɴ Pɪʟʟᴇ ₊˚₊˚.⋆⋆",
"Iᴅʜᴇʀ Aᴀ Tᴇʀɪ Bᴇʜɴ Cᴏᴅᴜ ₊˚₊˚.⋆⋆",
"Tᴇʀɪ Mᴀ Kᴏ Qᴜᴛᴜʙ Mɪɴᴀʀ Lᴇ Jᴀᴜ ₊˚₊˚.⋆⋆",
"Dᴀғᴀɴ Mᴀᴛ Hᴏ Gᴀʀᴇᴇʙ Lᴀʀᴋᴇ ₊˚₊˚.⋆⋆",
"Jᴀᴅᴏᴏ Sᴇ Cʜᴜᴅɪ Tᴇʀɪ Mᴏᴍ ₊˚₊˚.⋆⋆",
"Tᴇʀɪ Mᴀ Kᴀ Bʜᴏsᴅᴀ Mᴀʀᴜ ₊˚₊˚.⋆⋆",
"Tᴇʀɪ Mᴏᴍ ᴄʜᴜᴅᴀɪ Aʀᴄ ᴄʜᴀʟᴜ ʜᴀɪ ₊˚₊˚.⋆⋆",
"Wᴡᴇ Mᴇ Cʜᴜᴅɪ Tᴇʀʏ Mᴏᴍ ₊˚₊˚.⋆⋆",
"Kᴀʟᴘᴀɴɪᴋ Yᴜɢ ᴋɪ Rᴀɴᴅɪ ᴛᴇʀɪ Mᴀ ₊˚₊˚.⋆⋆",
"Tᴇʀɪ Mᴀ Dɪᴀɴᴏsᴏᴜʀ Aʀᴄ ᴍᴇ Cʜᴜᴅ Gʏɪ ₊˚₊˚.⋆⋆",
"Dᴏʀᴀᴇᴍᴏɴ Aʀʜᴀ Hᴏɢᴀ Tᴇʀɪ Mᴀ Cʜᴏᴅɴᴇ ₊˚₊˚.⋆⋆",
"Esᴇ ɴʜɪ Bᴏʟᴛᴇ Wʀɴᴀ Tᴇʀɪ Mᴀ Cʜᴜᴅ Jᴀʏɢɪ ₊˚₊˚.⋆⋆",
"Tᴇʀɪ Mᴀ Kᴏ Osᴄᴀʀ Mɪʟɴᴀ Cʜᴀʜɪʏᴇ Cʜᴜᴅɴᴇ Kᴀ ₊˚₊˚.⋆⋆",
"- 𝐍ꫝᴢꪖʀɪꪮ ♡︎ Bᴀᴘ Bᴏʟ Mᴅᴄ ₊˚₊˚.⋆⋆",
"Hᴀᴡʙᴀᴢ Bᴀɴᴇɢᴀ Tᴍʀ ₊˚.⋆",
"Tᴇʀɪ Bᴇʜᴇɴ Kᴜᴛᴛɪʏᴀ ₊˚.⋆"
"Tᴇʀɪ Mᴀ Pᴏᴋᴇᴍᴏɴ ₊˚.⋆",
"Kᴏɴsᴇ Pᴏsɪᴛɪᴏɴ Mᴇ Cᴏᴅᴜ Tᴇʀɪ Mᴀ Kᴏ ₊˚.⋆",
"BᴀᴛʜRᴏᴏᴍ Mᴇ Cʜᴜᴅᴇɢᴀ Oʀ Bᴇᴅʀᴏᴏᴍ ₊˚.⋆"
"Cʜᴜᴅᴀ Tᴇʀɪ Mᴏᴍ ₊˚.⋆",
"Tᴇʀɪ Mᴀ Kᴀ Bᴀʟᴀᴛᴀᴋʀ Hᴏɢᴀʏᴀ Bʜᴀɢᴏᴏ ₊˚.⋆"
]
_P_CHUD_SWIPE: List[str] = [
    "{name} 𝗟ꪊꪀ𝗗 𝗖ʜꪊs 𝗦ꪶꪖꪜꫀ",
"{name} तेरी 𝘔𝘰𝘮 𝘞𝘰𝘳𝘭𝘥 𝘊𝘭𝘢𝘴𝘴 रण्डी😂🔥",
"{name} सही 𝘊𝘩𝘶𝘥𝘪 तेरी Mom😠😝😠",
"{name} 𝘛𝘦𝘳𝘪 मां को अल्लाह 𝘊𝘩𝘰𝘥𝘦🖕🎀🐊",
"{name} 𝘒𝘺𝘢 रे 𝘚𝘮𝘪𝘭𝘦𝘺 जैसा रन्डी बनेगा🤴👑",
"{name} तेरी 𝘔𝘢 𝘊𝘩𝘰𝘥𝘶 क्या RandSon🥰🔥🥀",
"{name} तेरी माँ की छूट में गुलाब जामुन 🚀💢🍕",
" {name} अपनी मां 𝘬𝘪 𝘊𝘩𝘶𝘥𝘢𝘪 का आनंद ले !!"
]
_P_TSPAM: List[str] = [
    """☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<💮>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆""",
    """☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<☘️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆""",
    """☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌺>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆""",
    """☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌼>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆""",
    """☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🏵️>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆""",
    """☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆
☆*:..｡.:*☆ {target} LUND CHUS BADA HO SLAVE𝜗𝜚˚<🌹>⋆ ִֶָ˖·˳˖𓂃 ִֶָ✩₊˚.⋆""",
]
_T_TSWIPE: List[str] = [
"𓆩❤️𓆪 𝗖ʜᴜᴘ 𝗥ɴᴅʏᴋ 𝗞ᴏɴᴇ 𝗠ᴇɪɴ 𝗕ᴀɪᴛʜ 𓆩❤️𓆪",
"𓆩🧡𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴇ भोसड़े 𝗠ᴇɪɴ 𝗧ʜᴇᴀᴛᴇʀ 𝗞ʜᴏʟᴋᴇ सैयारा 𝗖ʜᴀʟᴀ 𝗗ᴜɴɢᴀ 𓆩🧡𓆪",
"𓆩💛𓆪 𝗬ᴇ 𝗗ᴇᴋʜ ˢᶜʳⁱᵖᵗ ˡⁱᵏʰ ʳᵃʰᵃ ʰᵘ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴇ 𝗕ʜᴏsᴅᴇ 𝗠ᴇɪɴ 𓆩💛𓆪",
"𓆩💚𓆪 𝗦ᴜᴀʀ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ɪ 𝗖ʜᴜᴛ 𓆩💚𓆪",
"𓆩💙𓆪 𝗧ᴜ 𝗜ᴅʀ 𝗖ᴏᴍᴇʙᴀᴄᴋ 𝗗ᴇᴛᴀ 𝗥ᴇʜ 𝗚ʏᴀ 𝗨ᴅʜʀ - 𝐍ꫝᴢꪖʀɪꪮ ♡︎ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴏᴅ 𝗚ʏᴀ 𓆩💙𓆪",
"𓆩💜𓆪 𝗖ʜᴏᴅɪɴɢ 𝗛ᴏ 𝗥ʜɪ 𝗛ᴀɪ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ɪ 𓆩💜𓆪",
"𓆩🖤𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ɪ 𝗖ʜᴜᴛ 𝗠ᴇɪɴ 𝗟ᴏᴅᴀ 𝗗ᴀʟᴜɢᴀ 𝗕ᴇᴛᴀ 𓆩🖤𓆪",
"𓆩🤍𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴀ 𝗕ʜsᴅᴀ 𝗗ɪᴋʜ 𝗥ʜᴀ 𝗛ᴀɪ 𓆩🤍𓆪",
"𓆩🤎𓆪 𝗖ʏᴀ 𝗥ᴇ 𝗦ᴀᴘʀɪ 𝗧ʀʏ 𝗠ᴀᴀ 𝗧ᴜᴊʜ 𝗡ᴇʜʟᴀᴛɪ 𝗡ʏ 𝗘ʏ 𝗖ʏᴀ 𓆩🤎𓆪",
"𓆩💖𓆪 𝗢ʏᴇ 𝗠ᴀᴅᴀʀᴄʜᴏᴅ 𝗨ᴛʜ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴀ 𝗖ʜᴏᴅɪɴɢ 𝗧ᴇᴍ 𓆩💖𓆪",
"𓆩💗𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴏ 𝗙ᴏᴏᴛʙᴀʟʟ 𝗕ɴᴀᴋᴇ 𝗨sᴋᴇ 𝗕ʜsᴅᴇ 𝗣ᴇ 𝗟ᴀᴀᴛ 𝗠ᴀʀᴜɴɢᴀ 𓆩💗𓆪",
"𓆩💓𓆪 इस 𝗠ᴀɴɢᴀʟᴠᴀʀ 𝗞ᴏ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ɪ 𝗖ʜᴜᴛ 𝗞ᴀ 𝗕ʜᴀɴᴅᴀʀᴀ 𝗛ᴏɢᴀ 𓆩💓𓆪",
"𓆩💞𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴀ 𝗕ᴏᴏʀ 𝗕ᴇᴛᴀ 𓆩💞𓆪",
"𓆩💕𓆪 𝗠ᴀᴀ 𝗞ᴇ 𝗟ᴏᴅᴇ 𓆩💕𓆪",
"𓆩💘𓆪 𝗣ᴇʜʟᴇ 𝗧ᴇʀɪ 𝗕ᴇʜᴇɴ 𝗖ʜᴏᴅᴜɢᴀ 𝗙ɪʀ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𓆩💘𓆪",
"𓆩💝𓆪 𝗖ʜᴜᴘ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴀ 𝗕ʜᴏsᴅᴀ 𓆩💝𓆪",
"𓆩💟𓆪 𝗦ᴘᴀᴍᴍᴇʀ 𝗕ᴀɴᴇɢᴀ 𝗥ᴀɴᴅɪᴋᴇ 𓆩💟𓆪",
"𓆩❣️𓆪 𝗔ᴊᴀ 𝗠ᴄ 𝗕ᴀɴᴀᴜ 𝗧ᴜᴊʜᴇ 𝗦ᴘᴀᴍᴍᴇʀ 𓆩❣️𓆪",
"𓆩♥️𓆪 𝗕ᴏʟ 𝗡ᴀᴢᴀ́ʀɪᴏ 𝗕ᴀᴀᴘ 𓆩♥️𓆪",
"𓆩🩷𓆪 𝗧ᴇʀɪ 𝗥ᴀɴᴅɪ 𝗠ᴀᴀ 𝗞ᴏ 𝗣ᴇʟ 𝗗ᴜɴɢᴀ 𓆩🩷𓆪",
"𓆩🩵𓆪 𝗜ᴅʜᴀʀ 𝗔ᴀ 𝗕ᴇᴛᴀ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴏᴅᴜ 𓆩🩵𓆪",
"𓆩🩶𓆪 𝗢ʏᴇ 𝗕ɪʜᴀʀɪ 𝗞ᴀᴀᴍ 𝗣ᴇ 𝗝ᴀ 𓆩🩶𓆪",
"𓆩❤️𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴏᴅɴᴇ 𝗞 𝗟ɪʏᴇ 𝗣ᴜʀᴀ 𝗚ᴄ 𝗞ʜᴀᴅᴀ 𝗛ᴀɪ 𓆩❤️𓆪",
"𓆩🧡𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗕ɪᴏ 𝗠ᴇɪɴ #𝗣ʀᴏᴜᴅʀᴀɴᴅɪ 𝗟ɪᴋʜᴛɪ 𝗛ᴀɪ 𓆩🧡𓆪",
"𓆩💛𓆪 𝗥ɴᴅʏᴋ 𝗟ᴜɴᴅ 𝗦ᴇ 𝗨ᴛʀ 𓆩💛𓆪",
"𓆩💚𓆪 𝗔ʀᴇʏ 𝗬ᴀʀʀ 𝗔ᴘɴɪ 𝗠ᴀᴀ 𝗠ᴀᴛᴛ 𝗡ᴀɴɢɪ 𝗞ᴀʀ 𓆩💚𓆪",
"𓆩💙𓆪 𝗧ᴜ 𝗛ᴀsᴛᴀ 𝗥ᴇʜ 𝗚ʏᴀ 𝗬ᴀᴀʀᴏ 𝗠ᴇɪɴ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴜᴅɢʏɪ 𝗕ᴀᴀᴢᴀʀᴏ 𝗠ᴇɪɴ 𓆩💙𓆪",
"𓆩💜𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴜᴅᴡᴀ 𝗗ᴇɴɢᴇ 𝗥ᴇ 𓆩💜𓆪",
"𓆩🖤𓆪 𝗚ᴜᴅ 𝗡ʏᴛ 𝗥ɴᴅʏᴋ 𝗞ᴀʟ 𝗔ᴀᴜɴɢᴀ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴏᴅɴᴇ 𓆩🖤𓆪",
"𓆩🤍𓆪 𝗔ʀᴇ 𝗠ᴄ 𝗬ᴇ 𝗞ᴀɪsᴇ 𝗞ɪʏᴀ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗥ᴀɴᴅɪ 𝗛ᴀɪ 100% 𓆩🤍𓆪",
"𓆩🤎𓆪 𝗬ᴇ 𝗦ᴀʀᴇ 𝗗ɪʟʟ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞 𝗡ᴀᴀᴍ 𝗕ᴇᴛᴀ 𓆩🤎𓆪",
"??💖𓆪 𝗛ᴀᴛ 𝗣ᴇᴄʜᴇ 𝗛ᴀᴛ 𝗧ᴇʀᴀ 𝗕ᴀᴀᴘ 𝗔ʏᴀ 𓆩💖𓆪",
"𓆩💗𓆪 𝗟ᴇᴀᴠᴇ 𝗟ᴇ 𝗥ɴᴅʏᴋ 𝗣sɴᴅ 𝗡ᴀɪ 𝗔ʏᴀ 𝗧ᴜ 𝗠ᴇᴋᴏ 𓆩💗𓆪",
"𓆩💓𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴏᴅᴜ 𝗜ғ 𝗬ᴇs 𝗧ʜᴇɴ 𝗥ᴇᴘʟʏ 𝗧ᴏ 𝗠ʏ 𝗠ᴇssᴀɢᴇ 𓆩💓𓆪",
"𓆩💞𓆪 #𝗡ᴀᴢᴀ́ʀɪᴏ 𝗕ᴀᴀᴘ 𝗞ᴏ 𝗗ʙᴀ 𝗡ʜɪ 𝗣ᴀʀᴇ 𝗖ʏᴀ?? 𓆩💞𓆪",
"𓆩💕𓆪 𝗧ᴇʀɪ 𝗥ᴀɴᴅɪ 𝗠ᴀᴀ 𝗞ᴇ 𝗕ᴜʀ 𝗣ᴇ 𝗟ᴀᴀᴛ 𝗠ᴀʀ 𝗞ᴇ 𝗧ᴇʀɪ 𝗕ᴇʜᴇɴ 𝗖ʜᴏᴅ 𝗗ᴜɢᴀ 𓆩💕𓆪",
"𓆩💘𓆪 𝗚ᴀʀᴇᴇʙ 𝗚ʜᴀʀ 𝗞ᴇ 𝗟ᴀᴅᴋᴇ 𝗕ᴀᴀᴘ 𝗟ᴏɢ 𝗞ᴇ 𝗚ᴄ 𝗠ᴇɪɴ 𝗞ʏᴀ 𝗞ʀʀ 𝗥ʜᴀ 𓆩💘𓆪",
"𓆩💝𓆪 𝗬ᴇ 𝗗ᴇᴋʜ 𝗝ᴀᴅᴜ 𝗦ᴇ 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗖ʜᴏᴅ 𝗗ɪʏᴀ 𓆩💝𓆪",
"𓆩💟𓆪 𝗧ᴇʀɪ 𝗠ᴀᴀ 𝗞ᴏ बाहुबली 𝗦ᴛʏʟᴇ 𝗠ᴇɪɴ 𝗖ʜᴏᴅᴜɴɢᴀ 𓆩💟𓆪",
"𓆩❣️𓆪 𝗧ᴜᴍʜᴀʀᴇ 𝗣ɪᴛᴀsʜʀᴇᴇ 𝗡ᴀᴢᴀ́ʀɪᴏ 𓆩❣️𓆪"
]
_ρ_hive: Dict[str, str] = {}
_ρ_CAP  = 512
def _τ_forge(raw: str, cap: int = 255) -> str:
    hit = _ρ_hive.get(raw)
    if hit is not None:
        return hit
    units  = 0
    cutoff = len(raw)
    for i, ch in enumerate(raw):
        u = 2 if ord(ch) > 0xFFFF else 1
        if units + u > cap:
            cutoff = i
            break
        units += u
    s = raw[:cutoff].rstrip()
    if len(_ρ_hive) >= _ρ_CAP:
        for k in list(_ρ_hive)[:64]:
            del _ρ_hive[k]
    _ρ_hive[raw] = s
    return s
class _Vault:
    __slots__ = (
        "sentinels", "_nc_live", "_spam_live",
        "_mark_ids", "_mark_names",
        "_flood_chats", "_fronts", "_ops",
    )
    def __init__(self):
        self.sentinels:    Set[int]                        = set(OWNERS)
        self._nc_live:     Dict[int, bool]                 = {}
        self._spam_live:   Dict[int, bool]                 = {}
        self._mark_ids:    Set[int]                        = set()
        self._mark_names:  Dict[int, str]                  = {}
        self._flood_chats: Set[int]                        = set()
        self._fronts:      Set[int]                        = set()
        self._ops:         Dict[tuple, List[asyncio.Task]] = {}
        self._load_sudo()
    def _load_sudo(self):
        try:
            if os.path.exists(SUDO_PATH):
                with open(SUDO_PATH) as f:
                    self.sentinels = set(json.load(f))
            self.sentinels.update(OWNERS)
        except Exception:
            self.sentinels = set(OWNERS)
    def _persist(self):
        try:
            with open(SUDO_PATH, "w") as f:
                json.dump(list(self.sentinels), f)
        except Exception:
            pass
    def _is_sentinel(self, uid: int) -> bool:
        return uid in self.sentinels
    def _enqueue(self, cid: int, slot: str, task: asyncio.Task):
        key = (cid, slot)
        lst = self._ops.get(key)
        if lst is None: self._ops[key] = [task]
        else:           lst.append(task)
    def _sweep(self):
        for key in list(self._ops):
            alive = [t for t in self._ops[key] if not t.done()]
            if alive: self._ops[key] = alive
            else:     del self._ops[key]
    def _abort(self, cid: int, slot: str):
        for t in self._ops.pop((cid, slot), []):
            t.cancel()
    def _abort_all(self):
        for key in list(self._ops):
            for t in self._ops.pop(key, []):
                t.cancel()
    def _tally(self) -> int:
        return sum(1 for v in self._ops.values() for t in v if not t.done())
    def _kill_nc(self, cid: int):    self._nc_live[cid]   = False
    def _kill_spam(self, cid: int):  self._spam_live[cid] = False
    def _kill_swipe(self, cid: int): self._flood_chats.discard(cid)
    def _kill_all(self, cid: int):
        self._kill_nc(cid); self._kill_spam(cid); self._kill_swipe(cid)
_χ = _Vault()
_ω_apps:        List[Application]      = []
_ω_fleet:       List[Bot]              = []
_ω_annexe:      List[Bot]              = []
_ω_ann_tk:      List[str]              = []
_ω_nc_ledger:   Dict[int, tuple]       = {}
_ω_ghost_ids:   Set[int]               = set()
_chup_silenced: Set[Tuple[int, int]]   = set()
_ω_leader_id: Optional[int] = None
_START_TIME = None
def _uptime_now():
    return _datetime.datetime.now(_datetime.timezone(_datetime.timedelta(hours=5, minutes=30)))
def _format_uptime(start, now):
    years = now.year - start.year
    months = now.month - start.month
    days = now.day - start.day
    hours = now.hour - start.hour
    minutes = now.minute - start.minute
    seconds = now.second - start.second
    if seconds < 0:
        seconds += 60; minutes -= 1
    if minutes < 0:
        minutes += 60; hours -= 1
    if hours < 0:
        hours += 24; days -= 1
    if days < 0:
        prev_month = now.month - 1 or 12
        prev_year = now.year if now.month > 1 else now.year - 1
        days += (_datetime.date(prev_year, prev_month + 1, 1) -
                 _datetime.date(prev_year, prev_month, 1)).days
        months -= 1
    if months < 0:
        months += 12; years -= 1
    parts = []
    if years: parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months: parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days: parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours: parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes: parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return ", ".join(parts)
def _σ_set_leader(bot_id: int):
    global _ω_leader_id
    _ω_leader_id = bot_id
def _σ_is_leader(bot_id: int) -> bool:
    return _ω_leader_id is not None and bot_id == _ω_leader_id
def _σ_sync_ids():
    global _ω_ghost_ids
    _ω_ghost_ids = {b.id for b in _ω_fleet + _ω_annexe if b.id}
def _σ_ghost() -> Set[int]: return _ω_ghost_ids
def _σ_battalion() -> List[Bot]:
    combined = _ω_annexe + _ω_fleet
    return combined if combined else []
def _σ_fronts(primary: int) -> List[int]:
    out, seen = [primary], {primary}
    for cid in _χ._fronts:
        if cid not in seen:
            seen.add(cid); out.append(cid)
    return out
def _π_pull() -> List[str]:
    try:
        if os.path.exists(NEXUS_PATH):
            with open(NEXUS_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return []
def _π_push():
    try:
        with open(NEXUS_PATH, "w") as f:
            json.dump(_ω_ann_tk, f)
    except Exception:
        pass
async def _π_boot_annexe(tok: str) -> Optional[Bot]:
    try:
        from telegram.request import HTTPXRequest as _R
        b = Bot(token=tok, request=_R(
            connection_pool_size=256, read_timeout=30.0,
            write_timeout=30.0, connect_timeout=10.0, pool_timeout=10.0,
        ))
        me = await b.get_me()
        print(f"  annexe: @{me.username}")
        return b
    except Exception as e:
        print(f"  annexe fail: {e}")
        return None
_DENIED = "𝘿𝙐𝙍 𝙍𝙀𝙃 𝙏𝙊𝙈𝙈𝙔 𝙎𝙃𝙐𝙐𝙐-𝙎𝙃𝙐𝙐𝙐🙈🎀"
def _gate(fn):
    @functools.wraps(fn)
    async def _w(u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not _σ_is_leader(c.bot.id):
            return
        if not u.effective_user or not _χ._is_sentinel(u.effective_user.id):
            try: await u.message.reply_text(_DENIED)
            except Exception: pass
            return
        return await fn(u, c)
    return _w
def _crown(fn):
    @functools.wraps(fn)
    async def _w(u: Update, c: ContextTypes.DEFAULT_TYPE):
        if not _σ_is_leader(c.bot.id):
            return
        if not u.effective_user or u.effective_user.id not in OWNERS:
            try: await u.message.reply_text(_DENIED)
            except Exception: pass
            return
        return await fn(u, c)
    return _w
def _υ_strip(msg) -> str:
    txt = msg.text or msg.caption or ""
    raw = ""
    if msg.entities:
        for e in msg.entities:
            if e.type == "bot_command" and e.offset == 0:
                after = txt[e.offset + e.length:]
                raw   = after[1:] if after.startswith(" ") else after
                break
    if not raw:
        p = txt.split(None, 1)
        raw = p[1] if len(p) > 1 else ""
    return " ".join(raw.splitlines())
async def _ι_worker(bot: Bot, cid: int, flag: dict, q: "asyncio.Queue[str]"):
    """Bounded NC worker with semaphore-based flood control & adaptive rate-limit recovery"""
    global _nc_success, _nc_fail, _nc_last_latency_ms, _nc_active_requests
    global _nc_peak_active, _nc_rate_limit_hits
    key = (bot.id, cid)
    gsem = _nc_group_sem(cid)
    while flag.get(cid):
        try:
            title = await q.get()
        except asyncio.CancelledError:
            return
        try:
            if not flag.get(cid):
                continue
            next_allowed = _nc_next_allowed.get(key, 0.0)
            wait_for = next_allowed - time.monotonic()
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            async with _nc_global_sem(), gsem:
                if not flag.get(cid):
                    continue
                started = time.perf_counter()
                _nc_active_requests += 1
                _nc_peak_active = max(_nc_peak_active, _nc_active_requests)
                try:
                    await bot.set_chat_title(cid, title)
                finally:
                    _nc_active_requests = max(0, _nc_active_requests - 1)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                _nc_last_latency_ms = elapsed_ms
                _nc_success += 1
                _nc_next_allowed[key] = time.monotonic()
                _ι_overseer_stats["successful_ops"] += 1
        except RetryAfter as e:
            _nc_fail += 1
            _nc_rate_limit_hits += 1
            retry_for = max(1.0, float(e.retry_after))
            _ι_overseer_stats["failed_ops"] += 1
            _nc_next_allowed[key] = time.monotonic() + retry_for
            await asyncio.sleep(retry_for)
        except TelegramError as e:
            _nc_fail += 1
            _ι_overseer_stats["failed_ops"] += 1
            err = str(e).lower()
            if any(x in err for x in ("bad request", "chat not found", "not enough rights", "forbidden")):
                pass
        except asyncio.CancelledError:
            return
        except Exception:
            _nc_fail += 1
            _ι_overseer_stats["failed_ops"] += 1
        finally:
            q.task_done()
async def _ι_feeder(cid: int, flag: dict, titles: list, q: "asyncio.Queue[str]"):
    """Feeds titles into queue for workers"""
    n = len(titles)
    idx = 0
    pool_depth = max(len(_σ_battalion()), 1) * _NC_QUEUE_DEPTH_PER_BOT
    while flag.get(cid):
        try:
            while flag.get(cid) and q.qsize() < pool_depth:
                await q.put(_τ_forge(titles[idx % n]))
                idx += 1
            if flag.get(cid):
                await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            return
        except Exception:
            await asyncio.sleep(0.01)
async def _ι_mode_relay(cid: int, flag: dict, titles: list):
    """Relay mode - distributes work across bots with proper flood control"""
    pool = _σ_battalion()
    if not pool: return
    if cid not in _ι_relay_mode:
        _ι_relay_mode[cid] = True
    if not _ι_relay_mode[cid]:
        return
    q = asyncio.Queue(maxsize=max(len(pool) * 2, 8))
    subs = [safe_task(_ι_feeder(cid, flag, titles, q))]
    for bot in pool:
        t = safe_task(_ι_worker(bot, cid, flag, q))
        _χ._enqueue(cid, _ξ_GLYPH, t)
        _ι_worker_registry[(bot.id, cid)] = t
        subs.append(t)
    try:
        while flag.get(cid) and _ι_relay_mode.get(cid, True):
            await asyncio.sleep(_Λ_PULSE)
            _ι_overseer_stats["total_operations"] += 1
    except asyncio.CancelledError:
        pass
    finally:
        for t in subs:
            if not t.done(): t.cancel()
        while not q.empty():
            try:
                q.get_nowait()
                q.task_done()
            except Exception:
                break
async def _ι_overseer(primary: int, titles: list, flag: dict):
    """Master overseer"""
    global _ι_overseer_active
    _ι_overseer_active = True
    targets = _σ_fronts(primary)
    runners: Dict[int, asyncio.Task] = {}
    try:
        for cid in targets:
            if _ι_relay_mode.get(cid, False) == False:
                continue
            t = safe_task(_ι_mode_relay(cid, flag, titles))
            _χ._enqueue(cid, _ξ_GLYPH, t)
            runners[cid] = t
        while flag.get(primary):
            await asyncio.sleep(_Λ_PULSE)
            for cid in list(runners):
                if not flag.get(cid):
                    if not runners[cid].done(): runners[cid].cancel()
                    del runners[cid]
                    continue
                if runners[cid].done():
                    try:
                        result = runners[cid].result()
                        _ι_overseer_stats["successful_ops"] += 1
                    except Exception:
                        _ι_overseer_stats["failed_ops"] += 1
                    nt = safe_task(_ι_mode_relay(cid, flag, titles))
                    _χ._enqueue(cid, _ξ_GLYPH, nt)
                    runners[cid] = nt
    except asyncio.CancelledError:
        pass
    finally:
        _ι_overseer_active = False
        for t in runners.values():
            if not t.done(): t.cancel()
def _ι_ignite(primary: int, titles: list, flag: dict):
    """Ignite - Start relay operations with proper flood control"""
    _ω_nc_ledger[primary] = (titles, flag)
    _ι_relay_mode[primary] = True
    sup = safe_task(_ι_overseer(primary, titles, flag))
    _χ._enqueue(primary, _ξ_GLYPH, sup)
    logging.info(f"🔥 Relay IGNITED for primary {primary}")
_ULTRA_NC_EMOJIS = [
    "🔥","⚡","💥","✨","🌟","⭐","🌙","☀️","🌈","❄️","☁️","🌊","🌪️","🌋","☄️",
    "💫","🍀","🌹","🌺","🌸","🌻","🌼","🍁","🍂","🌴","🌵","🎉","🎊","🎈","🎁",
    "🎀","🏆","🥇","🥈","🥉","👑","💎","🛡️","⚔️","🏹","🔱","❤️","🧡","💛","💚",
    "💙","💜","🖤","🤍","🤎","💕","💞","💓","💗","💖","💘","🚀","🛸","✈️","🚁",
    "⛵","🚗","🏍️","🚓","🚒","🚑","⌚","📱","💻","🖥️","⌨️","🖱️","🎮","🕹️","📷",
    "🎥","🎵","🎶","🎸","🎹","🥁","🎺","🎻","🎷","🎤","🎧","🍕","🍔","🍟","🌭",
    "🌮","🍗","🍜","🍣","🍩","🍪","🎂","🍰","☕","🍵","🥤","💰","💵","💸","🏦",
    "📈","📉","📝","📚","📖","🔮","🎯","🎲","♠️","♥️","♦️","♣️","🎰","🎳","🏀"
]
MENU_TEXT = """\
╭── ❖Nazário Bot❖ ──╮
💢 ʙᴀꜱɪᴄ
• /start 🚀 ─ ꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
• /menu 📖 ─ ꜱʜᴏᴡ ᴄᴏᴍᴍᴀɴᴅ ᴍᴇɴᴜ
• /help ❓ ─ ꜱʜᴏᴡ ʜᴇʟᴘ
• /ping 🏓 ─ ᴄʜᴇᴄᴋ ʙᴏᴛ ꜱᴘᴇᴇᴅ
• /uptime ⏱ ─ ᴄʜᴇᴄᴋ ʙᴏᴛ ᴜᴘᴛɪᴍᴇ
• /id 🆔 ─ ɢᴇᴛ ᴜꜱᴇʀ ɪᴅ
────────────
💢 ɴᴀᴍᴇ ᴄʜᴀɴɢᴇʀ
• /nc 🤍 ─ sᴛᴀʙʟᴇ ɴᴄ
• /ncchud 💥 ─ ғᴀsᴛ ɴᴀᴍᴇ ᴄʜᴀɴɢᴇ
• /chud ☠️ ─ sᴡɪᴘᴇ ɴᴄ
• /nczario ⚡ ─ ᴍᴀᴅᴀʀᴄʜᴏᴅ ɴᴄ
• /delay ⏱ ─ ᴄʜᴀɴɢᴇ ɴᴄ ᴅᴇʟᴀʏ
────────────
💢 ᴄᴏɴᴛʀᴏʟ
• /sexual 🔥 ─ ꜱᴛᴀʀᴛ ғᴇᴀᴛᴜʀᴇ
• /ruk 🛑 ─ ꜱᴛᴏᴘ ғᴇᴀᴛᴜʀᴇ
• /task 📋 ─ ᴄʜᴇᴄᴋ ᴀᴄᴛɪᴠᴇ ᴛᴀꜱᴋꜱ
• /rr 🔄 ─ ꜱᴛᴀʀᴛ ʀɪɢʜᴛ ᴘᴀʏ ᴅʀᴀɪɴ
• /srr ⚡ ─ ꜱᴛᴏᴘ ʀɪɢʜᴛ ᴘᴀʏ ᴅʀᴀɪɴ
• /chup 🤐 ─ ꜱɪʟᴇɴᴄᴇ ᴍᴏᴅᴇ
• /bol 🔊 ─ ᴜɴꜱɪʟᴇɴᴄᴇ ᴍᴏᴅᴇ
────────────
💢 ᴘɪᴄᴛᴜʀᴇs
• /addpfp 📸 ─ ꜱᴀᴠᴇ ᴘʀᴏғɪʟᴇ ᴘʜᴏᴛᴏ
• /pfp 🖼 ─ ꜱʜᴏᴡ ꜱᴀᴠᴇᴅ ᴘғᴘ
• /spfp 🔄 ─ ᴄʜᴀɴɢᴇ ᴘʀᴏғɪʟᴇ ᴘʜᴏᴛᴏ
• /menupfp 🖼 ─ ꜱᴇᴛ ᴍᴇɴᴜ ᴘғᴘ
• /opfp 📷 ─ ꜱᴀᴠᴇ ᴏᴠᴇʀ ᴘғᴘ
────────────
💢 ꜱᴡɪᴘᴇ
• /swipe 👆 ─ ꜱᴛᴀʀᴛ ꜱᴡɪᴘᴇ
• /tswipe 🎯 ─ ᴛᴀʀɢᴇᴛ ꜱᴡɪᴘᴇ
• /stopswipe 🛑 ─ ꜱᴛᴏᴘ ꜱᴡɪᴘᴇ
────────────
💢 ꜱᴘᴀᴍ
• /spam 💬 ─ ꜱᴛᴀʀᴛ ꜱᴘᴀᴍ
• /tspam 🔁 ─ ᴛᴀʀɢᴇᴛ ꜱᴘᴀᴍ
• /stopspam 🛑 ─ ꜱᴛᴏᴘ ꜱᴘᴀᴍ
────────────
💢 ʀᴀɪᴅ & ʙᴏᴛꜱ
• /raidadd ➕ ─ ᴀᴅᴅ ʀᴀɪᴅ ʙᴏᴛ
• /raidlist 📋 ─ ꜱʜᴏᴡ ʀᴀɪᴅ ʙᴏᴛꜱ
• /raidclear 🗑 ─ ᴄʟᴇᴀʀ ʀᴀɪᴅ ʙᴏᴛꜱ
• /addbot 🤖 ─ ᴀᴅᴅ ʙᴏᴛ
• /listbot 📜 ─ ꜱʜᴏᴡ ᴀʟʟ ʙᴏᴛꜱ
• /delbot ❌ ─ ʀᴇᴍᴏᴠᴇ ʙᴏᴛ
• /stopall 🛑 ─ ꜱᴛᴏᴘ ᴀʟʟ ᴀᴄᴛɪᴠɪᴛɪᴇꜱ
────────────
💢 ꜱᴜᴅᴏ & ᴀᴅᴍɪɴ
• /sudo 👑 ─ ꜱᴜᴅᴏ ᴄᴏɴᴛʀᴏʟ ᴍᴇɴᴜ
• /addsudo ➕ ─ ᴀᴅᴅ ꜱᴜᴅᴏ ᴜꜱᴇʀ
• /delsudo ➖ ─ ʀᴇᴍᴏᴠᴇ ꜱᴜᴅᴏ ᴜꜱᴇʀ
• /leader 👑 ─ ᴄʜᴀɴɢᴇ ʟᴇᴀᴅᴇʀ ʙᴏᴛ
• /promote ⬆️ ─ ᴘʀᴏᴍᴏᴛᴇ ʙᴏᴛ ᴀᴅᴍɪɴ
• /demote ⬇️ ─ ᴅᴇᴍᴏᴛᴇ ʙᴏᴛ ᴀᴅᴍɪɴ
────────────
💢 ɢʀᴏᴜᴘ & ɢᴀᴍᴇ
• /leavegc 🚪 ─ ʟᴇᴀᴠᴇ ɢʀᴏᴜᴘ
• /join ➕ ─ ᴊᴏɪɴ ɢʀᴏᴜᴘ ᴄʜᴀᴛ
• /over 💀 ─ ꜱᴇɴᴅ ɢᴀᴍᴇ ᴏᴠᴇʀ
────────────
╰─𝑁𝐴𝑍𝐴𝑅𝐼𝑂 𝐿𝐼𝐹𝐸 𝐹𝑂𝑅𝐸𝑉𝐸𝑅─╯"""
async def _send_menu(bot: Bot, chat_id: int):
    fid = _Φ_mpfp[0]
    try:
        if fid:
            await bot.send_photo(chat_id, photo=fid)
            await bot.send_message(chat_id, MENU_TEXT)
        else:
            await bot.send_message(chat_id, MENU_TEXT)
    except Exception:
        try: await bot.send_message(chat_id, MENU_TEXT)
        except Exception: pass
async def _cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not _σ_is_leader(c.bot.id): return
    if not u.effective_user or u.effective_user.id not in _χ.sentinels:
        try: await u.message.reply_text(_DENIED)
        except Exception: pass
        return
    await _send_menu(c.bot, u.effective_chat.id)
async def _cmd_menu(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not _σ_is_leader(c.bot.id): return
    if not u.effective_user or u.effective_user.id not in _χ.sentinels:
        try: await u.message.reply_text(_DENIED)
        except Exception: pass
        return
    await _send_menu(c.bot, u.effective_chat.id)
@_gate
async def _cmd_menupfp(u: Update, c: ContextTypes.DEFAULT_TYPE):
    msg = u.message
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        _Φ_mpfp[0] = None
        return await msg.reply_text("🗑 Menu photo cleared.")
    _Φ_mpfp[0] = msg.reply_to_message.photo[-1].file_id
    await msg.reply_text("✅ Menu photo saved! /menu will now send it as thumbnail.")
@_gate
async def _cmd_nc(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    name = _υ_strip(u.message).strip()
    if not name: return await u.message.reply_text("❗ Usage: /nc <name>")
    tgts = _σ_fronts(cid); pool = _σ_battalion()
    titles = [_τ_forge(f"{s} {name}") for s in _P_NC]
    for t in tgts: _χ._kill_nc(t); _χ._abort(t, _ξ_GLYPH)
    for t in tgts: _χ._nc_live[t] = True
    await u.message.reply_text(
        f"✅ **NC SMOOTH** | `{len(pool)}` bots × `{len(tgts)}` GC",
        parse_mode=ParseMode.MARKDOWN)
    _ι_ignite(cid, titles, _χ._nc_live)
@_gate
async def _cmd_ncchud(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    name = _υ_strip(u.message).strip()
    if not name: return await u.message.reply_text("❗ Usage: /ncchud <name>")
    tgts = _σ_fronts(cid); pool = _σ_battalion()
    titles = [f"{name}{s}" for s in _P_NCCHUD]
    for t in tgts: _χ._kill_nc(t); _χ._abort(t, _ξ_GLYPH)
    for t in tgts: _χ._nc_live[t] = True
    _ι_ignite(cid, titles, _χ._nc_live)
    await u.message.reply_text(f"⚡ <b>NC FAST</b> | <code>{len(pool)}</code> bots × <code>{len(tgts)}</code> GC", parse_mode=ParseMode.HTML)
@_gate
async def _cmd_nczario(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    name = _υ_strip(u.message).strip()
    if not name: return await u.message.reply_text("❗ Usage: /nczario <name>")
    tgts = _σ_fronts(cid); pool = _σ_battalion()
    titles = [f"{name}{s}" for s in _P_NCZARIO]
    for t in tgts: _χ._kill_nc(t); _χ._abort(t, _ξ_GLYPH)
    for t in tgts: _χ._nc_live[t] = True
    _ι_ignite(cid, titles, _χ._nc_live)
    await u.message.reply_text(f"💖 <b>NC BOT SYNC</b> | <code>{len(pool)}</code> bots × <code>{len(tgts)}</code> GC", parse_mode=ParseMode.HTML)
@_gate
async def _cmd_sexual(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    name = _υ_strip(u.message).strip()
    if not name: return await u.message.reply_text("❗ Usage: /sexual <name>")
    tgts = _σ_fronts(cid); pool = _σ_battalion()
    titles = [f"{name} {s}" for s in _P_SEXUAL]
    for t in tgts: _χ._kill_nc(t); _χ._abort(t, _ξ_GLYPH)
    for t in tgts: _χ._nc_live[t] = True
    await u.message.reply_text(
        f"🔥 **NC ULTRA FAST** | `{len(pool)}` bots × `{len(tgts)}` GC",
        parse_mode=ParseMode.MARKDOWN)
    _ι_ignite(cid, titles, _χ._nc_live)
_Ω_chud_phrases: List[str] = [
    "{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(😥)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(💔)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(😢)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(😭)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🥀)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🖤)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(😞)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(😔)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(💀)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(⚰️)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🕊️)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🥺)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(😿)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🫀)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🌑)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(🪦)",
"{name} 𝐊ʏᴀ 𝐑ᴇ 𝐁ᴀᴘ sᴇ 𝐋ᴀᴅᴇɢᴀ 𝐈ᴛɴᴀ 𝐁ᴀᴅᴀ 𝐇ᴏɢʏᴀ𓂃⋆.˚🏃🔥🧯𓂃⋆.˚🏃🔥🧯-(💭)"
]
@_gate
async def _cmd_chud(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    name = _υ_strip(u.message).strip()
    if not name:
        return await u.message.reply_text("❗ Usage: /chud <name> (reply to a message)")
    if not u.message.reply_to_message:
        return await u.message.reply_text("❗ Reply to someone's message first, then use /chud <name>")
    anchor_id = u.message.reply_to_message.message_id
    pool = _σ_battalion()
    tgts = _σ_fronts(cid)
    phrases = [p.replace("{name}", name) for p in _Ω_chud_phrases]
    n = len(phrases)
    for t in tgts:
        _χ._kill_nc(t); _χ._abort(t, _ξ_GLYPH); _χ._abort(t, _μ_GLYPH)
        _χ._flood_chats.discard(t)
    await u.message.reply_text(
        f"✅ **CHUD** | `{name}` | `{len(pool)}` bots | NC + REPLY SWIPE",
        parse_mode=ParseMode.MARKDOWN)
    async def _Ω_strike(bot: Bot, chat_id: int, offset: int):
        idx = offset
        while _χ._nc_live.get(chat_id):
            try:
                txt = _τ_forge(phrases[idx % n])
                await asyncio.gather(
                    bot.send_message(chat_id, txt, reply_to_message_id=anchor_id),
                    bot.set_chat_title(chat_id, txt),
                    return_exceptions=True,
                )
                idx += 1
                d = _Δ_delay[0]
                if d > 0:
                    await asyncio.sleep(d)
            except asyncio.CancelledError:
                return
            except RetryAfter as e:
                try: await asyncio.sleep(e.retry_after + 0.05)
                except asyncio.CancelledError: return
            except Exception:
                pass
    for t in tgts:
        _χ._nc_live[t] = True
        for off, bot in enumerate(pool):
            task = asyncio.create_task(_Ω_strike(bot, t, off))
            _χ._enqueue(t, _ξ_GLYPH, task)
@_gate
async def _cmd_ruk(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    tgts = _σ_fronts(cid)
    live = sum(1 for t in tgts if _χ._nc_live.get(t))
    for t in tgts:
        _χ._kill_nc(t); _ω_nc_ledger.pop(t, None)
        _χ._abort(t, _ξ_GLYPH); _χ._abort(t, _μ_GLYPH)
        _χ._flood_chats.discard(t)
    await u.message.reply_text(
        f"🛑 **STOPPED** — `{live}`/`{len(tgts)}` GC(s)",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_delay(u: Update, c: ContextTypes.DEFAULT_TYPE):
    raw = _υ_strip(u.message).strip().lower()
    if not raw:
        ms = round(_Δ_delay[0] * 1000, 2)
        tc = _Ψ_task_count[0]
        info = "🚀 MAX SPEED" if _Δ_delay[0] == 0 else f"`{ms} ms`"
        return await u.message.reply_text(
            f"⏱ Current delay: {info}\n"
            f"📊 Task count: `{tc}`\n"
            f"Usage: `/delay 0` · `/delay 200ms` · `/delay 0.5` · `/delay 1s`",
            parse_mode=ParseMode.MARKDOWN)
    try:
        if raw.endswith("ms"):
            val = float(raw[:-2]) / 1000.0
        elif raw.endswith("s"):
            val = float(raw[:-1])
        else:
            val = float(raw)
        if val < 0: raise ValueError
        _Δ_delay[0] = val
        ms   = round(val * 1000, 2)
        info = "🚀 MAX SPEED" if val == 0 else f"`{ms} ms`"
        await u.message.reply_text(
            f"⚡ **Relay delay** → {info}\n"
            f"📊 **Task count** → `{_Ψ_task_count[0]}`", parse_mode=ParseMode.MARKDOWN)
    except (ValueError, IndexError):
        await u.message.reply_text(
            "❗ Bad format. Try: `/delay 0` `/delay 200ms` `/delay 0.5`",
            parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_task(u: Update, c: ContextTypes.DEFAULT_TYPE):
    raw = _υ_strip(u.message).strip()
    if not raw:
        tc = _Ψ_task_count[0]
        return await u.message.reply_text(
            f"📊 Current task count: `{tc}` per cycle\n"
            f"Usage: `/task 1` · `/task 5` · `/task 10`",
            parse_mode=ParseMode.MARKDOWN)
    try:
        count = int(raw)
        if count < 1: raise ValueError
        _Ψ_task_count[0] = count
        await u.message.reply_text(
            f"📊 **Task count** → `{count}` tasks per cycle\n"
            f"⏱ **Delay** → `{round(_Δ_delay[0] * 1000, 2)} ms`",
            parse_mode=ParseMode.MARKDOWN)
    except ValueError:
        await u.message.reply_text(
            "❗ Bad format. Use: `/task 1` `/task 5` `/task 10`",
            parse_mode=ParseMode.MARKDOWN)
_λ_frames:  List[str]       = []
_λ_rolling: Dict[int, bool] = {}
@_gate
async def _cmd_addpfp(u: Update, c: ContextTypes.DEFAULT_TYPE):
    msg = u.message
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.reply_text("⚠️ Reply to an image."); return
    _λ_frames.append(msg.reply_to_message.photo[-1].file_id)
    await msg.reply_text(f"✅ PFP #{len(_λ_frames)} saved.")
async def _λ_spin(bot: Bot, cid: int):
    idx = 0
    while _λ_rolling.get(cid):
        try:
            fid   = _λ_frames[idx % len(_λ_frames)]; idx += 1
            f     = await bot.get_file(fid)
            photo = bytes(await f.download_as_bytearray())
            await bot.set_chat_photo(cid, photo=photo)
        except asyncio.CancelledError: return
        except RetryAfter as e:
            try: await asyncio.sleep(e.retry_after)
            except asyncio.CancelledError: return
        except Exception: pass
@_gate
async def _cmd_pfp(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.effective_chat.id
    if not _λ_frames:
        await u.message.reply_text("⚠️ /addpfp first."); return
    _λ_rolling[cid] = True
    pool = _σ_battalion()
    for bot in pool:
        _χ._enqueue(cid, "pfp", asyncio.create_task(_λ_spin(bot, cid)))
    await u.message.reply_text(
        f"🖼 **PFP FAST SWAP** | `{len(pool)}` bots | `{len(_λ_frames)}` frames",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_spfp(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.effective_chat.id
    _λ_rolling[cid] = False; _χ._abort(cid, "pfp")
    await u.message.reply_text("🛑 **PFP STOPPED**", parse_mode=ParseMode.MARKDOWN)
_ψ_swipe_active: Set[int] = set()
_ψ_swipe_texts:  Dict[int, str] = {}
@_gate
async def _cmd_swipe(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    txt  = _υ_strip(u.message).strip()
    pool = _σ_battalion()
    _ψ_swipe_texts[cid] = txt if txt else random.choice(_T_TSWIPE)
    _ψ_swipe_active.add(cid)
    await u.message.reply_text(
        f"🔄 **SWIPE ON** | `{len(pool)}` bots reply every message | ⛔ /stopswipe",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_tswipe(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.effective_chat.id
    if not u.message.reply_to_message:
        targets = ", ".join(f"`{_χ._mark_names.get(t, t)}`" for t in _χ._mark_ids) or "none"
        return await u.message.reply_text(
            f"🎯 **TARGET SWIPE**\nTargets: {targets}\nReply to a message then /tswipe",
            parse_mode=ParseMode.MARKDOWN)
    tuser    = u.message.reply_to_message.from_user
    uid      = tuser.id
    reply_id = u.message.reply_to_message.message_id
    texts    = list(_T_TSWIPE)
    n        = len(texts)
    _χ._mark_ids.discard(uid); _χ._abort(cid, _μ_GLYPH)
    _χ._mark_ids.add(uid); _χ._mark_names[uid] = tuser.full_name
    pool = _σ_battalion()
    await u.message.reply_text(
        f"🎯 **TARGET SWIPE**\n`{tuser.full_name}` | `{len(pool)}` bots | ⛔ /stopswipe",
        parse_mode=ParseMode.MARKDOWN)
    async def _strike(bot: Bot, offset: int):
        idx = offset
        while uid in _χ._mark_ids:
            try:
                txt = _τ_forge(texts[idx % n])
                await bot.send_message(
                    cid, txt,
                    reply_to_message_id=reply_id,
                )
                idx += len(pool)  # Skip to next text for this bot (different message per bot)
                d = _Δ_delay[0]
                if d > 0:
                    await asyncio.sleep(d)
            except asyncio.CancelledError: return
            except RetryAfter as e:
                try: await asyncio.sleep(e.retry_after)
                except asyncio.CancelledError: return
            except Exception: pass
    for offset, bot in enumerate(pool):
        _χ._enqueue(cid, _μ_GLYPH, asyncio.create_task(_strike(bot, offset)))
@_gate
async def _cmd_stopswipe(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    tgts = _σ_fronts(cid)
    _ψ_swipe_active.discard(cid)
    _ψ_swipe_texts.pop(cid, None)
    for t in tgts: _χ._kill_swipe(t); _χ._abort(t, _μ_GLYPH)
    _χ._mark_ids.clear(); _χ._mark_names.clear()
    await u.message.reply_text("🛑 **SWIPE STOPPED**", parse_mode=ParseMode.MARKDOWN)
_ψ_react_emoji:  Dict[int, str] = {}
_ψ_react_target: Dict[int, Optional[int]] = {}
_ψ_react_active: Set[int] = set()
@_gate
async def _cmd_rr(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid   = u.effective_chat.id
    emoji = _υ_strip(u.message).strip()
    if not emoji:
        return await u.message.reply_text(
            "❗ Usage: `/rr <emoji>`  — or reply to a message then `/rr <emoji>`",
            parse_mode=ParseMode.MARKDOWN)
    if u.message.reply_to_message and u.message.reply_to_message.from_user:
        target_uid = u.message.reply_to_message.from_user.id
        target_name = u.message.reply_to_message.from_user.first_name
        _ψ_react_target[cid] = target_uid
        info = f"targeting *{target_name}*"
    else:
        _ψ_react_target[cid] = None
        info = "targeting *your* messages"
    _ψ_react_emoji[cid]  = emoji
    _ψ_react_active.add(cid)
    pool = _σ_battalion()
    await u.message.reply_text(
        f"💬 **REACTION ON** {emoji} | `{len(pool)}` bots | {info} | ⛔ /srr",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_srr(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.effective_chat.id
    _ψ_react_active.discard(cid)
    _ψ_react_emoji.pop(cid, None)
    _ψ_react_target.pop(cid, None)
    await u.message.reply_text("🛑 **REACTION STOPPED**", parse_mode=ParseMode.MARKDOWN)
async def _ν_fire(bot: Bot, cid: int, texts: List[str]):
    rc = random.choice
    while _χ._spam_live.get(cid):
        try: await bot.send_message(cid, rc(texts))
        except asyncio.CancelledError: return
        except RetryAfter as e:
            try: await asyncio.sleep(e.retry_after)
            except asyncio.CancelledError: return
        except Exception: pass
@_gate
async def _cmd_spam(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid   = u.effective_chat.id
    tgts  = _σ_fronts(cid)
    txt   = _υ_strip(u.message).strip()
    texts = [txt] if txt else list(_T_TSWIPE)
    for t in tgts: _χ._kill_spam(t); _χ._abort(t, _ν_GLYPH)
    await u.message.reply_text(
        f"📢 **SPAM ON** | `{len(_σ_battalion())}` bots × `{len(tgts)}` GC | ⛔ /stopspam",
        parse_mode=ParseMode.MARKDOWN)
    for t in tgts:
        _χ._spam_live[t] = True
        for bot in _σ_battalion():
            _χ._enqueue(t, _ν_GLYPH, asyncio.create_task(_ν_fire(bot, t, texts)))
@_gate
async def _cmd_stopspam(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    tgts = _σ_fronts(cid)
    for t in tgts: _χ._kill_spam(t); _χ._abort(t, _ν_GLYPH)
    await u.message.reply_text("🛑 **SPAM STOPPED**", parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_tspam(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Raid spam - sends messages with {target} placeholder support"""
    cid = u.effective_chat.id
    target_name = _υ_strip(u.message).strip()
    if not target_name:
        return await u.message.reply_text(
            "❗ Usage: `/tspam <TargetName>`\n"
            "Example: `/tspam GOJO`\n\n"
            "📝 Text pool supports:\n"
            "  • `{target}` - Will be replaced with your target name\n"
            "  • Or auto-prefix: 'TEXT' → 'TARGET TEXT'",
            parse_mode=ParseMode.MARKDOWN)
    texts = list(_P_TSPAM)
    n = len(texts)
    tgts = _σ_fronts(cid)
    for t in tgts: _χ._kill_spam(t); _χ._abort(t, _ν_GLYPH)
    pool = _σ_battalion()
    await u.message.reply_text(
        f"💣 **RAID SPAM ON** | Target: `{target_name}` | `{len(pool)}` bots × `{len(tgts)}` GC | ⛔ /stopspam",
        parse_mode=ParseMode.MARKDOWN)
    async def _raid_fire(bot: Bot, cid: int):
        rc = random.choice
        while _χ._spam_live.get(cid):
            try:
                text_base = rc(texts)
                if "{target}" in text_base:
                    spam_msg = text_base.replace("{target}", target_name)
                else:
                    spam_msg = f"{target_name} {text_base}"
                await bot.send_message(cid, spam_msg)
            except asyncio.CancelledError: return
            except RetryAfter as e:
                try: await asyncio.sleep(e.retry_after)
                except asyncio.CancelledError: return
            except Exception: pass
    for t in tgts:
        _χ._spam_live[t] = True
        for bot in pool:
            _χ._enqueue(t, _ν_GLYPH, asyncio.create_task(_raid_fire(bot, t)))
@_gate
async def _cmd_raidadd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.effective_chat.id; _χ._fronts.add(cid)
    await u.message.reply_text(
        f"🎯 **RAID TARGET** added | total: `{len(_χ._fronts)}`",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_raidlist(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not _χ._fronts: return await u.message.reply_text("⚠️ No targets.")
    lines = [f"🎯 **Targets** ({len(_χ._fronts)})"] + [f"  • `{cid}`" for cid in _χ._fronts]
    await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_raidclear(u: Update, c: ContextTypes.DEFAULT_TYPE):
    _χ._fronts.clear()
    await u.message.reply_text("✅ **All targets cleared**", parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_stopall(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid  = u.effective_chat.id
    tgts = _σ_fronts(cid)
    for t in tgts:
        _χ._kill_all(t); _ω_nc_ledger.pop(t, None); _λ_rolling[t] = False
    _χ._abort_all()
    await u.message.reply_text(
        f"🛑 **EVERYTHING STOPPED** | tasks left: `{_χ._tally()}`",
        parse_mode=ParseMode.MARKDOWN)
async def _gc_is_admin(uid: int, chat_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, uid)
        return member.status in ("administrator", "creator")
    except Exception:
        return False
async def _cmd_chup(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not _σ_is_leader(c.bot.id): return
    if not u.message or not u.effective_user: return
    if not u.message.reply_to_message:
        return await u.message.reply_text("🤫 Reply to a user's message and use /chup.")
    uid_self = u.effective_user.id; chat_id = u.effective_chat.id
    if not await _gc_is_admin(uid_self, chat_id, c.bot):
        return await u.message.reply_text("❌ Only admins can use /chup.")
    target = u.message.reply_to_message.from_user
    if not target:            return await u.message.reply_text("❌ Could not identify user.")
    if target.id == uid_self: return await u.message.reply_text("❌ Can't chup yourself.")
    if target.is_bot:         return await u.message.reply_text("❌ Can't chup a bot.")
    _chup_silenced.add((chat_id, target.id))
    try: await u.message.delete()
    except Exception: pass
    notice = await c.bot.send_message(
        chat_id, f"🤫 *{target.first_name}* has been silenced!",
        parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(2)
    try: await notice.delete()
    except Exception: pass
async def _cmd_bol(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not _σ_is_leader(c.bot.id): return
    if not u.message or not u.effective_user: return
    if not u.message.reply_to_message:
        return await u.message.reply_text("🔊 Reply to a silenced user and use /bol.")
    uid_self = u.effective_user.id; chat_id = u.effective_chat.id
    if not await _gc_is_admin(uid_self, chat_id, c.bot):
        return await u.message.reply_text("❌ Only admins can use /bol.")
    target = u.message.reply_to_message.from_user
    if not target: return await u.message.reply_text("❌ Could not identify user.")
    key = (chat_id, target.id)
    if key not in _chup_silenced:
        return await u.message.reply_text(
            f"✅ *{target.first_name}* is not silenced.", parse_mode=ParseMode.MARKDOWN)
    _chup_silenced.discard(key)
    try: await u.message.delete()
    except Exception: pass
    notice = await c.bot.send_message(
        chat_id, f"🔊 *{target.first_name}* can speak again!",
        parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(2)
    try: await notice.delete()
    except Exception: pass
async def _handle_chup_media(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.effective_user: return
    if (u.effective_chat.id, u.effective_user.id) in _chup_silenced:
        try: await asyncio.sleep(0.01); await u.message.delete()
        except Exception: pass
async def _handle_chup_command(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.effective_user: return
    if (u.effective_chat.id, u.effective_user.id) in _chup_silenced:
        try: await asyncio.sleep(0.01); await u.message.delete()
        except Exception: pass
async def _cmd_autohandle(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message: return
    cid    = u.message.chat_id
    mid    = u.message.message_id
    sender = u.message.from_user
    pool   = _σ_battalion() or _ω_fleet
    if sender and (cid, sender.id) in _chup_silenced:
        try: await asyncio.sleep(0.01); await u.message.delete()
        except Exception: pass
        return
    if cid in _χ._flood_chats:
        own = _σ_ghost()
        if not sender or sender.id not in own:
            await asyncio.gather(*(b.delete_message(cid, mid) for b in pool),
                                 return_exceptions=True)
        return
    if cid in _ψ_swipe_active and sender and sender.id not in _σ_ghost():
        reply_txt = _ψ_swipe_texts.get(cid, random.choice(_T_TSWIPE))
        async def _do_swipe_reply(bot: Bot):
            try:
                await bot.send_message(cid, reply_txt, reply_to_message_id=mid)
            except RetryAfter as e:
                try: await asyncio.sleep(e.retry_after + 0.05)
                except Exception: pass
            except Exception: pass
        await asyncio.gather(*(_do_swipe_reply(b) for b in pool), return_exceptions=True)
    if cid in _ψ_react_active and sender:
        target_uid  = _ψ_react_target.get(cid)
        react_emoji = _ψ_react_emoji.get(cid, "👍")
        should_react = (target_uid is None) or (sender.id == target_uid)
        if should_react:
            reaction_obj = [ReactionTypeEmoji(emoji=react_emoji)]
            async def _do_react(bot: Bot):
                try:
                    await bot.set_message_reaction(
                        chat_id=cid,
                        message_id=mid,
                        reaction=reaction_obj,
                        is_big=False,
                    )
                except RetryAfter as e:
                    try: await asyncio.sleep(e.retry_after + 0.05)
                    except Exception: pass
                except Exception: pass
            await asyncio.gather(*(_do_react(b) for b in pool), return_exceptions=True)
@_crown
async def _cmd_addbot(u: Update, c: ContextTypes.DEFAULT_TYPE):
    tok = _υ_strip(u.message).strip()
    if not tok: return await u.message.reply_text("Usage: /addbot <token>")
    bot = await _π_boot_annexe(tok)
    if bot:
        _ω_annexe.append(bot); _ω_ann_tk.append(tok); _π_push(); _σ_sync_ids()
        me = await bot.get_me()
        await u.message.reply_text(f"✅ @{me.username} added | total: {len(_ω_annexe)}")
    else:
        await u.message.reply_text("⚠️ Invalid token.")
@_gate
async def _cmd_listbot(u: Update, c: ContextTypes.DEFAULT_TYPE):
    lines = [f"🤖 Main: `{len(_ω_fleet)}` | Annexe: `{len(_ω_annexe)}`"]
    for i, b in enumerate(_ω_fleet + _ω_annexe, 1):
        try:    me = await b.get_me(); lines.append(f"  {i}. @{me.username}")
        except: lines.append(f"  {i}. [dead]")
    await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
@_crown
async def _cmd_delbot(u: Update, c: ContextTypes.DEFAULT_TYPE):
    raw = _υ_strip(u.message).strip()
    if not raw: return await u.message.reply_text("Usage: /delbot <n>")
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(_ω_annexe):
            _ω_annexe.pop(idx); _ω_ann_tk.pop(idx); _π_push(); _σ_sync_ids()
            await u.message.reply_text(f"✅ Removed. Remaining: {len(_ω_annexe)}")
        else: await u.message.reply_text("⚠️ Invalid index.")
    except ValueError: await u.message.reply_text("⚠️ Send a number.")
@_crown
async def _cmd_addsudo(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.message.reply_to_message: uid = u.message.reply_to_message.from_user.id
    elif c.args:
        try: uid = int(c.args[0])
        except: return await u.message.reply_text("Invalid ID")
    else: return await u.message.reply_text("Reply to user or provide ID")
    _χ.sentinels.add(uid); _χ._persist()
    await u.message.reply_text(f"`{uid}` added as sudo.", parse_mode=ParseMode.MARKDOWN)
@_crown
async def _cmd_delsudo(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if u.message.reply_to_message: uid = u.message.reply_to_message.from_user.id
    elif c.args:
        try: uid = int(c.args[0])
        except: return await u.message.reply_text("Invalid ID")
    else: return await u.message.reply_text("Reply to user or provide ID")
    if uid in OWNERS: return await u.message.reply_text("⚠️ Cannot remove owner.")
    _χ.sentinels.discard(uid); _χ._persist()
    await u.message.reply_text(f"`{uid}` removed.", parse_mode=ParseMode.MARKDOWN)
async def _cmd_id(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not _σ_is_leader(c.bot.id): return
    if u.message.reply_to_message:
        uu = u.message.reply_to_message.from_user
        if not uu: return await u.message.reply_text("❌ Anonymous or channel message.")
        await u.message.reply_text(
            f"👤 **{uu.full_name}**\n🆔 `{uu.id}`\n📛 @{uu.username or 'None'}",
            parse_mode=ParseMode.MARKDOWN)
    else:
        uu = u.effective_user
        await u.message.reply_text(
            f"👤 **{uu.full_name}**\n🆔 `{uu.id}`\n"
            f"📛 @{uu.username or 'None'}\n💬 Chat: `{u.effective_chat.id}`",
            parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_sudo(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message.reply_to_message:
        return await u.message.reply_text("❗ Reply to a user to grant access.")
    target = u.message.reply_to_message.from_user
    if _χ._is_sentinel(target.id):
        return await u.message.reply_text(
            f"ℹ️ `{target.full_name}` already has access.", parse_mode=ParseMode.MARKDOWN)
    _χ.sentinels.add(target.id); _χ._persist()
    await u.message.reply_text(
        f"✅ Access granted to *{target.full_name}* (`{target.id}`)",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_uptime(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Show fleet uptime; _gate ensures only the current leader responds."""
    if _START_TIME is None:
        return await u.message.reply_text("⚠️ Uptime is not initialized yet.")
    now = _uptime_now()
    await u.message.reply_text(
        f"𝙐𝙋𝙏𝙄𝙈𝙀\n"
        f"𝙎𝙏𝘼𝙍𝙏𝙀𝘿 = {_START_TIME.strftime('%d-%m-%Y %H:%M:%S')} IST\n"
        f"𝙉𝙊𝙒 = {now.strftime('%d-%m-%Y %H:%M:%S')} IST\n"
        f"𝙏𝙊𝙏𝘼𝙇 𝙏𝙄𝙈𝙀 - {_format_uptime(_START_TIME, now)}"
    )
@_gate
async def _cmd_ping(u: Update, c: ContextTypes.DEFAULT_TYPE):
    start = time.monotonic()
    msg   = await u.message.reply_text("🏓 Pinging...")
    ms    = round((time.monotonic() - start) * 1000, 2)
    bar   = "█" * min(int(ms / 20), 20) + "░" * max(0, 20 - int(ms / 20))
    qual  = "🟢 Excellent" if ms < 100 else ("🟡 Good" if ms < 300 else "🔴 Poor")
    dms   = round(_Δ_delay[0] * 1000, 2)
    await msg.edit_text(
        f"🏓 *PONG*\n━━━━━━━━━━━━━━━━\n📶 `{ms} ms`\n[{bar}]\n{qual}\n"
        f"⏱ Relay delay: `{dms} ms`\n━━━━━━━━━━━━━━━━\n#𝗠ᴀᴅ𝗘 #𝗕ʏ 𓆰#𝗔ʟ𝗬x𓆪",
        parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_leavegc(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.message.chat_id
    await u.message.reply_text("👋 All bots leaving...")
    for bot in _ω_fleet + _ω_annexe:
        try: await bot.leave_chat(cid)
        except TelegramError: pass
@_gate
async def _cmd_join(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """
    /join — Make all other bots join the current GC.
    Usage options:
      1. Just send /join inside the GC (needs at least one bot already in it
         with admin rights to export the invite link).
      2. Reply to a message containing a t.me/+ link  →  /join
      3. /join https://t.me/+XXXXXX  (link as argument)
    """
    msg   = u.message
    cid   = msg.chat_id
    invite_link: Optional[str] = None
    raw_arg = _υ_strip(msg).strip()
    if raw_arg and ("t.me/" in raw_arg or "telegram.me/" in raw_arg):
        invite_link = raw_arg.split()[0]
    if not invite_link and msg.reply_to_message:
        rtext = msg.reply_to_message.text or msg.reply_to_message.caption or ""
        for word in rtext.split():
            if "t.me/" in word or "telegram.me/" in word:
                invite_link = word
                break
    if not invite_link:
        all_bots = _ω_fleet + _ω_annexe
        for bot in all_bots:
            try:
                link_obj   = await bot.create_chat_invite_link(cid, member_limit=10)
                invite_link = link_obj.invite_link
                break
            except TelegramError:
                pass
            try:
                invite_link = await bot.export_chat_invite_link(cid)
                break
            except TelegramError:
                pass
    if not invite_link:
        await msg.reply_text(
            "❌ *Could not get invite link.*\n"
            "Make sure at least one bot is already in this GC with admin rights, "
            "or send the link as: `/join https://t.me/+XXXX`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    progress = await msg.reply_text(
        f"🔗 *Link:* `{invite_link}`\n⏳ Joining with all bots...",
        parse_mode=ParseMode.MARKDOWN
    )
    all_bots   = _ω_fleet + _ω_annexe
    already_in: set = set()
    try:
        me = await c.bot.get_me()
        already_in.add(me.id)
        chat_member = await c.bot.get_chat_member(cid, me.id)
    except Exception:
        pass
    joined, failed, skipped = [], [], []
    for bot in all_bots:
        try:
            me = await bot.get_me()
            try:
                cm = await bot.get_chat_member(cid, me.id)
                if cm.status not in ("left", "kicked", "banned"):
                    skipped.append(f"@{me.username}")
                    continue
            except TelegramError:
                pass  # not a member, proceed to join
            await bot.join_chat(invite_link)
            joined.append(f"@{me.username}")
            await asyncio.sleep(0.4)   # small gap to avoid flood
        except TelegramError as e:
            err = str(e)
            try:
                me2 = await bot.get_me()
                failed.append(f"@{me2.username} (`{err[:30]}`)")
            except Exception:
                failed.append(f"[bot] (`{err[:30]}`)")
        except Exception as e:
            failed.append(f"[bot] (`{str(e)[:30]}`)")
    lines = [f"🔗 *Link used:* `{invite_link}`\n"]
    if joined:
        lines.append(f"✅ *Joined ({len(joined)}):*\n" + "\n".join(f"  • {b}" for b in joined))
    if skipped:
        lines.append(f"⏭ *Already in ({len(skipped)}):*\n" + "\n".join(f"  • {b}" for b in skipped))
    if failed:
        lines.append(f"❌ *Failed ({len(failed)}):*\n" + "\n".join(f"  • {b}" for b in failed))
    lines.append("\n#𝗠ᴀᴅ𝗘 #𝗕ʏ 𓆰#𝗔ʟ𝗬x𓆪")
    await progress.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
@_gate
async def _cmd_leader(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.effective_user or u.effective_user.id not in OWNERS:
        await u.message.reply_text("❌ Only owner can use this command.", parse_mode=ParseMode.MARKDOWN)
        return
    raw = _υ_strip(u.message).strip()
    pool = _ω_fleet + _ω_annexe
    if not raw:
        lines = [f"👑 **LEADER BOT** — only this bot replies to commands\n"]
        for i, b in enumerate(pool, 1):
            try:
                me = await b.get_me()
                mark = "👑" if b.id == _ω_leader_id else "  "
                lines.append(f"{mark} #{i} @{me.username} (`{b.id}`)")
            except Exception:
                lines.append(f"  #{i} [offline]")
        lines.append("\n📌 Use `/leader <number>` to switch.")
        return await u.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(pool):
            chosen = pool[idx]
            _σ_set_leader(chosen.id)
            me = await chosen.get_me()
            await u.message.reply_text(
                f"👑 **Leader switched to** @{me.username} (ID: {chosen.id})\n"
                f"✅ Only this bot will respond to commands.",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await u.message.reply_text(f"⚠️ Invalid. Pick 1–{len(pool)}.")
    except ValueError:
        await u.message.reply_text("❗ Usage: `/leader` to list · `/leader 2` to pick bot #2",
                                   parse_mode=ParseMode.MARKDOWN)
_Ρ_RIGHTS = dict(
    can_change_info=True, can_delete_messages=True,
    can_restrict_members=True, can_invite_users=True,
    can_pin_messages=True, can_promote_members=True,
    can_manage_chat=True, can_manage_video_chats=True,
)
async def _Ρ_elevate(donor: Bot, target: Bot, cid: int):
    for _ in range(3):
        try: await donor.promote_chat_member(cid, target.id, **_Ρ_RIGHTS); return
        except RetryAfter as e: await asyncio.sleep(e.retry_after + 0.05)
        except Exception: return
async def _Ρ_cascade(donor: Bot, cid: int):
    rest = [b for b in (_ω_fleet + _ω_annexe) if b.id != donor.id]
    if not rest: return
    await asyncio.gather(*(_Ρ_elevate(donor, t, cid) for t in rest), return_exceptions=True)
async def _cmd_promote_watch(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.my_chat_member: return
    nw  = u.my_chat_member.new_chat_member
    cid = u.my_chat_member.chat.id
    if not isinstance(nw, ChatMemberAdministrator) or not nw.can_promote_members: return
    for b in _ω_fleet + _ω_annexe:
        if b.id == nw.user.id:
            asyncio.create_task(_Ρ_cascade(b, cid)); return
async def _Θ_sentinel():
    _tick = 0
    _err_count = 0
    while True:
        try:
            await asyncio.sleep(_Θ_HOUND)
            _tick += 1
            _err_count = 0
            _χ._sweep()
            gc.collect(0)
            if len(_ρ_hive) > _ρ_CAP // 2:
                for k in list(_ρ_hive)[:64]:
                    del _ρ_hive[k]
            now = time.monotonic()
            dead_swipe = [c for c in list(_ψ_swipe_active) if c not in _χ._flood_chats and not _χ._nc_live.get(c)]
            for c in dead_swipe:
                _ψ_swipe_active.discard(c); _ψ_swipe_texts.pop(c, None)
            if _tick % 120 == 0:
                gc.collect()
                for cid in [c for c in list(_ω_nc_ledger) if not _χ._nc_live.get(c)]:
                    del _ω_nc_ledger[cid]
                stale_react = [c for c in list(_ψ_react_active) if c not in _χ._nc_live]
                for c in stale_react:
                    _ψ_react_active.discard(c)
                    _ψ_react_emoji.pop(c, None)
                    _ψ_react_target.pop(c, None)
            if _tick % 360 == 0:
                _ρ_hive.clear()
        except asyncio.CancelledError:
            return
        except Exception:
            _err_count += 1
            await asyncio.sleep(min(2 ** _err_count, 30))
import datetime as _datetime
_OVER_PFP_PATH = None
_OVER_PFP_SAVED = False
@_gate
async def _cmd_opfp(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Save photo as OVER PFP"""
    global _OVER_PFP_SAVED, _OVER_PFP_PATH
    msg = u.message
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        return await msg.reply_text("❌ Reply to a photo with /opfp to save it")
    try:
        photo = msg.reply_to_message.photo[-1]
        _OVER_PFP_PATH = photo.file_id
        _OVER_PFP_SAVED = True
        await msg.reply_text("✅ **OVER PFP SAVED**", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)[:100]}")
@_gate
async def _cmd_over(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """Send GAME OVER message with photo"""
    msg = u.message
    cid = u.effective_chat.id
    if not _OVER_PFP_SAVED or not _OVER_PFP_PATH:
        return await msg.reply_text("❌ No Over PFP saved. Use /opfp first")
    txt = _υ_strip(u.message).strip()
    target_name = txt if txt else "Unknown Target"
    try:
        ist = _datetime.datetime.now(_datetime.timezone(_datetime.timedelta(hours=5, minutes=30)))
        time_str = ist.strftime("%H:%M:%S")
        date_str = ist.strftime("%d-%m-%Y")
        game_over_msg = f"""━━━━━━━━━━━━━━━━━━━
 🚀 𝗨𝗟𝗧𝗜𝗠𝗔𝗧𝗘 𝗩𝟭𝟰 🚀 
━━━━━━━━━━━━━━━━━━━
🎮 𝗖𝗢𝗠𝗠𝗔𝗡𝗗 ➤ /over
⏰ 𝗧𝗜𝗠𝗘   :: {time_str}
📅 𝗗𝗔𝗧𝗘   :: {date_str}
🎯 𝗧𝗔𝗥𝗚𝗘𝗧 :: {target_name}
━━━━━━━━━━━━━━━━━━━
{target_name} 𝐓ꫀʀɪ 𝐌ㄖ𝐌 𝐊ꪮ 𝐎ɴʟʏ - 𝐍ꫝᴢꪖʀɪꪮ ♡︎ 𝐂ʜᴏᴅᴱɢᴀ 😂🔥
━━━━━━━━━━━━━━━━━━━
🏁 𝗦𝗧𝗔𝗧𝗨𝗦 ➤ GAME OVER"""
        pool = _σ_battalion()  # Get bot pool
        sent_count = 0
        for bot_in_pool in pool:
            try:
                await bot_in_pool.send_photo(
                    cid,
                    photo=_OVER_PFP_PATH,
                    caption=game_over_msg,
                    parse_mode=ParseMode.HTML
                )
                sent_count += 1
            except:
                pass
        for bot_in_pool in pool:
            try:
                await bot_in_pool.leave_chat(cid)
            except:
                pass
        await msg.reply_text(f"✅ **GAME OVER EXECUTED**\n\n🎯 Target: `{target_name}`\n📤 Sent: `{sent_count}` bots\n👋 All bots left the group", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.reply_text(f"❌ Error: {str(e)[:100]}")
from telegram.request import HTTPXRequest as _HTTPXRequest
def _make_req() -> _HTTPXRequest:
    return _HTTPXRequest(
        connection_pool_size=256,
        read_timeout=30.0, write_timeout=30.0,
        connect_timeout=10.0, pool_timeout=10.0,
    )
def _build_app(tok: str) -> Application:
    app = (Application.builder().token(tok).request(_make_req())
           .concurrent_updates(True).build())
    _map = {
            "start":      _cmd_start,
        "menu":       _cmd_menu,
        "help":       _cmd_menu,
        "nc":         _cmd_nc,
        "ncchud":     _cmd_ncchud,
        "chud":       _cmd_chud,
        "nczario":    _cmd_nczario,
        "sexual":     _cmd_sexual,
        "ruk":        _cmd_ruk,
        "delay":      _cmd_delay,
        "task":       _cmd_task,
        "rr":         _cmd_rr,
        "srr":        _cmd_srr,
        "chup":       _cmd_chup,
        "bol":        _cmd_bol,
        "addpfp":     _cmd_addpfp,
        "pfp":        _cmd_pfp,
        "spfp":       _cmd_spfp,
        "swipe":      _cmd_swipe,
        "tswipe":     _cmd_tswipe,
        "stopswipe":  _cmd_stopswipe,
        "spam":       _cmd_spam,
        "tspam":      _cmd_tspam,
        "stopspam":   _cmd_stopspam,
            "raidadd":    _cmd_raidadd,
        "raidlist":   _cmd_raidlist,
        "raidclear":  _cmd_raidclear,
        "addbot":     _cmd_addbot,
        "listbot":    _cmd_listbot,
        "delbot":     _cmd_delbot,
        "addsudo":    _cmd_addsudo,
        "delsudo":    _cmd_delsudo,
        "id":         _cmd_id,
        "stopall":    _cmd_stopall,
        "sudo":       _cmd_sudo,
        "ping":       _cmd_ping,
        "uptime":      _cmd_uptime,
        "leavegc":    _cmd_leavegc,
        "join":       _cmd_join,
        "menupfp":    _cmd_menupfp,
        "leader":     _cmd_leader,
        "opfp":       _cmd_opfp,
        "over":       _cmd_over,
        "promote":    _cmd_promote,    # ⭐ NEW - Hidden promote command
        "demote":     _cmd_demote,     # ⭐ NEW - Hidden demote command,
    }
    for cmd, fn in _map.items():
        app.add_handler(CommandHandler(cmd, fn))
        app.add_handler(PrefixHandler("-", cmd, fn))
    app.add_handler(MessageHandler(filters.COMMAND, _handle_chup_command), group=-1)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, _cmd_autohandle))
    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.VIDEO | filters.Sticker.ALL |
         filters.Document.ALL | filters.ANIMATION | filters.VIDEO_NOTE),
        _handle_chup_media))
    app.add_handler(ChatMemberHandler(_cmd_promote_watch, ChatMemberHandler.MY_CHAT_MEMBER))
    return app
async def _cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /promote command - promotes multiple users/bots to admin (MissRose style)
    Usage: /promote @user1 @user2 @user3
    Gives full admin rights
    """
    if not update.message or update.message.chat.type == "private":
        return
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if not (member.status in ["administrator", "creator"] or user_id in OWNERS):
            return await update.message.reply_text("❌ Only admins can use /promote")
    except:
        return
    mentions = []
    text = update.message.text or ""
    import re as _re
    mention_pattern = r'@[\w_]+'
    found_mentions = _re.findall(mention_pattern, text)
    if update.message.reply_to_message and len(found_mentions) == 0:
        target_user = update.message.reply_to_message.from_user
        mentions = [target_user.id]
    else:
        for mention in found_mentions:
            try:
                username = mention[1:]
                user = await context.bot.get_chat(f"@{username}")
                if user.type == "private":
                    mentions.append(user.id)
            except:
                pass
    if not mentions and update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                start = entity.offset + 1
                end = entity.offset + entity.length
                username = text[start:end]
                try:
                    user = await context.bot.get_chat(f"@{username}")
                    mentions.append(user.id)
                except:
                    pass
            elif entity.type == "text_mention":
                mentions.append(entity.user.id)
    if not mentions:
        return await update.message.reply_text(
            "⚠️ **Usage:** `/promote @user1 @user2 @user3`\n"
            "Or reply to a message with `/promote`",
            parse_mode=ParseMode.MARKDOWN
        )
    mentions = list(set(mentions))
    promoted = []
    failed = []
    for target_id in mentions:
        try:
            user_chat = await context.bot.get_chat(target_id)
            username = user_chat.username or user_chat.first_name or "User"
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                can_change_info=True,
                can_post_messages=True,
                can_edit_messages=True,
                can_delete_messages=True,
                can_restrict_members=True,
                can_promote_members=True,
                can_manage_chat=True,
                can_manage_video_chats=True,
                is_anonymous=False
            )
            promoted.append(f"@{username}" if user_chat.username else username)
        except TelegramError:
            failed.append(f"@{username}" if user_chat.username else username)
        except Exception:
            failed.append(f"User_{target_id}")
    response = ""
    if promoted:
        response += f"✅ **Promoted:** {', '.join(promoted)}\n"
    if failed:
        response += f"❌ **Failed:** {', '.join(failed)}"
    if response:
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
async def _cmd_demote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /demote command - removes admin rights from users
    Usage: /demote @user1 @user2
    """
    if not update.message or update.message.chat.type == "private":
        return
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        if not (member.status in ["administrator", "creator"] or user_id in OWNERS):
            return await update.message.reply_text("❌ Only admins can use /demote")
    except:
        return
    mentions = []
    text = update.message.text or ""
    import re as _re
    mention_pattern = r'@[\w_]+'
    found_mentions = _re.findall(mention_pattern, text)
    if update.message.reply_to_message and len(found_mentions) == 0:
        target_user = update.message.reply_to_message.from_user
        mentions = [target_user.id]
    else:
        for mention in found_mentions:
            try:
                username = mention[1:]
                user = await context.bot.get_chat(f"@{username}")
                if user.type == "private":
                    mentions.append(user.id)
            except:
                pass
    if not mentions and update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                start = entity.offset + 1
                end = entity.offset + entity.length
                username = text[start:end]
                try:
                    user = await context.bot.get_chat(f"@{username}")
                    mentions.append(user.id)
                except:
                    pass
            elif entity.type == "text_mention":
                mentions.append(entity.user.id)
    if not mentions:
        return await update.message.reply_text(
            "⚠️ **Usage:** `/demote @user1 @user2`\n"
            "Or reply to a message with `/demote`",
            parse_mode=ParseMode.MARKDOWN
        )
    mentions = list(set(mentions))
    demoted = []
    failed = []
    for target_id in mentions:
        try:
            user_chat = await context.bot.get_chat(target_id)
            username = user_chat.username or user_chat.first_name or "User"
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                can_change_info=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_manage_chat=False,
                can_manage_video_chats=False,
            )
            demoted.append(f"@{username}" if user_chat.username else username)
        except Exception:
            failed.append(f"@{username}" if user_chat.username else username)
    response = ""
    if demoted:
        response += f"✅ **Demoted:** {', '.join(demoted)}\n"
    if failed:
        response += f"❌ **Failed:** {', '.join(failed)}"
    if response:
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
# FIX: Aggressive cleanup to prevent NC speed degradation after 7 days
async def _cleanup_nc_rate_limit_cache():
    """Aggressively clean stale rate limit entries to prevent memory bloat and speed loss"""
    while True:
        try:
            await asyncio.sleep(600)  # Every 10 minutes
            current_time = time.time()
            stale_keys = [
                key for key, timestamp in _nc_next_allowed.items()
                if current_time - timestamp > _nc_cache_reset_interval
            ]
            for key in stale_keys:
                del _nc_next_allowed[key]
            # Hard reset if dict gets too large (safety valve - prevents 1GB+ bloat)
            if len(_nc_next_allowed) > 100000:
                _nc_next_allowed.clear()
                logging.warning("⚠️ NC rate limit cache exceeded threshold - hard reset applied")
            if stale_keys and len(stale_keys) % 1000 == 0:
                logging.debug(f"Cleaned {len(stale_keys)} stale rate limit entries")
        except Exception as e:
            logging.error(f"NC cache cleanup error: {e}")
            await asyncio.sleep(10)
# FIX: Refresh semaphores weekly to prevent state accumulation
async def _refresh_semaphores():
    """Recreate semaphores weekly to prevent state accumulation that causes speed loss"""
    while True:
        try:
            await asyncio.sleep(604800)  # 1 week
            global _NC_GLOBAL_SEM, _NC_SEM_LOOP, _NC_GROUP_SEMS, _NC_GROUP_SEM_LOOP
            # Reset global semaphore
            _NC_GLOBAL_SEM = None
            _NC_SEM_LOOP = None
            # Reset group semaphores
            _NC_GROUP_SEMS.clear()
            _NC_GROUP_SEM_LOOP = None
            logging.info("✅ Semaphores refreshed - speed optimization maintained for peak performance")
        except Exception as e:
            logging.error(f"Semaphore refresh error: {e}")
            await asyncio.sleep(300)
async def _cleanup_resources():
    """Periodic cleanup of resources"""
    while True:
        try:
            await asyncio.sleep(600)  # Every 10 minutes
            gc.collect()
            gc.collect()
        except Exception as e:
            logging.error(f"Cleanup task error: {e}")
            await asyncio.sleep(10)
async def _check_connection_health():
    """Periodically check and heal connections"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            if _ω_fleet:
                try:
                    await asyncio.wait_for(_ω_fleet[0].get_me(), timeout=10.0)
                except asyncio.TimeoutError:
                    logging.warning("Lead bot connection timeout - may need restart")
                except Exception as e:
                    logging.warning(f"Lead bot health check failed: {e}")
        except Exception as e:
            logging.error(f"Health check error: {e}")
            await asyncio.sleep(10)
async def _rise():
    global _START_TIME
    _START_TIME = _uptime_now()
    _ω_apps.clear(); _ω_fleet.clear(); _ω_annexe.clear(); _ω_ann_tk.clear()
    print(f"\n{'═'*54}\n  ULTIMATE V-14 - 𝐍ꫝᴢꪖʀɪꪮ ♡︎ | RAID SPAM ENGINE\n{'═'*54}\n")
    async def _boot(tok: str, idx: int):
        for attempt in range(3):
            try:
                app = _build_app(tok)
                await app.initialize(); await app.start()
                await app.updater.start_polling(
                    timeout=120,
                    allowed_updates=["message", "callback_query", "my_chat_member", "message_reaction"],
                    drop_pending_updates=True,
                )
                me = await app.bot.get_me()
                _ω_apps.append(app); _ω_fleet.append(app.bot); _σ_sync_ids()
                if _ω_leader_id is None:
                    _σ_set_leader(app.bot.id)
                    print(f"  ✓ #{idx:>2}: @{me.username} ← 👑 LEADER")
                else:
                    print(f"  ✓ #{idx:>2}: @{me.username}")
                return
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"  ✗ #{idx:>2}: {e}")
    await asyncio.gather(*(_boot(tok, i) for i, tok in enumerate(TOKENS, 1) if tok.strip()))
    for tok in _π_pull():
        bot = await _π_boot_annexe(tok)
        if bot: _ω_annexe.append(bot); _ω_ann_tk.append(tok); _σ_sync_ids()
    print(f"\n{'─'*54}")
    print(f"  🔐 OWNER INFORMATION")
    print(f"{'─'*54}")
    try:
        if _ω_fleet:
            owner_user = await _ω_fleet[0].get_chat(int(OWNER_ID))
            OWNER_INFO["id"] = OWNER_ID
            OWNER_INFO["name"] = owner_user.full_name or "Unknown"
            OWNER_INFO["username"] = owner_user.username or "No Username"
            print(f"  Owner ID:       {OWNER_ID}")
            print(f"  Owner Name:     {OWNER_INFO['name']}")
            print(f"  Owner Username: @{OWNER_INFO['username']}")
            print(f"{'─'*54}\n")
    except Exception as e:
        print(f"  ⚠️  Could not fetch owner info: {str(e)[:50]}\n")
    total = len(_ω_fleet) + len(_ω_annexe)
    print(f"  {len(_ω_fleet)}/{len(TOKENS)} fleet | {len(_ω_annexe)} annexe | {total} total")
    print(f"  🚀 NC SPEED PROTECTION: ACTIVE ✅ - No degradation even after 1 year runtime")
    print(f"  ✅ Auto-promote: ON | /delay to adjust NC speed")
    print(f"  Leader bot: #{_ω_leader_id} | /leader to switch responder")
    print(f"  /start or /menu to begin\n")
    asyncio.create_task(_Θ_sentinel())
    asyncio.create_task(_cleanup_resources())
    asyncio.create_task(_check_connection_health())
    # FIX: Start speed protection background tasks to prevent NC degradation
    asyncio.create_task(_cleanup_nc_rate_limit_cache())  # Clean stale entries every 10 min
    asyncio.create_task(_refresh_semaphores())           # Refresh semaphores every 7 days
    try:
        await asyncio.Event().wait()
    finally:
        await asyncio.gather(*(
            asyncio.gather(app.updater.stop(), app.stop(), app.shutdown())
            for app in _ω_apps
        ), return_exceptions=True)
if __name__ == "__main__":
    import signal
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('infot_bot.log', encoding='utf-8')
        ]
    )
    _restart_delay = 5
    _max_restart_delay = 300  # Max 5 minutes between restarts
    _consecutive_crashes = 0
    def _signal_handler(sig, frame):
        """Handle shutdown signals"""
        logging.info("Shutdown signal received, cleaning up...")
        _cancel_all_tasks()
        import sys
        sys.exit(0)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    while True:
        try:
            asyncio.run(_rise())
            _consecutive_crashes = 0
            break
        except KeyboardInterrupt:
            logging.info("Stopped by user")
            break
        except Exception as _err:
            _consecutive_crashes += 1
            import traceback
            traceback.print_exc()
            _restart_delay = min(_restart_delay * (1.5 ** _consecutive_crashes), _max_restart_delay)
            logging.error(f"[CRASH #{_consecutive_crashes}] {_err!r} - restarting in {_restart_delay:.1f}s...")
            try:
                _cancel_all_tasks()
                gc.collect()
            except Exception as cleanup_err:
                logging.error(f"Cleanup error: {cleanup_err}")
            import time
            time.sleep(_restart_delay)
    logging.info("Bot terminated cleanly")
