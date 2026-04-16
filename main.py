import os, sys, shutil, subprocess, time, zipfile, tempfile
from datetime import datetime
import telebot
from telebot import types

# ⚙️ SETTINGS
BOT_TOKEN = "8734983589:AAGnlauxRkxRoZjvwJv9OuBd3n21R8S36VM"
AUTHORIZED_USERS = [8702041633]
START_DIR = "/"
MAX_VIEW_SIZE = 1024 * 1024
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024
ITEMS_PER_PAGE = 10

bot = telebot.TeleBot(BOT_TOKEN)
user_states, user_current_dir, user_clipboard, user_page = {}, {}, {}, {}

def is_authorized(uid): return uid in AUTHORIZED_USERS
def get_cwd(uid): return user_current_dir.get(uid, START_DIR)
def set_cwd(uid, p): user_current_dir[uid] = p

def fmt_size(s):
    for u in ['B','KB','MB','GB','TB']:
        if s < 1024.0: return str(round(s,1)) + " " + u
        s /= 1024.0
    return str(round(s,1)) + " PB"

def get_info(p):
    try:
        s = os.stat(p)
        return {'size':fmt_size(s.st_size),'raw':s.st_size,
                'mod':datetime.fromtimestamp(s.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'cre':datetime.fromtimestamp(s.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                'perms':oct(s.st_mode)[-3:],'uid':s.st_uid,'gid':s.st_gid,
                'link':os.path.islink(p)}
    except Exception as e: return {'error':str(e)}

def femoji(n, isd=False):
    if isd: return "📁"
    ext = os.path.splitext(n)[1].lower()
    m = {'.py':'🐍','.js':'🟨','.html':'🌐','.css':'🎨','.json':'📋',
         '.txt':'📄','.md':'📝','.jpg':'🖼','.png':'🖼','.mp4':'🎬',
         '.mp3':'🎵','.zip':'📦','.pdf':'📕','.sh':'⚙','.log':'📜',
         '.conf':'🔧','.env':'🔐','.db':'🗄','.sql':'🗄','.xml':'📋'}
    return m.get(ext, '📄')

def check_auth(m):
    if isinstance(m, types.Message):
        uid = m.from_user.id
        if not is_authorized(uid):
            bot.reply_to(m, "⛔ Access Denied!\nYour ID: `" + str(uid) + "`", parse_mode='Markdown')
            return False
    else:
        if not is_authorized(m.from_user.id):
            bot.answer_callback_query(m.id, "⛔ Access Denied!", show_alert=True)
            return False
    return True

def kb_dir(uid, path, page=0):
    mk = types.InlineKeyboardMarkup(row_width=1)
    try: items = sorted(os.listdir(path))
    except PermissionError:
        mk.add(types.InlineKeyboardButton("❌ Permission Denied", callback_data="noop"))
        mk.add(types.InlineKeyboardButton("⬆ Back", callback_data="go_parent"))
        return mk
    except Exception as e:
        mk.add(types.InlineKeyboardButton("❌ " + str(e)[:40], callback_data="noop"))
        return mk
    dirs = [i for i in items if os.path.isdir(os.path.join(path, i))]
    files = [i for i in items if os.path.isfile(os.path.join(path, i))]
    alls = dirs + files
    total = len(alls)
    tp = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = min(page, tp - 1)
    s, e = page * ITEMS_PER_PAGE, min((page + 1) * ITEMS_PER_PAGE, total)
    if path != '/':
        mk.add(types.InlineKeyboardButton("📂 .. (Parent)", callback_data="go_parent"))
    for item in alls[s:e]:
        fp = os.path.join(path, item)
        isd = os.path.isdir(fp)
        em = femoji(item, isd)
        if isd:
            mk.add(types.InlineKeyboardButton(em + " " + item + "/", callback_data="cd|" + item))
        else:
            try: sz = fmt_size(os.path.getsize(fp))
            except: sz = "?"
            mk.add(types.InlineKeyboardButton(em + " " + item + " (" + sz + ")", callback_data="fl|" + item))
    if tp > 1:
        nav = []
        if page > 0: nav.append(types.InlineKeyboardButton("⬅", callback_data="pg|" + str(page-1)))
        nav.append(types.InlineKeyboardButton(str(page+1) + "/" + str(tp), callback_data="noop"))
        if page < tp - 1: nav.append(types.InlineKeyboardButton("➡", callback_data="pg|" + str(page+1)))
        mk.row(*nav)
    mk.row(types.InlineKeyboardButton("➕ New File", callback_data="act|newfile"),
           types.InlineKeyboardButton("📁 New Folder", callback_data="act|newfolder"))
    mk.row(types.InlineKeyboardButton("📋 Paste", callback_data="act|paste"),
           types.InlineKeyboardButton("🔍 Search", callback_data="act|search"))
    mk.row(types.InlineKeyboardButton("💻 Terminal", callback_data="act|terminal"),
           types.InlineKeyboardButton("📊 Disk", callback_data="act|disk"))
    mk.row(types.InlineKeyboardButton("🔄 Refresh", callback_data="act|refresh"),
           types.InlineKeyboardButton("📍 GoTo", callback_data="act|goto"))
    mk.add(types.InlineKeyboardButton(str(len(dirs)) + " folders, " + str(len(files)) + " files", callback_data="noop"))
    return mk

def kb_factions(fn):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.row(types.InlineKeyboardButton("👁 View", callback_data="fa|view|"+fn),
           types.InlineKeyboardButton("✏ Edit", callback_data="fa|edit|"+fn))
    mk.row(types.InlineKeyboardButton("⬇ Download", callback_data="fa|dl|"+fn),
           types.InlineKeyboardButton("🗑 Delete", callback_data="fa|del|"+fn))
    mk.row(types.InlineKeyboardButton("✂ Cut", callback_data="fa|cut|"+fn),
           types.InlineKeyboardButton("📋 Copy", callback_data="fa|copy|"+fn))
    mk.row(types.InlineKeyboardButton("✏ Rename", callback_data="fa|ren|"+fn),
           types.InlineKeyboardButton("🔒 Chmod", callback_data="fa|chm|"+fn))
    mk.row(types.InlineKeyboardButton("ℹ Info", callback_data="fa|info|"+fn),
           types.InlineKeyboardButton("📦 Zip", callback_data="fa|zip|"+fn))
    mk.add(types.InlineKeyboardButton("⬅ Back", callback_data="act|refresh"))
    return mk

def kb_dactions(n):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.row(types.InlineKeyboardButton("📂 Open", callback_data="cd|"+n),
           types.InlineKeyboardButton("🗑 Delete", callback_data="da|del|"+n))
    mk.row(types.InlineKeyboardButton("✏ Rename", callback_data="da|ren|"+n),
           types.InlineKeyboardButton("📦 Zip+DL", callback_data="da|zdl|"+n))
    mk.row(types.InlineKeyboardButton("✂ Cut", callback_data="da|cut|"+n),
           types.InlineKeyboardButton("📋 Copy", callback_data="da|copy|"+n))
    mk.row(types.InlineKeyboardButton("ℹ Info", callback_data="da|info|"+n),
           types.InlineKeyboardButton("🔒 Chmod", callback_data="da|chm|"+n))
    mk.add(types.InlineKeyboardButton("⬅ Back", callback_data="act|refresh"))
    return mk

def kb_confirm(a, t):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.row(types.InlineKeyboardButton("✅ Yes", callback_data="cf|"+a+"|"+t),
           types.InlineKeyboardButton("❌ Cancel", callback_data="act|refresh"))
    return mk

def refresh(cid, mid, uid):
    cwd = get_cwd(uid)
    pg = user_page.get(uid, 0)
    mk = kb_dir(uid, cwd, pg)
    bot.edit_message_text("📂 *File Manager*\n📍 `" + cwd + "`", cid, mid, reply_markup=mk, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def cmd_start(m):
    if not check_auth(m): return
    uid = m.from_user.id
    set_cwd(uid, START_DIR); user_page[uid] = 0
    t = ("🗂 *File Manager Bot*\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "👋 Welcome *" + m.from_user.first_name + "*!\n\n"
         "/fm - File Manager\n/cd path - Go to dir\n"
         "/terminal cmd - Run command\n/cat file - View\n"
         "/edit file - Edit\n/touch file - Create file\n"
         "/mkdir name - Create folder\n/rm name - Delete\n"
         "/rename old new - Rename\n/search q - Search\n"
         "/zip name - Zip\n/unzip name - Unzip\n"
         "/info - System info\n/df - Disk\n/ps - Processes\n"
         "/pwd - Current dir\n/help - Help\n\n"
         "📍 Dir: `" + get_cwd(uid) + "`")
    bot.reply_to(m, t, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def cmd_help(m):
    if not check_auth(m): return
    t = ("📖 *Help*\n━━━━━━━━━━━━━━━━━━━━\n"
         "/fm - File Manager GUI\n/cd path - Change dir\n"
         "/ls - List\n/pwd - Current path\n"
         "/touch name - New file\n/mkdir name - New folder\n"
         "/rm name - Delete\n/cat name - View\n"
         "/edit name - Edit\n/rename old new - Rename\n"
         "/terminal cmd - Run command\n/search q - Find\n"
         "/zip name - Compress\n/unzip name - Extract\n"
         "/info - System\n/df - Disk\n/ps - Processes\n"
         "Send any file to upload\n/cancel - Cancel")
    bot.reply_to(m, t, parse_mode='Markdown')

@bot.message_handler(commands=['fm','files'])
def cmd_fm(m):
    if not check_auth(m): return
    uid = m.from_user.id; cwd = get_cwd(uid); user_page[uid] = 0
    if not os.path.exists(cwd): set_cwd(uid, START_DIR); cwd = START_DIR
    mk = kb_dir(uid, cwd, 0)
    bot.reply_to(m, "📂 *File Manager*\n📍 `" + cwd + "`", reply_markup=mk, parse_mode='Markdown')

@bot.message_handler(commands=['cd'])
def cmd_cd(m):
    if not check_auth(m): return
    uid = m.from_user.id; args = m.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(m, "Usage: /cd <path>"); return
    p = args[1].strip()
    if not os.path.isabs(p): p = os.path.join(get_cwd(uid), p)
    p = os.path.abspath(p)
    if not os.path.isdir(p): bot.reply_to(m, "❌ Not a dir: `"+p+"`", parse_mode='Markdown'); return
    set_cwd(uid, p); user_page[uid] = 0
    mk = kb_dir(uid, p, 0)
    bot.reply_to(m, "📂 *File Manager*\n📍 `" + p + "`", reply_markup=mk, parse_mode='Markdown')

@bot.message_handler(commands=['pwd'])
def cmd_pwd(m):
    if not check_auth(m): return
    bot.reply_to(m, "📍 `" + get_cwd(m.from_user.id) + "`", parse_mode='Markdown')

@bot.message_handler(commands=['ls'])
def cmd_ls(m):
    if not check_auth(m): return
    cwd = get_cwd(m.from_user.id)
    try:
        items = sorted(os.listdir(cwd))
        if not items: bot.reply_to(m, "📂 Empty"); return
        t = "📂 `" + cwd + "`\n"
        for i in items:
            fp = os.path.join(cwd, i); isd = os.path.isdir(fp)
            if isd: t += femoji(i,True) + " `" + i + "/`\n"
            else:
                try: sz = fmt_size(os.path.getsize(fp))
                except: sz = "?"
                t += femoji(i) + " `" + i + "` (" + sz + ")\n"
        for c in range(0, len(t), 4000): bot.reply_to(m, t[c:c+4000], parse_mode='Markdown')
    except Exception as e: bot.reply_to(m, "❌ " + str(e))

@bot.message_handler(commands=['touch'])
def cmd_touch(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /touch <file>"); return
    fp = os.path.join(get_cwd(m.from_user.id), args[1].strip())
    try:
        with open(fp,'a'): os.utime(fp,None)
        bot.reply_to(m, "✅ Created: `"+fp+"`", parse_mode='Markdown')
    except Exception as e: bot.reply_to(m, "❌ "+str(e))

@bot.message_handler(commands=['mkdir'])
def cmd_mkdir(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /mkdir <name>"); return
    dp = os.path.join(get_cwd(m.from_user.id), args[1].strip())
    try: os.makedirs(dp, exist_ok=True); bot.reply_to(m, "✅ Created: `"+dp+"`", parse_mode='Markdown')
    except Exception as e: bot.reply_to(m, "❌ "+str(e))

@bot.message_handler(commands=['rm'])
def cmd_rm(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /rm <name>"); return
    t = os.path.join(get_cwd(m.from_user.id), args[1].strip())
    if not os.path.exists(t): bot.reply_to(m,"❌ Not found"); return
    try:
        if os.path.isdir(t): shutil.rmtree(t)
        else: os.remove(t)
        bot.reply_to(m, "✅ Deleted: `"+t+"`", parse_mode='Markdown')
    except Exception as e: bot.reply_to(m, "❌ "+str(e))

@bot.message_handler(commands=['cat'])
def cmd_cat(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /cat <file>"); return
    fn = args[1].strip(); fp = os.path.join(get_cwd(m.from_user.id), fn)
    if not os.path.isfile(fp): bot.reply_to(m,"❌ Not found"); return
    try:
        sz = os.path.getsize(fp)
        if sz > MAX_VIEW_SIZE: bot.reply_to(m,"❌ Too large"); return
        with open(fp,'r',errors='replace') as f: c = f.read()
        if not c.strip(): bot.reply_to(m,"📄 Empty"); return
        t = "📄 *"+fn+"*\n\n`"+c[:3500]+"`"
        if len(c)>3500: t += "\n...truncated"
        bot.reply_to(m, t, parse_mode='Markdown')
    except Exception as e: bot.reply_to(m, "❌ "+str(e))

@bot.message_handler(commands=['edit'])
def cmd_edit(m):
    if not check_auth(m): return
    uid = m.from_user.id; args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /edit <file>"); return
    fn = args[1].strip(); fp = os.path.join(get_cwd(uid), fn)
    user_states[uid] = {'action':'edit_content','filepath':fp,'filename':fn}
    prev = ""
    if os.path.isfile(fp):
        try:
            with open(fp,'r',errors='replace') as f: c = f.read()
            if c: prev = "\n\nCurrent:\n`" + c[:2000] + "`"
        except: pass
    bot.reply_to(m, "✏ *Edit: "+fn+"*\n📍 `"+fp+"`\n\nSend new content.\n/cancel to cancel."+prev, parse_mode='Markdown')

@bot.message_handler(commands=['rename'])
def cmd_rename(m):
    if not check_auth(m): return
    args = m.text.split()
    if len(args)<3: bot.reply_to(m,"Usage: /rename <old> <new>"); return
    cwd = get_cwd(m.from_user.id)
    try: os.rename(os.path.join(cwd,args[1]), os.path.join(cwd,args[2])); bot.reply_to(m,"✅ Done", parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

@bot.message_handler(commands=['terminal','cmd','shell','exec'])
def cmd_terminal(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /terminal <cmd>"); return
    cmd = args[1].strip(); cwd = get_cwd(m.from_user.id)
    bot.send_chat_action(m.chat.id, 'typing')
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30)
        out = ""
        if r.stdout: out += r.stdout
        if r.stderr: out += "\nSTDERR:\n" + r.stderr
        if not out: out = "Done (no output)"
        resp = "💻 `"+cmd+"`\nExit: "+str(r.returncode)+"\n\n`"+out[:3500]+"`"
        if len(resp) > 4000:
            with tempfile.NamedTemporaryFile(mode='w',suffix='.txt',delete=False) as f:
                f.write("$ "+cmd+"\n\n"+r.stdout+"\n"+r.stderr); tp=f.name
            with open(tp,'rb') as fl: bot.send_document(m.chat.id, fl, caption="💻 "+cmd)
            os.unlink(tp)
        else: bot.reply_to(m, resp, parse_mode='Markdown')
    except subprocess.TimeoutExpired: bot.reply_to(m,"⏱ Timeout")
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

@bot.message_handler(commands=['search'])
def cmd_search(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /search <query>"); return
    q = args[1].strip(); cwd = get_cwd(m.from_user.id)
    bot.send_chat_action(m.chat.id, 'typing')
    try:
        r = subprocess.run('find "'+cwd+'" -maxdepth 5 -iname "*'+q+'*" 2>/dev/null | head -50',
                          shell=True, capture_output=True, text=True, timeout=15)
        if r.stdout.strip():
            fl = r.stdout.strip().split('\n')
            t = "🔍 `"+q+"` ("+str(len(fl))+")\n\n"
            for f in fl: t += "`"+f+"`\n"
            bot.reply_to(m, t[:4000], parse_mode='Markdown')
        else: bot.reply_to(m, "🔍 Nothing found", parse_mode='Markdown')
    except: bot.reply_to(m, "❌ Search failed")

@bot.message_handler(commands=['info'])
def cmd_info(m):
    if not check_auth(m): return
    bot.send_chat_action(m.chat.id, 'typing')
    try:
        t = ("🖥 *System Info*\n━━━━━━━━━━━━━━━━━━━━\n"
             "Host: `"+subprocess.getoutput('hostname')+"`\n"
             "User: `"+subprocess.getoutput('whoami')+"`\n"
             "IP: `"+subprocess.getoutput('hostname -I 2>/dev/null || echo N/A').strip()+"`\n\n"
             "System:\n`"+subprocess.getoutput('uname -a')+"`\n\n"
             "Uptime:\n`"+subprocess.getoutput('uptime')+"`\n\n"
             "Memory:\n`"+subprocess.getoutput('free -h 2>/dev/null || echo N/A')+"`\n\n"
             "Disk:\n`"+subprocess.getoutput('df -h / 2>/dev/null')+"`\n\n"
             "CPUs: `"+subprocess.getoutput('nproc 2>/dev/null || echo N/A')+"`")
        bot.reply_to(m, t, parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

@bot.message_handler(commands=['df'])
def cmd_df(m):
    if not check_auth(m): return
    bot.reply_to(m, "💾\n`"+subprocess.getoutput("df -h")[:3500]+"`", parse_mode='Markdown')

@bot.message_handler(commands=['ps'])
def cmd_ps(m):
    if not check_auth(m): return
    bot.reply_to(m, "📊\n`"+subprocess.getoutput("ps aux --sort=-%mem | head -20")[:3500]+"`", parse_mode='Markdown')

@bot.message_handler(commands=['zip'])
def cmd_zip(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /zip <name>"); return
    n = args[1].strip(); t = os.path.join(get_cwd(m.from_user.id), n)
    if not os.path.exists(t): bot.reply_to(m,"❌ Not found"); return
    try:
        zp = t + '.zip'
        if os.path.isdir(t): shutil.make_archive(t,'zip',t)
        else:
            with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as zf: zf.write(t,n)
        bot.reply_to(m,"✅ `"+zp+"` ("+fmt_size(os.path.getsize(zp))+")", parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

@bot.message_handler(commands=['unzip'])
def cmd_unzip(m):
    if not check_auth(m): return
    args = m.text.split(maxsplit=1)
    if len(args)<2: bot.reply_to(m,"Usage: /unzip <file>"); return
    n = args[1].strip(); zp = os.path.join(get_cwd(m.from_user.id), n)
    if not os.path.isfile(zp): bot.reply_to(m,"❌ Not found"); return
    try:
        ed = os.path.join(get_cwd(m.from_user.id), os.path.splitext(n)[0])
        with zipfile.ZipFile(zp,'r') as zf: zf.extractall(ed)
        bot.reply_to(m,"✅ Extracted: `"+ed+"`", parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

@bot.message_handler(commands=['cancel'])
def cmd_cancel(m):
    uid = m.from_user.id
    if uid in user_states: del user_states[uid]
    bot.reply_to(m, "❌ Cancelled")
    # ============================================
# CALLBACK HANDLER
# ============================================
@bot.callback_query_handler(func=lambda call: True)
def handle_cb(call):
    if not check_auth(call): return
    uid = call.from_user.id; d = call.data
    cid = call.message.chat.id; mid = call.message.message_id
    try:
        if d == "noop": bot.answer_callback_query(call.id); return
        elif d == "go_parent":
            p = os.path.dirname(get_cwd(uid)); set_cwd(uid,p); user_page[uid]=0
            mk = kb_dir(uid,p,0)
            bot.edit_message_text("📂 *File Manager*\n📍 `"+p+"`",cid,mid,reply_markup=mk,parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        elif d.startswith("cd|"):
            dn = d.split("|",1)[1]; nd = os.path.abspath(os.path.join(get_cwd(uid),dn))
            if os.path.isdir(nd):
                set_cwd(uid,nd); user_page[uid]=0; mk=kb_dir(uid,nd,0)
                bot.edit_message_text("📂 *File Manager*\n📍 `"+nd+"`",cid,mid,reply_markup=mk,parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        elif d.startswith("pg|"):
            pg=int(d.split("|")[1]); user_page[uid]=pg; cwd=get_cwd(uid)
            mk=kb_dir(uid,cwd,pg)
            bot.edit_message_text("📂 *File Manager*\n📍 `"+cwd+"`",cid,mid,reply_markup=mk,parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        elif d.startswith("fl|"):
            fn=d.split("|",1)[1]; cwd=get_cwd(uid); fp=os.path.join(cwd,fn)
            if os.path.isdir(fp):
                t="📁 *"+fn+"/*\n📍 `"+fp+"`"; mk=kb_dactions(fn)
            else:
                info=get_info(fp); t="📄 *"+fn+"*\n📍 `"+fp+"`\n"
                if 'error' not in info: t+=info['size']+" | "+info['mod']+" | "+info['perms']
                mk=kb_factions(fn)
            bot.edit_message_text(t,cid,mid,reply_markup=mk,parse_mode='Markdown')
            bot.answer_callback_query(call.id)
        elif d.startswith("fa|"):
            pts=d.split("|",2); act=pts[1]; fn=pts[2]; cwd=get_cwd(uid); fp=os.path.join(cwd,fn)
            if act=="view":
                if not os.path.isfile(fp): bot.answer_callback_query(call.id,"❌ Not found!",show_alert=True); return
                sz=os.path.getsize(fp)
                if sz>MAX_VIEW_SIZE: bot.answer_callback_query(call.id,"Too large",show_alert=True); return
                try:
                    with open(fp,'r',errors='replace') as f: c=f.read()
                    if not c.strip(): bot.send_message(cid,"📄 Empty")
                    else:
                        t="📄 *"+fn+"*\n\n`"+c[:3500]+"`"
                        if len(c)>3500: t+="\n...truncated"
                        bot.send_message(cid,t,parse_mode='Markdown')
                except Exception as e: bot.send_message(cid,"❌ "+str(e))
                bot.answer_callback_query(call.id)
            elif act=="edit":
                user_states[uid]={'action':'edit_content','filepath':fp,'filename':fn}
                bot.send_message(cid,"✏ *Edit: "+fn+"*\nSend new content.\n/cancel to cancel.",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="dl":
                if not os.path.isfile(fp): bot.answer_callback_query(call.id,"❌ Not found!",show_alert=True); return
                sz=os.path.getsize(fp)
                if sz>MAX_DOWNLOAD_SIZE: bot.answer_callback_query(call.id,"Too large",show_alert=True); return
                bot.send_chat_action(cid,'upload_document')
                try:
                    with open(fp,'rb') as f: bot.send_document(cid,f,caption="📄 "+fn+" | "+fmt_size(sz))
                except Exception as e: bot.send_message(cid,"❌ "+str(e))
                bot.answer_callback_query(call.id)
            elif act=="del":
                t="⚠ *Delete?*\n📄 `"+fn+"`\n`"+fp+"`\n\nCannot undo!"
                mk=kb_confirm("df",fn)
                bot.edit_message_text(t,cid,mid,reply_markup=mk,parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="cut":
                user_clipboard[uid]={'action':'cut','source':fp,'name':fn}
                bot.answer_callback_query(call.id,"✂ Cut: "+fn,show_alert=True)
            elif act=="copy":
                user_clipboard[uid]={'action':'copy','source':fp,'name':fn}
                bot.answer_callback_query(call.id,"📋 Copied: "+fn,show_alert=True)
            elif act=="ren":
                user_states[uid]={'action':'rename','filepath':fp,'filename':fn}
                bot.send_message(cid,"✏ *Rename: "+fn+"*\nSend new name.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="chm":
                user_states[uid]={'action':'chmod','filepath':fp,'filename':fn}
                try: cp=oct(os.stat(fp).st_mode)[-3:]
                except: cp="?"
                bot.send_message(cid,"🔒 *Chmod: "+fn+"*\nCurrent: `"+cp+"`\nSend perms (755).\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="info":
                info=get_info(fp)
                if 'error' in info: bot.answer_callback_query(call.id,info['error'],show_alert=True); return
                t=("ℹ *File Info*\n━━━━━━━━━━━━\n"
                   "📄 `"+fn+"`\n📍 `"+fp+"`\n"
                   "Size: "+info['size']+"\nModified: "+info['mod']+"\n"
                   "Created: "+info['cre']+"\nPerms: "+info['perms']+"\n"
                   "UID: "+str(info['uid'])+" GID: "+str(info['gid'])+"\n"
                   "Symlink: "+str(info['link']))
                bot.send_message(cid,t,parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="zip":
                bot.send_chat_action(cid,'typing')
                try:
                    zp=fp+'.zip'
                    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as zf: zf.write(fp,fn)
                    bot.send_message(cid,"✅ Zipped ("+fmt_size(os.path.getsize(zp))+")")
                except Exception as e: bot.send_message(cid,"❌ "+str(e))
                bot.answer_callback_query(call.id)
        elif d.startswith("da|"):
            pts=d.split("|",2); act=pts[1]; n=pts[2]; cwd=get_cwd(uid); fp=os.path.join(cwd,n)
            if act=="del":
                t="⚠ *Delete Folder?*\n📁 `"+n+"/`\nAll contents deleted!"
                mk=kb_confirm("dd",n)
                bot.edit_message_text(t,cid,mid,reply_markup=mk,parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="ren":
                user_states[uid]={'action':'rename','filepath':fp,'filename':n}
                bot.send_message(cid,"✏ *Rename: "+n+"/*\nSend new name.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="zdl":
                bot.send_chat_action(cid,'typing')
                try:
                    zp=shutil.make_archive(os.path.join(tempfile.gettempdir(),n),'zip',fp)
                    sz=os.path.getsize(zp)
                    if sz>MAX_DOWNLOAD_SIZE: bot.send_message(cid,"❌ Too large"); os.unlink(zp)
                    else:
                        with open(zp,'rb') as f: bot.send_document(cid,f,caption="📁 "+n+"/ | "+fmt_size(sz))
                        os.unlink(zp)
                except Exception as e: bot.send_message(cid,"❌ "+str(e))
                bot.answer_callback_query(call.id)
            elif act=="cut":
                user_clipboard[uid]={'action':'cut','source':fp,'name':n}
                bot.answer_callback_query(call.id,"✂ Cut: "+n+"/",show_alert=True)
            elif act=="copy":
                user_clipboard[uid]={'action':'copy','source':fp,'name':n}
                bot.answer_callback_query(call.id,"📋 Copied: "+n+"/",show_alert=True)
            elif act=="chm":
                user_states[uid]={'action':'chmod','filepath':fp,'filename':n}
                try: cp=oct(os.stat(fp).st_mode)[-3:]
                except: cp="?"
                bot.send_message(cid,"🔒 Chmod: "+n+"/\nCurrent: `"+cp+"`\nSend perms.",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="info":
                info=get_info(fp)
                try:
                    cts=os.listdir(fp)
                    nf=sum(1 for c in cts if os.path.isfile(os.path.join(fp,c)))
                    nd=sum(1 for c in cts if os.path.isdir(os.path.join(fp,c)))
                    tsz=subprocess.getoutput('du -sh "'+fp+'" 2>/dev/null').split()[0]
                except: nf=nd="?"; tsz="?"
                t=("ℹ *Folder Info*\n━━━━━━━━━━━━\n"
                   "📁 `"+n+"/`\n📍 `"+fp+"`\n"
                   "Size: "+str(tsz)+"\nFiles: "+str(nf)+" Folders: "+str(nd)+"\n"
                   "Modified: "+str(info.get('mod','?'))+"\nPerms: "+str(info.get('perms','?')))
                bot.send_message(cid,t,parse_mode='Markdown')
                bot.answer_callback_query(call.id)
        elif d.startswith("cf|"):
            pts=d.split("|",2); act=pts[1]; tgt=pts[2]; cwd=get_cwd(uid); tp=os.path.join(cwd,tgt)
            try:
                if act=="df": os.remove(tp); bot.answer_callback_query(call.id,"✅ Deleted",show_alert=True)
                elif act=="dd": shutil.rmtree(tp); bot.answer_callback_query(call.id,"✅ Deleted",show_alert=True)
            except Exception as e: bot.answer_callback_query(call.id,"❌ "+str(e)[:80],show_alert=True)
            refresh(cid,mid,uid)
        elif d.startswith("act|"):
            act=d.split("|")[1]
            if act=="refresh": refresh(cid,mid,uid); bot.answer_callback_query(call.id,"🔄")
            elif act=="newfile":
                user_states[uid]={'action':'newfile'}
                bot.send_message(cid,"📄 Send filename.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="newfolder":
                user_states[uid]={'action':'newfolder'}
                bot.send_message(cid,"📁 Send folder name.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="paste":
                if uid not in user_clipboard: bot.answer_callback_query(call.id,"📋 Empty!",show_alert=True); return
                cl=user_clipboard[uid]; cwd=get_cwd(uid); dst=os.path.join(cwd,cl['name'])
                try:
                    if cl['action']=='copy':
                        if os.path.isdir(cl['source']): shutil.copytree(cl['source'],dst)
                        else: shutil.copy2(cl['source'],dst)
                        bot.answer_callback_query(call.id,"✅ Pasted",show_alert=True)
                    elif cl['action']=='cut':
                        shutil.move(cl['source'],dst); del user_clipboard[uid]
                        bot.answer_callback_query(call.id,"✅ Moved",show_alert=True)
                    refresh(cid,mid,uid)
                except Exception as e: bot.answer_callback_query(call.id,"❌ "+str(e)[:80],show_alert=True)
            elif act=="search":
                user_states[uid]={'action':'search'}
                bot.send_message(cid,"🔍 Send query.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="terminal":
                user_states[uid]={'action':'terminal'}
                bot.send_message(cid,"💻 *Terminal*\n📍 `"+get_cwd(uid)+"`\nSend command.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            elif act=="disk":
                bot.send_chat_action(cid,'typing')
                try: bot.send_message(cid,"💾\n`"+subprocess.getoutput("df -h")[:3500]+"`",parse_mode='Markdown')
                except Exception as e: bot.send_message(cid,"❌ "+str(e))
                bot.answer_callback_query(call.id)
            elif act=="goto":
                user_states[uid]={'action':'goto'}
                bot.send_message(cid,"📍 Send full path.\n/cancel",parse_mode='Markdown')
                bot.answer_callback_query(call.id)
    except Exception as e:
        try: bot.answer_callback_query(call.id,"❌ "+str(e)[:80],show_alert=True)
        except: pass

# ============================================
# UPLOAD HANDLERS
# ============================================
@bot.message_handler(content_types=['document'])
def h_doc(m):
    if not check_auth(m): return
    uid=m.from_user.id; cwd=get_cwd(uid)
    try:
        fi=bot.get_file(m.document.file_id); dl=bot.download_file(fi.file_path)
        fn=m.document.file_name; fp=os.path.join(cwd,fn)
        with open(fp,'wb') as f: f.write(dl)
        bot.reply_to(m,"✅ Uploaded: `"+fn+"`\n📍 `"+fp+"`",parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))
    if uid in user_states: del user_states[uid]

@bot.message_handler(content_types=['photo'])
def h_photo(m):
    if not check_auth(m): return
    cwd=get_cwd(m.from_user.id)
    try:
        fi=bot.get_file(m.photo[-1].file_id); dl=bot.download_file(fi.file_path)
        ext=os.path.splitext(fi.file_path)[1] or '.jpg'
        fn="photo_"+str(int(time.time()))+ext; fp=os.path.join(cwd,fn)
        with open(fp,'wb') as f: f.write(dl)
        bot.reply_to(m,"✅ Saved: `"+fp+"`",parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

@bot.message_handler(content_types=['video','audio','voice','video_note','sticker'])
def h_media(m):
    if not check_auth(m): return
    cwd=get_cwd(m.from_user.id)
    try:
        ct=m.content_type
        if ct=='video': fid=m.video.file_id; fn=getattr(m.video,'file_name',None) or "video_"+str(int(time.time()))+".mp4"
        elif ct=='audio': fid=m.audio.file_id; fn=getattr(m.audio,'file_name',None) or "audio_"+str(int(time.time()))+".mp3"
        elif ct=='voice': fid=m.voice.file_id; fn="voice_"+str(int(time.time()))+".ogg"
        elif ct=='video_note': fid=m.video_note.file_id; fn="vnote_"+str(int(time.time()))+".mp4"
        elif ct=='sticker': fid=m.sticker.file_id; fn="sticker_"+str(int(time.time()))+".webp"
        else: return
        fi=bot.get_file(fid); dl=bot.download_file(fi.file_path)
        fp=os.path.join(cwd,fn)
        with open(fp,'wb') as f: f.write(dl)
        bot.reply_to(m,"✅ Saved: `"+fp+"`",parse_mode='Markdown')
    except Exception as e: bot.reply_to(m,"❌ "+str(e))

# ============================================
# STATE HANDLER
# ============================================
@bot.message_handler(func=lambda m: m.from_user.id in user_states)
def h_state(m):
    if not check_auth(m): return
    uid=m.from_user.id; st=user_states.get(uid)
    if not st: return
    txt=(m.text or "").strip()
    if txt=='/cancel':
        del user_states[uid]; bot.reply_to(m,"❌ Cancelled"); return
    cwd=get_cwd(uid)
    if st['action']=='newfile':
        fp=os.path.join(cwd,txt)
        try:
            with open(fp,'w') as f: pass
            bot.reply_to(m,"✅ Created: `"+fp+"`",parse_mode='Markdown')
        except Exception as e: bot.reply_to(m,"❌ "+str(e))
        del user_states[uid]
    elif st['action']=='newfolder':
        dp=os.path.join(cwd,txt)
        try: os.makedirs(dp,exist_ok=True); bot.reply_to(m,"✅ Created: `"+dp+"`",parse_mode='Markdown')
        except Exception as e: bot.reply_to(m,"❌ "+str(e))
        del user_states[uid]
    elif st['action']=='edit_content':
        fp=st['filepath']; fn=st['filename']
        try:
            with open(fp,'w') as f: f.write(txt)
            bot.reply_to(m,"✅ Saved: `"+fn+"` ("+fmt_size(os.path.getsize(fp))+")",parse_mode='Markdown')
        except Exception as e: bot.reply_to(m,"❌ "+str(e))
        del user_states[uid]
    elif st['action']=='rename':
        old=st['filepath']; new=os.path.join(os.path.dirname(old),txt)
        try: os.rename(old,new); bot.reply_to(m,"✅ Renamed",parse_mode='Markdown')
        except Exception as e: bot.reply_to(m,"❌ "+str(e))
        del user_states[uid]
    elif st['action']=='chmod':
        fp=st['filepath']
        try:
            md=int(txt,8); os.chmod(fp,md)
            bot.reply_to(m,"✅ Perms: `"+txt+"`",parse_mode='Markdown')
        except ValueError: bot.reply_to(m,"❌ Invalid (use 755 etc)"); return
        except Exception as e: bot.reply_to(m,"❌ "+str(e))
        del user_states[uid]
    elif st['action']=='search':
        bot.send_chat_action(m.chat.id,'typing')
        try:
            r=subprocess.run('find "'+cwd+'" -maxdepth 5 -iname "*'+txt+'*" 2>/dev/null | head -50',
                            shell=True,capture_output=True,text=True,timeout=15)
            if r.stdout.strip():
                fl=r.stdout.strip().split('\n')
                rsp="🔍 `"+txt+"` ("+str(len(fl))+")\n\n"
                for f in fl: rsp+="`"+f+"`\n"
                bot.reply_to(m,rsp[:4000],parse_mode='Markdown')
            else: bot.reply_to(m,"🔍 Nothing found",parse_mode='Markdown')
        except: bot.reply_to(m,"❌ Failed")
        del user_states[uid]
    elif st['action']=='terminal':
        bot.send_chat_action(m.chat.id,'typing')
        try:
            r=subprocess.run(txt,shell=True,cwd=cwd,capture_output=True,text=True,timeout=30)
            out=""
            if r.stdout: out+=r.stdout
            if r.stderr: out+="\nSTDERR:\n"+r.stderr
            if not out: out="Done"
            rsp="💻 `"+txt+"`\nExit: "+str(r.returncode)+"\n\n`"+out[:3500]+"`"
            if len(rsp)>4000:
                with tempfile.NamedTemporaryFile(mode='w',suffix='.txt',delete=False) as f:
                    f.write("$ "+txt+"\n\n"+r.stdout+"\n"+r.stderr); tp=f.name
                with open(tp,'rb') as fl: bot.send_document(m.chat.id,fl,caption=txt)
                os.unlink(tp)
            else: bot.reply_to(m,rsp,parse_mode='Markdown')
        except subprocess.TimeoutExpired: bot.reply_to(m,"⏱ Timeout")
        except Exception as e: bot.reply_to(m,"❌ "+str(e))
        bot.send_message(m.chat.id,"💻 Next cmd or /cancel")
        return
    elif st['action']=='goto':
        p=os.path.abspath(txt)
        if os.path.isdir(p):
            set_cwd(uid,p); user_page[uid]=0
            mk=kb_dir(uid,p,0)
            bot.reply_to(m,"📂 *File Manager*\n📍 `"+p+"`",reply_markup=mk,parse_mode='Markdown')
        else: bot.reply_to(m,"❌ Not found: `"+p+"`",parse_mode='Markdown')
        del user_states[uid]

# ============================================
# START BOT
# ============================================
if __name__ == '__main__':
    print("=" * 40)
    print("  FILE MANAGER BOT STARTED")
    print("  Dir: " + START_DIR)
    print("  Users: " + str(AUTHORIZED_USERS))
    print("=" * 40)
    bot.remove_webhook()
    while True:
        try: bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except KeyboardInterrupt: print("Stopped"); sys.exit(0)
        except Exception as e: print("Error: "+str(e)); time.sleep(5)
