import asyncio
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

from scanner import ScanResult, scan_file

logging.basicConfig(
level=logging.INFO,
format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(name)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "."
ALLOWED_EXTENSIONS = {".lua", ".luau", ".txt"}
DUMPER_SCRIPT = Path(file).parent / "dumper.lua"
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8 MB – Discord upload limit


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


def safe_stem(name: str) -> str:
"""Return a sanitised file stem (no path separators, limit length)."""
p = Path(name)
# Path(".lua").stem == ".lua" (no suffix), Path("foo.lua").stem == "foo"
stem = p.stem if p.suffix else p.name
# If the stem is just the extension dot-prefix (e.g. ".lua"), strip it
if stem.startswith("."):
stem = stem[1:]
stem = re.sub(r"[^\w-.]", "", stem)
return stem[:64] or "script"

async def _download_url(session: aiohttp.ClientSession, url: str) -> bytes:
"""Download content from url, raising ValueError on problems."""
async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
if resp.status != 200:
raise ValueError(f"HTTP {resp.status} when fetching URL")
content_length = resp.headers.get("Content-Length")
if content_length and int(content_length) > MAX_FILE_SIZE:
raise ValueError("Remote file is too large (> 8 MB)")
data = await resp.read()
if len(data) > MAX_FILE_SIZE:
raise ValueError("Remote file is too large (> 8 MB)")
return data

def _find_lua() -> str | None:
"""Return the name of the first available Lua interpreter, or None."""
for candidate in ("lua", "lua5.4", "lua5.3", "lua5.2", "lua5.1", "luajit"):
if subprocess.run(
["which", candidate], capture_output=True
).returncode == 0:
return candidate
return None

_LUA_BIN: str | None = _find_lua()

def _run_dumper(input_path: Path, output_path: Path) -> tuple[bool, str]:
"""
Run the Lua dumper on input_path, writing result to output_path.

Returns (success, error_message).        
The dumper is invoked as:        
    lua dumper.lua <input> <output>        
"""        
if _LUA_BIN is None:        
    return False, "`lua` interpreter not found on the server"        
try:        
    result = subprocess.run(        
        [_LUA_BIN, str(DUMPER_SCRIPT), str(input_path), str(output_path)],        
        capture_output=True,        
        text=True,        
        timeout=30,        
    )        
    if result.returncode != 0:        
        stderr = result.stderr.strip() or result.stdout.strip()        
        return False, stderr or "Dumper exited with a non-zero code"        
    return True, ""        
except FileNotFoundError:        
    return False, "`lua` interpreter not found on the server"        
except subprocess.TimeoutExpired:        
    return False, "Dumper timed out (> 30 s)"



_SEVERITY_EMOJI = {"CRITICAL": "🚨", "HIGH": "⛔", "MEDIUM": "⚠️"}
_SEVERITY_COLOR = {
"CRITICAL": discord.Color.dark_red(),
"HIGH": discord.Color.red(),
"MEDIUM": discord.Color.orange(),
}

async def _alert_dangerous_file(
ctx: commands.Context,
filename: str,
result: ScanResult,
stage: str = "pre-dump",
) -> None:
"""
Send a Discord embed alarm and log the incident when a dangerous file
is detected.

*stage* is either ``"pre-dump"`` (file blocked before execution) or        
``"post-dump"`` (dangerous patterns found in deobfuscated output).        
"""        
top = result.highest_severity        
    

logger.warning(        
    "[SECURITY ALERT] Dangerous file blocked | stage=%s | "        
    "user=%s (id=%s) | channel=#%s (id=%s) | file=%s | "        
    "severity=%s | findings=%s",        
    stage,        
    ctx.author,        
    ctx.author.id,        
    ctx.channel,        
    ctx.channel.id,        
    filename,        
    top,        
    [f.name for f in result.findings],        
)        
    
if stage == "post-dump":        
    description = (        
        f"The file **{discord.utils.escape_markdown(filename)}** was "        
        "deobfuscated and the resulting code contains dangerous patterns. "        
        "The output has been withheld."        
    )        
else:        
    description = (        
        f"The file **{discord.utils.escape_markdown(filename)}** was "        
        "blocked before execution because it contains patterns associated "        
        "with bot path discovery or remote code execution."        
    )        
    
embed = discord.Embed(        
    title=f"{_SEVERITY_EMOJI.get(top, '⚠️')} Dangerous File Blocked",        
    description=description,        
    color=_SEVERITY_COLOR.get(top, discord.Color.orange()),        
)        
embed.add_field(name="Submitted by", value=ctx.author.mention, inline=True)        
embed.add_field(name="Channel", value=ctx.channel.mention, inline=True)        
embed.add_field(name="Severity", value=top, inline=True)        
embed.add_field(name="Stage", value=stage, inline=True)        
    
findings_lines = [        
    f"• **{f.name}** `[{f.severity}]` – {f.description}"        
    for f in result.findings        
]        
if findings_lines:        
    embed.add_field(        
        name="Findings",        
        value="\n".join(findings_lines)[:1024],        
        inline=False,        
    )        
    
embed.set_footer(text="This incident has been logged. Contact an admin if needed.")        
    
await ctx.send(embed=embed)

# ---------------------------------------------------------------------------#
# Command
# ---------------------------------------------------------------------------#

@bot.command(name="spectre", aliases=["l"])
async def spectre_command(ctx, *, arg=""):
"""
.spectre [url] o .spectre con archivo adjunto.
"""
attachment = None
raw_name = None
file_bytes = None
url = None

if ctx.message.attachments:  
    attachment = ctx.message.attachments[0]  
    raw_name = attachment.filename  

elif arg:  
    match = re.search(r"https?://\S+", arg)  
    if not match:  
        await ctx.send("❌ Introduce una URL válida o adjunta un archivo.")  
        return  

    url = match.group(0).rstrip(")")  

    if "pastebin.com/" in url and "/raw/" not in url:  
        code = url.split("/")[-1]  
        url = f"https://pastebin.com/raw/{code}"  

    if "github.com" in url and "/blob/" in url:  
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")  

    try:  
        async with aiohttp.ClientSession() as session:  
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:  

                if resp.status != 200:  
                    await ctx.send(f"❌ HTTP error {resp.status}")  
                    return  

                content_length = resp.headers.get("Content-Length")  
                if content_length and int(content_length) > MAX_FILE_SIZE:  
                    await ctx.send("❌ Archivo demasiado grande (> 8MB)")  
                    return  

                file_bytes = await resp.read()  

    except Exception as e:  
        await ctx.send(f"❌ Error descargando URL: {e}")  
        return  

    if len(file_bytes) > MAX_FILE_SIZE:  
        await ctx.send("❌ Archivo demasiado grande (> 8MB)")  
        return  

    try:  
        file_bytes.decode("utf-8")  
    except UnicodeDecodeError:  
        await ctx.send("❌ El archivo no parece ser texto válido.")  
        return  

    raw_name = url.split("/")[-1].split("?")[0]  

    if not raw_name or "." not in raw_name:  
        raw_name = "script.lua"  

else:  
    await ctx.send(  
        "❌ Uso: `.spectre or .l` [url] o adjunta un archivo `.lua`, `.luau` o `.txt`."  
    )  
    return  

  
ext = Path(raw_name).suffix.lower()

# solo validar si es archivo adjunto
if attachment and ext not in ALLOWED_EXTENSIONS:
    await ctx.send(
        f"❌ Tipo de archivo no soportado `{ext}`. "
        f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    )
    return

# asegurar extensión válida para dumper
if ext not in ALLOWED_EXTENSIONS:
    ext = ".lua"

async with ctx.typing():  
    try:  
        if attachment:  
            if attachment.size > MAX_FILE_SIZE:  
                await ctx.send("❌ Archivo demasiado grande (> 8 MB).")  
                return  

            file_bytes = await attachment.read()  

    except Exception as exc:  
        await ctx.send(f"❌ Error leyendo archivo: {exc}")  
        return  

    pre_scan = scan_file(file_bytes)  

    if pre_scan.is_dangerous:  
        await _alert_dangerous_file(ctx, raw_name, pre_scan, stage="pre-dump")  
        return  

    if pre_scan.findings:  
        logger.warning(  
            "[SECURITY WARNING] Suspicious file | user=%s | file=%s | findings=%s",  
            ctx.author,  
            raw_name,  
            [f.name for f in pre_scan.findings],  
        )  

    stem = _safe_stem(raw_name)  
    output_name = f"{stem}.lua.txt"  

    with tempfile.TemporaryDirectory() as tmpdir:  
        tmp = Path(tmpdir)  

        input_path = tmp / f"input{ext}"  
        output_path = tmp / output_name  

        input_path.write_bytes(file_bytes)  

        start = time.monotonic()  
        success, error = _run_dumper(input_path, output_path)  
        elapsed_ms = int((time.monotonic() - start) * 1000)  

        if not success:  
            await ctx.send(f"❌ Spectre error: {error}")  
            return  

        if not output_path.exists() or output_path.stat().st_size == 0:  
            await ctx.send("❌ Spectre produced no output.")  
            return  

        post_scan = scan_file(output_path.read_bytes())  

        if post_scan.is_dangerous:  
            await _alert_dangerous_file(  
                ctx,  
                raw_name,  
                post_scan,  
                stage="post-dump",  
            )  
            return  

        await ctx.send(  
            f"👻 Cypher Spectre reconstructed the script in {elapsed_ms} ms",  
            file=discord.File(str(output_path), filename=output_name),  
        )

@bot.event
async def on_ready():
print("Cypher Spectre Engine Online")
print(f"Logged in as {bot.user} (id: {bot.user.id})")
print("Command Prefix:", PREFIX)

if name == "main":
if not TOKEN:
raise RuntimeError(
"DISCORD_TOKEN environment variable is not set. "
"Copy .env.example to .env and fill in your token."
)
bot.run(TOKEN)