from enum import Enum
import time
import math

rus_letters = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
lat_letters = "abcdefghijklmnopqrstuvwxyz"
digits = "1234567890"
puncts = ".,-:;?!()[]{}"

class html_level:
    level_type = "" #class, tag...
    level_name = ""
    level_id = "" #number in contents list

class html_data:
    element = None
    text = ""
    parent = None
    tag_name = ""
    class_name = ""

    def __init__(self, _element, _text, _parent):
        self.element = _element
        if isinstance(_text, list):
            _text = ' '.join(_text)
        self.text = _text
        self.parent = _parent

    def clone(self):
        my_clone = html_data(self.element, self.text, self.parent)
        return my_clone


def is_digit(val):
    if type(val) == str:
        val = val.replace(',', '.')
    try:
        return not math.isnan(float(val))
    except:
        return False

def get_closest_attribute(el, attr_name):
    if attr_name == "class":
        attr_name = "attrs"
    cur_parent = el.element

    while 1:
        if hasattr(cur_parent, attr_name):
            if cur_parent.__getattribute__(attr_name):
                if len(cur_parent.__getattribute__(attr_name)) > 0:
                    if attr_name == "attrs":
                        if cur_parent.attrs.get('class'):
                            return cur_parent.attrs.get('class')[0]
                        else:
                            flg_get_next_parent = True
                    else:
                        return cur_parent.__getattribute__(attr_name)
                else:
                    flg_get_next_parent = True
            else:
                flg_get_next_parent = True
        else:
            flg_get_next_parent = True

        if flg_get_next_parent:
            cur_parent = cur_parent.parent

def fit_to_list_v2(el, brothers, regime):
    # returns 1 if el fits to brothers list (by tag name or class name)
    # regime is brother_regime
    cr_tag_name = ""
    cr_class_name = ""
    if (regime.name == 'ALL' or regime.name == 'TAG_NAME') and hasattr(el, "name"):
        cr_tag_name = el.name
    if (regime.name == 'ALL' or regime.name == 'CLASS_NAME') and hasattr(el, "attrs"):
        cr_class_name = el.attrs.get("class")

    if cr_tag_name or cr_class_name:
        brother = brothers[0]
        if hasattr(brother, "attrs") and cr_class_name != "":
            if brother.attrs.get("class") == cr_class_name:
                return True
        else:
            if hasattr(brother, "name") and cr_tag_name != "":
                if brother.name == cr_tag_name:
                    return True

def fit_to_list(el, brothers):
    # returns 1 if el fits to brothers list (by tag name or class name)
    cr_tag_name = ""
    cr_class_name = ""
    if hasattr(el, "name"):
        cr_tag_name = el.name
    if hasattr(el, "attrs"):
        cr_class_name = el.attrs.get("class")

    if cr_tag_name or cr_class_name:
        brother = brothers[0]
        if hasattr(brother, "attrs") and cr_class_name != "":
            if brother.attrs.get("class") == cr_class_name:
                return True
        else:
            if hasattr(brother, "name") and cr_tag_name != "":
                if brother.name == cr_tag_name:
                    return True

def is_element_ok(el):
    if hasattr(el, 'text'):
        if el.text != None:
            if len(el.text) > 0:
                return True

def get_html_brothers_v2(el, regime):
    # goes through the contents and get all relatives on the same level with the same class names or tag names
    cr_brothers = []
    total_brothers = []
    elements_to_check = []
    elements_to_check.append(el)
    while len(elements_to_check) > 0:
        new_el = elements_to_check.pop(0)
        if is_element_ok(new_el):
            if hasattr(new_el, "contents"):
                for cont in new_el.contents:
                    if is_element_ok(cont):
                        elements_to_check.append(cont)
                        flg_found = False
                        for brothers in cr_brothers:
                            if fit_to_list_v2(cont, brothers, regime):
                                brothers.append(cont)
                                flg_found = True
                        if not flg_found:
                            new_list = []
                            new_list.append(cont)
                            cr_brothers.append(new_list[0:])
                for brothers in cr_brothers:
                    if len(brothers) > 1:
                        total_brothers.append(brothers)
                cr_brothers = []
        return total_brothers


def get_html_brothers(el):
    # goes through the contents and get all relatives on the same level with the same class names or tag names
    cr_brothers = []
    total_brothers = []
    elements_to_check = []
    elements_to_check.append(el)
    while len(elements_to_check) > 0:
        new_el = elements_to_check.pop(0)
        if hasattr(new_el,"contents"):
            for cont in new_el.contents:
                elements_to_check.append(cont)
                flg_found = False
                for brothers in cr_brothers:
                    if fit_to_list(cont, brothers):
                        brothers.append(cont)
                        flg_found = True
                if not flg_found:
                    new_list = []
                    new_list.append(cont)
                    cr_brothers.append(new_list[0:])
            for brothers in cr_brothers:
                if len(brothers) > 1:
                    total_brothers.append(brothers)
            cr_brothers = []
    return total_brothers

def get_contents_tree(el):
    texts = [] #of html_data
    elements_to_check = []
    el_obj = html_data(el, "", el.parent)
    elements_to_check.append(el_obj)
    while 1:
        for new_el in elements_to_check:
            element_to_remove = new_el
            if hasattr(new_el.element, "contents"):
                if len(new_el.element.contents) > 0:
                    for cont in new_el.element.contents:
                        elements_to_check.append(html_data(cont, "", new_el.element))
                    if hasattr(new_el.element, "attrs"):
                        if new_el.element.attrs.get("href"):
                            new_text = html_data(new_el.element, new_el.element.attrs["href"], new_el.parent)
                            if len(clear_string(new_text.text, rus_letters + lat_letters + digits)) > 0:
                                if new_el.element.name and new_el.element.name != "script":
                                    new_text.class_name = get_closest_attribute(new_text, "class")
                                    new_text.tag_name = get_closest_attribute(new_text, "name")
                                    texts.append(new_text)
                elif hasattr(new_el.element, "attrs"):  # get old price from kupivip
                    for attr in new_el.element.attrs:
                        if new_el.element.name and new_el.element.name != "script":
                            new_text = html_data(new_el.element, new_el.element.attrs[attr], new_el.parent)
                            new_text.class_name = get_closest_attribute(new_text, "class")
                            new_text.tag_name = get_closest_attribute(new_text, "name")
                            texts.append(new_text)
            elif "String" in str(type(new_el.element)):
                new_el_str = str(new_el.element)
                new_el_str = new_el_str.replace("\n","")
                new_el_str = new_el_str.strip()
                if len(new_el_str) > 0:
                    if len(clear_string(new_el_str, rus_letters + lat_letters + digits)) > 0:
                        if new_el.element.name and new_el.element.name != "script":
                            new_text = html_data(new_el.element, new_el_str, new_el.parent)
                            new_text.class_name = get_closest_attribute(new_text, "class")
                            new_text.tag_name = get_closest_attribute(new_text, "name")
                            texts.append(new_text)

            elements_to_check.remove(element_to_remove)
        if len(elements_to_check) == 0:
            break
    return texts


def find_html_element(html_el, field_name, field_val):
    #returns element if its field_name = field_val
    all_elements = []
    for el in html_el.contents:
        if hasattr(el, "contents"):
            all_elements.append(el)
    elements_to_remove = []
    while(1):
        for el in all_elements:
            for cont in el.contents:
                if hasattr(cont, "attrs"):
                    for key in cont.attrs:
                        if key == field_name:
                            if cont.attrs[field_name][0] == field_val:
                                return cont
                            elif hasattr(cont, "contents"):
                                all_elements.append(cont)
            elements_to_remove.append(el)
        for el in elements_to_remove:
            all_elements.remove(el)
        elements_to_remove.clear()
        if not all_elements:
            break

def clear_string(str_to_clear, legitimate_symbols):
    i = 0
    new_str = ""
    while i <= len(str_to_clear)-1:
        cr_symb = str(str_to_clear[i].lower())
        if legitimate_symbols.find(cr_symb) != -1:
            #if puncts.find(cr_symb) == -1 or i < len(str_to_clear)-1:
                new_str += str_to_clear[i]
        i += 1
    return new_str.strip()

def clear_link(link_to_clear, prefix):
    # cuts the start of the link_to_clear until meets 'h' or 'w'
    h_start = link_to_clear.find("h")
    w_start = link_to_clear.find("w")
    if h_start == -1:
        if w_start == -1:
            return ""
        else:
            start = w_start
    else:
        if w_start == -1:
            start = h_start
        else:
            start = min(h_start,w_start)
    res = link_to_clear[start:]
    # add http(s) to the beginning
    http_prefix = prefix.split(":")[0]
    if http_prefix[0] == 'h':
        if res.find("http") != 0:
            res = http_prefix + "://" + res
    return res

def execute_query(conn, query, time_limit=0):
    c = conn.cursor()
    cr_time = time.clock()
    while 1:
        try:
            c.execute(query)
            conn.commit()
            return c.lastrowid
        except:
            if (time_limit > 0 and time.clock() - cr_time > time_limit) or time_limit == 0:
                print("unable to execute: " + query)
                return -1

def build_insert_expression(data_dict, table_to_insert):
    """
    creates INSERT INTO command
    :param data_dict: {fieldName: [fieldValue, flgStringType]}
    :param table_to_insert:
    :return: command str
    """

    command_str_left = "INSERT INTO " + table_to_insert + " ("
    command_str_right = " VALUES ("

    for field_name in data_dict:
            field_value = data_dict[field_name][0]
            flg_string_type = data_dict[field_name][1]
            if command_str_left[-1] != "(":
                command_str_left += ","
                command_str_right += ","
            if flg_string_type: command_str_right += "'"
            command_str_left += field_name
            command_str_right +=  str(field_value)
            if flg_string_type: command_str_right += "'"
    command_str = command_str_left + ")" + command_str_right + ")"

    return command_str