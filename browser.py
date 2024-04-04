'''
Simple web browser created for CS4560 at the University of Utah. Created
by following instructions in https://browser.engineering.
- Landen Hughes
- Spring 2024
- Prof. Panchekha
'''

import socket
import ssl
import datetime
import tkinter
import tkinter.font
import os.path
import urllib.parse
import dukpy
CACHE = {}
WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100
HSTEP, VSTEP = 13, 18
IMAGE_REFERENCES = []
FONTS = {}
INPUT_WIDTH_PX = 200
RUNTIME_JS = open("runtime.js").read()
EVENT_DISPATCH_JS = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
    "font-family": "Times"
}
COOKIE_JAR = {}
def set_parameters(**params):
    global WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
    if "WIDTH" in params: WIDTH = params["WIDTH"]
    if "HEIGHT" in params: HEIGHT = params["HEIGHT"]
    if "HSTEP" in params: HSTEP = params["HSTEP"]
    if "VSTEP" in params: VSTEP = params["VSTEP"]
    if "SCROLL_STEP" in params: SCROLL_STEP = params["SCROLL_STEP"]

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white"
        )
        # self.window.title("Browser")
        self.canvas.pack(fill=tkinter.BOTH, expand=1)
        self.url = None
        self.tabs = []
        self.bookmarks = []
        self.active_tab = None
        self.scroll = 0
        self.chrome = Chrome(self)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        # self.window.bind("<Configure>", self.resize)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)
        self.window.bind("<BackSpace>", self.handle_backspace)
        self.window.bind("Button-2", self.handle_middle_click)
        bi_times = tkinter.font.Font(
            family="Times",
            size=16,
            weight="bold",
            slant="italic"
        )
        
    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)
        # for cmd in self.display_list:
        #     if cmd.top > self.scroll + HEIGHT: continue
        #     if cmd.bottom < self.scroll: continue
        #     cmd.execute(self.scroll, self.canvas)
        # for cmd in self.display_list:
        #     # print(w)
        #     if cmd.y > self.scroll + HEIGHT: continue
        #     if cmd.y + VSTEP < self.scroll: continue
            
        #     #used a try/except block to catch type errors when the word isn't a unicode character
        #     try:
        #         path = "openmoji/" + hex(ord(w)).upper().split("X", 1)[1] + ".png"
        #         # print("PATH:", path)
        #         if os.path.isfile(path):
        #             emoji = tkinter.PhotoImage(file=path)
        #             IMAGE_REFERENCES.append(emoji)
        #             self.canvas.create_image(x, y - self.scroll, image=emoji)
        #         else:
        #             self.canvas.create_text(x, y - self.scroll, text=w, font=f, anchor="nw")
        #     except:
        #         self.canvas.create_text(x, y - self.scroll, text=w, font=f, anchor="nw")
        # if self.display_list and self.display_list[-1][1] >  HEIGHT:
        #     self.canvas.create_rectangle(WIDTH - 8,
        #                          self.scroll / self.display_list[-1][1] * HEIGHT,
        #                          WIDTH,
        #                          (HEIGHT / self.display_list[-1][1]) * HEIGHT + (self.scroll / self.display_list[-1][1]) * HEIGHT,
        #                          width=0,
        #                          fill="blue")

    def scrolldown(self, e):
        self.active_tab.scrolldown()
        self.draw()

    def scrollup(self, e):
        self.active_tab.scrollup()
        self.draw()
        
    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
        else:
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()
        
    def handle_middle_click(self, e):
        if e.y < self.chrome.bottom:
            pass
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.middleClick(e.x, tab_y, self)
        self.draw()
        
    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        if self.chrome.keypress(e.char):
            self.draw()
        elif self.focus == "content":
            self.active_tab.keypress(e.char)
            self.draw()
        # self.chrome.keypress(e.char)
        # self.draw()
        
    def handle_enter(self, e):
        self.chrome.enter()
        self.draw()
        
    def handle_backspace(self, e):
        self.chrome.back()
        self.draw()

    # def resize(self, e):
    #     global WIDTH, HEIGHT
    #     WIDTH = e.width
    #     HEIGHT = e.height
    #     self.document.paint()
    #     self.draw()
        
    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom, self)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()
        
class Tab:
    def __init__(self, tab_height, browser):
        self.browser = browser
        self.tab_height = tab_height
        self.scroll = 0
        self.history = []
        self.focus = None
    def __repr__(self):
        return "Tab(history={})".format(self.history)
    
    def load(self, url, payload = None, method = None):
        self.url = url
        self.history.append(url)
        self.headers, body = url.request(top_level_url = self.url, payload = payload, method = method)
        self.allowed_origins = None
        if "content-security-policy" in self.headers:
            csp = self.headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())
        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        idList = []
        for node in tree_to_list(self.nodes, []):
            if isinstance(node, Element):
                if "id" in node.attributes:
                    if "-" in node.attributes["id"]:
                        node.attributes["id"] = node.attributes["id"].replace("-", "_")
                    idList.append(node)
        links = [node.attributes["href"] for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        self.js = JSContext(self, idList)
        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            _, body = script_url.request(top_level_url = url)
            try:
                self.js.run(body)
            except dukpy.JSRuntimeError as e:
                print("Script", script, "crashed", e)
        for link in links:
            link_url = url.resolve(link)
            if not self.allowed_request(link_url):
                print("Blocked style", link, "due to CSP")
                continue
            try:
                _, body = link_url.request(top_level_url = url, browser = self.browser)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        if url.fragment != None:
            self.scroll_to(url.fragment)
        self.render()
        
    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        if self.url.fragment != None:
            self.scroll_to(self.url.fragment)
        self.display_list = []
        paint_tree(self.document, self.display_list)
        
    def scroll_to(self, fragment):
        for obj in tree_to_list(self.document, []):
                if isinstance(obj.node, Element):
                    if fragment == obj.node.attributes.get("id"):
                        self.scroll = obj.y    
    
    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def click(self, x_val, y_val):
        self.focus = None
        x, y = x_val, y_val
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width \
            and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                if self.js.dispatch_event("click", elt): return
                if "#" == elt.attributes.get("href")[0]:
                    self.scroll_to(elt.attributes["href"][1:])
                    self.url.fragment = elt.attributes["href"][1:]
                else:
                    url = self.url.resolve(elt.attributes["href"])
                    return self.load(url)
            elif elt.tag == "input":
                if self.js.dispatch_event("click", elt): return
                elt.attributes["value"] = ""
                if self.focus:
                    self.focus.is_focused = False
                self.focus = elt
                elt.is_focused = True
                return self.render()
            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt): return
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent
            
    def submit_form(self, elt):
        if self.js.dispatch_event("submit", elt): return
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]
        method = (
            "GET"
            if elt.attributes.get("method") == None
            else elt.attributes["method"]
        )
        # print("INPUTS:", inputs)
        body = ""
        for input in inputs:
            name = input.attributes["name"]
            name = urllib.parse.quote(name)
            value = input.attributes.get("value", "")
            value = urllib.parse.quote(value)
            body += "&" + name + "=" + value
        body = body[1:]
        url = self.url.resolve(elt.attributes["action"])
        self.load(url, body, method)
        
    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.render()
            
    def middleClick(self, ex, ey, browser):
        x, y = ex, ey
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width
        and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                browser.new_tab(url)
                browser.active_tab = self
                return
            elt = elt.parent
            
    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)
            
    def scrolldown(self):
        max_y = max(
            self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        
    def scrollup(self):
        if self.scroll - SCROLL_STEP >= 0:
            self.scroll -= SCROLL_STEP
        else:
            self.scroll = 0
    
    def allowed_request(self, url):
        return self.allowed_origins == None or \
            url.origin() in self.allowed_origins

class JSContext:
    def __init__(self, tab, idList):
        self.tab = tab
        self.idList = idList
        self.node_to_handle = {}
        self.handle_to_node = {}
        self.interp = dukpy.JSInterpreter()
        self.interp.export_function("log", print)
        self.interp.export_function("querySelectorAll", self.querySelectorAll)
        self.interp.export_function("getAttribute", self.getAttribute)
        self.interp.export_function("innerHTML_set", self.innerHTML_set)
        self.interp.export_function("getChildren", self.getChildren)
        self.interp.export_function("createElement", self.createElement)
        self.interp.export_function("appendChild", self.appendChild)
        self.interp.export_function("insertBefore", self.insertBefore)
        self.interp.export_function("XMLHttpRequest_send", self.XMLHttpRequest_send)
        self.interp.export_function("get_cookies", self.getCookies)
        self.interp.export_function("set_cookies", self.setCookies)
        self.interp.evaljs(RUNTIME_JS)
        self.createIdNodes()
    def run(self, code):
        return self.interp.evaljs(code)
    def createIdNodes(self):
        for node in self.idList:
            jsString = "{} = new Node({})".format(node.attributes["id"], self.get_handle(node))
            self.interp.evaljs(jsString)
    def removeIdNodes(self, node):
        self.idList.remove(node)
        jsString = "delete {}".format(node.attributes["id"])
        self.interp.evaljs(jsString)
    def querySelectorAll(self, selector_test):
        selector = CSSParser(selector_test).selector()
        nodes = [node for node in tree_to_list(self.tab.nodes, [])
                 if selector.matches(node)]
        return [self.get_handle(node) for node in nodes]
    def get_handle(self, elt):
        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt
        else:
            handle = self.node_to_handle[elt]
        return handle
    def getAttribute(self, handle, attr):
        elt = self.handle_to_node[handle]
        attr = elt.attributes.get(attr, None)
        return attr if attr else ""
    def getChildren(self, handle):
        elt = self.handle_to_node[handle]
        elements = []
        for child in elt.children:
            if isinstance(child, Element):
                elements.append(self.get_handle(child))
        return elements
    def appendChild(self, parent_handle, child_handle):
        parent = self.handle_to_node[parent_handle]
        child = self.handle_to_node[child_handle]
        child.parent = parent
        parent.children.append(child)
        self.tab.render()
    def insertBefore(self, parent_handle, child_handle, sibling_handle = None):
        parent = self.handle_to_node[parent_handle]
        child = self.handle_to_node[child_handle]
        child.parent = parent
        if(sibling_handle):
            sibling = self.handle_to_node[sibling_handle]
            siblingIndex = parent.children.index(sibling)
            parent.children.insert(siblingIndex, child)
        else:
            parent.children.append(child)
        self.tab.render()
    def dispatch_event(self, type, elt):
        handle = self.node_to_handle.get(elt, -1)
        # self.interp.evaljs(
        #     EVENT_DISPATCH_JS, type=type, handle=handle)
        do_default = self.interp.evaljs(
            EVENT_DISPATCH_JS, type=type, handle=handle)
        return not do_default
    def createElement(self, tagName):
        elt = Element(tagName, {}, None)
        return self.get_handle(elt)
    def innerHTML_set(self, handle, s):
        doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
        new_nodes = doc.children[0].children
        elt = self.handle_to_node[handle]
        for child in tree_to_list(elt, []):
            if isinstance(child, Element):
                if "id" in child.attributes:
                    self.removeIdNodes(child)
        elt.children = new_nodes
        for child in tree_to_list(elt, []):
            if isinstance(child, Element):
                if "id" in child.attributes:
                    self.idList.append(child)
        for child in elt.children:
            child.parent = elt
        self.tab.render()
        self.createIdNodes()
    def XMLHttpRequest_send(self, method, url, body):
        full_url = self.tab.url.resolve(url)
        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-origin XHR blocked by CSP")
        if full_url.origin() != self.tab.url.origin():
            raise Exception("Cross-origin XHR request not allowed")
        _, out = full_url.request(top_level_url = self.tab.url, payload = body)
        return out
    def getCookies(self):
        cookies = COOKIE_JAR.get(self.tab.url.host, ("", {}))
        if "httponly" in cookies[1]:
            return ""
        return COOKIE_JAR.get(self.tab.url.host, ("", {}))[0]
    
    def setCookies(self, cookie):
        cookies = COOKIE_JAR.get(self.tab.url.host, ("", {}))
        if "httponly" in cookies[1]:
            return ""
        params = {}
        if ";" in cookie:
            cookie, rest = cookie.split(";", 1)
            for param in rest.split(";"):
                if '=' in param:
                    param, value = param.split("=", 1)
                else:
                    value = "true"
                params[param.strip().casefold()] = value.casefold()
        COOKIE_JAR[self.tab.url.host] = (cookie, params)
class Chrome:
    def __init__(self, browser):
        self.focus = None
        self.address_bat = ""
        self.browser = browser
        self.font = get_font(20, "normal", "roman", "Times")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding
        plus_width = self.font.measure("+") + 2*self.padding
        self.newtab_rect = Rect(
           self.padding, self.padding,
           self.padding + plus_width,
           self.padding + self.font_height)
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
            self.font_height + 2*self.padding
        self.bottom = self.urlbar_bottom
        back_width = self.font.measure("<") + 2*self.padding
        self.back_rect = Rect(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)

        self.address_rect = Rect(
            self.back_rect.top + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding * 2 - 20,
            self.urlbar_bottom - self.padding)
        self.bookmarks_rect = Rect(
            self.address_rect.right + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding
        )
    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2*self.padding
        return Rect(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i + 1), self.tabbar_bottom)
        
    def blur(self):
        self.focus = None
    
    def paint(self):
        cmds = []
        cmds.append(DrawRect(
            Rect(0, 0, WIDTH, self.bottom),
            "white"))
        cmds.append(DrawLine(Rect(
            0, self.bottom, WIDTH,
            self.bottom), "black", 1))
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(Rect(
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top,
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top),
            "+", self.font, "black"))
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(Rect(
                bounds.left, 0, bounds.left, bounds.bottom),
                "black", 1))
            cmds.append(DrawLine(Rect(
                bounds.right, 0, bounds.right, bounds.bottom),
                "black", 1))
            cmds.append(DrawText(Rect(
                bounds.left + self.padding, bounds.top + self.padding,
                bounds.left + self.padding, bounds.top + self.padding),
                "Tab {}".format(i), self.font, "black"))
            if tab == self.browser.active_tab:
                cmds.append(DrawLine(Rect(
                    0, bounds.bottom, bounds.left, bounds.bottom),
                    "black", 1))
                cmds.append(DrawLine(Rect(
                    bounds.right, bounds.bottom, WIDTH, bounds.bottom),
                    "black", 1))
        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(Rect(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            self.back_rect.left + self.padding,
            self.back_rect.top),
            "<", self.font, "black"))
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        if self.focus == "address bar":
            cmds.append(DrawText(Rect(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_rect.left + self.padding,
                self.address_rect.top),
                self.address_bar, self.font, "black"))
            w = self.font.measure(self.address_bar)
            cmds.append(DrawLine(Rect(
                self.address_rect.left + self.padding + w,
                self.address_rect.top,
                self.address_rect.left + self.padding + w,
                self.address_rect.bottom),
                "red", 1))
        else:
            url = str(self.browser.active_tab.url)
            if self.browser.active_tab.url.scheme == "https" and "ssl failed" not in self.browser.active_tab.headers:
                url = "\N{lock}" + url
            cmds.append(DrawText(Rect(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_rect.left + self.padding,
                self.address_rect.top),
                url, self.font, "black"))
            
        #draw bookmarks button
        if str(self.browser.active_tab.url) in self.browser.bookmarks:
            cmds.append(DrawRect(self.bookmarks_rect, "yellow"))
        cmds.append(DrawOutline(self.bookmarks_rect, "black", 1))
        #Left side of bookmark icon
        cmds.append(DrawLine(Rect(
            self.address_rect.right + self.padding * 2,
            self.urlbar_top + self.padding * 2,
            self.address_rect.right + self.padding * 2,
            self.urlbar_bottom - self.padding * 2),
            "black", 1))
        #Right side of bookmark icon
        cmds.append(DrawLine(Rect(
            self.address_rect.right + self.padding * 4,
            self.urlbar_top + self.padding * 2,
            self.address_rect.right + self.padding * 4,
            self.urlbar_bottom - self.padding * 2),
            "black", 1))
        #Top side of bookmark icon
        cmds.append(DrawLine(Rect(
            self.address_rect.right + self.padding * 2,
            self.urlbar_top + self.padding * 2,
            self.address_rect.right + self.padding * 4,
            self.urlbar_top + self.padding * 2),
            "black", 1))
        #Left slant of bookmark icon
        cmds.append(DrawLine(Rect(
            self.address_rect.right + self.padding * 2,
            self.urlbar_bottom - self.padding * 2,
            self.address_rect.right + self.padding * 3,
            self.urlbar_top + self.padding * 4),
            "black", 1))
        #Right slant of bookmark icon
        cmds.append(DrawLine(Rect(
            self.address_rect.right + self.padding * 4,
            self.urlbar_bottom - self.padding * 2,
            self.address_rect.right + self.padding * 3,
            self.urlbar_top + self.padding * 4),
            "black", 1))
        return cmds
    
    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char
            return True
        return False
            
    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None
            
    def back(self):
        if self.focus == "address bar":
            self.address_bar = self.address_bar[:-1]
            
    def click(self, x, y):
        self.focus = None
        if self.newtab_rect.containsPoint(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))
        elif self.back_rect.containsPoint(x, y):
            self.browser.active_tab.go_back()
        elif self.address_rect.containsPoint(x, y):
            self.focus = "address bar"
            self.address_bar = ""
        elif self.bookmarks_rect.containsPoint(x, y):
            if str(self.browser.active_tab.url) in self.browser.bookmarks:
                self.browser.bookmarks.remove(str(self.browser.active_tab.url))
            else:
                self.browser.bookmarks.append(str(self.browser.active_tab.url))
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).containsPoint(x, y):
                    self.browser.active_tab = tab
                    break

class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
    def __repr__(self):
        return "Rect({}, {}, {}, {})".format(
            self.left,
            self.top,
            self.right,
            self.bottom
        )
        
    def containsPoint(self, x, y):
        return x >= self.left and x < self.right \
            and y >= self.top and y < self.bottom

class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color)

class DrawLine:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness)
        
class InputLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.children = []
        self.parent = parent
        self.previous = previous
        self.type = self.node.attributes.get("type", "")
    def __repr__(self):
        return "InputLayout(x={}, y={}, width={}, height={}, tag={})".format(
            self.x, self.y, self.width, self.height, self.node.tag)
    def layout(self):
        family = self.node.style["font-family"]
        self.color = self.node.style["color"]
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style, family)
        
        if self.node.tag == "input" and self.type == "hidden":
            self.width = float(0)
        else:
            self.width = INPUT_WIDTH_PX
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x
        if self.node.tag == "input" and self.type == "hidden":
            self.height = float(0)
        else:
            self.height = self.font.metrics("linespace")
        
    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)
    
    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color", "transparent")
        color = self.node.style["color"]
        if self.type == "hidden":
                return cmds
        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
            if self.type == "password":
                text = "*"*len(text)
        elif self.node.tag == "button":
            if len(self.node.children) == 1 and \
                isinstance(self.node.children[0], Text):
                    text = self.node.children[0].text
            else:
                print("Ignoring HTML contents inside button")
                text = ""
        if self.node.is_focused:
            cx = self.x + self.font.measure(text)
            cmds.append(DrawLine(Rect(
                cx, self.y, cx, self.y + self.height), "black", 1))
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        cmds.append(DrawText(Rect(self.x, self.y, self.x, self.y), text, self.font, color))
        return cmds
    def should_paint(self):
        return True

class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0
        
    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1
            
    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]
    
    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("parsing error")
        self.i += 1
        
    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        if prop.casefold() == "font":
            i = self.i
            self.ignore_until(["}",";"])
            val = self.s[i:self.i].strip()
        else:
            val = self.word()
        return prop.casefold(), val
    
    def body(self):
        # print("GOT TO BODY")
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                prop = prop.casefold()
                if prop == "font":
                    split = val.split(" ")
                    if(len(split)) == 1:
                        pairs["font-family"] = split[0]
                    elif(len(split)) == 2:
                        pairs["font-size"] = split[0]
                        pairs["font-family"] = split[1]
                    elif(len(split)) == 3:
                        if(split[0] == "italic"):
                            pairs["font-style"] = split[0]
                        else:
                            pairs["font-weight"] = split[0]
                        pairs["font-size"] = split[1]
                        pairs["font-family"] = split[2]
                    elif(len(split)) == 4:
                        pairs["font-style"] = split[0]
                        pairs["font-weight"] = split[1]
                        pairs["font-size"] = split[2]
                        pairs["font-family"] = split[3]
                    elif(len(split)) > 4:
                        pairs["font-style"] = split[0]
                        pairs["font-weight"] = split[1]
                        pairs["font-size"] = split[2]
                        font_family = " ".join(split[3:])
                        pairs["font-family"] = font_family
                else:
                    pairs[prop.casefold()] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs
    
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None
    
    def selector(self):
        # print("Got to selector")
        word = self.word()
        # print('word: ', word)
        out = TagSelector(word.casefold())
        if out.tag[0] == ".":
            out = ClassSelector(word[1:])
        else:
            out = TagSelector(word.casefold())
        # print("Got response from word in selector:", out)
        self.whitespace()
        # print("GOT HERE")
        while self.i < len(self.s) and self.s[self.i] != "{":
            # print("NOW HERE")
            tag = self.word()
            if tag[0] == ".":
                descendant = ClassSelector(tag[1:])
            else:
                descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        # print('out: ', out)
        return out
    
    def parse(self):
        # print("Got to parse")
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules

def style(node, rules):
    node.style = {}
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent and property in node.parent.style:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value
    for selector, body in rules:
        if isinstance(node, Text): continue
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            node.style[property] = value
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"
    for child in node.children:
        style(child, rules)
        
def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list
        
class TagSelector:
    def __init__(self, tag):
        # print("Got to tagSelector constructor")
        self.tag = tag
        self.priority = 1
    def __repr__(self):
        return "TagSelector(tag={}, priority={})".format(
            self.tag, self.priority)
    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag
    
class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority
    def __repr__(self):
        return ("DescendantSelector(ancestor={}, descendant={}, priority={})") \
            .format(self.ancestor, self.descendant, self.priority)
    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False

def cascade_priority(rule):
    selector, body = rule
    return selector.priority

class URL:
    def __init__(self, url):
        #parse URL into components
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "about"]
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        elif self.scheme == "file":
            self.path = url
            return
        elif self.scheme == "":
            self.path = "testFile.txt"
            return
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        self.path = "/" + url
        
        if self.scheme == "about":
            self.port = "None"
            self.host = "None"
            self.path = "bookmarks"
        
        self.fragment = None
        if "#" in self.path:
            self.path, self.fragment = self.path.split("#", 1)
        
        self.referrer_policy = None
        
    def __repr__(self):
        fragment_part = "" if self.fragment == None else ", fragment=" + self.fragment
        return "URL(scheme={}, host={}, port={}, path={!r}{})".format(
            self.scheme, self.host, self.port, self.path, fragment_part)
    
    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        if self.fragment != None:
            return self.scheme + "://" + self.host + port_part + self.path + "#" + self.fragment
        else:
            return self.scheme + "://" + self.host + port_part + self.path

    def readFromFile(self, url):
        body = open(r'{}'.format(url), 'r')
        return body.read()
    
    def origin(self):
        return self.scheme + "://" + self.host + ":" + str(self.port)
    
    def request(self, top_level_url, browser=None, headers=None, payload=None, method=None):
        if self.scheme == "file":
            return URL.readFromFile(self, self.path)
        if self.scheme == "about":
            httpString = "<!doctype html>"
            for bookmark in browser.bookmarks:
                httpString += f"<a href=\"{bookmark}\">{bookmark}</a><br>"
            return httpString
        url = f"{self.scheme}://{self.host}{self.port}{self.path}"

        if url in CACHE.keys():
            #check for expiration
            ct = datetime.datetime.now()
            st = CACHE[url][2]
            timeDifference = ct - st
            secDifference = timeDifference.total_seconds()
            #print(f"Found {url} in cache. It has been cached for {secDifference} seconds. Its lifespan is {cache[url][1]}.")
            if secDifference <= CACHE[url][1]:
                return CACHE[url][0]
            else:
                #if cache entry is expired, remove it from the cache
                del CACHE[url]

        #create a socket
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        #connect to server and sent a request
        s.connect((self.host, self.port))
        
        if self.scheme == "https":
            try:
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            except:
                return {"ssl failed": "yes"}, "<!doctype html>\n Secure Connection Failed"

        #initialize sendData
        # sendData = ("GET {} HTTP/1.1\r\n".format(self.path))
        if method == None:
            method = "POST" if payload else "GET"
        body = "{} {} HTTP/1.0\r\n".format(method, self.path)
        if method == "GET":
            headerData = {"host": "{}".format(self.host), "connection" : "close", "user-agent" : "iguana"}
            if headers != None:
                #headerData = {}
                for key, value in headers.items():
                    headerData[key.lower()] = value
            for key, value in headerData.items():
                body += key.casefold() + ": " + value + "\r\n"
        if payload:
            length = len(payload.encode("UTF8"))
            body += "Content-Length: {}\r\n".format(length)
        if self.host in COOKIE_JAR:
            cookie, params = COOKIE_JAR[self.host]
            allow_cookie = True
            if top_level_url and params.get("samesite", "none") == "lax":
                if method != "GET":
                    allow_cookie = self.host == top_level_url.host
            if allow_cookie:
                body += "Cookie: {}\r\n".format(cookie)
        should_send_referrer = True
        if top_level_url.referrer_policy:
            if top_level_url.referrer_policy == "no-referrer":
                should_send_referrer = False
            elif top_level_url.referrer_policy == "same-origin":
                if top_level_url.origin() == self.origin():
                    should_send_referrer = True
                else:
                    should_send_referrer = False
        
        if should_send_referrer:
            body += "Referer: {}\r\n".format(top_level_url)
        body += "\r\n" + (payload if payload else "")
        s.send(body.encode("utf8"))
        #read response from server
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        # print("STATUSLINE:", statusline)
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            #make headers lowercase and strip whitespace from values
            response_headers[header.casefold()] = value.strip()
        #check for a redirect code
        if "set-cookie" in response_headers:
            cookie = response_headers["set-cookie"]
            params = {}
            if ";" in cookie:
                cookie, rest = cookie.split(";", 1)
                for param in rest.split(";"):
                    if '=' in param:
                        param, value = param.split("=", 1)
                    else:
                        value = "true"
                    params[param.strip().casefold()] = value.casefold()
            COOKIE_JAR[self.host] = (cookie, params)
        if "referrer-policy" in response_headers:
            top_level_url.referrer_policy = response_headers["referrer-policy"]
        if status[0] == '3':
            redirectLocation = response_headers["location"]
            if "://" not in redirectLocation:
                redirectLocation = self.scheme + "://" + self.host + redirectLocation
            _, redirect = (URL(redirectLocation)).request(top_level_url = self.url, browser = browser)
            return redirect
        
        assert "transfer-encoding" not in response_headers
        assert "conent-encoding" not in response_headers
        body = response.read()

        #check for caching
        if status == "200":
            if "cache-control" in response_headers:
                cacheControlVal = response_headers["cache-control"]
                if cacheControlVal.startswith("max-age"):
                    parts = cacheControlVal.split("max-age=")
                    #store the body, max age, and current timestamp in the cache
                    #print(f"Caching {body} at {datetime.datetime.now()} for {parts[1]} seconds.")
                    CACHE[url] = (body, int(parts[1]), datetime.datetime.now())

        #now that the response has been received, close the connection
        s.close()
        return response_headers, body
    
    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + \
                ":" + str(self.port) + url)
    
class Text:
    def __init__(self,text):
        self.text = text
        self.is_focused = False
    def __repr__(self):
        return "Text('{}')".format(self.text)

class Tag:
    def __init__(self, tag):
        self.tag = tag
    def __repr__(self):
        return "Tag('{}')".format(self.tag)
    
class ClassSelector:
    def __init__(self, className):
        self.classname = className
        self.priority = 10
    def __repr__(self):
        return "ClassSelector(classname={}, priority={})".format(
            self.classname, self.priority)
    def matches(self, node):
        nodeClass = node.attributes.get("class", "")
        splitNodeClass = nodeClass.split()
        return isinstance(node, Element) and self.classname in splitNodeClass
class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x = 0
        # print('self.x in document layout init: ', self.x)
        self.y = 0
        self.width = None
        self.height = None
        # self.display_list = []
    
    def __repr__(self):
        return "DocumentLayout()"
    
    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        # self.display_list = child.display_list
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        # print('self.x in document layout layout : ', self.x)
        self.y = VSTEP
        child.layout()
        self.height = child.height
    def paint(self):
        return []
    def should_paint(self):
        return True
   
class BlockLayout:
    def __init__(self, node, parent, previous):
        self.heightOfFirstLine = 0
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        # self.display_list = []
        self.x = None
        # print('self.x in block init: ', self.x)
        self.y = None
        self.width = None
        self.height = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.centered = False
        self.super = False
        self.abbr = False

        self.line = []
        
    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

    def layout_intermediate(self):
        previous = None
        for child in self.node.children:
            next = BlockLayout(child, self, previous)
            self.children.append(next)
            previous = next
            
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and 
                  child.tag in BLOCK_ELEMENTS
                  for child in self.node.children]):
            return "block"
        elif self.node.children or self.node.tag == "input":
            return "inline"
        else:
            return "block"
        
    def layout(self):
        mode = self.layout_mode()
        self.x = self.parent.x
        # print('self.x in block layout layout: ', self.x)
        self.width = self.parent.width
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        if mode == "block":
            previous = None
            for child in self.node.children:
                #print("CURRENT CHILD:", child)
                if isinstance(child, Element) and child.tag == "head":
                    continue
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.cursor_x = 0
            self.cursor_y = 0
            self.line = []
            self.new_line()
            self.recurse(self.node)
            # self.flush()
        if isinstance(self.node, Element) and self.node.tag == "li":
                    self.x = self.parent.x + (2 * HSTEP)
                    self.width = self.parent.width - (2 * HSTEP)
        else:
            width = self.node.style.get("width", "auto")
            self.x = self.parent.x
            if width == "auto":
                self.width = self.parent.width
            else:
                widthAsFloat = float(width[:-2])
                if widthAsFloat < 0:
                    self.width = self.parent.width
                else:
                    self.width = widthAsFloat
        for child in self.children:
            child.layout()
        # if mode == "block":
        self.height = sum([child.height for child in self.children])
        # else:
        #     height = self.node.style.get("height", "auto")
        #     if height == "auto":
        #         self.height = self.cursor_y
        #     else:
        #         self.height = float(height[:-2])
        # for child in self.children:
            # self.display_list.extend(child.display_list)
            
    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)
        
    def paint(self):
        cmds = []
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        if isinstance(self.node, Element) and self.node.tag == "li":
            # print("drawing rect")
            rect = DrawRect(Rect(self.x - HSTEP - 2, self.y + (self.heightOfFirstLine / 2 - 2), 
                            self.x - HSTEP + 2, self.y + 4 + (self.heightOfFirstLine / 2 - 2)), "black")
            cmds.append(rect)
        if isinstance(self.node, Element) and self.node.tag == "nav" and \
        "class" in self.node.attributes and "links" in self.node.attributes["class"]:
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.self_rect(), "lightgray")
            cmds.append(rect)
        if self.layout_mode() == "inline":
            #TODO: Put lists back in
            # if isinstance(self.node, Element) and self.node.tag == "li":
            #     # print("got here")
            #     # for x, y, word, font, color in self.display_list:
            #     #     cmds.append(DrawText(x + 2 * HSTEP, y, word, font, color))
            # else:
            #     for x, y, word, font, color in self.display_list:
            #         # print("node tag:", self.node.tag, "word:", word)
            #         cmds.append(DrawText(x, y, word, font, color))
            for child in self.children:
                    child.paint()
        return cmds
    
    def should_paint(self):
        return isinstance(self.node, Text) or \
            (self.node.tag != "input" and self.node.tag != "button")
        
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            elif node.tag == "input" or node.tag == "button":
                self.input(node)
            else:
                for child in node.children:
                    self.recurse(child)
                
    def word(self, node, word):
        family = node.style["font-family"]
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style, family)
        if self.abbr:
            #print("ORIGINAL FONT SIZE:", self.size)
            buffer = ""
            isLower = False
            for c in word:
                if c.islower() == isLower:
                    #print("First", buffer, c)
                    buffer += c.upper()
                    continue
                if c.islower():
                    if len(buffer) > 0:
                        #print("Second", buffer, c)
                        self.line.append((self.cursor_x, buffer, font, self.super, color))
                        self.cursor_x += font.measure(buffer)
                        font = get_font(size//2, "bold", style, family)
                        buffer = c.upper()
                    else:
                        #print("Third", buffer, c)
                        font = get_font(size//2, "bold", style, family)
                        buffer += c.upper()
                    isLower = True
                else:
                    #print("Fourth", buffer, c)
                    self.line.append((self.cursor_x, buffer, font, self.super, color))
                    self.cursor_x += font.measure(buffer)
                    font = get_font(size, weight, style, family)
                    buffer = c
                    isLower = False
            #print("Fifth", buffer, c)
            self.line.append((self.cursor_x, buffer, font, self.super, color))
            w = font.measure(word)
            font = get_font(size, weight, style, family)
            #print("ADDING SPACE IN SIZE", self.size)
            self.cursor_x += w + font.measure(" ")
        else:
            w = font.measure(word)
            if self.cursor_x + w > self.width:
                self.new_line()
                if "\N{soft hyphen}" in word:
                    wordBuffer = ""
                    parts = word.split("\N{soft hyphen}")
                    for part in parts:
                        #print("CURRENT PART:", part, "CURRENT BUFFER:", wordBuffer)
                        if self.cursor_x + font.measure(wordBuffer + part + "-") <= WIDTH - HSTEP:
                            #print("PART FITS ON LINE, ADDING TO BUFFER")
                            wordBuffer += part
                        else:
                            #print("PART DOESN'T FIT ON LINE, CALLING FLUSH")
                            self.word(wordBuffer + "-")
                            self.new_line()
                            wordBuffer = part
                    self.word(wordBuffer)
                    return
                self.new_line()
            # self.line.append((self.cursor_x, word, font, self.super, color))
            line = self.children[-1]
            previous_word = line.children[-1] if line.children else None
            text = TextLayout(node, word, line, previous_word)
            line.children.append(text)
            self.cursor_x += w + font.measure(" ")
            
    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)
    
    def input(self, node):
        w = INPUT_WIDTH_PX
        if self.cursor_x + w > self.width:
            self.new_line()
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        input = InputLayout(node, line, previous_word)
        line.children.append(input)

        family = self.node.style["font-family"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style, family)

        self.cursor_x += w + font.measure(" ")
        
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        
        for word in self.children:
            word.layout()
        if not self.children:
            max_ascent = 10
        else:
            max_ascent = max([word.font.metrics("ascent")
                        for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        if not self.children:
            max_ascent = 10
        else:
            max_descent = max([word.font.metrics("descent")
                            for word in self.children])
        #added from discord
        if not self.children:
            self.height = 0
            return
        self.height = 1.25 * (max_ascent + max_descent)
    def paint(self):
        return []
    def should_paint(self):
        return True
        
class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
    def __repr__(self):
        return ("TextLayout(x={}, y={}, width={}, height={}, word={})").format(
            self.x, self.y, self.width, self.height, self.word)
    def layout(self):
        family = self.node.style["font-family"]
        self.color = self.node.style["color"]
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style, family)
        
        self.width = self.font.measure(self.word)
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")
    def paint(self):
        return [DrawText(Rect(self.x, self.y, self.x, self.y), self.word, self.font, self.color)]
    def should_paint(self):
        return True
    

def paint_tree(layout_object, display_list):
    if layout_object.should_paint():
        display_list.extend(layout_object.paint())
    for child in layout_object.children:
        paint_tree(child, display_list)

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
    def __repr__(self):
        return repr(self.text)

class DrawText:
    def __init__(self, rect, text, font, color):
        self.rect = rect
        self.top = self.rect.top
        self.left = self.rect.left
        self.text = text
        self.font = font
        self.color = color
        self.bottom = self.rect.bottom + font.metrics("linespace")
        
    def __repr__(self):
        return "DrawText(top={} left={} bottom={} text={} font={})" \
            .format(self.top, self.left, self.bottom, self.text, self.font)
            
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            fill = self.color,
            anchor='nw'
        )

class DrawRect:
    def __init__(self, rect, color):
        self.rect = rect
        self.top = self.rect.top
        self.left = self.rect.left
        self.bottom = self.rect.bottom
        self.right = self.rect.right
        self.color = color
        
    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.top, self.left, self.bottom, self.right, self.color)
    
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color
        )

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.is_focused = False
    def __repr__(self):
        if len(self.attributes) == 0:
            return "<" + self.tag + ">"
        else:
            stringBuilder = "<" + self.tag
            for key in self.attributes.keys():
                stringBuilder += " " + key + "=\"" + self.attributes[key] + "\""
            stringBuilder += ">"
            return stringBuilder
class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []
        self.SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
        ]
        self.HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
        ]
    def get_attributes(self, text):
        # print("called get on:", text)
        in_key = False
        in_value = False
        in_dquotes = False
        in_squotes = False
        in_start = True
        # parts = text.split()
        # print(parts)
        parts = []
        partBuffer = ""
        for c in text:
            # print("Looking at c:", c, "Buffer:", partBuffer, "In key:", in_key, "In value:", in_value)
            if c == " ":
                if not in_key and not in_value:
                    in_key = True
                    parts.append(partBuffer)
                    partBuffer = ""
                elif in_dquotes or in_squotes:
                    partBuffer += c
                else:
                    if in_value and not in_squotes and not in_dquotes:
                        in_value = False
                        in_key = True
                    parts.append(partBuffer)
                    partBuffer = ""
            elif c == "=":
                if in_key:
                    in_key = False
                    in_value = True
                partBuffer += c
            elif c == "\"":
                # alt='Les "Horribles" Cernettes'
                # alt="Hello"
                if not in_squotes:
                    #not in ' ', test for double quotes
                    if not in_dquotes:
                        #not in " " either, start a new quote block
                        in_dquotes = True
                    else:
                        in_dquotes = False
                        in_key = True
                        in_value = False
                        parts.append(partBuffer)
                        partBuffer = ""
                else:
                    #is in ' ', treat like a regular character
                    partBuffer += c
            elif c == "\'":
                if not in_dquotes:
                    #not in " ", test for double quotes
                    if not in_squotes:
                        #not in ' ' either, start a new quote block
                        in_squotes = True
                    else:
                        in_squotes = False
                        in_key = True
                        in_value = False
                        parts.append(partBuffer)
                        partBuffer = ""
                else:
                    #is in " ", treat like a regular character
                    partBuffer += c
            else:
                # print("Adding letter:", c, "In value:", in_value, "In key:", in_key)
                partBuffer += c
        if partBuffer:
            parts.append(partBuffer)
        #print("PARTS:", parts)

        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            # print("Pair:", attrpair)
            if "=" in attrpair:
                # print("1")
                key, value = attrpair.split("=", 1)
                attributes[key.casefold()] = value
                if len(value) > 2 and value[0] in ["'", "\""]:
                    # print("2")
                    value = value[1:-1]
            # elif attrpair == "":
            #     print("3")
            #     continue
            # else:
            #     print("4")
            #     attributes[attrpair.casefold()] = ""
        return tag, attributes
    def parse(self):
        text = ""
        in_tag = False
        inComment = False
        counter = 0
        in_script = False
        for i, c in enumerate(self.body):
            # print("examining", c)
            # if c == "\/"" or c ==" ":
                # print(in_tag, inComment, counter, in_script)
            if in_script:
                if c == "<":
                    if self.body[i+1:i+9] == "/script>":
                        in_tag = True
                        in_script = False
                        if text:
                            self.add_text(text)
                        text = ""
                    else:
                        text += c
                else:
                    text += c
            else:
                if counter > 0:
                    counter -= 1
                    continue
                if c == "<":
                    if self.body[i+1:i+4] == "!--":
                        counter = 5
                        inComment = True
                    in_tag = True
                    if text:
                        self.add_text(text)
                    text = ""
                elif c == ">":
                    if self.body[i-2:i] == "--":
                        inComment = False
                        if self.body[i-4:i-2] == "<!":
                            continue
                    elif not inComment and in_tag:
                        if text == "script":
                            in_script = True
                        elif text == "/script":
                            in_script = False
                        self.add_tag(text)
                        text = ""
                    in_tag = False
                else:
                    if not inComment:
                        text += c
        
        if not in_tag and text:
            self.add_text(text)
        return self.finish()
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)
    def add_tag(self, tag):
        unfinishedBuffer = []
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            if tag == "p":
                for i, unfinished_tag in enumerate(self.unfinished):
                    if unfinished_tag.tag == "p":
                        if i == len(self.unfinished)-1:
                            u_parent = self.unfinished[i-1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished
                        else:
                            for j in range(len(self.unfinished)-1, i, -1):
                                u_parent = self.unfinished[j-1]
                                u_parent.children.append(self.unfinished[j])
                                unfinished = self.unfinished[j]
                                unfinishedBuffer.append(Element(unfinished.tag, unfinished.attributes, unfinished.parent))
                                del self.unfinished[j]
                            u_parent = self.unfinished[i-1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished[i]
                        #u_parent = self.unfinished[i-1]
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)
            while unfinishedBuffer:
                self.unfinished.append(unfinishedBuffer.pop())
    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

def get_font(size, weight, slant, family):
    key = (size, weight, slant, family)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant, family=family)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        Browser().new_tab(URL("https://browser.engineering"))
    else:
        Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
    
