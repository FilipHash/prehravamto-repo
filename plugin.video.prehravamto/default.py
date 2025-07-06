# -*- coding: utf-8 -*-

import sys
import os
import re
import io
import json
import urllib.parse
import urllib.request
import http.cookiejar

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

# Globální proměnné
ADDON = xbmcaddon.Addon()
ADDON_HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]

CJ = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CJ))

PROFILE_DIR = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.prehravamto/')
HISTORY_FILE = os.path.join(PROFILE_DIR, 'history.txt')
CACHE_FILE = os.path.join(PROFILE_DIR, 'csfd_cache.json')
premium_checked = False

ZANRY = {
    "Akční": "https://www.csfd.cz/zebricky/nejlepsi-akcni-filmy/",
    "Animovaný": "https://www.csfd.cz/zebricky/nejlepsi-animovane-filmy/",
    "Dobrodružný": "https://www.csfd.cz/zebricky/nejlepsi-dobrodruzne-filmy/",
    "Dokumentární": "https://www.csfd.cz/zebricky/nejlepsi-dokumentarni-filmy/",
    "Fantasy": "https://www.csfd.cz/zebricky/nejlepsi-fantasy-filmy/",
    "Historický": "https://www.csfd.cz/zebricky/nejlepsi-historicke-filmy/",
    "Horor": "https://www.csfd.cz/zebricky/nejlepsi-horory/",
    "Katastrofický": "https://www.csfd.cz/zebricky/nejlepsi-katastroficke-filmy/",
    "Komedie": "https://www.csfd.cz/zebricky/nejlepsi-komedie/",
    "Krimi": "https://www.csfd.cz/zebricky/nejlepsi-krimi-filmy/",
}


def notify(title, message):
    if ADDON.getSettingBool("enable_notifications"):
        xbmcgui.Dialog().notification(title, message, xbmcgui.NOTIFICATION_INFO, 4000)


def get_credentials():
    email = ADDON.getSetting("email")
    password = ADDON.getSetting("password")
    return email, password


def check_credentials():
    email, password = get_credentials()
    if not email or not password:
        xbmcgui.Dialog().ok("PrehravamTo", "Nejprve vyplňte e-mail a heslo v nastavení addonu.")
        sys.exit()


def build_url(query):
    return BASE_URL + '?' + urllib.parse.urlencode(query)


def main_menu():
    global premium_checked
    if not premium_checked:
        check_credentials()
        email, password = get_credentials()
        if test_login(email, password):
            premium_checked = True

    xbmcplugin.setPluginCategory(ADDON_HANDLE, "PrehravamTo")

    addon_path = os.path.dirname(__file__)
    thumbs = {
        'search': os.path.join(addon_path, 'resources', 'ikony', 'hledat.png'),
        'history': os.path.join(addon_path, 'resources', 'ikony', 'historie.png'),
        'genres': os.path.join(addon_path, 'resources', 'ikony', 'zanr.png'),
        'tip_dnes': os.path.join(addon_path, 'resources', 'ikony', 'tipy.png'),
        'zebricky': os.path.join(addon_path, 'resources', 'ikony', 'zebricek.png'),
        'donate': os.path.join(addon_path, 'resources', 'ikony','qr_donate.jpeg'),
        'settings': os.path.join(addon_path, 'resources', 'ikony', 'nastaveni.png'),
    }

    # Vyhledat film
    li = xbmcgui.ListItem(label='♦ VYHLEDAT DLE NÁZVU ♦ ')
    li.setArt({'thumb': thumbs['search'], 'icon': thumbs['search']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'search'}),
                               listitem=li, isFolder=True)

    # Historie
    li = xbmcgui.ListItem(label='♦  HISTORIE VYHLEDÁVÁNÍ ♦ ')
    li.setArt({'thumb': thumbs['history'], 'icon': thumbs['history']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'history'}),
                               listitem=li, isFolder=True)

    # Podle žánru
    li = xbmcgui.ListItem(label='♦ VÝBĚR DLE ŽÁNRŮ ♦ ')
    li.setArt({'thumb': thumbs['genres'], 'icon': thumbs['genres']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'zanry'}),
                               listitem=li, isFolder=True)

    # Tip na dnes
    li = xbmcgui.ListItem(label='♦ TIPY NA DNES ♦ ')
    li.setArt({'thumb': thumbs['tip_dnes'], 'icon': thumbs['tip_dnes']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'tip_dnes'}),
                               listitem=li, isFolder=True)

    # Žebříčky
    li = xbmcgui.ListItem(label='♦ ŽEBŘÍČKY ♦ ')
    li.setArt({'thumb': thumbs['zebricky'], 'icon': thumbs['zebricky']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'zebricky', 'from': 0}),
                               listitem=li, isFolder=True)

    # Donate
    li = xbmcgui.ListItem(label='♥ DONATE - Podpoř mě ♥ ')
    li.setArt({'thumb': thumbs['donate'], 'icon': thumbs['donate'], 'fanart': thumbs['donate']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'donate'}),
                               listitem=li, isFolder=False)

    # Nastavení
    li = xbmcgui.ListItem(label='♦ NASTAVENÍ ♦')
    li.setArt({'thumb': thumbs['settings'], 'icon': thumbs['settings']})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE,
                               url=build_url({'action': 'settings'}),
                               listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)



def parse_premium_time(html):
    match = re.search(r'Premium:[^<]*</strong>\s*<span[^>]*class="color-green"[^>]*>([^<]+)</span>', html, re.I)
    if match:
        return match.group(1).strip()
    return None


def test_login(email, password):
    login_url = 'https://prehrajto.cz/'
    data = urllib.parse.urlencode({
        'email': email,
        'password': password,
        '_submit': 'Přihlásit se',
        '_do': 'login-loginForm-submit',
    }).encode('utf-8')

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://prehrajto.cz/#login',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    req = urllib.request.Request(login_url, data=data, headers=headers)
    with OPENER.open(req) as response:
        html = response.read().decode('utf-8')

    if "Odhlásit" in html:
        premium = parse_premium_time(html)
        if premium:
            notify("prehrajto.cz Premium", f"Zbývá: {premium}")
        else:
            notify("prehrajto.cz", "Přihlášení OK")
        return True
    else:
        xbmcgui.Dialog().ok("prehrajto.cz", "Přihlášení selhalo.")
        return False


def load_cache():
    if xbmcvfs.exists(CACHE_FILE):
        with io.open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    folder = os.path.dirname(CACHE_FILE)
    if not xbmcvfs.exists(folder):
        xbmcvfs.mkdirs(folder)
    with io.open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_csfd_plot(query_title):
    if not ADDON.getSettingBool("enable_csfd_info"):
        return ""

    cache = load_cache()
    if query_title in cache:
        return cache[query_title]

    try:
        search_url = f"https://www.csfd.cz/hledat/?q={urllib.parse.quote(query_title)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(search_url, headers=headers)
        with OPENER.open(req) as response:
            html = response.read().decode('utf-8')

        match = re.search(r'<a href="(/film/\d+-[^/]+/)"[^>]*class="film-title-name"', html)
        if match:
            film_url = "https://www.csfd.cz" + match.group(1)
            req = urllib.request.Request(film_url, headers=headers)
            with OPENER.open(req) as response:
                film_html = response.read().decode('utf-8')

            plot_match = re.search(r'<div class="plot-preview">.*?<p>(.*?)</p>', film_html, re.DOTALL)
            if plot_match:
                plot = re.sub(r'<.*?>', '', plot_match.group(1)).strip()
                cache[query_title] = plot
                save_cache(cache)
                return plot

    except Exception as e:
        xbmc.log(f"[CSFD ERROR] {e}", xbmc.LOGERROR)

    cache[query_title] = ""
    save_cache(cache)
    return ""


def search_movies(query, page=1):
    search_url = f"https://prehrajto.cz/hledej/{urllib.parse.quote(query)}?vp-page={page}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(search_url, headers=headers)
    with OPENER.open(req) as response:
        html = response.read().decode('utf-8')

    pattern = re.compile(r'<a class="video[^"]*" href="([^"]+)"[^>]*>.*?<h3 class="video__title[^"]*">(.*?)</h3>', re.DOTALL)
    results = []
    for href, title in pattern.findall(html):
        title_clean = re.sub(r'<.*?>', '', title).strip()
        url = 'https://prehrajto.cz' + href
        results.append({'title': title_clean, 'url': url})

    return results


def list_search_results(query, page=1, from_tip='0'):
    save_search_history(query)
    movies = search_movies(query, page)

    if from_tip in ['0', '2']:
        if page > 1:
            prev_url = build_url({'action': 'search_results', 'query': query, 'page': page - 1, 'from_tip': from_tip})
            xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=prev_url,
                                        listitem=xbmcgui.ListItem(label='Předchozí stránka'), isFolder=True)
        next_url = build_url({'action': 'search_results', 'query': query, 'page': page + 1, 'from_tip': from_tip})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=next_url,
                                    listitem=xbmcgui.ListItem(label='Další stránka'), isFolder=True)

    if from_tip == '0' and page == 1 and ADDON.getSettingBool("enable_csfd_info"):
        plot = get_csfd_plot(query)
        url = build_url({'action': 'search_results', 'query': query, 'page': 1, 'from_tip': '2'})
        li_info = xbmcgui.ListItem(label=query)
        li_info.setInfo('video', {'title': query, 'plot': plot})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li_info, isFolder=True)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return

    elif from_tip == '1' and ADDON.getSettingBool("enable_csfd_info"):
        for movie in movies:
            plot = get_csfd_plot(movie['title'])
            url = build_url({'action': 'search_results', 'query': movie['title'], 'page': 1, 'from_tip': '2'})
            li = xbmcgui.ListItem(label=movie['title'])
            li.setInfo('video', {'title': movie['title'], 'plot': plot})
            xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return

    else:
        for movie in movies:
            url = build_url({'action': 'play', 'video_url': movie['url'], 'title': movie['title']})
            li = xbmcgui.ListItem(label=movie['title'])
            li.setProperty('IsPlayable', 'true')
            li.setInfo('video', {'title': movie['title']})
            xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def save_search_history(query):
    folder = os.path.dirname(HISTORY_FILE)
    if not xbmcvfs.exists(folder):
        xbmcvfs.mkdirs(folder)
    with io.open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(query + '\n')


def load_search_history():
    if not xbmcvfs.exists(HISTORY_FILE):
        return []
    with io.open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    seen = set()
    unique = []
    for line in reversed(lines):
        if line and line not in seen:
            unique.append(line)
            seen.add(line)
    return unique


def show_history():
    history = load_search_history()
    if not history:
        xbmcgui.Dialog().ok("PrehravamTo", "Historie je prázdná.")
        return

    for query in history:
        url = build_url({'action': 'search_results', 'query': query, 'page': 1, 'from_tip': '0'})
        li = xbmcgui.ListItem(label=query)
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def play_movie(video_url, title='Film'):
    stream_url = video_url + "?do=download"
    li = xbmcgui.ListItem(path=stream_url)
    li.setInfo('video', {'title': title})
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def csfd_tip_na_dnes():
    req = urllib.request.Request('https://www.csfd.cz/televize/', headers={'User-Agent': 'Mozilla/5.0'})
    with OPENER.open(req) as response:
        html = response.read().decode('utf-8')

    pattern = re.compile(r'<a href="(/film/\d+-[^/]+/)" class="film-title-name">(.*?)</a>')
    films = pattern.findall(html)

    for href, title in films:
        query = title.strip()
        plot = get_csfd_plot(query)
        url = build_url({'action': 'search_results', 'query': query, 'page': 1, 'from_tip': '1'})
        li = xbmcgui.ListItem(label=query)
        li.setInfo('video', {'title': query, 'plot': plot})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def csfd_zebricky(start_from=0):
    url = f"https://www.csfd.cz/zebricky/filmy/nejlepsi/"
    if start_from > 0:
        url += f"?from={start_from}"

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with OPENER.open(req) as response:
        html = response.read().decode('utf-8')

    pattern = re.compile(r'<a[^>]*href="(/film/\d+-[^/]+/)"[^>]*class="film-title-name"[^>]*>(.*?)</a>', re.DOTALL)
    films = pattern.findall(html)[:100]

    for href, title in films:
        query = title.strip()
        plot = get_csfd_plot(query)
        url = build_url({'action': 'search_results', 'query': query, 'page': 1, 'from_tip': '1'})
        li = xbmcgui.ListItem(label=query)
        li.setInfo('video', {'title': query, 'plot': plot})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)

    if films:
        next_url = build_url({'action': 'zebricky', 'from': start_from + 100})
        li = xbmcgui.ListItem(label='Další stránka žebříčku')
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=next_url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def csfd_zanry_menu():
    for zanr, link in ZANRY.items():
        url = build_url({'action': 'zanr_filmy', 'zanr': zanr, 'page': 1})
        li = xbmcgui.ListItem(label=zanr)
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def csfd_zanr_filmy(zanr, page=1):
    base_url = ZANRY.get(zanr)
    if not base_url:
        xbmcgui.Dialog().ok("PrehravamTo", "Žánr nenalezen.")
        return

    url = base_url
    if page > 1:
        url += f"?page={page}"

    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with OPENER.open(req) as response:
        html = response.read().decode('utf-8')

    pattern = re.compile(r'<a href="(/film/\d+-[^/]+/)" title="[^"]+" class="film-title-name">\s*(.*?)\s*</a>')
    films = pattern.findall(html)

    for href, title in films:
        query = title.strip()
        plot = get_csfd_plot(query)
        url = build_url({'action': 'search_results', 'query': query, 'page': 1, 'from_tip': '1'})
        li = xbmcgui.ListItem(label=query)
        li.setInfo('video', {'title': query, 'plot': plot})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)

    if films:
        next_url = build_url({'action': 'zanr_filmy', 'zanr': zanr, 'page': page + 1})
        li = xbmcgui.ListItem(label='Další stránka')
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=next_url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)
    

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get('action')

    if action == 'search':
        keyboard = xbmc.Keyboard('', 'Zadej název filmu')
        keyboard.doModal()
        if keyboard.isConfirmed():
            query = keyboard.getText().strip()
            if query:
                list_search_results(query, 1, from_tip='0')
    elif action == 'search_results':
        query = params.get('query')
        page = int(params.get('page', '1'))
        from_tip = params.get('from_tip', '0')
        list_search_results(query, page, from_tip=from_tip)
    elif action == 'history':
        show_history()
    elif action == 'play':
        play_movie(params.get('video_url', ''), params.get('title', 'Film'))
    elif action == 'tip_dnes':
        csfd_tip_na_dnes()
    elif action == 'zebricky':
        csfd_zebricky(int(params.get('from', '0')))
    elif action == 'zanry':
        csfd_zanry_menu()
    elif action == 'zanr_filmy':
        zanr = params.get('zanr')
        page = int(params.get('page', '1'))
        csfd_zanr_filmy(zanr, page)  
    elif action == 'settings':
        ADDON.openSettings()
     
    else:
        main_menu()


if __name__ == '__main__':
    router(sys.argv[2][1:] if len(sys.argv) > 2 else '')