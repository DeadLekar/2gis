from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import time
from bs4 import BeautifulSoup
import sqlite3 as lite
import serviceFunctions as sf
from datetime import datetime
from enum import Enum
import requests

class brother_regime(Enum):
    TAG_NAME = 1
    CLASS_NAME = 2
    ALL = 3

def get_last_child(el, child_arr, soup):
    for ch_name in child_arr:
        next_el = soup


def get_cities(driver,c,conn):
    cities = {}
    link = "https://2gis.ru/countries/global/moscow?queryState=center%2F27.224121%2C55.751849%2Fzoom%2F5"
    driver.get(link)

    txt = driver.execute_script("return document.body.innerHTML")
    soup = BeautifulSoup(''.join(txt), 'html.parser')

    elements = soup.find_all('div', 'world__countries')
    if len(elements) == 0:
        return

    children = elements[0].findChildren('li','world__listItem')
    for ch in children:
        name = ch.contents[1].text
        link = ch.contents[1].contents[0].attrs['href']
        cities[name] = link
        if len(ch.contents) == 3:
            for sub_ch in ch.contents[2].contents:
                name = sub_ch.contents[0].text
                cities[name] = 'None'

    for city in cities:
        qurery_str = "INSERT INTO cities (name, link) VALUES ('" + city + "','" + cities[city] + "')"
        c.execute(qurery_str)
        conn.commit()


def get_next_city(driver, cr_city):
    txt = driver.execute_script("return document.body.innerHTML")
    soup = BeautifulSoup(''.join(txt), 'html.parser')
    elements = soup.find_all('div', 'world__countries')
    i = 0
    flg_cr_city_found = False
    for el in elements[0].contents[0].contents[1].contents:
        if cr_city != "" and cr_city in el.text:
            flg_cr_city_found = True
        else:
            if cr_city == "" or flg_cr_city_found:
                click_elements = driver.find_elements_by_class_name("world__section")
                for click_el in click_elements:
                    if "Россия" in click_el.text:
                        click_el.click()
                        click_elements = click_el.find_elements_by_class_name("world__list")
                        click_elements = click_elements[0].find_elements_by_class_name("world__listItem")
                        click_elements[i].click()
                        return driver, el.contents[1].text
        i += 1
    return driver, ""

#def click(x,y):
#    win32api.SetCursorPos((x,y))
#    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
#    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)

def load_next_page(soup, driver, site_props, visited_links):
    # derermines the next page button on the page, tries to click it
    cr_link = driver.current_url
    flg_return_1 = False
    paginator = soup.find_all(site_props['nextPaginatorNameTag'], site_props['nextPaginatorNameClass'])

    next_link = ""
    if len(paginator) > 0:
        # look for the last element
        last_el = None
        last_class = None
        #css_str = "."
        for el in paginator[0].contents:
            if hasattr(el, "attrs"):
                last_el = el
        #data_tree = sf.get_contents_tree(last_el)
        brothers_list = sf.get_html_brothers_v2(last_el, brother_regime.TAG_NAME)
        if len(brothers_list) > 0:
            last_brother = None
            last_brother_cont = None
            for brother in brothers_list[0]:
                brother_cont_list = sf.get_contents_tree(brother)
                for brother_cont in brother_cont_list:
                    if brother_cont.tag_name == "a":
                        last_brother_cont = brother_cont
                        break
            if last_brother_cont.text != "":
                clear_link = sf.clear_link(last_brother_cont.text, '')
                if clear_link in visited_links:
                    return 0
                try:
                    clear_link = sf.clear_link(last_brother_cont.text, '')
                    driver.get(clear_link)
                    return 1
                except:
                    pass

        if last_el.attrs.get('href'):
            next_link = last_el.attrs['href']
            if site_props.get("linkPrefix"):
                if not site_props['linkPrefix'] in next_link:
                    next_link = site_props['linkPrefix'] + next_link
            if next_link != cr_link:
                driver.get(next_link)
                return 1 # next link is loaded
            else:
                return 0 # link is finished

        if hasattr(last_el, "attrs"):
            if len(last_el.attrs.get("class")) > 1: #lamoda
                css_str = "."
                for css_el in last_el.attrs.get("class"):
                    css_str += css_el + "."
                css_str = css_str[:len(css_str)-1]
                click_el = driver.find_element_by_css_selector(css_str)
                if click_el.location['x'] == 0:
                    return 0
            else:
                last_class = last_el.attrs.get("class")[0]
                click_el = driver.find_element_by_class_name(last_class)
            driver.execute_script("window.scrollBy(0," + str(click_el.location['y'] - 200) + ")")
            if site_props.get("closeWindow"):
                try:
                    close_elements = driver.find_elements_by_class_name(site_props['closeWindow'])
                    for close_el in close_elements:
                        if close_el.location['x'] > 0 and close_el.location['y'] > 0:
                            close_el.click()
                except:
                    pass
            try:
                click_el.click()
            except:
                return 0
            return 1
        else:
            pass
        #try:
            last_el.click()
            return 1
        #except:
        #    pass

def seek_companies(dbPath, driverPath):
    #seeks for companies in all cities; fills db table

    # load object to seek
    objects = {}
    conn = lite.connect(dbPath)
    c = conn.cursor()
    c.execute("SELECT id, name FROM objects WHERE isChecked=0")
    for obj_row in c.fetchall():
        objects[obj_row[0]] = obj_row[1]

    driver = webdriver.Chrome(driverPath)
    cr_city = ""
    visited_links = []

    for obj in objects:
        while 1:
            link = "https://2gis.ru/countries/global/moscow?queryState=center%2F27.224121%2C55.751849%2Fzoom%2F5"
            driver.get(link)
            driver.maximize_window()
            driver, cr_city = get_next_city(driver, cr_city)
            if cr_city == "":
                break
            time.sleep(2)
            seek_form = driver.find_elements_by_class_name("suggest__input")
            if len(seek_form) > 0:
                isCheckedReq = c.execute("SELECT id FROM checkedData WHERE city = '" + cr_city + "' AND obj = '" + objects[obj] + "'").fetchall()
                if len(isCheckedReq) == 0:
                    seek_form[0].clear()
                    seek_form[0].send_keys(objects[obj])
                    btn = driver.find_elements_by_class_name("searchBar__submit")
                    if len(btn) > 0:
                        btn[0].click()
                        while 1:
                            time.sleep(3)
                            if driver.current_url in visited_links:
                                break
                            txt = driver.execute_script("return document.body.innerHTML")
                            soup = BeautifulSoup(''.join(txt), 'html.parser')
                            cards = soup.find_all("div", "miniCard__content")
                            if len(cards) == 0:
                                cards = soup.find_all("div", "card__scrollerIn")
                            # cards = driver.find_elements_by_class_name("miniCard__content")
                            if len(cards) > 0:
                                # frame = driver.find_element_by_class_name("searchResults__content")
                                # hover = ActionChains(driver).move_to_element(frame)
                                # hover.perform()
                                # driver.execute_script("window.scrollBy(0, 200)")
                                # time.sleep(5)
                                for card in cards:
                                    data_tree = sf.get_contents_tree(card)
                                    obj_link = ""
                                    obj_type = ""
                                    obj_addr = ""
                                    obj_name = ""
                                    for data_el in data_tree:
                                        if data_el.class_name == "link" and obj_link == "":
                                            obj_link = data_el.text.strip()
                                        elif data_el.class_name == "miniCard__headerTitleLink" and obj_type == "" and data_el.text[0] != "/":
                                            obj_type_arr = data_el.text.split(",")
                                            obj_type = obj_type_arr[len(obj_type_arr)-1].strip()
                                            obj_name = (','.join(obj_type_arr[:len(obj_type_arr)-1])).strip()
                                        elif data_el.class_name == "cardHeader__headerNameText":
                                            obj_name = data_el.text
                                        elif data_el.class_name == "cardHeader__headerDescriptionText":
                                            obj_type = data_el.text
                                        elif data_el.class_name == "card__addressLink":
                                            obj_addr = data_el.text
                                        elif data_el.class_name == "miniCard__headerTitleLink" and obj_link == "":
                                            obj_link = data_el.text.strip()
                                        elif data_el.class_name == "miniCard__address" and obj_addr == "":
                                            obj_addr = data_el.text.strip()
                                    if obj_link != "" and obj_type != "" and obj_addr != "":
                                        while 1:
                                            try:
                                                c.execute("INSERT INTO output (name, addr, link, request, industry, city) VALUES ('" + obj_name + "','" + obj_addr + "','" + obj_link + "','" + objects[obj] + "','" + obj_type + "','" + cr_city + "')")
                                                conn.commit()
                                                break
                                            except: pass
                                    # close_el = driver.find_elements_by_class_name("_close")
                                    # close_el = driver.find_elements_by_css_selector("a.link.frame__controlsButton._close._undashed")
                                    # if len(close_el) > 0:
                                    #    close_el[len(close_el)-1].click()
                            visited_links.append(driver.current_url)
                            if not load_next_page(soup, driver, {'nextPaginatorNameTag': 'div', 'nextPaginatorNameClass': 'pagination'}, visited_links):
                                break
                    c.execute("INSERT INTO checkedData (obj, city) VALUES ('" + objects[obj] + "','" + cr_city + "')")
                    conn.commit()
                    try:
                        back_link = driver.find_element_by_css_selector("a.link.frame__controlsButton._back._undashed")
                        if back_link:
                            if back_link.location['x'] > 0 and back_link.location['y'] > 0:
                                back_link.click()
                                time.sleep(2)
                                seek_form = driver.find_elements_by_class_name("suggest__input")
                                continue
                    except: pass

def read_address(driver):
    result = []
    try:
        org_button = driver.find_element_by_css_selector("a.cardInfrastructureItem__link._type_firms._clickable")
    except: return None

    org_button.click()
    time.sleep(2)
    companies = driver.find_elements_by_css_selector("article.miniCard._type_branch._searchType_inbuild")
    for comp in companies:
        name = comp.text.split("\n")[0]
        name_arr = name.split(",")  # get industry
        result.append([name, name_arr[-1]])
    return result

    #companies = []
    #txt = driver.execute_script("return document.body.innerHTML")
    #soup = BeautifulSoup(''.join(txt), 'html.parser')
    #cards = soup.find_all("div", "cardInfrastructureFirmsList__listItemName")
    #for card in cards:
    #    name = card.contents[0].contents[0]
    #    name_arr = name.split(",")  # get industry
    #    companies.append([name, name_arr[-1]])
    #return companies


def start_driver(link, seek_form_class_name, btn_class_name):
    driver = webdriver.Chrome(driverPath)
    driver.get(link)
    driver.maximize_window()
    seek_form = driver.find_element_by_class_name(seek_form_class_name)
    btn = driver.find_element_by_class_name(btn_class_name)
    return driver, seek_form, btn


def read_single_card(driver):
    """
    reads data from 2gis single card
    :param driver: Chrome
    :return: data_dict: {fieldName: [fieldValue, flgStringType]}, back_link
    """
    data_dict = {}
    back_link = None
    try:
        brand_name = sf.clear_string(driver.find_element_by_class_name("cardHeader__headerNameText").text, sf.rus_letters + sf.lat_letters + sf.digits + sf.puncts + " ")
        data_dict["brandName"] = [brand_name, True]
    except: pass
    try:
        addr = driver.find_element_by_class_name("card__addressLink").text
        data_dict["addr"] = [sf.clear_string(addr, sf.lat_letters+sf.rus_letters+sf.puncts+sf.digits), True]
    except: pass
    try:
        subs_num = driver.find_element_by_class_name("mediaContacts__filials").text
        data_dict["subsNum"] = [subs_num, False]
    except: pass

    txt = driver.execute_script("return document.body.innerHTML")
    soup = BeautifulSoup(''.join(txt), 'html.parser')
    geo_list = soup.find_all("div", "_geo")
    for geo in geo_list:
        for cont in geo.contents:
            if hasattr(cont, 'attrs'):
                data_lat = cont.attrs.get('data-lat')
                data_lon = cont.attrs.get('data-lon')
                if data_lat:
                    data_dict["geo_lat"] = [data_lat, False]
                    data_dict["geo_lon"] = [data_lon, False]
                    break
    try:
        back_links = driver.find_elements_by_css_selector("a.link.frame__controlsButton._close._undashed")
        for link in back_links:
            if link.location['x'] > 0 and link.location['y'] > 0:
                back_link = link
                break
    except: pass

    return data_dict, back_link


def click_element(driver, name, flg_class=True):
    # click to all-types button
    try:
        if flg_class:
            elem = driver.find_element_by_class_name(name)
        else:
            elem = driver.find_element_by_css_selector(name)
        elem.click()
        time.sleep(2)
    except: pass


def seek_industries_search_bar(dbPath, driverPath):
    # seeks for companies in all cities; fills db table
    # load objects to seek

    categories = {}
    conn = lite.connect(dbPath)
    c = conn.cursor()
    c.execute("SELECT id, name FROM searches WHERE isChecked=0")
    for obj_row in c.fetchall():
        categories[obj_row[0]] = obj_row[1]

    cities_to_look = ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Нижний Новгород', 'Казань', 'Челябинск', 'Омск', 'Самара', 'Ростов-на-Дону', 'Уфа', 'Красноярск', 'Пермь', 'Воронеж','Волгоград']
    cr_city = ""
    visited_links = []
    start_link = "https://2gis.ru/countries/global/moscow?queryState=center%2F27.224121%2C55.751849%2Fzoom%2F5" # the link to enter a new city
    flg_reload_categories = False
    while 1: # go through cities
        driver = webdriver.Chrome(driverPath)
        driver.get(start_link)
        driver.maximize_window()
        if not flg_reload_categories:
            driver, cr_city = get_next_city(driver, cr_city)
        if cr_city == "": break
        time.sleep(2)
        while 1: # go through categories
            if cr_city not in cities_to_look:
            #if cr_city != 'Екатеринбург':
                driver.close()
                flg_reload_categories = False
                break

            cat_name = get_next_category(categories, cr_city, conn)
            if not cat_name:
                driver.close()
                flg_reload_categories = False
                break # go to the next city
            seek_form = driver.find_elements_by_class_name("suggest__input")
            if len(seek_form) > 0:
                seek_form[0].clear()
                seek_form[0].send_keys(cat_name)
                btn = driver.find_elements_by_class_name("searchBar__submit")
                if len(btn) > 0:
                    btn[0].click()
                    time.sleep(2)
                    while 1: # go through companies in current category
                        cards = driver.find_elements_by_class_name("miniCard__content")
                        if cards:
                            for card in cards: # collect data for each company on the page
                                # driver.execute_script("window.scrollBy(0," + str(card.location['y'] - 200) + ")")
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                try:
                                    card.click()
                                    data_dict = {}
                                    data_dict["catName"] = [cat_name, True]
                                    data_dict["cityName"] = [cr_city, True]
                                    time.sleep(3)
                                    # read and save data
                                    # txt = driver.execute_script("return document.body.innerHTML")
                                    # soup = BeautifulSoup(''.join(txt), 'html.parser')
                                    # brand_name = sf.clear_string(driver.find_element_by_class_name("cardHeader__headerNameText").text, sf.rus_letters+sf.lat_letters+sf.digits+sf.puncts+" ")
                                    brand_name = sf.clear_string(card.find_element_by_class_name('miniCard__headerTitleLink').text, sf.rus_letters+sf.lat_letters+sf.digits+sf.puncts+" ")
                                    data_dict["brandName"] = [brand_name, True]
                                except: pass
                                try:
                                    addr = driver.find_element_by_class_name("card__addressLink").text
                                    data_dict["addr"] = [addr, True]
                                except: pass
                                try:
                                    web_site = driver.find_element_by_class_name("link").text
                                    data_dict["webSite"] = [web_site, True]
                                except: pass
                                try:
                                    filials_num = sf.clear_string(driver.find_element_by_class_name("card__filialsLink").text, sf.digits)
                                    data_dict["filialsNum"] = [filials_num, True]
                                except: pass

                                cmd = sf.build_insert_expression(data_dict, "output_categories")
                                sf.execute_query(conn, cmd, 3)

                                try:
                                    css_arr = ["a.link.frame__controlsButton._back._undashed","a.link.frame__controlsButton._close._undashed"]
                                    for css in css_arr:
                                        if click_closing_button(driver, css): break
                                    else:
                                        print ('Did not find closing button for:' + driver.current_url)
                                except: pass

                        else: # got a single card
                            data_dict, back_link = read_single_card(driver)
                            if len(data_dict) == 0:
                                print("unable to read data: city = {}, category = {}, link = {}".format(cr_city, cat_name, driver.current_url))
                            else:
                                data_dict["catName"] = [cat_name, True]
                                data_dict["cityName"] = [cr_city, True]
                                cmd = sf.build_insert_expression(data_dict, "output_categories")
                                sf.execute_query(conn, cmd, 3)

                            if back_link.location_once_scrolled_into_view['x'] > 0 and back_link.location_once_scrolled_into_view['y'] > 0:
                                try:
                                    back_link.click()
                                    time.sleep(2)
                                    flg_reload_categories = True
                                except: pass
                                break

                        # load next page
                        try:
                            next_link_disabled = driver.find_element_by_css_selector("div.pagination__arrow._right._disabled")
                            click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
                            flg_reload_categories = True
                            break # a disabled next arrow found - the end of the list
                        except:
                            next_link = driver.find_element_by_css_selector("div.pagination__arrow._right")
                            next_link.click()
                            time.sleep(2)
                        finally:
                            flg_reload_categories = True
                            break
                    sf.execute_query(conn, "INSERT INTO checkedData (obj, city) VALUES ('{}', '{}')".format(cat_name, cr_city))
    driver.close()

def click_closing_button(driver, css_sting):
    back_links = driver.find_elements_by_css_selector(css_sting)
    for link in back_links:
        if link.location['x'] > 0 and link.location['y'] > 0:
            link.click()
            time.sleep(2)
            return True

def get_next_category(categories, cr_city, conn):
    c = conn.cursor()
    for cat in categories:
        cat_name = categories[cat]
        flg_checked = c.execute("SELECT id FROM checkedData WHERE obj='{}' AND city='{}'".format(cat_name, cr_city)).fetchone()
        if not flg_checked: return cat_name


def get_next_page(driver):
    try:
        next_link_disabled = driver.find_element_by_css_selector("div.pagination__arrow._right._disabled")
        # if here, there's no further pages in category: closing the frame
        # click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
        # click_element(driver, "a.link.frame__controlsButton._close._undashed", False)
        # time.sleep(2)
        return 0  # a disabled next arrow found - the end of the list
    except:
        i = 0
        while 1:
            i += 1
            print('trying to locate the arrow {}'.format(i))
            def find_next_link(driver):
                next_link = driver.find_element_by_css_selector("div.pagination__arrow._right")
                if next_link:
                    return next_link
                else:
                    return 0 # no next link

            next_link = WebDriverWait(driver, 5).until(find_next_link)
            time.sleep(1)
            try:
                next_link.location_once_scrolled_into_view
                break
            except:
                pass

        i = 0
        while 1:
            i += 1
            print('trying to click next arrow {}'.format(i))
            try:
                while next_link.location['x'] == 0: pass
                next_link.click()
                break
            except:
                pass
            if i > 10:
                return -1 # unable to locate next arrow, need to refrash
        return 1 # next arrow is clicked


def seek_industries_4(dbPath, driverPath):
    # seeks for companies in all cities; fills db table with links

    # load objects to seek
    cnt_loads = 0
    conn = lite.connect(dbPath)
    c = conn.cursor()

    categories = {}
    c.execute("SELECT id, name FROM categories WHERE isActive=1")
    for obj_row in c.fetchall(): categories[obj_row[0]] = obj_row[1]

    cities = {}
    c.execute("SELECT id, name FROM cities WHERE isActive=1")
    for obj_row in c.fetchall(): cities[obj_row[0]] = obj_row[1]

    driver = webdriver.Chrome(driverPath)
    link_template = 'https://2gis.ru/{}/search/{}/'

    for city_id in cities.keys():
        cr_city = cities[city_id]
        for cat_id in categories.keys():
            cr_cat = categories[cat_id]
            is_checked = c.execute("SELECT id FROM checkedData WHERE category='{}' AND city='{}'".format(cr_cat,cr_city))
            if not is_checked.fetchone():
                cr_link = link_template.format(cr_city,cr_cat)
                driver.maximize_window()
                driver.get(cr_link)
                time.sleep(6)
                txt = driver.execute_script("return document.body.innerHTML")
                soup = BeautifulSoup(''.join(txt), 'html.parser')
                total_objects_el = soup.find_all('span', 'searchBar__mediaTabTextValue')
                if len(total_objects_el) > 0:
                    total_objects_num = total_objects_el[0].text
                else:
                    print('Unable to get total number of the companies for {}'.format(cr_link))
                    break
                cnt_objects = 0
                while 1:  # go through companies in current category
                    cards_list = soup.findAll("a", "mediaMiniCard__link")
                    if cards_list:  # large list
                        for card in cards_list:  # collect data for each company on the page
                            cnt_objects += 1
                            href = card.attrs['href']
                            if href:
                                sf.execute_query(conn, "INSERT INTO output (category, city, link) VALUES ('{}','{}','{}')".format(cr_cat, cr_city, href))
                    else:  # mini list
                        cards_list = soup.find_all("div", "searchResults__list")
                        if cards_list:
                            for card in cards_list[0].contents:
                                cnt_objects += 1
                                link_item = card.find_all("a", "miniCard__headerTitleLink")
                                if link_item:
                                    href = link_item[0].attrs.get('href')
                                    if href:
                                        sf.execute_query(conn,"INSERT INTO output (category, city, link) VALUES ('{}','{}','{}')".format(cr_cat, cr_city, href))

                        else:  # single card
                            cnt_objects += 1
                            data_dict, back_link = read_single_card(driver)
                            if len(data_dict) == 0:
                                print("unable to read data: city = {}, category = {}, link = {}".format(cr_city,cr_cat,driver.current_url))
                            else:
                                data_dict["catName"] = [cr_cat, True]
                                data_dict["cityName"] = [cr_city, True]
                                cmd = sf.build_insert_expression(data_dict, "output_categories")
                                sf.execute_query(conn, cmd, 3)
                            back_link.click()
                            time.sleep(2)
                            break

                    # get next link
                    response = get_next_page(driver)
                    while response == -1:
                        driver.get(driver.current_url)
                        response = get_next_page(driver)
                    if response == 0: break
                    txt = driver.execute_script("return document.body.innerHTML")
                    soup = BeautifulSoup(''.join(txt), 'html.parser')
                sf.execute_query(conn,"INSERT INTO checkedData (category, city) VALUES ('{}', '{}')".format(cr_cat, cr_city))
                if cnt_objects / total_objects_num < 0.9:
                    print('{} objects detected instead of {} for {}'.format(cnt_objects, total_objects_num, cr_city))

    # else:
    #    click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
    #    click_element(driver, "a.link.frame__controlsButton._close._undashed", False)
    #    time.sleep(2)


def get_next_link(conn):
    """
    returns next link to download
    :param conn: connection to database
    :return: a dictionnary with link id, url, category name
    """
    c = conn.cursor()
    row = c.execute("SELECT id, link, catName FROM links WHERE isChecked=0").fetchone()
    return {'id': row[0], 'link': row[1], 'catName': row[2]}

def get_geo(dbPath, table_name):
    i = 1
    conn = lite.connect(dbPath)
    c = conn.cursor()
    rows = c.execute("SELECT link, id FROM {} WHERE link is not null AND geo_lon is Null".format(table_name)).fetchall()
    for row in rows:
        if i % 500 == 0: print(i)
        link = row[0]
        id = row[1]
        left = link.find('%2F')
        if left > 0:
            link1 = link[left + 3:]
            center = link1.find('%2C')
            if center > 0:
                lon = link1[: center]
                right = link1.find('%2F')
                if right > 0:
                    lat = link1[center + 3 : right]
                    sf.execute_query(conn, "UPDATE {} SET geo_lon = {} WHERE id = {}".format(table_name, lon, id), 3)
                    sf.execute_query(conn, "UPDATE {} SET geo_lat = {} WHERE id = {}".format(table_name, lat, id), 3)
                    i += 1
        else:
            print(link)

def read_link(link):
    result = {}
    r = requests.get(link)
    soup = BeautifulSoup(r.text, 'html.parser')

    name_el = soup.find_all("h1", "mediaCardHeader__cardHeaderName")
    if not name_el: #small card
        name_el = soup.find_all("h1", "cardHeader__headerNameText")
        if not name_el:
            name_el = soup.find_all("div", "card__headerWrapper")
    if name_el:
        val = name_el[0].text.split(',')[0]
        result['brand'] = sf.clear_string(val, sf.rus_letters + sf.lat_letters + sf.digits + sf.puncts + ' ')

    comp_type = soup.find_all("div", "cardHeader__headerDescriptionText")
    if comp_type:
        result["compType"] = comp_type[0].text

    addr_el = soup.find_all("div", "mediaCardHeader__cardAddressName")
    if not addr_el:
        addr_el = soup.find_all("a", "card__addressLink")

    if addr_el:
        result['addr'] = sf.clear_string(addr_el[0].text, sf.rus_letters + sf.lat_letters + sf.digits + sf.puncts + ' ' + '/')
        """
        addr_arr = result['addr'].split(',')
        if len(addr_arr) > 1:
            result['cityName'] = addr_arr[1]
        else:
            result['cityName'] = result['addr']
        """

    tel_el = soup.find_all("a", "contact__phonesItemLink")
    if not tel_el:
        tel_el = soup.find_all("a", "mediaContacts__phonesNumber")
    if tel_el:
        result['tel'] = tel_el[0].text

    rubric_el = soup.find_all("div", "cardRubrics__rubrics")
    if not rubric_el:
        rubric_el = soup.find_all("div", "mediaAttributes__rubrics")
    if rubric_el:
        txt = ""
        for el in rubric_el[0].contents:
            txt += el.text + "|"
        txt = txt[:len(txt)-1]
        result['gisCatStr'] = txt
        result['gisCatMain'] = txt.split("|")[0]

    website_el = soup.find_all("div", "card__legal")
    if not website_el:
        website_el = soup.find_all("a", "mediaContacts__website")
    if not website_el:
        website_el = soup.find_all("a", "contact__linkText")
        if website_el:
            if hasattr(website_el[0], 'attrs'):
                result['website'] = website_el[0].get('title')
    else:
        result['website'] = website_el[0].text

    description_el = soup.find_all("li", "cardAttributes__attrsListItem")
    if not description_el:
        description_el = soup.find_all("ul", "mediaAttributes__groupList")
    descr_field = ''
    if description_el:
        for el in description_el[0].contents:
            descr_field += el.text + ';'
        descr_field = descr_field[0:-1]
        result['descr'] = descr_field

        # get stars
        stars_pos = result['descr'].find('звезд')
        if stars_pos != -1:
            result['stars'] = result['descr'][stars_pos - 2 : stars_pos - 1]

        # get restaurant
        rest_pos = result['descr'].find('естор')
        if rest_pos != -1:
            result['hasRest'] = 1

        # get price
        bill_offset = 5
        bill_pos = result['descr'].find(' чек ')
        if bill_pos == -1:
            bill_pos = result['descr'].find(' чек')
            bill_offset = 4
        if bill_pos == -1:
            bill_pos = result['descr'].find(' от ')
            bill_offset = 4

        if bill_pos != -1:
            bill = ''
            while sf.is_digit(result['descr'][bill_pos + bill_offset]):
                bill += str(result['descr'][bill_pos + bill_offset])
                bill_pos += 1
            result['bill'] = bill

    return result

def read_addr_cards(dbPath, table_name):
    conn = lite.connect(dbPath)
    c = conn.cursor()
    rows = c.execute("SELECT link, id FROM {} WHERE link is not Null and isChecked = 0".format(table_name)).fetchall()
    LINK_START = "https://2gis.ru"
    cnt = 0
    for row in rows:
        link = LINK_START + row[0]
        print(link)
        id = row[1]
        html_data = read_link(link)
        if len(html_data) > 0:
            if html_data.get('addr'): sf.execute_query(conn, "UPDATE {} SET addr = '{}' WHERE id={}".format(table_name, html_data['addr'], id), 3)
            if html_data.get('brand'): sf.execute_query(conn,"UPDATE {} SET brand = '{}' WHERE id={}".format(table_name, html_data['brand'], id), 3)
            if html_data.get('website'): sf.execute_query(conn, "UPDATE {} SET website = '{}' WHERE id={}".format(table_name, html_data['website'], id), 3)
            if html_data.get('tel'): sf.execute_query(conn, "UPDATE {} SET tel = '{}' WHERE id={}".format(table_name, html_data['tel'], id), 3)
            if html_data.get('compType'): sf.execute_query(conn, "UPDATE {} SET compType = '{}' WHERE id={}".format(table_name, html_data['compType'], id), 3)
            if html_data.get('descr'): sf.execute_query(conn, "UPDATE {} SET descr = '{}' WHERE id={}".format(table_name, html_data['descr'], id), 3)
            if html_data.get('bill'): sf.execute_query(conn, "UPDATE {} SET bill = '{}' WHERE id={}".format(table_name, html_data['bill'], id), 3)
            if html_data.get('stars'): sf.execute_query(conn, "UPDATE {} SET stars = '{}' WHERE id={}".format(table_name, html_data['stars'], id), 3)
            if html_data.get('hasRest'): sf.execute_query(conn, "UPDATE {} SET hasRest = '{}' WHERE id={}".format(table_name, html_data['hasRest'], id), 3)
            conn.commit()

        sf.execute_query(conn, "UPDATE {} SET isChecked = 1 WHERE id={}".format(table_name, id), 3)
        conn.commit()
        time.sleep(0.5)


compName = "Vlad_desctop"
driverPath = ""
dbPath = "//METSYS/analysts/Marketing/DataBase/gisDataMarketing.db"
if compName == "Vlad_desctop":
    driverPath = "C:/Program Files (x86)/Google/Chrome/Application/chromedriver.exe"
elif compName == "Vlad_laptop":
    driverPath = "C:/Users/vkovalenko/AppData/Local/Google/Chrome/Application/chromedriver.exe"
elif compName == "Vlad_laptop_home":
    driverPath = "C:/my_folder/browserDrivers/chromedriver.exe"
    dbPath = "C:/my_folder/scripts/2gis/gisDataMarketing.db"

seek_industries_4(dbPath, driverPath)

# read_addr_cards(dbPath, 'output')

# get_geo(dbPath, "barbers")




