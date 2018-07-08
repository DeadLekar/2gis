from selenium import webdriver
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

def get_next_addr(driver, addr_id):
    # return item number addr_id
    possible_addr_links = driver.find_elements_by_class_name("_type_building")
    if len(possible_addr_links) >= addr_id +1:
        return possible_addr_links[addr_id], len(possible_addr_links)
    else:
        return None, 0

def start_driver(link, seek_form_class_name, btn_class_name):
    driver = webdriver.Chrome(driverPath)
    driver.get(link)
    driver.maximize_window()
    seek_form = driver.find_element_by_class_name(seek_form_class_name)
    btn = driver.find_element_by_class_name(btn_class_name)
    return driver, seek_form, btn

def seek_addresses(dbPath, driverPath):
    #checks companies in address list
    companies = []
    conn = lite.connect(dbPath)
    c = conn.cursor()
    addr_row = c.execute("SELECT addr,id FROM addresses WHERE isChecked = 0").fetchall()
    addresses = [[addr[1], addr[0]] for addr in addr_row]
    driver, seek_form, btn = start_driver("https://2gis.ru/moscow", "suggest__input", "searchBar__submit")
    cnt_loads = 0 # number of downloadings, using for reload driver every 500 times to avoid the memory overflow
    for addr in addresses:
        if addr[0] == 42:
            a = 1
        cnt_loads += 1
        if cnt_loads % 500 == 0:
            driver.close()
            driver, seek_form, btn = start_driver("https://2gis.ru/moscow", "suggest__input", "searchBar__submit")
        seek_form.clear()
        seek_form.send_keys(addr[1])
        btn.click()
        time.sleep(3)
        # check if there are several possible addresses
        i = 0
        next_possible_addr, addr_cnt = get_next_addr(driver, i)
        if addr_cnt > 0:
            last_request_word = addr[1].split(" ")[-1]
            while next_possible_addr:
                flg_right_addr = False
                # compare last digits from the request and the result
                current_addr = next_possible_addr.text.split("\n")[0]
                if sf.is_digit(last_request_word):
                    if current_addr.find(last_request_word) == len(current_addr) - len(last_request_word):
                        flg_right_addr = True # last digits in current address and request are equal
                else:
                    flg_right_addr = True
                if flg_right_addr:
                    next_possible_addr.click()
                    time.sleep(2)
                    companies = read_address(driver)
                    if companies:
                        for comp in companies:
                            sf.execute_query(conn,"INSERT INTO output_addr (addr, company, industry, link) VALUES ('{}','{}','{}')".format(addr[1], comp[0], comp[1], comp[2]))
                        close_btn_arr = driver.find_elements_by_class_name("_close")
                        for close_btn in close_btn_arr:
                            if close_btn.location['x'] > 0:
                                close_btn.click()
                                break
                    break
                i += 1
                time.sleep(2)
                next_possible_addr, addr_cnt = get_next_addr(driver, i)
        else: #the only address: get companies
            companies = read_address(driver)
            if companies:
                for comp in companies:
                    sf.execute_query(conn, "INSERT INTO output_addr (addr, company, industry) VALUES ('{}','{}','{}')".format(addr[1], comp[0], comp[1]))
        sf.execute_query(conn, "UPDATE addresses SET isChecked = 1 WHERE id = {}".format(addr[0]))
    driver.close()

def click_rubric(driver, item_name):
    try:
        html_ind_list = driver.find_elements_by_class_name("rubricsList__listItem")  # get items from web page
        for html_ind_item in html_ind_list:
            if item_name in html_ind_item.text:
                html_ind_item.location_once_scrolled_into_view
                html_ind_item.click()
                time.sleep(2)
                return driver, True
    except: pass
    return driver, False

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

def get_subcategory(driver, sub_name):
    # clicks to all type button, click the sub_name subcategory from the list
    btn_all_types_list = driver.find_elements_by_class_name("_type_all")
    for btn in btn_all_types_list:
        if btn.location['x'] > 0:
            btn.click()
            time.sleep(2)
    # go to the horeca section
    time.sleep(2)
    driver, flg_click = click_rubric(driver, sub_name)
    return driver, flg_click

def seek_industries(dbPath, driverPath):
    # seeks for companies in all cities; fills db table
    # load objects to seek

    categories = {}
    conn = lite.connect(dbPath)
    c = conn.cursor()
    c.execute("SELECT id, name FROM searches WHERE isChecked=0")
    for obj_row in c.fetchall():
        categories[obj_row[0]] = obj_row[1]

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
            # click to all-types button
            flg_reload_categories = False
            btn_all_types_list = driver.find_elements_by_class_name("_type_all")
            for btn in btn_all_types_list:
                if btn.location['x'] > 0:
                    btn.click()
                    time.sleep(2)

            # go to the horeca section
            driver, flg_click = click_rubric(driver, 'Досуг')
            if flg_click:
                # check if the category is not ckecked yet
                flg_checked = None
                for cat in categories:  # go through horeca subsections from database
                    cat_name = categories[cat]
                    flg_checked = c.execute("SELECT id FROM checkedData WHERE obj='{}' AND city='{}'".format(cat_name, cr_city)).fetchone()
                    if not flg_checked: break
                if flg_checked: break # all categories are checked in current city
                sub_frame = driver.find_element_by_css_selector("div.rubricsList._subRubrics")
                sub_frame_iterm, flg_click = click_rubric(sub_frame, categories[cat])
                if flg_click:
                    # isCheckedReq = c.execute("SELECT id FROM checkedData WHERE city = '" + cr_city + "' AND obj = '" + categories[cat] + "'").fetchall()
                    #if len(isCheckedReq) == 0:
                    while 1: # go through companies in curren category
                        cards = driver.find_elements_by_class_name("mediaResults__resultsItem")
                        if cards:
                            for card in cards: # collect data for each company on the page
                                # driver.execute_script("window.scrollBy(0," + str(card.location['y'] - 200) + ")")
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                card.click()
                                data_dict = {}
                                data_dict["catName"] = [cat_name, True]
                                data_dict["cityName"] = [cr_city, True]
                                time.sleep(3)
                                # read and save data
                                # txt = driver.execute_script("return document.body.innerHTML")
                                # soup = BeautifulSoup(''.join(txt), 'html.parser')
                                try:
                                    brand_name = sf.clear_string(driver.find_element_by_class_name("mediaCardHeader__cardHeaderName").text, sf.rus_letters+sf.lat_letters+sf.digits+sf.puncts+" ")
                                    data_dict["brandName"] = [brand_name, True]
                                except: pass
                                try:
                                    addr = driver.find_element_by_class_name("mediaCardHeader__cardAddressName").text
                                    data_dict["addr"] = [addr, True]
                                except: pass
                                try:
                                    web_site = driver.find_element_by_class_name("mediaContacts__website").text
                                    data_dict["webSite"] = [web_site, True]
                                except: pass
                                try:
                                    quisine_list = driver.find_elements_by_class_name("mediaAttributes__groupList")
                                    for item in quisine_list:
                                        if "кухня" in item.text:
                                            quisine = sf.clear_string(item.text, sf.rus_letters+sf.lat_letters+sf.digits+sf.puncts+" ")
                                            data_dict["quisine"] = [quisine, True]
                                            break
                                except: pass
                                try:
                                    subs_num = driver.find_element_by_class_name("mediaContacts__filials").text
                                    data_dict["subsNum"] = [subs_num, False]
                                except: pass
                                try:
                                    mean_check = driver.find_element_by_class_name("mediaAttributes__groupListItemSum").text.replace("руб", "")
                                    data_dict["meanCheck"] = [mean_check, False]
                                except: pass
                                cmd = sf.build_insert_expression(data_dict, "output_categories")
                                # sf.execute_query(conn, cmd, 3) !!!!!!!!!!!!!!!!!!!!!!!

                                try:
                                    back_links = driver.find_elements_by_css_selector("a.link.frame__controlsButton._back._undashed")
                                    for link in back_links:
                                        if link.location['x'] > 0 and link.location['y'] > 0:
                                            link.click()
                                            time.sleep(2)
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
                            back_link.click()
                            time.sleep(2)
                            flg_reload_categories = True
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
                    sf.execute_query(conn, "INSERT INTO checkedData (obj, city) VALUES ('{}', '{}')".format(categories[cat], cr_city))

        driver.close()

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

def seek_industries_3(dbPath, driverPath):
    # seeks for companies in all cities; fills db table with links

    # load objects to seek
    cnt_loads = 0
    categories = {}
    conn = lite.connect(dbPath)
    c = conn.cursor()
    c.execute("SELECT id, name FROM searches WHERE isChecked=0")
    for obj_row in c.fetchall(): categories[obj_row[0]] = obj_row[1]

    cr_city = ""
    start_link = "https://2gis.ru/countries/global/moscow?queryState=center%2F27.224121%2C55.751849%2Fzoom%2F5" # the link to enter a new city
    driver = webdriver.Chrome(driverPath)
    driver.get(start_link)
    driver.maximize_window()
    while 1: # go through cities
        if cnt_loads > 500:
            cnt_loads = 0
            driver = webdriver.Chrome(driverPath)
            driver.get(start_link)
            driver.maximize_window()
        driver.get(start_link)
        driver, cr_city = get_next_city(driver, cr_city)
        if cr_city == "": break
        time.sleep(2)

        while 1: # go through subcategories
            # get next unchecked category
            cat_name = get_next_category(categories, cr_city, conn)
            if not cat_name: break # all categories are checked in current city
            # click to all-types button
            driver, flg_click = get_subcategory(driver, "Досуг")
            if flg_click:
                sub_frame = driver.find_element_by_css_selector("div.rubricsList._subRubrics")
                sub_frame_iterm, flg_click = click_rubric(sub_frame, cat_name)
                if flg_click:
                    while 1: # go through companies in current category
                        txt = driver.execute_script("return document.body.innerHTML")
                        soup = BeautifulSoup(''.join(txt), 'html.parser')
                        cards = soup.findAll("div", "mediaResults__resultsItem")

                        if cards: # large list
                            for card in cards: # collect data for each company on the page
                                href = card.contents[0].contents[0].attrs.get('href')
                                if href:
                                    sf.execute_query(conn, "INSERT INTO output_categories (catName, cityName, link) VALUES ('{}','{}','{}')".format(cat_name,cr_city,href))
                        else: # mini list
                            cards_list = soup.find_all("div", "searchResults__list")
                            if cards_list:
                                for card in cards_list[0].contents:
                                    link_item = card.find_all("a", "miniCard__headerTitleLink")
                                    if link_item:
                                        href = link_item[0].attrs.get('href')
                                        if href:
                                            sf.execute_query(conn,"INSERT INTO output_categories (catName, cityName, link) VALUES ('{}','{}','{}')".format(cat_name, cr_city, href))

                            else: # single card
                                data_dict, back_link = read_single_card(driver)
                                if len(data_dict) == 0:
                                    print("unable to read data: city = {}, category = {}, link = {}".format(cr_city, cat_name, driver.current_url))
                                else:
                                    data_dict["catName"] = [cat_name, True]
                                    data_dict["cityName"] = [cr_city, True]
                                    cmd = sf.build_insert_expression(data_dict, "output_categories")
                                    sf.execute_query(conn, cmd, 3)
                                back_link.click()
                                time.sleep(2)
                                break

                        try:
                            next_link_disabled = driver.find_element_by_css_selector("div.pagination__arrow._right._disabled")
                            # if here, there's no further pages in category: closing the frame
                            click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
                            click_element(driver, "a.link.frame__controlsButton._close._undashed", False)
                            time.sleep(2)
                            break # a disabled next arrow found - the end of the list
                        except:
                            next_link = driver.find_element_by_css_selector("#module-1-13-1-1-2-2 > div.pagination__arrow._right")
                            next_link.location_once_scrolled_into_view
                            next_link.click()
                            time.sleep(2)
                            cnt_loads += 1
                sf.execute_query(conn, "INSERT INTO checkedData (obj, city) VALUES ('{}', '{}')".format(cat_name, cr_city))
            else:
                click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
                click_element(driver, "a.link.frame__controlsButton._close._undashed", False)
                time.sleep(2)
                break


def seek_industries_4(dbPath, driverPath):
    # seeks for companies in all cities; fills db table with links

    # load objects to seek
    cnt_loads = 0
    conn = lite.connect(dbPath)
    c = conn.cursor()

    categories = {}
    c.execute("SELECT id, name FROM searches WHERE isChecked=0")
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
            is_checked = c.execute("SELECT id FROM checkedData WHERE obj='{}' AND city='{}'".format(cr_cat,cr_city))
            if not is_checked.fetchone():
                cr_link = link_template.format(cr_city,cr_cat)
                driver.get(cr_link)
                driver.maximize_window()
                while 1:  # go through companies in current category
                    txt = driver.execute_script("return document.body.innerHTML")
                    soup = BeautifulSoup(''.join(txt), 'html.parser')
                    cards_block = soup.findAll("div", "miniCard__headerTitle")
                    if cards_block:  # large list
                        for card in cards_block[0].contents:  # collect data for each company on the page
                            if hasattr(card.contents[0].contents[1].contents[1].contents[0],'attrs'):
                                href = card.contents[0].contents[1].contents[1].contents[0].attrs.get('href')
                            else:
                                href = card.contents[0].contents[0].contents[1].contents[0].attrs.get('href')
                            if href:
                                sf.execute_query(conn, "INSERT INTO output_categories (catName, cityName, link) VALUES ('{}','{}','{}')".format(cr_cat, cr_city, href))
                    else:  # mini list
                        cards_list = soup.find_all("div", "searchResults__list")
                        if cards_list:
                            for card in cards_list[0].contents:
                                link_item = card.find_all("a", "miniCard__headerTitleLink")
                                if link_item:
                                    href = link_item[0].attrs.get('href')
                                    if href:
                                        sf.execute_query(conn,
                                                         "INSERT INTO output_categories (catName, cityName, link) VALUES ('{}','{}','{}')".format(cr_cat, cr_city, href))

                        else:  # single card
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

                    try:
                        next_link_disabled = driver.find_element_by_css_selector("div.pagination__arrow._right._disabled")
                        # if here, there's no further pages in category: closing the frame
                        click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
                        click_element(driver, "a.link.frame__controlsButton._close._undashed", False)
                        time.sleep(2)
                        break  # a disabled next arrow found - the end of the list
                    except:
                        next_link = driver.find_element_by_css_selector("div.pagination__arrow._right")
                        next_link.location_once_scrolled_into_view
                        next_link.click()
                        time.sleep(2)
                        cnt_loads += 1
                sf.execute_query(conn,"INSERT INTO checkedData (obj, city) VALUES ('{}', '{}')".format(cr_cat, cr_city))
                conn.commit()
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

def seek_industries_moscow(dbPath, driverPath, table_name):
    # seeks for companies in all cities; fills db table
    # load objects to seek

    conn = lite.connect(dbPath)
    cnt_loads = 0
    cr_city = "Москва"

    driver = webdriver.Chrome(driverPath)
    time.sleep(2)
    while 1: # go through links from database
        next_link_data = get_next_link(conn)
        if next_link_data:
            next_link = next_link_data['link']
            cat_name = next_link_data['catName']
            link_id = next_link_data['id']
            sf.execute_query(conn, "UPDATE links SET isChecked = 1 WHERE id={}".format(link_id))
            driver.get(next_link)
            driver.maximize_window()
        else: break # all links are checked, finish

        if cnt_loads > 500:
            cr_url = driver.current_url
            driver.close()
            cnt_loads = 0
            driver = webdriver.Chrome(driverPath)
            driver.get(cr_url)
            driver.maximize_window()

        while 1: # go through companies saving href
            txt = driver.execute_script("return document.body.innerHTML")
            soup = BeautifulSoup(''.join(txt), 'html.parser')
            cards = soup.findAll("div", "mediaResults__resultsItem")
            if cards:  # large list
                for card in cards:  # collect data for each company on the page
                    href = card.contents[0].contents[0].attrs.get('href')
                    if href:
                        sf.execute_query(conn, "INSERT INTO {} (catName, cityName, link) VALUES ('{}','{}','{}')".format(table_name, cat_name, cr_city, href))
            else:  # mini list or single card
                cards_list = soup.find_all("div", "searchResults__list")
                if cards_list: # mini list
                    for card in cards_list[0].contents:
                        link_item = card.find_all("a", "miniCard__headerTitleLink")
                        if link_item:
                            href = link_item[0].attrs.get('href')
                            if href:
                                sf.execute_query(conn,"INSERT INTO {} (catName, cityName, link) VALUES ('{}','{}','{}')".format(table_name, cat_name, cr_city, href))

                else:  # single card
                    data_dict, back_link = read_single_card(driver)
                    if len(data_dict) == 0:
                        print("unable to read data: city = {}, category = {}, link = {}".format(cr_city, cat_name, driver.current_url))
                    else:
                        data_dict["catName"] = [cat_name, True]
                        data_dict["cityName"] = [cr_city, True]
                        cmd = sf.build_insert_expression(data_dict, "output_categories_rbc")
                        sf.execute_query(conn, cmd, 3)
                    back_link.click()
                    time.sleep(2)
                    break

            try:
                next_link_disabled = driver.find_element_by_css_selector("div.pagination__arrow._right._disabled")
                # if here, there's no further pages in category: closing the frame
                click_element(driver, "a.link.searchBar__mediaButton.searchBar__mediaClose._undashed", False)
                click_element(driver, "a.link.frame__controlsButton._close._undashed", False)
                time.sleep(2)
                sf.execute_query(conn, "UPDATE links SET isChecked = 2 WHERE id={}".format(link_id))
                break  # a disabled next arrow found - the end of the list
            except:
                next_link_data = driver.find_element_by_css_selector("#module-1-13-1-1-2-2 > div.pagination__arrow._right")
                next_link_data.location_once_scrolled_into_view
                next_link_data.click()
                time.sleep(2)
                cnt_loads += 1

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
        val = name_el[0].text
        result['brandName'] = sf.clear_string(val, sf.rus_letters + sf.lat_letters + sf.digits + sf.puncts + ' ')

    addr_el = soup.find_all("div", "mediaCardHeader__cardAddressName")
    if not addr_el:
        addr_el = soup.find_all("a", "card__addressLink")

    if addr_el:
        result['addr'] = sf.clear_string(addr_el[0].text, sf.rus_letters + sf.lat_letters + sf.digits + sf.puncts + ' ')
        addr_arr = result['addr'].split(',')
        if len(addr_arr) > 1:
            result['cityName'] = addr_arr[1]
        else:
            result['cityName'] = result['addr']

    quisine_el_list = soup.find_all("ul", "mediaAttributes__groupList")
    if quisine_el_list:
        txt = ""
        for el in quisine_el_list[0].contents:
            txt += el.text
        if txt:
            result['quisine'] = txt

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
        website_el = soup.find_all("a", "contact__linkText")
        if website_el:
            if hasattr(website_el[0], 'attrs'):
                result['website'] = website_el[0].get('title')
    else:
        result['website'] = website_el[0].text

    # parking parameters
    parking_params = soup.find_all('div', 'cardParking')
    result['isFree'] = -1
    result['isUnderground'] = -1
    result['isFree'] = -1
    if parking_params:
        for pp in parking_params[0].contents:
            if 'для клиентов' in pp.text.lower() or 'бщедоступн' in pp.text.lower():
                if 'для клиентов' in pp.text.lower(): result['isFree'] = 0
                if 'бщедоступн' in pp.text.lower(): result['isFree'] = 1
            if 'бщедоступн' in pp.text.lower(): result['isForClients'] = 0
            if 'мест' in pp.text: result['placesNum'] = pp.text.split(' ')[0].strip()
            if 'платн' in pp.text.lower():
                if pp.text.find('Платн') == -1:
                    if pp.text.find('платн') > 0:
                        result['isFree'] = 1
                else:
                    # 'Платная — 250 ₽/час'
                    result['isFree'] = 0
                    if '—' in pp.text and '₽' in pp.text:
                        result['fee'] = pp.text.split('—')[1].split('₽')[0].strip()
                    else: result['fee'] = pp.text
            if 'земн' in pp.text.lower():
                if 'наземн' in pp.text.lower():
                    result['isUnderground'] = 1
                elif 'подземн' in pp.text.lower():
                    result['isUnderground'] = 0
            if 'ногоуровн' in pp.text.lower():
                result['isUnderground'] = 2

    return result

def read_addr_card(dbPath, table_name):
    conn = lite.connect(dbPath)
    c = conn.cursor()
    rows = c.execute("SELECT link, id FROM {} WHERE link is not Null and isChecked = 0".format(table_name)).fetchall()
    LINK_START = "https://2gis.ru"
    cnt = 0
    for row in rows:
        cnt += 1
        if cnt % 100 == 0: print(cnt)
        link = LINK_START + row[0]
        id = row[1]
        html_data = read_link(link)
        if len(html_data) > 0:
            if html_data.get('addr'): sf.execute_query(conn, "UPDATE {} SET addr = '{}' WHERE id={}".format(table_name, html_data['addr'], id), 3)
            if html_data.get('brandName'): sf.execute_query(conn,"UPDATE {} SET brandName = '{}' WHERE id={}".format(table_name, html_data['brandName'], id), 3)
            if html_data.get('website'): sf.execute_query(conn, "UPDATE {} SET website = '{}' WHERE id={}".format(table_name, html_data['website'], id), 3)
            if html_data.get('isUnderground'): sf.execute_query(conn, "UPDATE {} SET isUnderground = '{}' WHERE id={}".format(table_name,html_data[ 'isUnderground'], id), 3)
            if html_data.get('isFree'): sf.execute_query(conn, "UPDATE {} SET isFree = '{}' WHERE id={}".format(table_name, html_data['isFree'], id), 3)
            if html_data.get('placesNum'): sf.execute_query(conn, "UPDATE {} SET placesNum = '{}' WHERE id={}".format(table_name, html_data['placesNum'], id), 3)
            if html_data.get('fee'): sf.execute_query(conn, "UPDATE {} SET fee = '{}' WHERE id={}".format(table_name, html_data['fee'], id), 3)
        sf.execute_query(conn, "UPDATE {} SET isChecked = 1 WHERE id={}".format(table_name, id), 3)


        time.sleep(0.5)

def read_2gis_card_category(dbPath, table_name):
    conn = lite.connect(dbPath)
    c = conn.cursor()
    rows = c.execute("SELECT link, id FROM {} WHERE link is not Null AND gisCatMain is Null".format(table_name)).fetchall()
    LINK_START = "https://2gis.ru"
    for row in rows:
        link = LINK_START + row[0]

def seek_parking(dbPath, driverPath, table_name):
    # seeks for companies in all cities; fills db table
    # load objects to seek

    def read_url(cr_url):
        driver.get(cr_url)
        time.sleep(1)
        # r = requests.get(cr_url)
        # soup = BeautifulSoup(r.text, 'html.parser')
        txt = driver.execute_script("return document.body.innerHTML")
        soup = BeautifulSoup(''.join(txt), 'html.parser')
        cards = soup.findAll("a", "miniCard__headerTitleLink")
        if cards:  # large list
            for card in cards:  # collect data for each company on the page
                href = card.attrs.get('href')
                if href:
                    sf.execute_query(conn, "INSERT INTO {} (catName, cityName, link) VALUES ('{}','{}','{}')".format(table_name, cat_name, cr_city, href))


    conn = lite.connect(dbPath)
    cr_city = "Москва"
    cat_name = 'Парковки'

    driver = webdriver.Chrome(driverPath)
    cr_url_1 = 'https://2gis.ru/moscow/search/%D0%BF%D0%B0%D1%80%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0%20/tab/geo?queryState=center%2F37.644653%2C55.827709%2Fzoom%2F12'
    cr_url_start = 'https://2gis.ru/moscow/search/%D0%BF%D0%B0%D1%80%D0%BA%D0%BE%D0%B2%D0%BA%D0%B0%20/page/'
    cr_url_end = '/tab/geo?queryState=center%2F37.644653%2C55.827709%2Fzoom%2F12'

    read_url(cr_url_1)
    for i in range (2, 168):
        read_url(cr_url_start + str(i) + cr_url_end)

def test():
    driver = webdriver.Chrome(driverPath)
    driver.get(
        'https://2gis.ru/krasnoyarsk/search/%D0%9C%D0%B5%D0%B1%D0%B5%D0%BB%D1%8C%20%D0%B4%D0%BB%D1%8F%20%D0%BA%D0%B0%D1%84%D0%B5%2C%20%D1%80%D0%B5%D1%81%D1%82%D0%BE%D1%80%D0%B0%D0%BD%D0%BE%D0%B2/page/4/firm/70000001029069899/tab/firms?queryState=center%2F92.854493%2C56.03254%2Fzoom%2F15')
    css_arr = ["a.link.frame__controlsButton._back._undashed", "a.link.frame__controlsButton._close._undashed"]
    for css in css_arr:
        if click_closing_button(driver, css): break
    else:
        print('Did not find closing button for:' + driver.current_url)

compName = "Vlad_desctop"
driverPath = ""
if compName == "Vlad_desctop":
    driverPath = "C:/Program Files (x86)/Google/Chrome/Application/chromedriver.exe"
elif compName == "Vlad_laptop":
    driverPath = "C:/Users/vkovalenko/AppData/Local/Google/Chrome/Application/chromedriver.exe"
elif compName == "Vlad_desctop_411":
    driverPath = "C:/Users/vkovalenko/AppData/Local/Google/Chrome/chromedriver.exe"
dbPath = "//METSYS/analysts/Marketing/DataBase/gisDataMarketing.db"

# read_addr_card(dbPath, 'output_categories_rbc')
# seek_addresses(dbPath, driverPath)
seek_industries_4(dbPath, driverPath)
# seek_industries_moscow(dbPath, driverPath, 'output_categories_rbc')
# seek_parking (dbPath, driverPath, 'output_categories_rbc')
# get_geo(dbPath, "barbers")
# test()
# seek_industries_search_bar(dbPath, driverPath)





